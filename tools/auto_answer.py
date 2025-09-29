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
    "es": {
        "qué",
        "quién",
        "quien",
        "dónde",
        "cuándo",
        "cómo",
        "por qué"
    },
    "fr": {
        "qui",
        "quoi",
        "où",
        "quand",
        "pourquoi",
        "comment"
    },
    "de": {
        "wer",
        "was",
        "wo",
        "wann",
        "warum",
        "wie"
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
    """Run the agent if ``text`` looks like a question.

    The detection is heuristic and checks for a trailing question mark or the
    use of common question words in several popular languages. When activated,
    the agent's reply is printed and ``True`` is returned. Otherwise ``False`` is
    returned.
    """
    if looks_like_question(text):
        agent = agent or create_agent()
        language = LanguageHandler.choose_or_detect(text)
        answer, used_fallback, used_retriever = run_agent(
            text, executor=agent, return_details=True
        )
        answer = LanguageHandler.ensure_language(answer, language)
        if used_fallback:
            notice = LanguageHandler.ensure_language(
                "This response may not be accurate. It was created using a LMM fallback mechanism.",
                language,
            )
            answer = f"{notice}\n{answer}"
        elif used_retriever:
            notice = LanguageHandler.ensure_language(
                "This response was created using a document retrieval mechanism.",
                language,
            )
            answer = f"{notice}\n{answer}"
        print(f"\n\U0001f916 Agent Answer:\n{answer}\n")
        return True
    return False
