import importlib

def test_respond_with_retriever_stream(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    # stub dependencies before importing interface
    monkeypatch.setattr("AgentModule.create_agent", lambda: object())

    def fake_run_agent(message, executor=None, retriever=None, return_details=False):
        return "answer", False, False

    monkeypatch.setattr("AgentModule.edu_agent.run_agent", fake_run_agent)

    class DummyRag:
        def get_retriever(self, *_, **__):
            return None
        def ingest_paths(self, *args, **kwargs):
            return None

    monkeypatch.setattr("tools.rag_service.get_rag_service", lambda: DummyRag())

    interface = importlib.import_module("frontend_service.interface")
    monkeypatch.setattr(interface.LanguageHandler, "code_from_display", lambda _: "en")
    monkeypatch.setattr(interface.LanguageHandler, "choose_or_detect", lambda _: "en")
    monkeypatch.setattr(interface.LanguageHandler, "ensure_language", lambda t, l: t)
    gen = interface.respond_with_retriever("hello", [], "en")
    first_history, _ = next(gen)
    assert first_history[-2] == {"role": "user", "content": "hello"}
    assert first_history[-1] == {"role": "assistant", "content": "..."}
    second_history, _ = next(gen)
    assert second_history[-1] == {"role": "assistant", "content": "answer"}
