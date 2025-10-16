from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import shutil
import logging
import base64
import math
from datetime import date, timedelta
from pathlib import Path

from AgentModule import create_agent
from AgentModule.edu_agent import run_agent
from LearningPlanModule import LearningPlan
from QuizModule import generate_learning_plan_from_quiz, prepare_quiz_questions
from SummaryModule import StudySummaryGenerator
from tools.language_handler import LanguageHandler
from tools.rag_service import get_rag_service
from tools.covert_resource import convert_to_pdf

app = FastAPI(title="AI-Education API")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# 全局变量
rag_service = get_rag_service()
retriever = rag_service.get_retriever()
logger = logging.getLogger(__name__)
KNOWLEDGE_JSON_PATH = "data/course/big_data.json"
CURRENT_NODE = None
CURRENT_PDF_PATH = None  # 追踪当前选择的PDF


# Pydantic 模型
class ChatMessage(BaseModel):
    message: str
    history: List[List[str]] = []
    lang_choice: str = "auto"


class QuizStart(BaseModel):
    subject: str
    lang_choice: str = "auto"


class QuizAnswer(BaseModel):
    choice: str
    state: Dict[str, Any]


class LearningPlanRequest(BaseModel):
    name: str
    goals: str
    lang_choice: str = "auto"


class LearningPlanFromQuiz(BaseModel):
    name: str
    state: Dict[str, Any]
    lang_choice: str = "auto"


class SummaryRequest(BaseModel):
    topic: str
    lang_choice: str = "auto"


class NodeSelection(BaseModel):
    node_name: str


class PDFSelection(BaseModel):
    pdf_path: str


# API 路由
@app.get("/")
async def root():
    return FileResponse("backend/static/index.html")


@app.post("/api/chat")
async def chat(data: ChatMessage):
    """处理聊天消息 - 启用RAG检索"""
    global CURRENT_PDF_PATH
    message = data.message
    history = data.history
    lang_choice = data.lang_choice

    logger.info(f"📨 Chat request: {message[:50]}...")
    logger.info(f"📄 Current PDF: {CURRENT_PDF_PATH}")

    internal_history = []
    for user_msg, assistant_msg in history:
        internal_history.append({"role": "user", "content": user_msg})
        if assistant_msg:
            internal_history.append({"role": "assistant", "content": assistant_msg})

    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(message)

    # 创建针对当前PDF的retriever
    current_retriever = None
    if CURRENT_PDF_PATH and os.path.exists(CURRENT_PDF_PATH):
        from langchain_core.vectorstores import VectorStoreRetriever
        from langchain_core.callbacks import CallbackManagerForRetrieverRun

        class FilteredRetriever(VectorStoreRetriever):
            """只检索当前PDF的retriever"""

            pdf_path: str

            def _get_relevant_documents(
                self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
            ):
                # 获取向量存储
                vectorstore = rag_service._get_vectorstore()
                # 使用metadata过滤，只检索当前PDF
                docs = vectorstore.similarity_search(
                    query, k=4, filter={"source": self.pdf_path}
                )
                logger.info(
                    f"🔍 Filtered retrieval: found {len(docs)} docs from {self.pdf_path}"
                )
                return docs

        # 创建过滤后的retriever
        current_retriever = FilteredRetriever(
            vectorstore=rag_service._get_vectorstore(),
            search_kwargs={"k": 4},
            pdf_path=CURRENT_PDF_PATH,
        )
        logger.info(f"✅ Created filtered retriever for: {CURRENT_PDF_PATH}")
    else:
        current_retriever = retriever
        logger.info(f"⚠️ No current PDF, using global retriever")

    agent = create_agent()
    result, used_fallback, used_retriever = run_agent(
        message, executor=agent, retriever=current_retriever, return_details=True
    )

    logger.info(
        f"✅ Response generated. Used RAG: {used_retriever}, Fallback: {used_fallback}"
    )

    result = LanguageHandler.ensure_language(result, language)

    return {
        "response": result,
        "used_fallback": used_fallback,
        "used_retriever": used_retriever,
    }


@app.post("/api/quiz/start")
async def start_quiz(data: QuizStart):
    """开始测验"""
    code = LanguageHandler.code_from_display(data.lang_choice)
    language = (
        code if code != "auto" else LanguageHandler.choose_or_detect(data.subject)
    )
    questions, used_retriever = prepare_quiz_questions(
        data.subject, language=language, retriever=retriever
    )

    if not questions:
        raise HTTPException(status_code=400, detail="Failed to generate quiz")

    state = {
        "subject": data.subject,
        "language": language,
        "questions": questions,
        "index": 0,
        "scores": {},
        "correct_total": 0,
    }

    first_q = questions[0]
    return {"question": first_q, "state": state, "used_retriever": used_retriever}


@app.post("/api/quiz/answer")
async def answer_quiz(data: QuizAnswer):
    """回答测验问题"""
    state = data.state
    choice = data.choice.lower()

    if not state or state.get("index") is None:
        raise HTTPException(status_code=400, detail="Quiz not started")

    idx = state["index"]
    questions = state["questions"]

    if idx >= len(questions):
        return {"finished": True, "results": _compile_results(state)}

    current = questions[idx]
    topic = current["topic"]
    correct = current["correct"]

    if topic not in state["scores"]:
        state["scores"][topic] = [0, 0]

    state["scores"][topic][1] += 1

    if choice == correct or correct == "?":
        state["scores"][topic][0] += 1
        state["correct_total"] += 1
        is_correct = True
    else:
        is_correct = False

    state["index"] += 1

    if state["index"] >= len(questions):
        return {
            "finished": True,
            "is_correct": is_correct,
            "correct_answer": correct,
            "results": _compile_results(state),
            "state": state,
        }

    next_q = questions[state["index"]]
    return {
        "finished": False,
        "is_correct": is_correct,
        "correct_answer": correct,
        "next_question": next_q,
        "state": state,
    }


def _compile_results(state: Dict) -> str:
    lines = []
    total_questions = 0
    total_correct = state.get("correct_total", 0)

    for topic, (corr, tot) in state.get("scores", {}).items():
        perc = (corr / tot) * 100 if tot else 0
        lines.append(f"{topic}: {corr}/{tot} ({perc:.2f}%)")
        total_questions += tot

    if lines:
        overall = sum(
            (corr / tot) * 100 if tot else 0 for corr, tot in state["scores"].values()
        )
        overall /= len(state["scores"])
        lines.append(
            f"\nOverall Score: {total_correct}/{total_questions} ({overall:.2f}%)"
        )

    result = "\n".join(lines)
    lang = state.get("language", "auto")
    return LanguageHandler.ensure_language(result, lang)


@app.post("/api/learning-plan")
async def create_learning_plan(data: LearningPlanRequest):
    """生成学习计划"""
    code = LanguageHandler.code_from_display(data.lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(data.goals)

    plan = LearningPlan(user_name=data.name, user_language=language)
    goals_list = [g.strip() for g in data.goals.split(";") if g.strip()]
    user_input = {"goals": goals_list}

    plan.generate_plan_from_prompt(user_input)
    plan.save_to_file()

    return {
        "message": "Learning plan generated successfully",
        "plan": plan.learning_plan,
    }


@app.post("/api/learning-plan/from-quiz")
async def create_learning_plan_from_quiz(data: LearningPlanFromQuiz):
    """根据测验结果生成学习计划"""
    if not data.state or not data.state.get("scores"):
        raise HTTPException(status_code=400, detail="No quiz results available")

    code = LanguageHandler.code_from_display(data.lang_choice)
    language = code if code != "auto" else data.state.get("language", "en")

    plan = LearningPlan(
        user_name=data.name, quiz_results=data.state["scores"], user_language=language
    )
    generated_plan = plan.generate_plan()
    plan.save_to_file()

    return {
        "message": "Learning plan generated from quiz results",
        "plan": generated_plan,
    }


@app.post("/api/summary")
async def generate_summary(data: SummaryRequest):
    """生成知识总结"""
    code = LanguageHandler.code_from_display(data.lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(data.topic)

    summarizer = StudySummaryGenerator(retriever=retriever)
    summary, used_retriever = summarizer.generate_summary(
        data.topic, language=language, retriever=retriever
    )

    return {"summary": summary, "used_retriever": used_retriever}


@app.get("/api/knowledge-graph")
async def get_knowledge_graph():
    """获取知识图谱数据"""
    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {}


@app.get("/api/learning-nodes")
async def get_learning_nodes():
    """获取所有学习节点"""
    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        return []

    learning_nodes = []
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            learning_nodes.append(grandchild.get("name"))
            for great_grandchild in grandchild.get("great-grandchildren", []):
                learning_nodes.append(great_grandchild.get("name"))

    return learning_nodes


@app.post("/api/node/resources")
async def get_node_resources(data: NodeSelection):
    """获取节点资源"""
    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        return []

    resources = find_resources_for_node(data.node_name, graph_data)
    return resources


def find_resources_for_node(node_name: str, graph_data: dict) -> list:
    """查找指定节点的资源"""
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            if grandchild.get("name") == node_name:
                resources = grandchild.get("resource_path", [])
                return resources if isinstance(resources, list) else []

            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == node_name:
                    resources = great_grandchild.get("resource_path", [])
                    return resources if isinstance(resources, list) else []

    return []


@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...), node_name: str = ""):
    """上传文件到指定节点"""
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    if not node_name:
        raise HTTPException(status_code=400, detail="No node selected")

    save_dir = Path("data/RAG_files")
    save_dir.mkdir(parents=True, exist_ok=True)

    supported_conversion_exts = [".doc", ".docx", ".ppt", ".pptx"]
    newly_added_paths = []

    for file in files:
        filename = file.filename
        file_ext = Path(filename).suffix.lower()
        temp_path = save_dir / filename

        # 保存上传的文件
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if file_ext == ".pdf":
            newly_added_paths.append(str(temp_path))
        elif file_ext in supported_conversion_exts:
            pdf_path = convert_to_pdf(str(temp_path), str(save_dir))
            if pdf_path:
                newly_added_paths.append(pdf_path)

    if not newly_added_paths:
        raise HTTPException(status_code=400, detail="No valid files processed")

    # 更新 JSON
    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")

    updated = False
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            if grandchild.get("name") == node_name:
                if "resource_path" not in grandchild:
                    grandchild["resource_path"] = []
                grandchild["resource_path"].extend(newly_added_paths)
                updated = True
                break

            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == node_name:
                    if "resource_path" not in great_grandchild:
                        great_grandchild["resource_path"] = []
                    great_grandchild["resource_path"].extend(newly_added_paths)
                    updated = True
                    break

            if updated:
                break
        if updated:
            break

    if updated:
        with open(KNOWLEDGE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)

        # 添加到 RAG
        ingest_error = rag_service.ingest_paths(newly_added_paths)
        if ingest_error:
            return {
                "message": "Files uploaded but RAG indexing failed",
                "error": ingest_error,
            }

        return {
            "message": f"Successfully uploaded {len(newly_added_paths)} files",
            "paths": newly_added_paths,
        }

    raise HTTPException(status_code=404, detail=f"Node '{node_name}' not found")


@app.post("/api/pdf/select")
async def select_pdf(data: PDFSelection):
    """选择当前阅读的PDF"""
    global CURRENT_PDF_PATH
    pdf_path = data.pdf_path

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    # 设置当前PDF
    CURRENT_PDF_PATH = pdf_path
    logger.info(f"📄 Selected PDF: {pdf_path}")

    # 确保PDF已经在RAG数据库中
    ingest_error = rag_service.ingest_paths([pdf_path])
    if ingest_error:
        logger.error(f"❌ Failed to ingest PDF: {ingest_error}")
        return {"success": False, "error": ingest_error}

    logger.info(f"✅ PDF ingested successfully: {pdf_path}")
    return {"success": True, "pdf_path": pdf_path}


@app.get("/api/pdf/{path:path}")
async def get_pdf(path: str):
    """获取 PDF 文件"""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(path, media_type="application/pdf")


@app.get("/api/languages")
async def get_languages():
    """获取支持的语言列表"""
    return LanguageHandler.dropdown_choices()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
