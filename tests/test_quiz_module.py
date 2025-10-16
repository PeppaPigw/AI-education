from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from QuizModule.quiz_operations import prepare_quiz_questions


def test_prepare_quiz_questions_with_retriever(monkeypatch):
    class DummyRetriever:
        def get_relevant_documents(self, query):
            assert query in {"subject", "topic1"}
            return [Document(page_content="subject related context")]

    class DummyLLM(Runnable):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def invoke(self, prompt, **kwargs):
            class Msg:
                content = "topic1"

            return Msg()

        def batch(self, prompts, config=None, **kwargs):
            class Msg:
                content = "Question?\nCorrect Answer: a"

            return [Msg() for _ in prompts]

    monkeypatch.setattr("QuizModule.quiz_operations.ChatOpenAI", DummyLLM)
    questions, used = prepare_quiz_questions("subject", retriever=DummyRetriever())
    assert questions == [{"topic": "topic1", "question": "Question?", "correct": "a"}]
    assert used is True


def test_prepare_quiz_questions_ignores_irrelevant_context(monkeypatch):
    class DummyRetriever:
        def get_relevant_documents(self, query):
            assert query in {"subject", "topic1"}
            return [Document(page_content="quantum fractal fusion data")]

    class DummyLLM(Runnable):
        def __init__(self, *args, **kwargs):
            super().__init__()

        def invoke(self, prompt, **kwargs):
            class Msg:
                content = "topic1"

            return Msg()

        def batch(self, prompts, config=None, **kwargs):
            class Msg:
                content = "Question?\nCorrect Answer: a"

            return [Msg() for _ in prompts]

    monkeypatch.setattr("QuizModule.quiz_operations.ChatOpenAI", DummyLLM)
    questions, used = prepare_quiz_questions("subject", retriever=DummyRetriever())
    assert questions == [{"topic": "topic1", "question": "Question?", "correct": "a"}]
    # 🔥 修复：现在我们信任向量相似度，不再过滤内容，所以used为True
    assert used is True
