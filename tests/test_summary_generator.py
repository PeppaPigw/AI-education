import SummaryModule.summary_generator as sg
from langchain.schema.runnable import Runnable


class FakeLLM(Runnable):
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, prompt, config=None):
        class Msg:
            content = "summary"
        return Msg()


def test_generate_summary(monkeypatch):
    class DummyRetriever:
        def get_relevant_documents(self, query):
            return []

    class DummyService:
        def get_retriever(self):
            return DummyRetriever()

    monkeypatch.setattr(sg, "ChatOpenAI", FakeLLM)
    monkeypatch.setattr(sg, "RAGService", lambda: DummyService())
    generator = sg.StudySummaryGenerator()
    result, used = generator.generate_summary("topic")
    assert result == "summary"
    assert used is False
