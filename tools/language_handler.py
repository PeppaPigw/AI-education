"""Utilities for detecting and translating languages.

This module centralizes language-related helpers such as detection,
configuration handling and translation. It is used across the project to
ensure consistent language behaviour.
"""

import os
import json
from langdetect import detect
import langid
from deep_translator import GoogleTranslator

CONFIG_PATH = os.path.join("data", "user_config.json")

SUPPORTED_LANGUAGES = [
    "auto",
    "en",
    "pl",
    "cs",
    "sk",
    "de",
    "fr",
    "es",
    "it",
    "pt",
    "ru",
    "uk",
    "nl",
    "sv",
    "fi",
    "no",
    "da",
    "tr",
    "ja",
    "ko",
    "zh",
    "ar",
    "he"
]

LANGUAGE_LABELS = {
    "auto": "\U0001F310 Auto-detect",
    "en": "\U0001F1EC\U0001F1E7 EN English",
    "pl": "\U0001F1F5\U0001F1F1 PL Polski",
    "cs": "\U0001F1E8\U0001F1FF CS Čeština",
    "sk": "\U0001F1F8\U0001F1F0 SK Slovenčina",
    "de": "\U0001F1E9\U0001F1EA DE Deutsch",
    "fr": "\U0001F1EB\U0001F1F7 FR Français",
    "es": "\U0001F1EA\U0001F1F8 ES Español",
    "it": "\U0001F1EE\U0001F1F9 IT Italiano",
    "pt": "\U0001F1F5\U0001F1F9 PT Português",
    "ru": "\U0001F1F7\U0001F1FA RU Русский",
    "uk": "\U0001F1FA\U0001F1E6 UK Українська",
    "nl": "\U0001F1F3\U0001F1F1 NL Nederlands",
    "sv": "\U0001F1F8\U0001F1EA SV Svenska",
    "fi": "\U0001F1EB\U0001F1EE FI Suomi",
    "no": "\U0001F1F3\U0001F1F4 NO Norsk",
    "da": "\U0001F1E9\U0001F1F0 DA Dansk",
    "tr": "\U0001F1F9\U0001F1F7 TR Türkçe",
    "ja": "\U0001F1EF\U0001F1F5 JA 日本語",
    "ko": "\U0001F1F0\U0001F1F7 KO 한국어",
    "zh": "\U0001F1E8\U0001F1F3 ZH 中文",
    "ar": "\U0001F1F8\U0001F1E6 AR العربية",
    "he": "\U0001F1EE\U0001F1F1 HE עברית",
}


class LanguageHandler:
    """High level helpers for language detection and translation."""
    @staticmethod
    def detect_language(text: str) -> str:
        """Return a language code detected from ``text``.

        ``langid`` is tried first with a limited set of supported languages to
        improve accuracy. If that fails, ``langdetect`` is used as a fallback
        and defaults to English when detection is impossible.
        """
        try:
            langid.set_languages([l for l in SUPPORTED_LANGUAGES if l != "auto"])
            lang, _ = langid.classify(text)
        except Exception:
            try:
                lang = detect(text)
            except Exception:
                lang = "en"
        return lang

    @staticmethod
    def set_language(lang_code: str) -> None:
        """Persist the user's preferred language code."""
        os.makedirs("data", exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"language": lang_code}, f)

    @staticmethod
    def get_language() -> str:
        """Return the stored preferred language or ``"auto"`` if unset."""
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, encoding="utf-8") as f:
                config = json.load(f)
                return config.get("language", "auto")
        return "auto"

    @staticmethod
    def choose_or_detect(text: str = None) -> str:
        """Return the configured language or detect it from ``text``."""
        user_lang = LanguageHandler.get_language()
        if user_lang == "auto" and text:
            return LanguageHandler.detect_language(text)
        return user_lang

    @staticmethod
    def translate(text: str, target: str) -> str:
        """Translate text to the target language using deep-translator."""
        # TODO: improve this feature, maybe use a different model for the whole LLM
        if not text or target == "auto":
            return text
        try:
            return GoogleTranslator(source="auto", target=target).translate(text)
        except Exception:
            return text

    @staticmethod
    def ensure_language(text: str, language: str) -> str:
        """Ensure the text is in the specified language, translating if needed."""
        if language == "auto" or not text:
            return text
        detected = LanguageHandler.detect_language(text)
        if detected != language:
            return LanguageHandler.translate(text, language)
        return text

    @staticmethod
    def supported_languages() -> list[str]:
        """Return the list of supported language codes."""
        return SUPPORTED_LANGUAGES

    @staticmethod
    def dropdown_choices() -> list[str]:
        """Return display strings for the language dropdown."""
        return [LANGUAGE_LABELS[code] for code in SUPPORTED_LANGUAGES]

    @staticmethod
    def code_from_display(display: str) -> str:
        """Map a dropdown display label back to its language code."""
        for code, label in LANGUAGE_LABELS.items():
            if label == display:
                return code
        return "auto"
