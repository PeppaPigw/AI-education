import io
import os
import random
import sys
from contextlib import redirect_stdout
import shutil
import logging
import re

import gradio as gr
from dotenv import load_dotenv

# --- 后端逻辑与函数 (未作修改) ---
# 这部分代码与你提供的原始代码完全相同，以确保功能和接口不变。

# 确保脚本可以找到自定义模块
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
    raise RuntimeError(
        "api_key is not set. Create a .env file or export the variable."
    )

# 初始化服务
agent = create_agent()
rag_service = get_rag_service()
retriever = rag_service.get_retriever()

logger = logging.getLogger(__name__)

# CSS 样式 (未作修改)
CSS = """
* {
    font-family: 'Segoe UI', Tahoma, sans-serif;
}
#chatbot .message.user {
    background-color: #e6f3ff;
    border-radius: 8px;
}
#chatbot .message.bot {
    background-color: #f0f0f0;
    border-radius: 8px;
}
#chatbot .message.bot.fallback {
    background-color: #fff9c4;
}
"""

def respond(
    message: str,
    history: list[dict],
    lang_choice: str,
    retriever=None,
) -> tuple[list[dict], str]:
    """Return updated chat history and logs."""
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
                "Wiadomość generowana przez LLM, sprawdź jej poprawność &#10071;",
                language,
            )
            result = f"<div class='fallback'>{notice}<br>{result}</div>"
        elif used_retriever:
            notice = LanguageHandler.ensure_language(
                "Wiadomość generowana na podstawie dokumentu",
                language,
            )
            result = f"<div class='retrieval'>{notice}<br>{result}</div>"

    history[-1] = {"role": "assistant", "content": result}
    logs = buffer.getvalue()
    yield history, logs


def respond_with_retriever(message: str, history: list[dict], lang_choice: str):
    """Wrapper injecting the shared retriever into :func:`respond`."""
    yield from respond(message, history, lang_choice, retriever)


def process_knowledge(files: list):
    """Save uploaded files and ingest them into the RAG service."""
    if not files:
        yield "⚠️ No files uploaded."
        return

    yield "⏳ Processing..."
    save_dir = os.path.join("data", "RAG_files")
    os.makedirs(save_dir, exist_ok=True)
    paths: list[str] = []
    for file in files:
        if not file:
            continue
        filename = os.path.basename(file.name)
        dest = os.path.join(save_dir, filename)
        try:
            shutil.copy2(file.name, dest)
            logger.info("Saved %s to %s", file.name, dest)
        except FileNotFoundError:
            msg = f"❌ Source file not found: {file.name}"
            logger.error(msg)
            yield msg
            return
        paths.append(dest)
    if paths:
        error = rag_service.ingest_paths(paths)
        if error:
            msg = f"❌ Failed to ingest files: {error}"
            logger.error(msg)
            yield msg
            return
    yield f"✅ Processed {len(paths)} file(s)."


def _format_question(q: dict) -> str:
    """Return formatted question text with options on separate lines."""
    text = q["question"]
    text = re.sub(r"\s*([abcd]\))", r"\n\1", text, flags=re.I)
    text = text.strip()
    return f"**{q['topic']}**\n\n{text}"


def start_quiz(
    subject: str, lang_choice: str, retriever=None
) -> tuple[str, dict, str]:
    """Generate quiz questions and return the first one with state."""
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
        "📄 Quiz generated with document context"
        if used_retriever
        else "⚠️ Quiz generated without document context"
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
    """Generate a learning plan from custom goals."""
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
    """Generate a learning plan based on completed quiz results."""
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
    """Generate a detailed study summary."""
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(topic)
    summarizer = StudySummaryGenerator(retriever=retriever)
    summary, used_retriever = summarizer.generate_summary(
        topic, language=language, retriever=retriever
    )
    notice = (
        "📄 Summary generated with document context"
        if used_retriever
        else "⚠️ Summary generated without document context"
    )
    return f"{notice}\n\n{summary}"

# --- Gradio UI 构建 (已修改) ---
# 这部分是根据你的新布局要求重构的。

def build_interface() -> gr.Blocks:
    """创建具有右侧边栏布局的 Gradio UI。"""
    with gr.Blocks(css=CSS, theme=gr.themes.Soft()) as demo:
        with gr.Row():
            # 左侧 3/4 空白区域
            with gr.Column(scale=3):
                pass  # 此列根据要求留空

            # 右侧 1/4 功能面板
            with gr.Column(scale=1):
                gr.Markdown("<h1>EduGen 🎓</h1>")

                # 功能选择下拉菜单
                feature_choices = [
                    "Chat with the bot",
                    "Generate quiz",
                    "Learning plan",
                    "Summary",
                    "Upload Knowledge",
                ]
                feature_select = gr.Dropdown(
                    choices=feature_choices,
                    value=feature_choices[0],
                    label="Select Functionality",
                )

                # 语言选择下拉菜单
                lang_select = gr.Dropdown(
                    choices=LanguageHandler.dropdown_choices(),
                    value=LanguageHandler.dropdown_choices()[0],
                    label="Language",
                )

                # --- 各功能的 UI 组件组 ---
                
                # “Upload Knowledge” 功能组
                with gr.Group(visible=False) as upload_group:
                    with gr.Blocks() as upload_blocks:
                        gr.Markdown("### Upload Knowledge 🧠")
                        upload_files = gr.File(file_count="multiple", label="Upload Files")
                        process_btn = gr.Button("Process", variant="primary")
                        upload_status = gr.Markdown()
                        process_btn.click(process_knowledge, upload_files, upload_status)

                # “Chat with the bot” 功能组
                with gr.Group(visible=True) as chat_group:
                    with gr.Blocks() as chat_blocks:
                        gr.Markdown("### Chat with the bot 💬")
                        chatbot = gr.Chatbot(elem_id="chatbot", type="messages", label="Chat", height=500)
                        with gr.Row():
                            msg = gr.Textbox(
                                placeholder="Type your message and press enter...",
                                container=False,
                                scale=4,
                            )
                            send = gr.Button("Send", variant="primary", scale=1)
                        with gr.Accordion("Terminal Output", open=False):
                            logs = gr.Textbox(label=None, lines=8)
                        clear = gr.Button("Clear Chat History")
                        
                        def clear_history():
                            return [], "", ""
                        
                        msg.submit(
                            respond_with_retriever, [msg, chatbot, lang_select], [chatbot, logs]
                        ).then(lambda: "", outputs=msg)
                        send.click(
                            respond_with_retriever, [msg, chatbot, lang_select], [chatbot, logs]
                        ).then(lambda: "", outputs=msg)
                        clear.click(clear_history, None, [chatbot, logs, msg])

                # “Generate quiz” 功能组
                with gr.Group(visible=False) as quiz_group:
                    with gr.Blocks() as quiz_blocks:
                        gr.Markdown("### Generate quiz 📝")
                        quiz_subject = gr.Textbox(label="Subject")
                        start_btn = gr.Button("Start Quiz", variant="primary")
                        quiz_question = gr.Markdown(label="Question")
                        with gr.Row():
                            btn_a = gr.Button("A")
                            btn_b = gr.Button("B")
                            btn_c = gr.Button("C")
                            btn_d = gr.Button("D")
                        quiz_result = gr.Markdown(label="Result")
                        quiz_state = gr.State()
                        
                        gr.Markdown("---")
                        
                        quiz_name = gr.Textbox(label="Your name (for learning plan)")
                        plan_quiz_btn = gr.Button("Generate Learning Plan from Quiz")
                        plan_quiz_output = gr.Textbox(label="Plan Output", lines=10)

                        start_btn.click(
                            lambda sub, lang: start_quiz(sub, lang, retriever),
                            [quiz_subject, lang_select],
                            [quiz_question, quiz_state, quiz_result],
                        )
                        btn_a.click(lambda st: answer_quiz("a", st), quiz_state, [quiz_question, quiz_state, quiz_result])
                        btn_b.click(lambda st: answer_quiz("b", st), quiz_state, [quiz_question, quiz_state, quiz_result])
                        btn_c.click(lambda st: answer_quiz("c", st), quiz_state, [quiz_question, quiz_state, quiz_result])
                        btn_d.click(lambda st: answer_quiz("d", st), quiz_state, [quiz_question, quiz_state, quiz_result])
                        plan_quiz_btn.click(
                            run_learning_plan_from_quiz,
                            [quiz_name, quiz_state, lang_select],
                            plan_quiz_output,
                        )

                # “Learning plan” 功能组
                with gr.Group(visible=False) as plan_group:
                    with gr.Blocks() as plan_blocks:
                        gr.Markdown("### Learning plan 🗺️")
                        plan_name = gr.Textbox(label="Your name")
                        plan_goals = gr.Textbox(label="Learning goals (semicolon separated)")
                        plan_btn = gr.Button("Generate Plan", variant="primary")
                        plan_output = gr.Textbox(label="Plan Output", lines=10)
                        plan_btn.click(
                            run_learning_plan_interface,
                            [plan_name, plan_goals, lang_select],
                            plan_output,
                        )

                # “Summary” 功能组
                with gr.Group(visible=False) as summary_group:
                    with gr.Blocks() as summary_blocks:
                        gr.Markdown("### Summary 📜")
                        sum_topic = gr.Textbox(label="Topic or material")
                        sum_btn = gr.Button("Generate Summary", variant="primary")
                        sum_output = gr.Textbox(label="Summary", lines=10)
                        sum_btn.click(
                            lambda t, l: run_summary_interface(t, l, retriever),
                            [sum_topic, lang_select],
                            sum_output,
                        )

                # --- 控制 UI 显隐的逻辑 ---
                all_groups = [chat_group, quiz_group, plan_group, summary_group, upload_group]
                
                def switch_feature_visibility(feature_name: str):
                    """根据下拉菜单的选择，更新各个功能组的可见性。"""
                    is_visible = {choice: (feature_name == choice) for choice in feature_choices}
                    return {
                        chat_group: gr.update(visible=is_visible[feature_choices[0]]),
                        quiz_group: gr.update(visible=is_visible[feature_choices[1]]),
                        plan_group: gr.update(visible=is_visible[feature_choices[2]]),
                        summary_group: gr.update(visible=is_visible[feature_choices[3]]),
                        upload_group: gr.update(visible=is_visible[feature_choices[4]]),
                    }
                
                feature_select.change(
                    fn=switch_feature_visibility,
                    inputs=feature_select,
                    outputs=all_groups,
                    queue=False  # 界面切换无需排队，响应更快
                )

    return demo


def launch_gradio() -> None:
    """启动 Gradio 应用。"""
    demo = build_interface()
    demo.queue()
    demo.launch()


if __name__ == "__main__":
    launch_gradio()