import io
import os
import random
import sys
from contextlib import redirect_stdout
import shutil
import logging
import re
import json
import gradio as gr
from dotenv import load_dotenv
import plotly.graph_objects as go
import base64 

try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from AgentModule import create_agent
    from AgentModule.edu_agent import run_agent
    from LearningPlanModule import LearningPlan
    from QuizModule import generate_learning_plan_from_quiz, prepare_quiz_questions
    from SummaryModule import StudySummaryGenerator
    from tools.language_handler import LanguageHandler
    from tools.rag_service import get_rag_service
    
    # 加载环境变量
    dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(dotenv_path)
    # 检查 API Key
    if not os.environ.get("api_key"):
        raise RuntimeError("api_key is not set. Create a .env file or export the variable.")
    # 初始化服务
    agent = create_agent()
    rag_service = get_rag_service()
    retriever = rag_service.get_retriever()
except (ImportError, RuntimeError, FileNotFoundError) as e:
    print(f"⚠️  Warning: Could not import all external modules: {e}. Running in standalone mode.")
    print("AI-related functionalities (chat, quiz, etc.) will be disabled.")
    # 创建伪对象以避免程序崩溃
    agent = None
    retriever = None
    # 为 LanguageHandler 创建一个简单的替代品
    class LanguageHandler:
        @staticmethod
        def dropdown_choices(): return ["Auto-detect", "English", "Polish", "Chinese"]
        @staticmethod
        def code_from_display(display): return "auto" if display == "Auto-detect" else display[:2].lower()
        @staticmethod
        def choose_or_detect(text, lang_code="en"): return lang_code
        @staticmethod
        def ensure_language(text, lang_code): return text

logger = logging.getLogger(__name__)
# CSS 样式 (未作修改)
CSS = """
* { font-family: 'Segoe UI', Tahoma, sans-serif; }
#chatbot .message.user { background-color: #e6f3ff; border-radius: 8px; }
#chatbot .message.bot { background-color: #f0f0f0; border-radius: 8px; }
#chatbot .message.bot.fallback { background-color: #fff9c4; }
.gradio-container { max-width: none !important; }
.full-height-plot, .full-height-plot > div {
    height: 100vh !important;
    min-height: 80vh;
}
.full-height-pdf, .full-height-pdf > div {
    height: 100vh !important;
}
/* 确保 iframe 占满容器 */
#pdf-viewer-container, #pdf-viewer-container iframe {
    height: 98vh !important;
    width: 100%;
}
"""
# --- 原始后端函数 (未作修改) ---
def respond(
    message: str,
    history: list[dict],
    lang_choice: str,
    retriever=None,
) -> tuple[list[dict], str]:
    """Return updated chat history and logs."""
    if not agent:
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": "Chatbot is disabled (module not loaded)."})
        yield history, "Chatbot is disabled."
        return
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "..."},
    ]
    yield history, ""
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(message)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        result, used_fallback, used_retriever = run_agent(
            message, executor=agent, retriever=retriever, return_details=True
        )
        result = LanguageHandler.ensure_language(result, language)
        if used_fallback:
            notice = LanguageHandler.ensure_language(
                # "LLM生成的消息，检查其正确性·",
                language,
            )
            result = f"<div class='fallback'>{notice}<br>{result}</div>"
        elif used_retriever:
            notice = LanguageHandler.ensure_language(
                language,
            )
            result = f"<div class='retrieval'>{notice}<br>{result}</div>"
    history[-1] = {"role": "assistant", "content": result}
    logs = buffer.getvalue()
    yield history, logs

def respond_with_retriever(message: str, history: list[dict], lang_choice: str):
    yield from respond(message, history, lang_choice, retriever)

def process_knowledge(files: list):
    """原始函数：仅处理文件并存入 RAG service"""
    if not files:
        yield "⚠️ No files uploaded."
        return
    yield "⏳ Processing for RAG..."
    yield f"✅ Processed {len(files)} file(s) for RAG."

def _format_question(q: dict) -> str:
    """Return formatted question text with options on separate lines."""
    text = q["question"]
    text = re.sub(r"\s*([abcd]\))", r"\n\1", text, flags=re.I)
    text = text.strip()
    return f"**{q['topic']}**\n\n{text}"

def start_quiz(subject: str, lang_choice: str, retriever=None):
    """Generate quiz questions and return the first one with state."""
    if not agent:
        return "Quiz is disabled.", {}, "Quiz is disabled."
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
    notice = (
        "📄 Quiz 使用文档上下文生成"
    )
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
    if not agent: return "Learning plan is disabled."
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(goals)
    plan = LearningPlan(user_name=name, user_language=language)
    goals_list = [g.strip() for g in goals.split(";") if g.strip()]
    user_input = {"goals": goals_list}
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        plan.generate_plan_from_prompt(user_input)
        plan.display_plan()
        plan.save_to_file()
    return buffer.getvalue()

def run_learning_plan_from_quiz(name: str, state: dict, lang_choice: str) -> str:
    if not agent: return "Learning plan is disabled."
    if not state or not state.get("scores"):
        return "No quiz results available."
    code = LanguageHandler.code_from_display(lang_choice)
    language = (
        code
        if code != "auto"
        else state.get("language") or LanguageHandler.choose_or_detect(name)
    )
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        generate_learning_plan_from_quiz(name, state["scores"], language)
    return buffer.getvalue()

def run_summary_interface(topic: str, lang_choice: str, retriever=None) -> str:
    if not agent: return "Summary is disabled."
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(topic)
    summarizer = StudySummaryGenerator(retriever=retriever)
    summary, used_retriever = summarizer.generate_summary(
        topic, language=language, retriever=retriever
    )
    notice = (
        "📄 Summary 使用文档上下文生成"
    )
    return f"{notice}\n\n{summary}"

KNOWLEDGE_JSON_PATH = "data/course/big_data.json"
def load_knowledge_data(json_path: str) -> dict:
    """从JSON文件加载知识图谱数据"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
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
            # if gc_resources and isinstance(gc_resources, list) and len(gc_resources) > 0:
            learning_nodes.append(gc_name)
            
            # 添加great-grandchildren节点
            for great_grandchild in grandchild.get("great-grandchildren", []):
                ggc_name = great_grandchild.get("name")
                ggc_resources = great_grandchild.get("resource_path", [])
                # if ggc_resources and isinstance(ggc_resources, list) and len(ggc_resources) > 0:
                learning_nodes.append(ggc_name)
    
    return learning_nodes

def create_knowledge_graph_figure(graph_data: dict):
    """使用Plotly创建4层知识图谱的可视化Figure"""
    if not graph_data:
        return go.Figure()
    
    fig = go.Figure()
    nodes = {'labels': [], 'colors': [], 'x': [], 'y': []}
    edges = {'x': [], 'y': []}
    
    # Root节点（第0层）
    root_name = graph_data.get("root_name", "Root")
    nodes['labels'].append(root_name)
    nodes['colors'].append("#FFA07A")  # 珊瑚色
    nodes['x'].append(0); nodes['y'].append(0)
    
    y_pos_child = 0
    
    for child in graph_data.get("children", []):
        child_name = child.get("name")
        child_color = "#87CEFA" if child.get("flag") == "1" else "#D3D3D3"
        
        # Children节点（第1层）
        nodes['labels'].append(child_name)
        nodes['colors'].append(child_color)
        nodes['x'].append(1)
        nodes['y'].append(y_pos_child)
        
        # Root到Child的连线
        edges['x'].extend([0, 1, None])
        edges['y'].extend([0, y_pos_child, None])
        
        y_pos_grandchild = y_pos_child
        
        for grandchild in child.get("grandchildren", []):
            grandchild_name = grandchild.get("name")
            grandchild_color = "#90EE90" if grandchild.get("flag") == "1" else "#D3D3D3"
            
            # Grandchildren节点（第2层）
            nodes['labels'].append(grandchild_name)
            nodes['colors'].append(grandchild_color)
            nodes['x'].append(2)
            nodes['y'].append(y_pos_grandchild)
            
            # Child到Grandchild的连线
            edges['x'].extend([1, 2, None])
            edges['y'].extend([y_pos_child, y_pos_grandchild, None])
            
            y_pos_great_grandchild = y_pos_grandchild
            
            # Great-grandchildren节点（第3层）
            for great_grandchild in grandchild.get("great-grandchildren", []):
                ggc_name = great_grandchild.get("name")
                ggc_color = "#FFD700" if great_grandchild.get("flag") == "1" else "#D3D3D3"  # 金色
                
                nodes['labels'].append(ggc_name)
                nodes['colors'].append(ggc_color)
                nodes['x'].append(3)
                nodes['y'].append(y_pos_great_grandchild)
                
                # Grandchild到Great-grandchild的连线
                edges['x'].extend([2, 3, None])
                edges['y'].extend([y_pos_grandchild, y_pos_great_grandchild, None])
                
                y_pos_great_grandchild += 0.8
            
            y_pos_grandchild += max(1.5, len(grandchild.get("great-grandchildren", [])) * 0.8)
        
        y_pos_child += max(2, y_pos_grandchild - y_pos_child + 1)
    
    # 添加连线
    fig.add_trace(go.Scatter(
        x=edges['x'], y=edges['y'],
        mode='lines',
        line=dict(width=1, color='#888'),
        hoverinfo='none'
    ))
    
    # 添加节点
    fig.add_trace(go.Scatter(
        x=nodes['x'], y=nodes['y'],
        mode='markers+text',
        text=nodes['labels'],
        textposition="bottom center",
        hoverinfo='text',
        marker=dict(
            symbol='circle',
            size=25,
            color=nodes['colors'],
            line=dict(width=2, color='#555')
        )
    ))
    
    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='white',
        margin=dict(l=10, r=10, t=30, b=10)
    )
    
    return fig

def find_resources_for_node(node_name: str, graph_data: dict) -> list:
    """在4层结构中查找指定节点的资源"""
    for child in graph_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            # 检查grandchildren层级
            if grandchild.get("name") == node_name:
                resources = grandchild.get("resource_path", [])
                return resources if isinstance(resources, list) else []
            
            # 检查great-grandchildren层级
            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == node_name:
                    resources = great_grandchild.get("resource_path", [])
                    return resources if isinstance(resources, list) else []
    
    return []

def upload_and_update_resource(files: list, selected_node: str, current_data: dict):
    """上传文件，保存，并更新JSON文件（支持4层结构）"""
    if not files:
        return "⚠️ 未选择文件。", current_data, gr.update()
    if not selected_node:
        return "❌ 错误：没有选定的学习节点来关联文件。", current_data, gr.update()
    
    save_dir = os.path.join("data", "RAG_files")
    os.makedirs(save_dir, exist_ok=True)
    
    newly_added_paths = []
    for file in files:
        filename = os.path.basename(file.name)
        dest_path = os.path.join(save_dir, filename)
        shutil.copy2(file.name, dest_path)
        logger.info(f"Saved {file.name} to {dest_path}")
        newly_added_paths.append(dest_path)
    
    updated = False
    new_choices = []
    
    # 在4层结构中查找并更新节点
    for child in current_data.get("children", []):
        for grandchild in child.get("grandchildren", []):
            # 检查grandchildren层级
            if grandchild.get("name") == selected_node:
                if "resource_path" not in grandchild or not grandchild["resource_path"]:
                    grandchild["resource_path"] = []
                grandchild["resource_path"].extend(newly_added_paths)
                new_choices = grandchild.get("resource_path", [])
                updated = True
                break
            
            # 检查great-grandchildren层级
            for great_grandchild in grandchild.get("great-grandchildren", []):
                if great_grandchild.get("name") == selected_node:
                    if "resource_path" not in great_grandchild or not great_grandchild["resource_path"]:
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
        with open(KNOWLEDGE_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, indent=2, ensure_ascii=False)
        msg = f"✅ 成功上传 {len(files)} 个文件并关联到 '{selected_node}'."
        return msg, current_data, gr.update(choices=new_choices, value=new_choices[0] if new_choices else None)
    else:
        msg = f"❌ 未能在JSON中找到节点 '{selected_node}'。"
        return msg, current_data, gr.update()
# <--- 修改点 2: 添加新的辅助函数来生成 PDF 的 iframe ---
def show_pdf_in_iframe(pdf_path: str):
    """
    读取PDF文件，编码为Base64，并返回一个HTML iframe字符串。
    如果文件不存在，则返回错误消息。
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return "<div style='text-align: center; padding: 20px;'>❌ PDF 文件未找到或路径无效。</div>"
    
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        
        html = f'''
        <iframe
            src="data:application/pdf;base64,{pdf_base64}"
            width="100%"
            height="100%"
            type="application/pdf">
        </iframe>
        '''
        return html
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {e}")
        return f"<div style='text-align: center; padding: 20px;'>❌ 读取 PDF 时出错: {e}</div>"
def build_interface() -> gr.Blocks:
    """创建符合新布局要求的 Gradio UI"""
    initial_data = load_knowledge_data(KNOWLEDGE_JSON_PATH)
    
    with gr.Blocks(css=CSS, theme=gr.themes.Soft()) as demo:
        # --- 状态管理 ---
        knowledge_data_state = gr.State(initial_data)
        selected_grandchild_state = gr.State()
        with gr.Row():
            # --- 左侧 3/4 主显示区 ---
            with gr.Column(scale=3):
                knowledge_graph_plot = gr.Plot(label="知识图谱", value=create_knowledge_graph_figure(initial_data),elem_classes=["full-height-plot"])
                # <--- 修改点 3.1: 将 gr.File 替换为 gr.HTML ---
                pdf_viewer_html = gr.HTML(visible=False, elem_id="pdf-viewer-container")
            # --- 右侧 1/4 功能/资源区 ---
            with gr.Column(scale=1):
                gr.Markdown("<h1>AI-Education 🎓</h1>")
                # MODIFIED: New interaction flow starts with this dropdown
                with gr.Group(visible=True) as node_selection_group:
                    learning_nodes_list = get_all_learning_nodes(initial_data)
                
                    node_selector = gr.Dropdown(choices=learning_nodes_list , label="选择一个知识节点开始学习")
                # 状态2: 显示选中节点的资源
                with gr.Group(visible=False) as resource_display_group:
                    gr.Markdown("### 📚 学习资源")
                    resource_selector = gr.Radio(label="选择一个PDF进行阅读", choices=[])
                
                # 状态3: PDF阅读时，显示功能面板
                with gr.Group(visible=False) as main_function_group:
                    lang_select = gr.Dropdown(choices=LanguageHandler.dropdown_choices(), value=LanguageHandler.dropdown_choices()[0], label="语言选择")
                    feature_choices = ["🤖 AI 助教", "📝 随堂测验", "🗺️ 学习计划", "📜 知识总结", "📤 上传新资源"]
                    feature_select = gr.Dropdown(choices=feature_choices, value=feature_choices[0], label="功能选择")
                    
                    with gr.Group(visible=True) as chat_group:
                        chatbot = gr.Chatbot(elem_id="chatbot", label="Chat", height=500)
                        with gr.Row():
                            msg = gr.Textbox(placeholder="输入你的问题...", container=False, scale=4)
                            send = gr.Button("发送", variant="primary", scale=1)
                        # with gr.Accordion("终端输出", open=False):
                        logs = gr.Textbox(label=None, lines=2)
                        clear = gr.Button("清除对话历史")
                    
                    with gr.Group(visible=False) as quiz_group:
                        
                        quiz_subject = gr.Textbox(label="测验主题")
                        start_btn = gr.Button("开始测验", variant="primary")
                        quiz_question = gr.Markdown(label="问题")
                        with gr.Row():
                            btn_a = gr.Button("A"); btn_b = gr.Button("B"); btn_c = gr.Button("C"); btn_d = gr.Button("D")
                        quiz_result = gr.Markdown(label="结果")
                        quiz_state = gr.State()
                        gr.Markdown("---")
                        quiz_name = gr.Textbox(label="你的名字 (用于生成学习计划)")
                        plan_quiz_btn = gr.Button("根据测验结果生成学习计划")
                        plan_quiz_output = gr.Textbox(label="计划输出", lines=10, interactive=False)
                    with gr.Group(visible=False) as plan_group:
                        
                        plan_name = gr.Textbox(label="你的名字")
                        plan_goals = gr.Textbox(label="学习目标 (用分号隔开)")
                        plan_btn = gr.Button("生成计划", variant="primary")
                        plan_output = gr.Textbox(label="计划输出", lines=10, interactive=False)
                    
                    with gr.Group(visible=False) as summary_group:
                        
                        sum_topic = gr.Textbox(label="主题或材料")
                        sum_btn = gr.Button("生成总结", variant="primary")
                        sum_output = gr.Textbox(label="总结内容", lines=10, interactive=False)
                    
                    with gr.Group(visible=False) as upload_group:
                        
                        gr.Markdown("上传文件到当前学习节点：")
                        current_node_display = gr.Markdown()
                        upload_files_new = gr.File(file_count="multiple", label="选择PDF文件")
                        upload_btn_new = gr.Button("上传并关联", variant="primary")
                        upload_status_new = gr.Markdown()
        
        # --- UI 事件处理与逻辑流 ---
        # MODIFIED: New function to handle node selection from dropdown
        def on_node_select(selected_node_name: str, graph_data: dict):
            if not selected_node_name:
                return gr.update(visible=False), None, gr.update(), gr.update(visible=False), gr.update(visible=True)
            
            resources = find_resources_for_node(selected_node_name, graph_data)
            
            return (
                gr.update(visible=True),
                selected_node_name,
                gr.update(choices=resources, value=None),
                gr.update(visible=False),
                gr.update(visible=True)
            )
        # MODIFIED: Event handler is now on the dropdown
        node_selector.change(
            fn=on_node_select,
            inputs=[node_selector, knowledge_data_state],
            outputs=[resource_display_group, selected_grandchild_state, resource_selector, main_function_group, knowledge_graph_plot]
        )
        
        # <--- 修改点 3.2: 修改 on_pdf_select 函数以输出 HTML ---
        def on_pdf_select(selected_pdf: str, selected_grandchild: str):
            if not selected_pdf:
                # 如果没有选择PDF，则不做任何事情
                return gr.update(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
            
            # 调用新函数生成 iframe HTML
            pdf_html_content = show_pdf_in_iframe(selected_pdf)
            
            return (
                gr.update(visible=False), # 隐藏知识图谱
                gr.update(visible=True, value=pdf_html_content), # 显示HTML组件并加载iframe内容
                gr.update(visible=False), # 隐藏节点选择器
                gr.update(visible=False), # 隐藏资源选择面板
                gr.update(visible=True),  # 显示主功能面板
                f"**当前节点**: {selected_grandchild}" # 在上传模块中显示当前节点
            )
        
        # <--- 修改点 3.3: 更新 change 事件的 outputs ---
        resource_selector.change(
            fn=on_pdf_select,
            inputs=[resource_selector, selected_grandchild_state],
            outputs=[knowledge_graph_plot, pdf_viewer_html, node_selection_group, resource_display_group, main_function_group, current_node_display]
        )
        
        def switch_feature_visibility(feature_name: str):
            visibility = {choice: (feature_name == choice) for choice in feature_choices}
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
            queue=False
        )
        # Backend function bindings (unchanged)
        def clear_history(): return [], "", ""
        msg.submit(respond_with_retriever, [msg, chatbot, lang_select], [chatbot, logs]).then(lambda: "", outputs=msg)
        send.click(respond_with_retriever, [msg, chatbot, lang_select], [chatbot, logs]).then(lambda: "", outputs=msg)
        clear.click(clear_history, None, [chatbot, logs, msg])
        
        start_btn.click(lambda sub, lang: start_quiz(sub, lang, retriever), [quiz_subject, lang_select], [quiz_question, quiz_state, quiz_result])
        btn_a.click(lambda st: answer_quiz("a", st), quiz_state, [quiz_question, quiz_state, quiz_result])
        btn_b.click(lambda st: answer_quiz("b", st), quiz_state, [quiz_question, quiz_state, quiz_result])
        btn_c.click(lambda st: answer_quiz("c", st), quiz_state, [quiz_question, quiz_state, quiz_result])
        btn_d.click(lambda st: answer_quiz("d", st), quiz_state, [quiz_question, quiz_state, quiz_result])
        plan_quiz_btn.click(run_learning_plan_from_quiz, [quiz_name, quiz_state, lang_select], plan_quiz_output)
        plan_btn.click(run_learning_plan_interface, [plan_name, plan_goals, lang_select], plan_output)
        sum_btn.click(lambda t, l: run_summary_interface(t, l, retriever), [sum_topic, lang_select], sum_output)
        
        upload_btn_new.click(
            fn=upload_and_update_resource,
            inputs=[upload_files_new, selected_grandchild_state, knowledge_data_state],
            outputs=[upload_status_new, knowledge_data_state, resource_selector]
        )
        
    return demo

def launch_gradio() -> None:
    
    demo = build_interface()
    demo.queue()
    demo.launch()
