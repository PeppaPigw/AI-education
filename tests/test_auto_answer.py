import pytest
from tools import auto_answer
import tools.language_handler as lh


@pytest.mark.parametrize(
    "text,expected",
    [("Is this working?", True), ("This is a statement.", False)],
)
def test_looks_like_question_mark(text, expected):
    assert auto_answer.looks_like_question(text) is expected


def test_looks_like_question_word(monkeypatch):
    monkeypatch.setattr(lh.LanguageHandler, "detect_language", lambda text: "pl")
    assert auto_answer.looks_like_question("Kto to jest")
