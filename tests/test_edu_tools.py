import re
import tools.language_handler as lh
from tools import edu_tools as et


def test_define_word(monkeypatch):
    class FakeWN:
        def synsets(self, word):
            class FakeSynset:
                def __init__(self, definition):
                    self._def = definition

                def definition(self):
                    return self._def

            if word == "dog":
                return [FakeSynset("a domesticated canine")]
            return []

    monkeypatch.setattr(et, "wn", FakeWN())
    assert et.define_word.invoke("dog") == "a domesticated canine"
    assert et.define_word.invoke("asdfghjkl") == "No definition found."


def test_calculator():
    assert et.calculator.invoke("1 + 2*3") == "7"
    assert "Error" in et.calculator.invoke("1/0")


def test_current_date_format():
    date_str = et.current_date.invoke("")
    assert re.match(r"\d{4}-\d{2}-\d{2}", date_str)


def test_current_weekday():
    weekday = et.current_weekday.invoke("")
    assert weekday in [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]


def test_detect_language(monkeypatch):
    monkeypatch.setattr(lh.LanguageHandler, "detect_language", lambda text: "xx")
    assert et.detect_language.invoke("hello") == "xx"
