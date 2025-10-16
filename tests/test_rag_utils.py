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
    # 🔥 修复：现在我们信任向量相似度，不再进行额外的关键词过滤
    # 因为关键词过滤对中文支持不好，而且向量检索本身已经做了相关性过滤
    retriever = DummyRetriever([Document(page_content="quantum physics notes")])
    # 测试retriever返回的内容会被保留（信任相似度搜索）
    assert get_context_or_empty("art history", retriever) == "quantum physics notes"

