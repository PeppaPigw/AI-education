import os
import json
import re
import tools.language_handler as lh
from tools.language_handler import LanguageHandler


def test_set_get_and_choose_language(temp_config_path):
    LanguageHandler.set_language("en")
    assert LanguageHandler.get_language() == "en"
    LanguageHandler.set_language("auto")
    lang = LanguageHandler.choose_or_detect("Cześć")
    assert lang == "pl"


def test_ensure_language_translates(monkeypatch):
    monkeypatch.setattr(LanguageHandler, "detect_language", lambda text: "pl")

    class DummyTranslator:
        def __init__(self, source="auto", target="en"):
            self.source = source
            self.target = target

        def translate(self, text: str) -> str:
            return "hello"

    monkeypatch.setattr(lh, "GoogleTranslator", DummyTranslator)
    result = LanguageHandler.ensure_language("cześć", "en")
    assert result == "hello"


def test_ensure_language_no_translation(monkeypatch):
    monkeypatch.setattr(LanguageHandler, "detect_language", lambda text: "en")
    result = LanguageHandler.ensure_language("hello", "en")
    assert result == "hello"
