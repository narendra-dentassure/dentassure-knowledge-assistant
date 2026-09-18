"""Build or rebuild the local knowledge index from sample documents."""

from __future__ import annotations

from src.chunking import chunk_documents
from src.config import get_settings
from src.document_loader import load_documents
from src.hybrid_retriever import HybridRetriever
from src.logging_setup import configure_logging
from src.vectorstore import collection_is_ready, upsert_chunks

logger = configure_logging()


def ingest_corpus(force: bool = False) -> dict:
    """Load documents, chunk, embed, and persist them to Chroma.

    Returns a summary used by the Streamlit Documents tab.
    """
    settings = get_settings()
    documents = load_documents(settings.data_dir)
    chunks = chunk_documents(
        documents,
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )

    already_ready = collection_is_ready(settings.chroma_dir)
    if force or not already_ready:
        stored = upsert_chunks(settings.chroma_dir, chunks)
        logger.info("Index rebuild complete: %s chunks", stored)
    else:
        stored = len(chunks)
        logger.info("Existing Chroma index reused")

    return {
        "document_count": len(documents),
        "chunk_count": stored,
        "files": [
            {
                "name": doc.source,
                "type": doc.file_type,
                "pages": len(doc.pages),
            }
            for doc in documents
        ],
        "chunks": chunks,
        "retriever": HybridRetriever(chunks, settings.chroma_dir),
        "rebuilt": force or not already_ready,
    }
