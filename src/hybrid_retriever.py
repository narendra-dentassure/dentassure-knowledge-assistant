"""Hybrid retrieval: BM25 keyword search + vector search + RRF fusion."""

from __future__ import annotations

import re
from typing import Any

from rank_bm25 import BM25Okapi

from src.chunking import Chunk
from src.logging_setup import configure_logging
from src.vectorstore import query_vectors

logger = configure_logging()

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokenizer used by BM25."""
    return _TOKEN_RE.findall(text.lower())


class HybridRetriever:
    """Combine sparse and dense retrieval with Reciprocal Rank Fusion."""

    def __init__(self, chunks: list[Chunk], chroma_dir) -> None:
        self.chunks = chunks
        self.chroma_dir = chroma_dir
        self._chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        corpus = [tokenize(chunk.text) for chunk in chunks]
        self.bm25 = BM25Okapi(corpus) if corpus else None

    def _bm25_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        if not self.bm25 or not self.chunks:
            return []
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(
            enumerate(scores),
            key=lambda item: item[1],
            reverse=True,
        )[:top_k]
        matches: list[dict[str, Any]] = []
        max_score = max((score for _, score in ranked), default=1.0) or 1.0
        for index, score in ranked:
            chunk = self.chunks[index]
            matches.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "source": chunk.source,
                    "page": chunk.page,
                    "file_type": chunk.file_type,
                    "bm25_score": float(score) / max_score,
                }
            )
        return matches

    def retrieve(self, query: str, retrieve_k: int) -> list[dict[str, Any]]:
        """Return fused hybrid matches for a user question."""
        candidate_k = max(retrieve_k * 2, retrieve_k)
        vector_hits = query_vectors(self.chroma_dir, query, candidate_k)
        keyword_hits = self._bm25_search(query, candidate_k)
        fused = reciprocal_rank_fusion(vector_hits, keyword_hits)
        logger.info(
            "Hybrid retrieve: %s vector hits, %s BM25 hits, %s fused",
            len(vector_hits),
            len(keyword_hits),
            len(fused),
        )
        return fused[:candidate_k]


def reciprocal_rank_fusion(
    vector_hits: list[dict[str, Any]],
    keyword_hits: list[dict[str, Any]],
    k: int = 60,
) -> list[dict[str, Any]]:
    """Merge ranked lists using Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    merged: dict[str, dict[str, Any]] = {}

    for rank, hit in enumerate(vector_hits, start=1):
        chunk_id = hit["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        merged[chunk_id] = {**merged.get(chunk_id, {}), **hit}

    for rank, hit in enumerate(keyword_hits, start=1):
        chunk_id = hit["chunk_id"]
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
        merged[chunk_id] = {**merged.get(chunk_id, {}), **hit}

    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    results: list[dict[str, Any]] = []
    for chunk_id in ranked_ids:
        item = merged[chunk_id]
        item["rrf_score"] = scores[chunk_id]
        results.append(item)
    return results
