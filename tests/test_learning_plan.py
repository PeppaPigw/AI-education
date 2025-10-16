import LearningPlanModule.learning_plan as lp
from langchain.schema.runnable import Runnable


class FakeLLM(Runnable):
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, prompt, config=None):
        class Msg:
            content = "Book1\nBook2"

        return Msg()


def test_recommend_materials(monkeypatch):
    class DummyRetriever:
        def get_relevant_documents(self, query):
            return []

    class DummyService:
        def get_retriever(self):
            return DummyRetriever()

    monkeypatch.setattr(lp, "ChatOpenAI", FakeLLM)
    monkeypatch.setattr(lp, "RAGService", lambda: DummyService())
    plan = lp.LearningPlan("Alice")
    materials = plan.recommend_materials("math")
    assert materials == ["Book1", "Book2"]
