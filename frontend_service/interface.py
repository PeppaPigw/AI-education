import os
import random
import sys
import shutil
import logging
import re
import json
import gradio as gr
from dotenv import load_dotenv
import plotly.graph_objects as go
import base64
import math
from AgentModule import create_agent
from AgentModule.edu_agent import run_agent
from LearningPlanModule import LearningPlan
from QuizModule import generate_learning_plan_from_quiz, prepare_quiz_questions
from SummaryModule import StudySummaryGenerator
from tools.language_handler import LanguageHandler
from tools.rag_service import get_rag_service
from tools.covert_resource import convert_to_pdf

CURRENT_NODE = None
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path)

rag_service = get_rag_service()
retriever = rag_service.get_retriever()
logger = logging.getLogger(__name__)
CSS = """
* { font-family: 'Segoe UI', Tahoma, sans-serif; }
.gradio-container {
    max-width: none !important;
    background-color: #1a1a2e;
}
#chatbot {
    background-color: transparent; 
}
#chatbot .message.user {
    background-color: #4a90e2;
    color: #ffffff;
    border-radius: 15px 15px 5px 15px;
    padding: 10px 15px;
}
#chatbot .message.bot {
    background-color: #7d2a8b;
    color: #ffffff;
    border-radius: 15px 15px 15px 5px;
    padding: 10px 15px;
}
#chatbot .message.bot.fallback {
    background-color: #33ffcc;
    color: #1a1a2e;
    font-weight: bold;
}
.full-height-plot, .full-height-plot > div {
    height: 100vh !important;
    min-height: 80vh;
}
.full-height-pdf, .full-height-pdf > div {
    height: 100vh !important;
}
#pdf-viewer-container, #pdf-viewer-container iframe {
    height: 98vh !important;
    width: 100%;
}
"""


def convert_history_to_gradio_format(history: list[dict]) -> list[list[str]]:
    return [
        [history[i]["content"], history[i + 1]["content"]]
        for i in range(0, len(history), 2)
    ]


def respond(
    message: str,
    history: list[list[str]],
    lang_choice: str,
    retriever=None,
):

    internal_history = []
    for user_msg, assistant_msg in history:
        internal_history.append({"role": "user", "content": user_msg})
        if assistant_msg is not None:
            internal_history.append({"role": "assistant", "content": assistant_msg})
    internal_history.extend(
        [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "..."},
        ]
    )
    yield convert_history_to_gradio_format(internal_history), ""
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(message)

    agent = create_agent()

    result, used_fallback, used_retriever = run_agent(
        message, executor=agent, retriever=retriever, return_details=True
    )
    result = LanguageHandler.ensure_language(result, language)
    if used_fallback:
        notice = LanguageHandler.ensure_language(
            "",
            language,
        )
        result = f"<div class='fallback'>{notice}<br>{result}</div>"
    elif used_retriever:
        result = f"<div class='retrieval'>{result}</div>"

    internal_history[-1] = {"role": "assistant", "content": result}
    logs = ""

    yield convert_history_to_gradio_format(internal_history), logs


def respond_with_retriever(message: str, history: list[list[str]], lang_choice: str):
    yield from respond(message, history, lang_choice, retriever)


def stream_chat_only(message: str, history: list[list[str]], lang_choice: str):
    response_generator = respond_with_retriever(message, history, lang_choice)
    for response_tuple in response_generator:
        chat_history = response_tuple[0]
        yield chat_history


def process_knowledge(files: list):
    """原始函数：仅处理文件并存入 RAG service"""
    if not files:
        yield "⚠️ No files uploaded."
        return
    yield "⏳ Processing for RAG..."
    yield f"✅ Processed {len(files)} file(s) for RAG."


def _format_question(q: dict) -> str:
    text = q["question"]
    text = re.sub(r"\s*([abcd]\))", r"\n\1", text, flags=re.I)
    text = text.strip()
    return f"**{q['topic']}**\n\n{text}"


def start_quiz(subject: str, lang_choice: str, retriever=None):
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(subject)
    questions, used_retriever = prepare_quiz_questions(
        subject, language=language, retriever=retriever
    )
    if not questions:
        return "Failed to generate quiz.", {}, ""
    state = {
        "subject": subject,
        "language": language,
        "questions": questions,
        "index": 0,
        "scores": {},
        "correct_total": 0,
    }
    first_q = _format_question(questions[0])
    notice = "📄 Quiz 使用文档上下文生成"
    return first_q, state, notice


def answer_quiz(choice: str, state: dict) -> tuple[str, dict, str]:
    """Process an answer button click and return next question or results."""
    if not state or state.get("index") is None:
        return "Quiz not started.", state, ""
    idx = state["index"]
    questions = state["questions"]
    if idx >= len(questions):
        return "", state, _compile_results(state)
    current = questions[idx]
    topic = current["topic"]
    correct = current["correct"]
    scores = state.setdefault("scores", {}).setdefault(topic, [0, 0])
    scores[1] += 1
    if choice.lower() == correct or correct == "?":
        scores[0] += 1
        state["correct_total"] += 1
    state["index"] += 1
    if state["index"] >= len(questions):
        return "", state, _compile_results(state)
    next_q = _format_question(questions[state["index"]])
    return next_q, state, ""


def _compile_results(state: dict) -> str:
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


def run_learning_plan_interface(name: str, goals: str, lang_choice: str) -> str:
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(goals)
    plan = LearningPlan(user_name=name, user_language=language)
    goals_list = [g.strip() for g in goals.split(";") if g.strip()]
    user_input = {"goals": goals_list}

    print("\n" + "=" * 80)
    print("📝 生成学习计划...")
    print("=" * 80)
    plan.generate_plan_from_prompt(user_input)
    plan.display_plan()
    plan.save_to_file()
    return f"✅ 学习计划已生成并保存！请查看terminal获取详细信息。"


def run_learning_plan_from_quiz(name: str, state: dict, lang_choice: str) -> str:
    if not state or not state.get("scores"):
        return "No quiz results available."
    code = LanguageHandler.code_from_display(lang_choice)
    language = (
        code
        if code != "auto"
        else state.get("language") or LanguageHandler.choose_or_detect(name)
    )

    print("\n" + "=" * 80)
    print("📝 根据测验结果生成学习计划...")
    print("=" * 80)
    generate_learning_plan_from_quiz(name, state["scores"], language)
    return f"✅ 基于测验的学习计划已生成！请查看terminal获取详细信息。"


def run_summary_interface(topic: str, lang_choice: str, retriever=None) -> str:

    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(topic)
    summarizer = StudySummaryGenerator(retriever=retriever)
    summary, used_retriever = summarizer.generate_summary(
        topic, language=language, retriever=retriever
    )
    notice = "📄 Summary 使用文档上下文生成"
    return f"{notice}\n\n{summary}"


KNOWLEDGE_JSON_PATH = "data/course/big_data.json"


def load_knowledge_data(json_path: str) -> dict:
    """从JSON文件加载知识图谱数据"""
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def get_all_learning_nodes(graph_data: dict) -> list:
    """从知识数据中提取所有可学习的节点（grandchildren和great-grandchildren）"""
    learning_nodes = []
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            # 添加grandchildren节点
            gc_name = grandchild.get("name")
            gc_resources = grandchild.get("resource_path", [])

            learning_nodes.append(gc_name)

            for great_grandchild in grandchild.get("great-grandchildren", []):
                ggc_name = great_grandchild.get("name")
                ggc_resources = great_grandchild.get("resource_path", [])
                learning_nodes.append(ggc_name)

    return learning_nodes


def create_knowledge_graph_figure(graph_data: dict):
    """使用Plotly创建4层知识图谱的圆形辐射状可视化Figure"""
    if not graph_data:
        return go.Figure()

    fig = go.Figure()
    nodes = {"labels": [], "colors": [], "x": [], "y": []}
    edges = {"x": [], "y": []}

    root_name = graph_data.get("root_name", "Root")
    nodes["labels"].append(root_name)
    nodes["colors"].append("#FFA07A")  # 珊瑚色
    nodes["x"].append(0)
    nodes["y"].append(0)
    # 定义每层的半径和角度扩散因子
    radii = [0, 1.5, 3.0, 4.5]
    spread_factor = 0.95  # 子节点在其父节点扇区中的占比
    # Level 1: Children 围绕中心分布
    children = graph_data.get("children", [])
    num_children = len(children)
    child_angle_step = 2 * math.pi / num_children if num_children > 0 else 0
    for i, child in enumerate(children):
        # 使用极坐标转笛卡尔坐标：x = r * cos(θ), y = r * sin(θ)
        child_angle = i * child_angle_step
        x_child = radii[1] * math.cos(child_angle)
        y_child = radii[1] * math.sin(child_angle)

        child_name = child.get("name")
        child_color = "#87CEFA" if child.get("flag") == "1" else "#D3D3D3"
        nodes["labels"].append(child_name)
        nodes["colors"].append(child_color)
        nodes["x"].append(x_child)
        nodes["y"].append(y_child)

        # 添加从 Root 到 Child 的连线
        edges["x"].extend([0, x_child, None])
        edges["y"].extend([0, y_child, None])
        # Level 2: Grandchildren 在各自父节点的扇区内分布
        grandchildren = child.get("grandchildren", [])
        num_grandchildren = len(grandchildren)
        if num_grandchildren == 0:
            continue

        sector_angle = (
            child_angle_step * spread_factor if num_children > 1 else 2 * math.pi
        )
        start_angle = child_angle - sector_angle / 2
        gc_angle_step = sector_angle / num_grandchildren

        for j, grandchild in enumerate(grandchildren):

            gc_angle = start_angle + (j + 0.5) * gc_angle_step
            x_gc = radii[2] * math.cos(gc_angle)
            y_gc = radii[2] * math.sin(gc_angle)

            grandchild_name = grandchild.get("name")
            grandchild_color = "#90EE90" if grandchild.get("flag") == "1" else "#D3D3D3"
            nodes["labels"].append(grandchild_name)
            nodes["colors"].append(grandchild_color)
            nodes["x"].append(x_gc)
            nodes["y"].append(y_gc)

            edges["x"].extend([x_child, x_gc, None])
            edges["y"].extend([y_child, y_gc, None])
            # Level 3: Great-grandchildren 在各自父节点的子扇区内分布
            great_grandchildren = grandchild.get("great-grandchildren", [])
            num_ggc = len(great_grandchildren)
            if num_ggc == 0:
                continue
            sub_sector_angle = gc_angle_step * spread_factor
            ggc_start_angle = gc_angle - sub_sector_angle / 2
            ggc_angle_step = sub_sector_angle / num_ggc
            for k, ggc in enumerate(great_grandchildren):
                ggc_angle = ggc_start_angle + (k + 0.5) * ggc_angle_step
                x_ggc = radii[3] * math.cos(ggc_angle)
                y_ggc = radii[3] * math.sin(ggc_angle)
                ggc_name = ggc.get("name")
                ggc_color = "#FFD700" if ggc.get("flag") == "1" else "#D3D3D3"  # 金色
                nodes["labels"].append(ggc_name)
                nodes["colors"].append(ggc_color)
                nodes["x"].append(x_ggc)
                nodes["y"].append(y_ggc)

                edges["x"].extend([x_gc, x_ggc, None])
                edges["y"].extend([y_gc, y_ggc, None])

    fig.add_trace(
        go.Scatter(
            x=edges["x"],
            y=edges["y"],
            mode="lines",
            line=dict(width=1, color="#888"),
            hoverinfo="none",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=nodes["x"],
            y=nodes["y"],
            mode="markers+text",
            text=nodes["labels"],
            textposition="bottom center",
            textfont=dict(size=10),
            hoverinfo="text",
            marker=dict(
                symbol="circle",
                size=25,
                color=nodes["colors"],
                line=dict(width=2, color="#555"),
            ),
        )
    )

    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=30, b=10),
    )

    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return fig


def find_resources_for_node(node_name: str, graph_data: dict) -> list:
    """在4层结构中查找指定节点的资源"""
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            # 检查grandchildren层级
            if grandchild.get("name") == node_name:
                resources = grandchild.get("resource_path", [])
                return resources if isinstance(resources, list) else []

            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == node_name:

                    resources = great_grandchild.get("resource_path", [])
                    return resources if isinstance(resources, list) else []

    return []


def upload_and_update_resource(files: list, current_data: dict):
    global CURRENT_NODE
    selected_node = CURRENT_NODE
    if not files:
        return "⚠️ 未选择文件。", current_data, gr.update()
    if not selected_node:
        return "❌ 错误：没有选定的学习节点来关联文件。", current_data, gr.update()

    save_dir = os.path.join("data", "RAG_files")
    os.makedirs(save_dir, exist_ok=True)
    supported_conversion_exts = [".doc", ".docx", ".ppt", ".pptx"]

    newly_added_paths = []
    processed_files_count = 0

    for file in files:

        original_temp_path = file.name
        filename = os.path.basename(original_temp_path)
        file_ext = os.path.splitext(filename)[1].lower()
        try:

            if file_ext == ".pdf":
                dest_path = os.path.join(save_dir, filename)
                shutil.copy2(original_temp_path, dest_path)
                logger.info(f"📄 PDF文件已直接保存到: {dest_path}")
                newly_added_paths.append(dest_path)
                processed_files_count += 1

            elif file_ext in supported_conversion_exts:

                pdf_path = convert_to_pdf(original_temp_path, save_dir)
                if pdf_path:
                    newly_added_paths.append(pdf_path)
                    processed_files_count += 1
                else:

                    logger.warning(f"⚠️ 文件 '{filename}' 转换失败，已跳过。")

            else:
                logger.warning(
                    f"Unsupported file type '{file_ext}' for file '{filename}'. Skipping. 🤷"
                )
        except Exception as e:

            logger.error(f"处理文件 '{filename}' 时发生严重错误: {e}")
            return (
                f"❌ 处理 '{filename}' 时出错，请检查日志。",
                current_data,
                gr.update(),
            )
    if not newly_added_paths:
        return (
            "🤷‍♀️ 没有成功处理任何文件（可能因为格式不支持或转换失败）。",
            current_data,
            gr.update(),
        )

    updated = False
    new_choices = []

    for child in current_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            if grandchild.get("name") == selected_node:
                if "resource_path" not in grandchild or not grandchild["resource_path"]:
                    grandchild["resource_path"] = []
                grandchild["resource_path"].extend(newly_added_paths)
                new_choices = grandchild.get("resource_path", [])
                updated = True
                break

            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == selected_node:
                    if (
                        "resource_path" not in great_grandchild
                        or not great_grandchild["resource_path"]
                    ):
                        great_grandchild["resource_path"] = []
                    great_grandchild["resource_path"].extend(newly_added_paths)
                    new_choices = great_grandchild.get("resource_path", [])
                    updated = True
                    break

            if updated:
                break
        if updated:
            break

    if updated:
        with open(KNOWLEDGE_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=2, ensure_ascii=False)

        # 🔥 关键修复：将新上传的PDF文件ingest到RAG向量数据库
        logger.info(f"📥 正在将 {len(newly_added_paths)} 个PDF文件加入RAG向量数据库...")
        ingest_error = rag_service.ingest_paths(newly_added_paths)
        if ingest_error:
            logger.error(f"❌ RAG ingest失败: {ingest_error}")
            msg = f"⚠️ 文件已保存但RAG索引失败: {ingest_error}"
        else:
            logger.info(f"✅ 成功将 {len(newly_added_paths)} 个PDF文件加入RAG数据库")
            msg = f"✅ 成功处理并上传 {processed_files_count} 个文件，并关联到 '{selected_node}'，已加入RAG数据库。"

        return (
            msg,
            current_data,
            gr.update(
                choices=new_choices, value=new_choices[0] if new_choices else None
            ),
        )
    else:
        msg = f"❌ 未能在JSON中找到节点 '{selected_node}'。"
        return msg, current_data, gr.update()


def show_pdf_in_iframe(pdf_path: str):
    if not pdf_path or not os.path.exists(pdf_path):
        return "<div style='text-align: center; padding: 20px;'>❌ PDF 文件未找到或路径无效。</div>"

    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")

        html = f"""
        <iframe
            src="data:application/pdf;base64,{pdf_base64}"
            width="100%"
            height="100%"
            type="application/pdf">
        </iframe>
        """
        return html
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {e}")
        return f"<div style='text-align: center; padding: 20px;'>❌ 读取 PDF 时出错: {e}</div>"


def build_interface() -> gr.Blocks:

    initial_data = load_knowledge_data(KNOWLEDGE_JSON_PATH)

    with gr.Blocks(css=CSS, theme=gr.themes.Soft()) as demo:
        knowledge_data_state = gr.State(initial_data)
        selected_grandchild_state = gr.State()
        with gr.Row():

            with gr.Column(scale=3):
                knowledge_graph_plot = gr.Plot(
                    label="知识图谱",
                    value=create_knowledge_graph_figure(initial_data),
                    elem_classes=["full-height-plot"],
                )
                pdf_viewer_html = gr.HTML(visible=False, elem_id="pdf-viewer-container")
            # --- 右侧 1/4 功能/资源区 ---
            with gr.Column(scale=1):
                gr.Markdown("<h1>AI-Education 🎓</h1>")
                with gr.Group(visible=True) as node_selection_group:
                    learning_nodes_list = get_all_learning_nodes(initial_data)
                    node_selector = gr.Dropdown(
                        choices=learning_nodes_list, label="选择一个知识节点开始学习"
                    )

                # 状态2: 显示选中节点的资源
                with gr.Group(visible=False) as resource_display_group:
                    gr.Markdown("### 📚 学习资源")
                    resource_selector = gr.Radio(
                        label="选择一个PDF进行阅读", choices=[]
                    )

                # 状态3: PDF阅读时，显示功能面板
                with gr.Group(
                    visible=False, elem_id="main-function-group"
                ) as main_function_group:
                    lang_select = gr.Dropdown(
                        choices=LanguageHandler.dropdown_choices(),
                        value=LanguageHandler.dropdown_choices()[0],
                        label="语言选择",
                    )
                    feature_choices = [
                        "🤖 AI 助教",
                        "📝 随堂测验",
                        "🗺️ 学习计划",
                        "📜 知识总结",
                        "📤 上传新资源",
                    ]
                    feature_select = gr.Dropdown(
                        choices=feature_choices,
                        value=feature_choices[0],
                        label="功能选择",
                    )

                    with gr.Group(
                        visible=True, elem_classes=["feature-group"]
                    ) as chat_group:
                        chatbot = gr.Chatbot(
                            elem_id="chatbot", label="Chat", height=600
                        )
                        with gr.Row():
                            msg = gr.Textbox(
                                placeholder="输入你的问题...", container=False, scale=4
                            )
                            send = gr.Button("发送", variant="primary", scale=1)

                    with gr.Group(
                        visible=False, elem_classes=["feature-group"]
                    ) as quiz_group:
                        quiz_subject = gr.Textbox(label="测验主题")
                        start_btn = gr.Button("开始测验", variant="primary")
                        quiz_question = gr.Markdown(label="问题")
                        with gr.Row():
                            btn_a = gr.Button("A")
                            btn_b = gr.Button("B")
                            btn_c = gr.Button("C")
                            btn_d = gr.Button("D")
                        quiz_result = gr.Markdown(label="结果")
                        quiz_state = gr.State()
                        gr.Markdown("---")
                        quiz_name = gr.Textbox(label="你的名字 (用于生成学习计划)")
                        plan_quiz_btn = gr.Button("根据测验结果生成学习计划")
                        plan_quiz_output = gr.Markdown(
                            label="计划输出", elem_classes=["fill-height"]
                        )

                    with gr.Group(
                        visible=False, elem_classes=["feature-group"]
                    ) as plan_group:
                        plan_name = gr.Textbox(label="你的名字")
                        plan_goals = gr.Textbox(label="学习目标 (用分号隔开)")
                        plan_btn = gr.Button("生成计划", variant="primary")
                        plan_output = gr.Markdown(
                            label="计划输出", elem_classes=["fill-height"]
                        )

                    with gr.Group(
                        visible=False, elem_classes=["feature-group"]
                    ) as summary_group:
                        sum_topic = gr.Textbox(label="主题或材料")
                        sum_btn = gr.Button("生成总结", variant="primary")
                        sum_output = gr.Markdown(
                            label="总结内容", elem_classes=["fill-height"]
                        )
                    with gr.Group(
                        visible=False, elem_classes=["feature-group"]
                    ) as upload_group:
                        gr.Markdown("上传文件到当前学习节点：")
                        current_node_display = gr.Markdown()
                        upload_files_new = gr.File(
                            file_count="multiple", label="选择PDF文件"
                        )
                        upload_btn_new = gr.Button("上传并关联", variant="primary")
                        upload_status_new = gr.Markdown()

        def on_node_select(selected_node_name: str, graph_data: dict):
            if not selected_node_name:
                return (
                    gr.update(visible=False),
                    None,
                    gr.update(),
                    gr.update(visible=False),
                    gr.update(visible=True),
                )

            resources = find_resources_for_node(selected_node_name, graph_data)

            return (
                gr.update(visible=True),
                selected_node_name,
                gr.update(choices=resources, value=None),
                gr.update(visible=False),
                gr.update(visible=True),
            )

        node_selector.change(
            fn=on_node_select,
            inputs=[node_selector, knowledge_data_state],
            outputs=[
                resource_display_group,
                selected_grandchild_state,
                resource_selector,
                main_function_group,
                knowledge_graph_plot,
            ],
        )

        def on_pdf_select(selected_pdf: str, selected_grandchild: str):
            if not selected_pdf:
                return (
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(),
                )

            pdf_html_content = show_pdf_in_iframe(selected_pdf)

            # 🔥 关键修复：确保选中的PDF已经在RAG数据库中
            if os.path.exists(selected_pdf):
                logger.info(f"📚 确保PDF已加载到RAG: {selected_pdf}")
                ingest_error = rag_service.ingest_paths([selected_pdf])
                if ingest_error:
                    logger.error(f"❌ 加载PDF到RAG失败: {ingest_error}")
                else:
                    logger.info(f"✅ PDF已在RAG数据库中: {selected_pdf}")
            else:
                logger.warning(f"⚠️ PDF文件不存在: {selected_pdf}")

            # 这个函数是设置当前节点的关键
            global CURRENT_NODE
            CURRENT_NODE = selected_grandchild

            return (
                gr.update(visible=False),
                gr.update(visible=True, value=pdf_html_content),
                gr.update(visible=False),
                gr.update(visible=False),
                gr.update(visible=True),
                f"**当前节点**: {selected_grandchild}",
            )

        resource_selector.change(
            fn=on_pdf_select,
            inputs=[resource_selector, selected_grandchild_state],
            outputs=[
                knowledge_graph_plot,
                pdf_viewer_html,
                node_selection_group,
                resource_display_group,
                main_function_group,
                current_node_display,
            ],
        )

        def switch_feature_visibility(feature_name: str):
            visibility = {
                choice: (feature_name == choice) for choice in feature_choices
            }
            return {
                chat_group: gr.update(visible=visibility[feature_choices[0]]),
                quiz_group: gr.update(visible=visibility[feature_choices[1]]),
                plan_group: gr.update(visible=visibility[feature_choices[2]]),
                summary_group: gr.update(visible=visibility[feature_choices[3]]),
                upload_group: gr.update(visible=visibility[feature_choices[4]]),
            }

        feature_select.change(
            fn=switch_feature_visibility,
            inputs=feature_select,
            outputs=[chat_group, quiz_group, plan_group, summary_group, upload_group],
            queue=False,
        )
        msg.submit(stream_chat_only, [msg, chatbot, lang_select], [chatbot]).then(
            lambda: "", outputs=msg
        )
        send.click(stream_chat_only, [msg, chatbot, lang_select], [chatbot]).then(
            lambda: "", outputs=msg
        )

        start_btn.click(
            lambda sub, lang: start_quiz(sub, lang, retriever),
            [quiz_subject, lang_select],
            [quiz_question, quiz_state, quiz_result],
        )
        btn_a.click(
            lambda st: answer_quiz("a", st),
            quiz_state,
            [quiz_question, quiz_state, quiz_result],
        )
        btn_b.click(
            lambda st: answer_quiz("b", st),
            quiz_state,
            [quiz_question, quiz_state, quiz_result],
        )
        btn_c.click(
            lambda st: answer_quiz("c", st),
            quiz_state,
            [quiz_question, quiz_state, quiz_result],
        )
        btn_d.click(
            lambda st: answer_quiz("d", st),
            quiz_state,
            [quiz_question, quiz_state, quiz_result],
        )
        plan_quiz_btn.click(
            run_learning_plan_from_quiz,
            [quiz_name, quiz_state, lang_select],
            plan_quiz_output,
        )
        plan_btn.click(
            run_learning_plan_interface,
            [plan_name, plan_goals, lang_select],
            plan_output,
        )
        sum_btn.click(
            lambda t, l: run_summary_interface(t, l, retriever),
            [sum_topic, lang_select],
            sum_output,
        )

        # --- MODIFICATION START 3 ---

        upload_btn_new.click(
            fn=upload_and_update_resource,
            inputs=[upload_files_new, knowledge_data_state],
            outputs=[upload_status_new, knowledge_data_state, resource_selector],
        )
        # --- MODIFICATION END 3 ---

    return demo


def launch_gradio() -> None:

    demo = build_interface()
    demo.queue()
    demo.launch()
