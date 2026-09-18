"""Chunking unit tests."""

from src.chunking import Chunk, chunk_documents
from src.document_loader import LoadedDocument


def test_chunk_documents_creates_overlapping_chunks() -> None:
    text = " ".join(f"word{i}" for i in range(400))
    documents = [LoadedDocument(source="sop.txt", file_type="txt", pages=[(1, text)])]
    chunks = chunk_documents(documents, chunk_size=600, overlap=120)
    assert len(chunks) >= 2
    assert all(isinstance(chunk, Chunk) for chunk in chunks)
    assert chunks[0].source == "sop.txt"
    assert chunks[0].page == 1
    assert chunks[0].chunk_id.startswith("chunk_")


def test_empty_document_yields_no_chunks() -> None:
    documents = [LoadedDocument(source="empty.txt", file_type="txt", pages=[(1, "   ")])]
    assert chunk_documents(documents) == []
