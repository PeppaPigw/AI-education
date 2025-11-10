from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Form,
    status,
)
from fastapi.responses import FileResponse, RedirectResponse
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
from datetime import date, timedelta, datetime
from pathlib import Path

from AgentModule import create_agent
from AgentModule.edu_agent import run_agent
from LearningPlanModule import LearningPlan
from QuizModule import generate_learning_plan_from_quiz, prepare_quiz_questions
from SummaryModule import StudySummaryGenerator
from tools.language_handler import LanguageHandler
from tools.rag_service import get_rag_service
from tools.covert_resource import convert_to_pdf
from tools.llm_logger import get_llm_logger
from tools.ocr_service import get_ocr_service

app = FastAPI(title="AI-Education API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="backend/static"), name="static")
app.mount("/data", StaticFiles(directory="data"), name="data")

rag_service = get_rag_service()
retriever = rag_service.get_retriever()
logger = logging.getLogger(__name__)
KNOWLEDGE_JSON_PATH = "data/course/big_data.json"
CURRENT_NODE = None
CURRENT_PDF_PATH = None


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
    priority: str = "基础知识"
    deadline_days: int = 7


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


class QuizComplete(BaseModel):
    node_name: str
    score: int
    total: int


class LoginRequest(BaseModel):
    username: str
    password: str


class LLMLogRequest(BaseModel):
    messages: List[Dict[str, str]]
    response: Dict[str, Any]
    model: str
    module: str
    metadata: Optional[Dict] = None


class DeleteResourceRequest(BaseModel):
    node_name: str
    resource_index: int


@app.get("/")
async def root():
    return FileResponse("backend/static/login.html")


@app.get("/teacher.html")
async def get_teacher_page():
    return FileResponse("backend/static/teacher.html")


@app.get("/admin.html")
async def get_admin_page():
    return FileResponse("backend/static/admin.html")


@app.post("/login/student")
async def login_student(
    student_id: str = Form(..., alias="student_id"), password: str = Form(...)
):
    if student_id == "stuwangqiyu" and password == "123456":
        return RedirectResponse(
            url="/static/mainpage.html", status_code=status.HTTP_302_FOUND
        )
    else:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.post("/login/teacher")
async def login_teacher(
    teacher_id: str = Form(..., alias="teacher_id"), password: str = Form(...)
):
    if teacher_id == "teawangqiyu" and password == "123456":

        return RedirectResponse(url="/teacher.html", status_code=status.HTTP_302_FOUND)
    else:

        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@app.post("/login/admin")
async def login_admin(
    admin_username: str = Form(..., alias="admin_username"), password: str = Form(...)
):
    if admin_username == "adminwangqiyu" and password == "123456":
        return RedirectResponse(url="/admin.html", status_code=status.HTTP_302_FOUND)
    else:
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


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

                vectorstore = rag_service._get_vectorstore()

                docs = vectorstore.similarity_search(
                    query, k=4, filter={"source": self.pdf_path}
                )
                logger.info(
                    f"🔍 Filtered retrieval: found {len(docs)} docs from {self.pdf_path}"
                )
                return docs

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


def find_children_index_for_pdf(pdf_path: str) -> Optional[int]:
    """根据PDF路径找到它属于big_data.json的哪个children"""
    if not pdf_path:
        return None

    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load knowledge graph: {e}")
        return None

    for i, child in enumerate(graph_data.get("children", [])):
        for grandchild in child.get("grandchildren", []):
            resources = grandchild.get("resource_path", [])
            if isinstance(resources, str):
                resources = [resources] if resources else []
            if pdf_path in resources:
                return i

            for great_grandchild in grandchild.get("great-grandchildren", []):
                resources = great_grandchild.get("resource_path", [])
                if isinstance(resources, str):
                    resources = [resources] if resources else []
                if pdf_path in resources:
                    return i

                for ggc in great_grandchild.get("great-grandchildren", []):
                    resources = ggc.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []
                    if pdf_path in resources:
                        return i

    return None


def find_grandchild_and_collect_pdfs(pdf_path: str) -> List[str]:
    """找到PDF所属的grandchild，并收集该grandchild下所有great-grandchildren的PDF"""
    if not pdf_path:
        return []

    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load knowledge graph: {e}")
        return []

    all_pdfs = []

    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):

            found_in_this_grandchild = False

            resources = grandchild.get("resource_path", [])
            if isinstance(resources, str):
                resources = [resources] if resources else []
            if pdf_path in resources:
                found_in_this_grandchild = True

            for great_grandchild in grandchild.get("great-grandchildren", []):
                resources = great_grandchild.get("resource_path", [])
                if isinstance(resources, str):
                    resources = [resources] if resources else []
                if pdf_path in resources:
                    found_in_this_grandchild = True

            if found_in_this_grandchild:
                for great_grandchild in grandchild.get("great-grandchildren", []):
                    resources = great_grandchild.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []
                    for res in resources:
                        if res.endswith(".pdf") and os.path.exists(res):
                            all_pdfs.append(res)

                logger.info(
                    f"Found {len(all_pdfs)} PDFs in grandchild '{grandchild.get('name')}'"
                )
                return all_pdfs

    return []


@app.post("/api/quiz/start")
async def start_quiz(data: QuizStart):
    """开始测验"""
    global CURRENT_PDF_PATH

    code = LanguageHandler.code_from_display(data.lang_choice)
    language = (
        code if code != "auto" else LanguageHandler.choose_or_detect(data.subject)
    )

    current_retriever = None
    if CURRENT_PDF_PATH and os.path.exists(CURRENT_PDF_PATH):
        from langchain_core.vectorstores import VectorStoreRetriever
        from langchain_core.callbacks import CallbackManagerForRetrieverRun

        children_index = find_children_index_for_pdf(CURRENT_PDF_PATH)
        logger.info(f"🔍 Current PDF belongs to children[{children_index}]")

        question_file_path = None
        if children_index is not None and 0 <= children_index <= 5:
            question_file_path = f"data/Question/Q{children_index + 1}.txt"
            if os.path.exists(question_file_path):
                logger.info(f"📄 Using question file: {question_file_path}")
            else:
                logger.warning(f"⚠️ Question file not found: {question_file_path}")
                question_file_path = None

        class QuizFilteredRetriever(VectorStoreRetriever):
            """Quiz专用retriever：检索当前PDF和对应的Question文件"""

            pdf_path: str
            question_file_content: str = ""

            def _get_relevant_documents(
                self, query: str, *, run_manager: CallbackManagerForRetrieverRun = None
            ):

                vectorstore = rag_service._get_vectorstore()

                docs = vectorstore.similarity_search(
                    query, k=3, filter={"source": self.pdf_path}
                )
                logger.info(f"🔍 Found {len(docs)} docs from current PDF")

                if self.question_file_content:
                    from langchain_core.documents import Document

                    question_doc = Document(
                        page_content=self.question_file_content[:2000],
                        metadata={"source": "question_bank"},
                    )
                    docs.append(question_doc)
                    logger.info("✅ Added question bank content to context")

                return docs

        question_content = ""
        if question_file_path and os.path.exists(question_file_path):
            with open(question_file_path, "r", encoding="utf-8") as f:
                question_content = f.read()

        current_retriever = QuizFilteredRetriever(
            vectorstore=rag_service._get_vectorstore(),
            search_kwargs={"k": 3},
            pdf_path=CURRENT_PDF_PATH,
            question_file_content=question_content,
        )
        logger.info(f"✅ Created quiz retriever for: {CURRENT_PDF_PATH}")
    else:
        current_retriever = retriever
        logger.info(f"⚠️ No current PDF, using global retriever")

    questions, used_retriever = prepare_quiz_questions(
        data.subject, language=language, retriever=current_retriever
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
        overall = (total_correct / total_questions) * 100 if total_questions > 0 else 0
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

    deadline_days = data.deadline_days if hasattr(data, "deadline_days") else 7
    deadline_date = (datetime.now() + timedelta(days=deadline_days)).strftime(
        "%Y-%m-%d"
    )
    priority = data.priority if hasattr(data, "priority") else "基础知识"

    for entry in plan.learning_plan:
        entry["deadline"] = deadline_date
        entry["priority"] = priority

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
    global CURRENT_PDF_PATH

    code = LanguageHandler.code_from_display(data.lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(data.topic)

    current_retriever = None
    if CURRENT_PDF_PATH and os.path.exists(CURRENT_PDF_PATH):
        from langchain_core.vectorstores import VectorStoreRetriever
        from langchain_core.callbacks import CallbackManagerForRetrieverRun

        related_pdfs = find_grandchild_and_collect_pdfs(CURRENT_PDF_PATH)

        if related_pdfs:
            logger.info(f"📚 Summary will use {len(related_pdfs)} related PDFs")

            class SummaryFilteredRetriever(VectorStoreRetriever):
                """Summary专用retriever：检索grandchild下所有great-grandchildren的PDF"""

                pdf_paths: List[str]

                def _get_relevant_documents(
                    self,
                    query: str,
                    *,
                    run_manager: CallbackManagerForRetrieverRun = None,
                ):

                    vectorstore = rag_service._get_vectorstore()

                    all_docs = []
                    for pdf_path in self.pdf_paths:
                        docs = vectorstore.similarity_search(
                            query, k=2, filter={"source": pdf_path}
                        )
                        all_docs.extend(docs)

                    logger.info(
                        f"🔍 Summary retrieval: found {len(all_docs)} docs from {len(self.pdf_paths)} PDFs"
                    )

                    return all_docs[:8]

            current_retriever = SummaryFilteredRetriever(
                vectorstore=rag_service._get_vectorstore(),
                search_kwargs={"k": 8},
                pdf_paths=related_pdfs,
            )
            logger.info(f"✅ Created summary retriever for {len(related_pdfs)} PDFs")
        else:
            logger.info(f"⚠️ No related PDFs found, using current PDF only")

            from langchain_core.vectorstores import VectorStoreRetriever
            from langchain_core.callbacks import CallbackManagerForRetrieverRun

            class SinglePDFRetriever(VectorStoreRetriever):
                pdf_path: str

                def _get_relevant_documents(
                    self,
                    query: str,
                    *,
                    run_manager: CallbackManagerForRetrieverRun = None,
                ):
                    vectorstore = rag_service._get_vectorstore()
                    docs = vectorstore.similarity_search(
                        query, k=4, filter={"source": self.pdf_path}
                    )
                    return docs

            current_retriever = SinglePDFRetriever(
                vectorstore=rag_service._get_vectorstore(),
                search_kwargs={"k": 4},
                pdf_path=CURRENT_PDF_PATH,
            )
    else:
        current_retriever = retriever
        logger.info(f"⚠️ No current PDF, using global retriever")

    summarizer = StudySummaryGenerator(retriever=current_retriever)
    summary, used_retriever = summarizer.generate_summary(
        data.topic, language=language, retriever=current_retriever
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


@app.post("/api/delete-resource")
async def delete_resource(data: DeleteResourceRequest):
    """删除节点的指定资源"""
    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")

    updated = False
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == data.node_name:
                    resources = great_grandchild.get("resource_path", [])
                    if isinstance(resources, str):
                        resources = [resources] if resources else []
                        great_grandchild["resource_path"] = resources

                    if 0 <= data.resource_index < len(resources):
                        deleted_resource = resources.pop(data.resource_index)
                        logger.info(
                            f"Deleted resource: {deleted_resource} from node: {data.node_name}"
                        )
                        updated = True
                        break
            if updated:
                break
        if updated:
            break

    if updated:
        with open(KNOWLEDGE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)

        return {"success": True, "message": "Resource deleted successfully"}

    raise HTTPException(
        status_code=404,
        detail=f"Node '{data.node_name}' not found or invalid resource index",
    )


@app.post("/api/pdf/select")
async def select_pdf(data: PDFSelection):
    """选择当前阅读的PDF"""
    global CURRENT_PDF_PATH
    pdf_path = data.pdf_path

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    CURRENT_PDF_PATH = pdf_path
    logger.info(f"📄 Selected PDF: {pdf_path}")
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


@app.get("/api/students")
async def get_students():
    """获取所有学生信息"""
    try:
        with open("data/Users/student.json", "r", encoding="utf-8") as f:
            students = json.load(f)
        return students
    except FileNotFoundError:
        return []


@app.get("/api/teachers")
async def get_teachers():
    """获取所有教师信息"""
    try:
        with open("data/Users/teacher.json", "r", encoding="utf-8") as f:
            teachers = json.load(f)
        return teachers
    except FileNotFoundError:
        return []


@app.get("/api/llm-logs")
async def get_llm_logs():
    """获取所有LLM调用日志"""
    try:
        with open("data/Log/llm_log.json", "r", encoding="utf-8") as f:
            logs = json.load(f)
        return logs
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logger.error("Failed to parse llm_log.json")
        return []


@app.get("/api/learning-plans")
async def get_learning_plans():
    """获取所有学习计划文件列表"""
    plans_dir = Path("data/learning_plans")
    if not plans_dir.exists():
        return []

    plan_files = []
    for file_path in plans_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                plan_data = json.load(f)
                plan_files.append(
                    {
                        "filename": file_path.name,
                        "path": str(file_path),
                        "data": plan_data,
                    }
                )
        except Exception as e:
            logger.error(f"Error reading plan file {file_path}: {e}")

    plan_files.sort(key=lambda x: x["filename"], reverse=True)
    return plan_files


def update_flags_recursive(node):
    """递归更新节点的flag，如果所有子节点都为1，则父节点也为1"""
    if "great-grandchildren" in node and node["great-grandchildren"]:
        all_complete = all(
            child.get("flag") == "1" for child in node["great-grandchildren"]
        )
        if all_complete:
            node["flag"] = "1"
            return True
        else:
            node["flag"] = "0"
            return False
    return node.get("flag") == "1"


def find_and_update_node(node, target_name):
    """递归查找并更新节点flag"""
    if node.get("name") == target_name:
        node["flag"] = "1"
        return True

    if "great-grandchildren" in node and node["great-grandchildren"]:
        for child in node["great-grandchildren"]:
            if find_and_update_node(child, target_name):

                all_complete = all(
                    c.get("flag") == "1" for c in node["great-grandchildren"]
                )
                if all_complete:
                    node["flag"] = "1"
                return True

    return False


@app.get("/api/learning-progress")
async def get_learning_progress():
    """获取学习进度统计"""
    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        return {"error": "Knowledge graph not found"}

    children = graph_data.get("children", [])

    total_chapters = len(children)
    completed_chapters = sum(1 for c in children if c.get("flag") == "1")
    chapter_progress = (
        (completed_chapters / total_chapters * 100) if total_chapters > 0 else 0
    )

    total_sections = 0
    completed_sections = 0
    for child in children:
        grandchildren = child.get("grandchildren", [])
        total_sections += len(grandchildren)
        completed_sections += sum(1 for gc in grandchildren if gc.get("flag") == "1")
    section_progress = (
        (completed_sections / total_sections * 100) if total_sections > 0 else 0
    )

    total_points = 0
    completed_points = 0

    def count_knowledge_points(node):
        nonlocal total_points, completed_points
        great_grandchildren = node.get("great-grandchildren", [])
        if great_grandchildren:
            for ggc in great_grandchildren:
                total_points += 1
                if ggc.get("flag") == "1":
                    completed_points += 1
                count_knowledge_points(ggc)

    for child in children:
        for grandchild in child.get("grandchildren", []):
            count_knowledge_points(grandchild)

    point_progress = (completed_points / total_points * 100) if total_points > 0 else 0

    overall_progress = (chapter_progress + section_progress + point_progress) / 3

    return {
        "overall": {
            "progress": round(overall_progress, 1),
            "completed": completed_chapters + completed_sections + completed_points,
            "total": total_chapters + total_sections + total_points,
        },
        "chapters": {
            "progress": round(chapter_progress, 1),
            "completed": completed_chapters,
            "total": total_chapters,
        },
        "sections": {
            "progress": round(section_progress, 1),
            "completed": completed_sections,
            "total": total_sections,
        },
        "points": {
            "progress": round(point_progress, 1),
            "completed": completed_points,
            "total": total_points,
        },
    }


@app.post("/api/quiz/complete")
async def complete_quiz(data: QuizComplete):
    """完成测验，更新节点flag"""
    try:
        with open(KNOWLEDGE_JSON_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Knowledge graph not found")

    pass_threshold = 0.8
    score_ratio = data.score / data.total if data.total > 0 else 0
    passed = score_ratio >= pass_threshold

    if not passed:
        return {
            "success": False,
            "message": f"Score {data.score}/{data.total} is below passing threshold",
            "passed": False,
        }

    updated = False
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            if find_and_update_node(grandchild, data.node_name):
                updated = True

                all_grandchildren_complete = all(
                    gc.get("flag") == "1" for gc in child.get("grandchildren", [])
                )
                if all_grandchildren_complete:
                    child["flag"] = "1"
                break

        if updated:
            break

    if updated:

        all_children_complete = all(
            c.get("flag") == "1" for c in graph_data.get("children", [])
        )
        if all_children_complete:
            graph_data["flag"] = "1"

        with open(KNOWLEDGE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        return {
            "success": True,
            "message": "Quiz completed successfully",
            "passed": True,
        }

    raise HTTPException(status_code=404, detail=f"Node '{data.node_name}' not found")


@app.post("/api/llm-log")
async def log_llm_call(data: LLMLogRequest):
    """Log LLM call from frontend or backend"""
    try:
        llm_logger = get_llm_logger()
        response_obj = type(
            "Response",
            (),
            {
                "content": data.response.get("choices", [{}])[0]
                .get("message", {})
                .get("content", ""),
                "response_metadata": {
                    "id": data.response.get("id", ""),
                    "object": data.response.get("object", ""),
                    "created": data.response.get("created", 0),
                    "model": data.response.get("model", ""),
                    "finish_reason": data.response.get("choices", [{}])[0].get(
                        "finish_reason", ""
                    ),
                    "token_usage": data.response.get("usage", {}),
                    "system_fingerprint": data.response.get("system_fingerprint", ""),
                },
            },
        )()

        llm_logger.log_llm_call(
            messages=data.messages,
            response=response_obj,
            model=data.model,
            module=data.module,
            metadata=data.metadata,
        )
        return {"success": True, "message": "LLM call logged"}
    except Exception as e:
        logger.error(f"Error logging LLM call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to log LLM call: {str(e)}")


@app.post("/api/ocr/extract")
async def extract_text_from_image(image: UploadFile = File(...)):
    """从上传的图片中提取文本"""
    try:
        image_data = await image.read()

        ocr_service = get_ocr_service()
        extracted_text = ocr_service.extract_text_from_image(image_data)

        logger.info(f"✅ OCR extraction successful, text length: {len(extracted_text)}")

        return {"success": True, "text": extracted_text, "message": "图片识别成功"}
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"图片识别失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
