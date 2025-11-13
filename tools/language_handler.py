import os
import json
from langdetect import detect
import langid
from deep_translator import GoogleTranslator

CONFIG_PATH = os.path.join("data", "user_config.json")

SUPPORTED_LANGUAGES = [
    "auto",
    "zh",
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
    "ar",
    "he",
]

LANGUAGE_LABELS = {
    "auto": "\U0001f310 Auto-detect",
    "zh": "\U0001f1e8\U0001f1f3 ZH 中文",
    "en": "\U0001f1ec\U0001f1e7 EN English",
    "pl": "\U0001f1f5\U0001f1f1 PL Polski",
    "cs": "\U0001f1e8\U0001f1ff CS Čeština",
    "sk": "\U0001f1f8\U0001f1f0 SK Slovenčina",
    "de": "\U0001f1e9\U0001f1ea DE Deutsch",
    "fr": "\U0001f1eb\U0001f1f7 FR Français",
    "es": "\U0001f1ea\U0001f1f8 ES Español",
    "it": "\U0001f1ee\U0001f1f9 IT Italiano",
    "pt": "\U0001f1f5\U0001f1f9 PT Português",
    "ru": "\U0001f1f7\U0001f1fa RU Русский",
    "uk": "\U0001f1fa\U0001f1e6 UK Українська",
    "nl": "\U0001f1f3\U0001f1f1 NL Nederlands",
    "sv": "\U0001f1f8\U0001f1ea SV Svenska",
    "fi": "\U0001f1eb\U0001f1ee FI Suomi",
    "no": "\U0001f1f3\U0001f1f4 NO Norsk",
    "da": "\U0001f1e9\U0001f1f0 DA Dansk",
    "tr": "\U0001f1f9\U0001f1f7 TR Türkçe",
    "ja": "\U0001f1ef\U0001f1f5 JA 日本語",
    "ko": "\U0001f1f0\U0001f1f7 KO 한국어",
    "ar": "\U0001f1f8\U0001f1e6 AR العربية",
    "he": "\U0001f1ee\U0001f1f1 HE עברית",
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
