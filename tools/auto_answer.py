from __future__ import annotations

from typing import Optional
from AgentModule.edu_agent import create_agent, run_agent, AgentExecutor
from tools.language_handler import LanguageHandler


QUESTION_WORDS = {
    "en": {
        "what",
        "who",
        "where",
        "when",
        "why",
        "how",
        "is",
        "are",
        "do",
        "does",
        "did",
        "can",
        "could",
        "would",
        "will",
        "should",
    },
    "pl": {
        "czy",
        "co",
        "kiedy",
        "gdzie",
        "dlaczego",
        "jak",
        "kto",
        "który",
        "która",
        "które",
    },
    "es": {"qué", "quién", "quien", "dónde", "cuándo", "cómo", "por qué"},
    "fr": {"qui", "quoi", "où", "quand", "pourquoi", "comment"},
    "de": {"wer", "was", "wo", "wann", "warum", "wie"},
    "zh": {
        "什么",
        "谁",
        "哪里",
        "哪儿",
        "何时",
        "怎么",
        "为什么",
        "几",
        "多少",
        "吗",
        "嘛",
        "呢",
        "要不要",
        "是不是",
        "有没有",
        "可不可以",
        "该不该",
        "为什么说",
        "你是",
    },
}


def looks_like_question(text: str) -> bool:
    """Heuristically determine if ``text`` is a question."""
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith("?"):
        return True
    first_word = stripped.split()[0].lower().strip("¿¡")
    lang = LanguageHandler.detect_language(text).split("-")[0]
    words = QUESTION_WORDS.get(lang)
    if words and first_word in words:
        return True
    return any(first_word in ws for ws in QUESTION_WORDS.values())


def auto_answer(text: str, agent: Optional[AgentExecutor] = None) -> bool:
    if looks_like_question(text):
        agent = agent or create_agent()
        language = LanguageHandler.choose_or_detect(text)
        answer, used_fallback, used_retriever = run_agent(
            text, executor=agent, return_details=True
        )
        answer = LanguageHandler.ensure_language(answer, language)
        answer = f"{answer}"
        print(f"\n\U0001f916 Agent Answer:\n{answer}\n")
        return True
    return False
