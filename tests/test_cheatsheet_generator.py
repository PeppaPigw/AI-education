import CheatSheetModule.cheatsheet_generator as cg
from langchain.schema.runnable import Runnable


class FakeLLM(Runnable):
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, prompt, config=None):
        class Msg:
            content = "cheatsheet"
        return Msg()


def test_generate_cheatsheet(monkeypatch):
    class DummyRetriever:
        def get_relevant_documents(self, query):
            return []

    class DummyService:
        def get_retriever(self):
            return DummyRetriever()

    monkeypatch.setattr(cg, "ChatOpenAI", FakeLLM)
    monkeypatch.setattr(cg, "RAGService", lambda: DummyService())
    generator = cg.CheatSheetGenerator()
    result, used = generator.generate_cheatsheet("topic")
    assert result == "cheatsheet"
    assert used is False
