from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import (
    CSVLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredFileLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

from tools.rag_service import get_rag_service


LOADERS = {
    ".txt": TextLoader,
    ".md": UnstructuredMarkdownLoader,
    ".markdown": UnstructuredMarkdownLoader,
    ".pdf": PyPDFLoader,
    ".docx": UnstructuredWordDocumentLoader,
    ".pptx": UnstructuredPowerPointLoader,
    ".html": UnstructuredHTMLLoader,
    ".htm": UnstructuredHTMLLoader,
    ".csv": CSVLoader,
    ".epub": UnstructuredEPubLoader,
}


def load_file(path: Path) -> List[Document]:
    """Load ``path`` into a list of Documents using an appropriate loader."""
    loader_cls = LOADERS.get(path.suffix.lower())
    if loader_cls is None:
        loader = UnstructuredFileLoader(str(path))
    else:
        loader = loader_cls(str(path))
    docs = loader.load()
    for doc in docs:
        doc.metadata["source"] = str(path)
    return docs


def ingest_folder(folder: str = "data/RAG_files") -> tuple[int, int]:
    """Ingest all files from ``folder`` into the RAG vector store.

    Returns a tuple of ``(documents, chunks)`` ingested.
    """
    rag = get_rag_service()
    all_docs: List[Document] = []
    folder_path = Path(folder)
    for file_path in folder_path.glob("**/*"):
        if file_path.is_file():
            all_docs.extend(load_file(file_path))
    if not all_docs:
        return (0, 0)
    splitter = RecursiveCharacterTextSplitter()
    chunks = splitter.split_documents(all_docs)
    rag.ingest_paths(chunks)
    return len(all_docs), len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest documents into RAG store")
    parser.add_argument(
        "folder",
        nargs="?",
        default="data/RAG_files",
        help="Folder containing documents to ingest",
    )
    args = parser.parse_args()
    ingest_folder(args.folder)


if __name__ == "__main__":
    main()
