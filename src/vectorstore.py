"""Chroma vector store helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import chromadb

from src.chunking import Chunk
from src.embeddings import embed_texts
from src.logging_setup import configure_logging

logger = configure_logging()

COLLECTION_NAME = "dentassure_knowledge"


def get_collection(persist_dir: Path) -> Any:
    """Open or create the persistent Chroma collection."""
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def collection_is_ready(persist_dir: Path) -> bool:
    """Return True if the vector store already contains documents."""
    try:
        collection = get_collection(persist_dir)
        return collection.count() > 0
    except Exception:
        logger.exception("Unable to inspect Chroma collection")
        return False


def reset_collection(persist_dir: Path) -> Any:
    """Drop and recreate the collection."""
    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        logger.info("No existing collection to delete")
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(persist_dir: Path, chunks: list[Chunk]) -> int:
    """Embed chunks and store them in Chroma."""
    collection = reset_collection(persist_dir)
    texts = [chunk.text for chunk in chunks]
    embeddings = embed_texts(texts)
    collection.upsert(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {
                "source": chunk.source,
                "page": chunk.page,
                "file_type": chunk.file_type,
            }
            for chunk in chunks
        ],
    )
    logger.info("Stored %s chunks in Chroma", len(chunks))
    return len(chunks)


def query_vectors(persist_dir: Path, query: str, top_k: int) -> list[dict[str, Any]]:
    """Return the nearest vector matches for a query."""
    collection = get_collection(persist_dir)
    query_embedding = embed_texts([query])[0]
    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, max(collection.count(), 1)),
        include=["documents", "metadatas", "distances"],
    )

    matches: list[dict[str, Any]] = []
    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for chunk_id, text, metadata, distance in zip(ids, documents, metadatas, distances):
        # Convert cosine distance to a 0-1 similarity score.
        score = max(0.0, 1.0 - float(distance))
        matches.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "source": metadata.get("source", "unknown"),
                "page": int(metadata.get("page", 1)),
                "file_type": metadata.get("file_type", ""),
                "vector_score": score,
            }
        )
    return matches
