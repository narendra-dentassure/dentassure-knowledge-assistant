"""Split loaded documents into overlapping retrieval chunks."""

from __future__ import annotations

from dataclasses import dataclass

from src.document_loader import LoadedDocument
from src.logging_setup import configure_logging

logger = configure_logging()


@dataclass
class Chunk:
    """A retrievable text chunk with source metadata."""

    chunk_id: str
    text: str
    source: str
    page: int
    file_type: str


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(words):
            break
        start = max(end - overlap, start + 1)
    return chunks


def chunk_documents(
    documents: list[LoadedDocument],
    chunk_size: int = 900,
    overlap: int = 150,
) -> list[Chunk]:
    """Create overlapping word chunks from loaded documents."""
    # chunk_size is treated as approximate word count for stable local splitting.
    word_chunk_size = max(80, chunk_size // 6)
    word_overlap = max(20, overlap // 6)

    chunks: list[Chunk] = []
    counter = 0
    for document in documents:
        for page_number, page_text in document.pages:
            parts = _split_text(page_text, word_chunk_size, word_overlap)
            for part in parts:
                counter += 1
                chunks.append(
                    Chunk(
                        chunk_id=f"chunk_{counter:04d}",
                        text=part,
                        source=document.source,
                        page=page_number,
                        file_type=document.file_type,
                    )
                )

    logger.info("Created %s chunks from %s documents", len(chunks), len(documents))
    return chunks
