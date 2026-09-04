"""Hybrid Retrieval fusing Semantic Vector Search, BM25 Keyword Search, and Metadata Filtering."""

import re
from typing import List, Dict, Any, Optional
from src.storage.vector_store import vector_store
from src.retrieval.bm25 import bm25_index
from src.retrieval.embeddings import embedder
from src.retrieval.reranker import reranker
from src.config import settings
from src.logging_config import rag_logger

HISTORICAL_INTENT_PATTERN = re.compile(
    r"\b(historical|superseded|obsolete|previous|old|past|in\s*20\d\d|rev(?:ision)?\s*[0-4])\b",
    re.IGNORECASE
)


class HybridRetriever:
    """Orchestrates hybrid search using Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking."""

    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k or settings.RRF_K

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        enable_rerank: bool = True
    ) -> List[Dict[str, Any]]:
        filters = dict(filters or {})

        # Version-awareness: If no explicit status or historical intent, prefer active documents
        if "status" not in filters:
            if not HISTORICAL_INTENT_PATTERN.search(query):
                # Prefer active version
                filters["status"] = "active"

        rag_logger.info(f"Hybrid search for query='{query}' with filters={filters}")

        # 1. Semantic Vector Search
        query_vector = embedder.embed_query(query)
        vector_candidates = vector_store.search(
            query_vector=query_vector,
            limit=settings.VECTOR_SEARCH_LIMIT,
            filters=filters
        )

        # 2. BM25 Keyword Search
        bm25_candidates = bm25_index.search(
            query=query,
            limit=settings.BM25_SEARCH_LIMIT,
            filters=filters
        )

        # 3. Reciprocal Rank Fusion (RRF)
        fused_pool = self._reciprocal_rank_fusion(vector_candidates, bm25_candidates)

        # 4. Local Reranking
        if enable_rerank and settings.RERANKER_ENABLED:
            final_results = reranker.rank(query=query, candidates=fused_pool, top_k=top_k)
        else:
            final_results = fused_pool[:top_k]

        rag_logger.info(
            f"Retrieved {len(vector_candidates)} vector + {len(bm25_candidates)} BM25 candidates. "
            f"Fused to {len(final_results)} top evidence chunks."
        )
        return final_results

    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fuses ranked candidate lists using Reciprocal Rank Fusion (RRF)."""
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}

        # Process Vector search ranks
        for rank, item in enumerate(vector_results, start=1):
            cid = item["chunk_id"]
            chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        # Process BM25 search ranks
        for rank, item in enumerate(bm25_results, start=1):
            cid = item["chunk_id"]
            if cid not in chunk_map:
                chunk_map[cid] = item
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + (1.0 / (self.rrf_k + rank))

        # Sort candidates by combined RRF score
        sorted_cids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        fused = []
        max_rrf = max(rrf_scores.values()) if rrf_scores else 1.0
        for cid in sorted_cids:
            chunk = dict(chunk_map[cid])
            # Normalized RRF score between 0.0 and 1.0
            norm_score = round(rrf_scores[cid] / max_rrf, 4)
            chunk["score"] = norm_score
            chunk["rrf_score"] = rrf_scores[cid]
            fused.append(chunk)

        return fused


hybrid_retriever = HybridRetriever()
