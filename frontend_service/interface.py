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

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from AgentModule import create_agent
from AgentModule.edu_agent import run_agent
from CheatSheetModule import CheatSheetGenerator
from FlashcardsModule import FlashcardSet
from LearningPlanModule import LearningPlan
from QuizModule import generate_learning_plan_from_quiz, prepare_quiz_questions
from SummaryModule import StudySummaryGenerator
from tools.language_handler import LanguageHandler
from tools.rag_service import get_rag_service

dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(dotenv_path)


if not os.environ.get("api_key"):
    raise RuntimeError(
        "api_key is not set. Create a .env file or export the variable."
    )

agent = create_agent()
rag_service = get_rag_service()
retriever = rag_service.get_retriever()

logger = logging.getLogger(__name__)

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
#flashcard-container {
  background-color: #fffbe6;
  border: 1px solid #ffd580;
  border-radius: 8px;
  padding: 16px;
  max-width: 500px;
  margin: auto;
  text-align: center;
  width: fit-content;
}
#flashcard-content {
  min-height: 120px;
  font-size: 1.1em;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}
#flashcard-buttons {
  display: grid;
  grid-template-columns: repeat(2, auto);
  gap: 4px;
  justify-content: center;
}
#flashcard-buttons button {
  width: 48px;
  margin: 0;
}
#flashcard-counter {
  font-weight: bold;
  margin-top: 8px;
}
#flashcard-container .wrap,
#flashcard-container .progress-text,
#flashcard-container .progress-bar-wrap,
#flashcard-container .eta-bar {
  display: none !important;
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
    """Return updated chat history and logs.

    The user's message is yielded immediately so it appears in the UI while the
    bot processes the response.
    """

    # show the user's message right away with a placeholder for the response
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

    # replace the placeholder with the actual response
    history[-1] = {"role": "assistant", "content": result}
    logs = buffer.getvalue()
    yield history, logs


def respond_with_retriever(message: str, history: list[dict], lang_choice: str):
    """Wrapper injecting the shared retriever into :func:`respond`."""
    yield from respond(message, history, lang_choice, retriever)


def process_knowledge(files: list):
    """Save uploaded files and ingest them into the RAG service.

    Emits status updates so the UI can show progress and final result.
    """

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
    # ensure each answer choice appears on its own line
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


def _init_flashcard_state(cards: list[dict]) -> dict:
    """Return a new flashcard navigation state."""
    return {"cards": cards, "index": 0, "side": "question"}


def _render_flashcard(state: dict) -> str:
    """Return the currently visible side of the flashcard."""
    if not state or not state.get("cards"):
        return ""
    card = state["cards"][state["index"]]
    side = state.get("side", "question")
    return card.get(side, "")


def run_flashcards_generate(
    topic: str, lang_choice: str, retriever=None
) -> tuple[str, dict, str, str]:
    """Generate flashcards from a topic and prepare viewer state."""
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(topic)
    flashcards = FlashcardSet(topic, retriever=retriever)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        used_retriever = flashcards.generate_from_prompt(
            topic_prompt=topic, language=language, retriever=retriever
        )
        path = flashcards.save_to_file()
    logs = buffer.getvalue()
    notice = (
        "📄 Flashcards generated with document context"
        if used_retriever
        else "⚠️ Flashcards generated without document context"
    )
    logs = notice + ("\n" + logs if logs else "")
    if path:
        logs += f"\nSaved to: {path}"
    cards = flashcards.to_dict_list()
    state = _init_flashcard_state(cards)
    first = _render_flashcard(state)
    progress = f"1/{len(cards)}" if cards else "0/0"
    return first, state, logs, progress

def run_flashcards_review(path: str) -> tuple[str, dict, str]:
    """Load flashcards from file for interactive review."""
    flashcards = FlashcardSet.load_from_file(path)
    if not flashcards:
        return "Failed to load flashcards.", {}, "0/0"
    cards = flashcards.to_dict_list()
    state = _init_flashcard_state(cards)
    first = _render_flashcard(state)
    progress = f"1/{len(cards)}" if cards else "0/0"
    return first, state, progress


def flashcard_flip(state: dict) -> tuple[str, dict]:
    """Flip between question and answer."""
    if not state or not state.get("cards"):
        return "", state
    state["side"] = "answer" if state.get("side") == "question" else "question"
    return _render_flashcard(state), state


def flashcard_next(state: dict) -> tuple[str, dict, str]:
    """Move to the next flashcard."""
    if not state or not state.get("cards"):
        return "", state, "0/0"
    state["index"] = (state["index"] + 1) % len(state["cards"])
    state["side"] = "question"
    return (
        _render_flashcard(state),
        state,
        f"{state['index'] + 1}/{len(state['cards'])}",
    )


def flashcard_prev(state: dict) -> tuple[str, dict, str]:
    """Move to the previous flashcard."""
    if not state or not state.get("cards"):
        return "", state, "0/0"
    state["index"] = (state["index"] - 1) % len(state["cards"])
    state["side"] = "question"
    return (
        _render_flashcard(state),
        state,
        f"{state['index'] + 1}/{len(state['cards'])}",
    )


def flashcard_shuffle(state: dict) -> tuple[str, dict, str]:
    """Shuffle flashcards order and restart."""
    if not state or not state.get("cards"):
        return "", state, "0/0"
    random.shuffle(state["cards"])
    state["index"] = 0
    state["side"] = "question"
    return _render_flashcard(state), state, f"1/{len(state['cards'])}"


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


def run_cheatsheet_interface(topic: str, lang_choice: str, retriever=None) -> str:
    """Generate a cheat sheet."""
    code = LanguageHandler.code_from_display(lang_choice)
    language = code if code != "auto" else LanguageHandler.choose_or_detect(topic)
    generator = CheatSheetGenerator(retriever=retriever)
    sheet, used_retriever = generator.generate_cheatsheet(
        topic, language=language, retriever=retriever
    )
    notice = (
        "📄 Cheat sheet generated with document context"
        if used_retriever
        else "⚠️ Cheat sheet generated without document context"
    )
    return f"{notice}\n\n{sheet}"


def build_interface() -> gr.Blocks:
    """Create the Gradio UI replicating the CLI menu."""
    with gr.Blocks(css=CSS, theme=gr.themes.Soft()) as demo:
        gr.Markdown("# EduGen", elem_id="title")
        lang_select = gr.Dropdown(
            choices=LanguageHandler.dropdown_choices(),
            value=LanguageHandler.dropdown_choices()[0],
            label="Language",
        )

        with gr.Accordion("Upload Knowledge", open=False):
            upload_files = gr.File(file_count="multiple")
            process_btn = gr.Button("Process")
            upload_status = gr.Markdown()
            process_btn.click(process_knowledge, upload_files, upload_status)

        with gr.Tabs():
            # Chat tab
            with gr.TabItem("Chat with the bot"):
                chatbot = gr.Chatbot(elem_id="chatbot", type="messages")
                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Type your message and press enter...",
                        container=False,
                    )
                    send = gr.Button("Send", variant="primary")
                    clear = gr.Button("Clear")
                logs = gr.Textbox(label="Terminal output", lines=8)

                def clear_history():
                    return [], ""

                msg.submit(
                    respond_with_retriever,
                    [msg, chatbot, lang_select],
                    [chatbot, logs],
                )
                send.click(
                    respond_with_retriever,
                    [msg, chatbot, lang_select],
                    [chatbot, logs],
                )
                clear.click(clear_history, None, [chatbot, logs])

            # Quiz tab
            with gr.TabItem("Generate quiz"):
                quiz_subject = gr.Textbox(label="Subject")
                start_btn = gr.Button("Start Quiz")
                quiz_question = gr.Markdown()
                with gr.Row():
                    btn_a = gr.Button("A")
                    btn_b = gr.Button("B")
                    btn_c = gr.Button("C")
                    btn_d = gr.Button("D")
                quiz_result = gr.Markdown()
                quiz_name = gr.Textbox(label="Your name")
                plan_quiz_btn = gr.Button("Generate Learning Plan from Quiz")
                plan_quiz_output = gr.Textbox(label="Plan Output", lines=10)
                quiz_state = gr.State()

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

            # Learning plan tab
            with gr.TabItem("Learning plan"):
                plan_name = gr.Textbox(label="Your name")
                plan_goals = gr.Textbox(label="Learning goals (semicolon separated)")
                plan_btn = gr.Button("Generate Plan")
                plan_output = gr.Textbox(label="Plan Output", lines=10)
                plan_btn.click(
                    run_learning_plan_interface,
                    [plan_name, plan_goals, lang_select],
                    plan_output,
                )

            # Flashcards tab
            with gr.TabItem("Flashcards"):
                with gr.Accordion("Generate flashcards", open=True):
                    fc_topic = gr.Textbox(label="Topic")
                    fc_gen_btn = gr.Button("Generate")
                    with gr.Column(elem_id="flashcard-container"):
                        fc_card = gr.Markdown(elem_id="flashcard-content")
                        with gr.Column(elem_id="flashcard-buttons"):
                            fc_prev = gr.Button("⬅️", size="sm", scale=0)
                            fc_next = gr.Button("➡️", size="sm", scale=0)
                            fc_flip = gr.Button("🔄", size="sm", scale=0)
                            fc_shuffle = gr.Button("🔀", size="sm", scale=0)
                        fc_counter = gr.Markdown("0/0", elem_id="flashcard-counter")
                    fc_logs = gr.Textbox(label="Logs", lines=4)
                    fc_state = gr.State()

                    fc_gen_btn.click(
                        lambda topic, lang: run_flashcards_generate(
                            topic, lang, retriever
                        ),
                        [fc_topic, lang_select],
                        [fc_card, fc_state, fc_logs, fc_counter],
                        show_progress=False,
                    )
                    fc_flip.click(
                        flashcard_flip,
                        fc_state,
                        [fc_card, fc_state],
                        show_progress=False,
                    )
                    fc_next.click(
                        flashcard_next,
                        fc_state,
                        [fc_card, fc_state, fc_counter],
                        show_progress=False,
                    )
                    fc_prev.click(
                        flashcard_prev,
                        fc_state,
                        [fc_card, fc_state, fc_counter],
                        show_progress=False,
                    )
                    fc_shuffle.click(
                        flashcard_shuffle,
                        fc_state,
                        [fc_card, fc_state, fc_counter],
                        show_progress=False,
                    )

                with gr.Accordion("Review flashcards", open=False):
                    fc_path = gr.Textbox(label="Path to flashcards JSON")
                    fc_load_btn = gr.Button("Load")
                    fc_load_btn.click(
                        run_flashcards_review,
                        fc_path,
                        [fc_card, fc_state, fc_counter],
                        show_progress=False,
                    )

            # Summary tab
            with gr.TabItem("Summary"):
                sum_topic = gr.Textbox(label="Topic or material")
                sum_btn = gr.Button("Generate Summary")
                sum_output = gr.Textbox(label="Summary", lines=10)
                sum_btn.click(
                    lambda t, l: run_summary_interface(t, l, retriever),
                    [sum_topic, lang_select],
                    sum_output,
                )

            # Cheat sheet tab
            with gr.TabItem("Cheat sheet"):
                cs_topic = gr.Textbox(label="Topic or material")
                cs_btn = gr.Button("Generate Cheat Sheet")
                cs_output = gr.Textbox(label="Cheat Sheet", lines=10)
                cs_btn.click(
                    lambda t, l: run_cheatsheet_interface(t, l, retriever),
                    [cs_topic, lang_select],
                    cs_output,
                )

    return demo


def launch_gradio() -> None:
    demo = build_interface()
    demo.queue()
    demo.launch()
