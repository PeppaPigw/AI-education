import pytest
import AgentModule.edu_agent as ea
import tools.language_handler as lh
from langchain_core.documents import Document


class DummyExecutor:
    def __init__(self, output):
        self.output = output

    def invoke(self, inputs):
        return {"output": self.output}


class FakeLLM:
    def __init__(self, *args, **kwargs):
        pass

    def invoke(self, prompt):
        class Msg:
            content = "Fallback answer"
        return Msg()

    def bind(self, **kwargs):
        return self


@pytest.fixture
def patched_agent(monkeypatch):
    monkeypatch.setattr(lh.LanguageHandler, "choose_or_detect", lambda text: "en")
    monkeypatch.setattr(lh.LanguageHandler, "ensure_language", lambda text, lang: text)
    monkeypatch.setattr(ea, "ChatOpenAI", FakeLLM)
    return lambda output: DummyExecutor(output)


def test_rag_search(monkeypatch):
    class DummyRetriever:
        def invoke(self, query):
            assert query == "cats"
            return [Document(page_content="cats one"), Document(page_content="cats two")]

    class DummyService:
        def get_retriever(self):
            return DummyRetriever()

    monkeypatch.setattr(ea, "RAGService", lambda: DummyService())
    result = ea.rag_search("cats")
    assert result == "cats one\n\ncats two"


def test_create_agent_includes_rag_search(monkeypatch):
    class DummyAgentExecutor:
        def __init__(self, agent, tools, verbose):
            self.agent = agent
            self.tools = tools

    def fake_create_react_agent(llm, tools, prompt):
        return object()

    monkeypatch.setattr(ea, "ChatOpenAI", FakeLLM)
    monkeypatch.setattr(ea, "create_react_agent", fake_create_react_agent)
    monkeypatch.setattr(ea, "AgentExecutor", DummyAgentExecutor)
    exec_ = ea.create_agent()
    assert any(t.name == "rag_search" for t in exec_.tools)


def test_run_agent_no_fallback(patched_agent):
    executor = patched_agent("The capital is Warsaw")
    output, used_fallback, used_retriever = ea.run_agent(
        "Question", executor=executor, return_details=True
    )
    assert output == "The capital is Warsaw"
    assert used_fallback is False
    assert used_retriever is False


def test_run_agent_with_fallback(patched_agent):
    executor = patched_agent("error: something broke")
    output, used_fallback, used_retriever = ea.run_agent(
        "Question", executor=executor, return_details=True
    )
    assert output == "Fallback answer"
    assert used_fallback is True
    assert used_retriever is False


def test_run_agent_injects_retriever_context(monkeypatch):

    class RecordingExecutor:
        def __init__(self):
            self.last_input = None

        def invoke(self, inputs):
            self.last_input = inputs["input"]
            return {"output": "ok"}

    class DummyRetriever:
        def invoke(self, query):
            assert query == "Question"
            return [Document(page_content="context from retriever about question")]

    monkeypatch.setattr(lh.LanguageHandler, "choose_or_detect", lambda text: "en")
    monkeypatch.setattr(lh.LanguageHandler, "ensure_language", lambda text, lang: text)

    exec_ = RecordingExecutor()
    output, used_fallback, used_retriever = ea.run_agent(
        "Question", executor=exec_, retriever=DummyRetriever(), return_details=True
    )
    assert "context from retriever" in exec_.last_input
    assert output == "ok"
    assert used_fallback is False
    assert used_retriever is True
