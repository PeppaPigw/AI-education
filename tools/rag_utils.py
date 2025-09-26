"""Helper utilities for retrieval-augmented generation."""

from __future__ import annotations

import logging
import re
from typing import Any


def get_context_or_empty(query: str, retriever: Any | None) -> str:
    """Return joined page contents for ``query`` using ``retriever``.

    If ``retriever`` is ``None``, retrieval fails, or no relevant documents are
    found, an empty string is returned. Retrieved documents are considered
    relevant only if they share at least one non-trivial word with the query so
    that unrelated RAG content does not override the user's request.
    """
    if not retriever:
        return ""

    try:
        if hasattr(retriever, "get_relevant_documents"):
            docs = retriever.get_relevant_documents(query)
        else:
            docs = retriever.invoke(query)
    except Exception as exc:  # pragma: no cover - retrieval errors
        logging.getLogger(__name__).warning("Retrieval failed: %s", exc)
        return ""

    if not docs:
        return ""

    # Build a set of meaningful query words (length >= 3) to check relevance.
    keywords = set(re.findall(r"\b\w{3,}\b", query.lower()))
    relevant_contents = []
    for doc in docs:
        text = getattr(doc, "page_content", str(doc))
        lower = text.lower()
        if not keywords or any(word in lower for word in keywords):
            relevant_contents.append(text)

    if not relevant_contents:
        return ""

    return "\n\n".join(relevant_contents)
