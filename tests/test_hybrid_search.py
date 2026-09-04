"""Tests for Hybrid Retrieval (Vector + BM25 + RRF + Reranker)."""

import pytest
from src.retrieval.bm25 import BM25Index
from src.retrieval.reranker import LocalCrossEncoderReranker
from src.retrieval.hybrid import HybridRetriever


def test_bm25_exact_code_matching():
    index = BM25Index()
    chunks = [
        {"chunk_id": "c1", "text": "Pump P-101 inspection findings and bearing cavitation.", "department": "mechanical"},
        {"chunk_id": "c2", "text": "Vessel V-204 tray thickness survey report.", "department": "mechanical"},
        {"chunk_id": "c3", "text": "Electrical motor M-301 winding temperature.", "department": "electrical"},
    ]
    index.build_index(chunks)

    # Search exact code P-101
    results = index.search("P-101", limit=2)
    assert len(results) > 0
    assert results[0]["chunk_id"] == "c1"

    # Search exact code V-204
    results_v = index.search("V-204", limit=2)
    assert len(results_v) > 0
    assert results_v[0]["chunk_id"] == "c2"


def test_reranker_reordering():
    reranker = LocalCrossEncoderReranker()
    query = "cavitation pitting threshold for pump impeller"
    candidates = [
        {"chunk_id": "c1", "text": "General safety guidelines for refinery personnel PPE gear.", "score": 0.5},
        {"chunk_id": "c2", "text": "Impeller cavitation pitting depth limit is 2.5 mm under SOP.", "score": 0.5},
    ]
    reranked = reranker.rank(query, candidates, top_k=2)
    assert len(reranked) == 2
    assert reranked[0]["chunk_id"] == "c2"
    assert reranked[0]["score"] > reranked[1]["score"]
