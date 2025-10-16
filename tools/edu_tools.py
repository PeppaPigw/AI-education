from __future__ import annotations
from tools.language_handler import LanguageHandler
from langchain.tools import tool
from nltk.corpus import wordnet as wn
from datetime import datetime
import logging
import nltk

try:
    import wikipedia  # type: ignore
except Exception:  # pragma: no cover - wikipedia may not be installed
    wikipedia = None


@tool
def wikipedia_search(query: str) -> str:
    """Return a short summary for a topic from Wikipedia."""
    if wikipedia is None:
        return "wikipedia library not available."
    try:
        return wikipedia.summary(query, sentences=3)
    except Exception as e:  # pragma: no cover - network issues
        return f"Error fetching data from Wikipedia: {e}"


@tool
def define_word(word: str) -> str:
    """Give dictionary definitions for a word using WordNet."""
    try:
        synsets = wn.synsets(word)
    except LookupError:
        try:
            nltk.download("wordnet", quiet=True)
            synsets = wn.synsets(word)
        except Exception:
            msg = "Missing NLTK 'wordnet' data. Run nltk.download('wordnet')"
            logging.getLogger(__name__).error(msg)
            return msg
    try:
        if not synsets:
            return "No definition found."
        defs = {s.definition() for s in synsets}
        return "; ".join(sorted(defs))
    except Exception as e:  # pragma: no cover
        return f"Error retrieving definition: {e}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    try:
        allowed_names = {"__builtins__": None}
        result = eval(expression, allowed_names, {})
        return str(result)
    except Exception as e:  # pragma: no cover - invalid expression
        return f"Error evaluating expression: {e}"


@tool
def current_date(unused: str = "") -> str:
    """Return today's date in ISO format."""
    return datetime.utcnow().strftime("%Y-%m-%d")


@tool
def current_weekday(unused: str = "") -> str:
    """Return the current day of the week."""
    return datetime.utcnow().strftime("%A")


@tool
def detect_language(text: str) -> str:
    """Detect the language of a given text sample."""
    try:
        return LanguageHandler.detect_language(text)
    except Exception as e:  # pragma: no cover - detection errors
        return f"Error detecting language: {e}"
