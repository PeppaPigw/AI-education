import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain_core.documents import Document
from tools.rag_utils import get_context_or_empty


class DummyRetriever:
    def __init__(self, docs):
        self._docs = docs

    def get_relevant_documents(self, query):
        return self._docs


def test_get_context_or_empty_returns_joined():
    retriever = DummyRetriever([Document(page_content="a"), Document(page_content="b")])
    assert get_context_or_empty("q", retriever) == "a\n\nb"


def test_get_context_or_empty_handles_empty():
    retriever = DummyRetriever([])
    assert get_context_or_empty("q", retriever) == ""


def test_get_context_or_empty_none_retriever():
    assert get_context_or_empty("q", None) == ""


def test_get_context_or_empty_filters_irrelevant():

    retriever = DummyRetriever([Document(page_content="quantum physics notes")])

    assert get_context_or_empty("art history", retriever) == "quantum physics notes"
