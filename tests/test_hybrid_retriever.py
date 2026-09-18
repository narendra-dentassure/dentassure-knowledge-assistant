"""Hybrid fusion unit tests — no embedding model required."""

from src.hybrid_retriever import reciprocal_rank_fusion, tokenize


def test_tokenize_lowercases_and_drops_punctuation() -> None:
    assert tokenize("Pre-Auth #12,000!") == ["pre", "auth", "12", "000"]


def test_rrf_prefers_items_ranked_high_in_both_lists() -> None:
    vector = [
        {"chunk_id": "a", "text": "A", "source": "p.pdf", "page": 1, "file_type": "pdf"},
        {"chunk_id": "b", "text": "B", "source": "p.pdf", "page": 2, "file_type": "pdf"},
    ]
    keyword = [
        {"chunk_id": "b", "text": "B", "source": "p.pdf", "page": 2, "file_type": "pdf"},
        {"chunk_id": "c", "text": "C", "source": "q.pdf", "page": 1, "file_type": "pdf"},
    ]
    fused = reciprocal_rank_fusion(vector, keyword)
    assert fused[0]["chunk_id"] == "b"
    assert "rrf_score" in fused[0]
    ids = [item["chunk_id"] for item in fused]
    assert ids == ["b", "a", "c"]
