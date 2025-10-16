from __future__ import annotations

import logging
import re
from typing import Any


def get_context_or_empty(query: str, retriever: Any | None) -> str:
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

    relevant_contents = []
    for doc in docs:
        text = getattr(doc, "page_content", str(doc))
        relevant_contents.append(text)

    if not relevant_contents:
        return ""

    return "\n\n".join(relevant_contents)
