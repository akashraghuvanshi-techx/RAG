"""BM25 Keyword Search Engine for Exact Industrial Identifiers (P-101, API 610, etc.)."""

import re
from typing import List, Dict, Any, Optional
from rank_bm25 import BM25Okapi
from src.logging_config import rag_logger

TOKEN_REGEX = re.compile(r"[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9]+)?")


def tokenize_for_bm25(text: str) -> List[str]:
    """Tokenizes text preserving industrial codes, tags, hyphens, and decimal standard numbers."""
    if not text:
        return []
    tokens = TOKEN_REGEX.findall(text.lower())
    return tokens


class BM25Index:
    """In-memory BM25 inverted index with metadata filtering."""

    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def build_index(self, chunks: List[Dict[str, Any]]) -> None:
        """Builds or replaces the BM25 index with a list of chunk dictionaries."""
        self.chunks = list(chunks)
        self.tokenized_corpus = [tokenize_for_bm25(c.get("text", "")) for c in self.chunks]
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            rag_logger.info(f"Built BM25 index with {len(self.chunks)} chunks.")
        else:
            self.bm25 = None

    def add_chunks(self, new_chunks: List[Dict[str, Any]]) -> None:
        """Appends new chunks to the index."""
        if not new_chunks:
            return
        self.chunks.extend(new_chunks)
        new_tokenized = [tokenize_for_bm25(c.get("text", "")) for c in new_chunks]
        self.tokenized_corpus.extend(new_tokenized)
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            rag_logger.info(f"Updated BM25 index. Total chunks: {len(self.chunks)}.")

    def search(
        self,
        query: str,
        limit: int = 30,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Executes BM25 keyword search with metadata pre-filtering."""
        if self.bm25 is None or not self.chunks:
            return []

        query_tokens = tokenize_for_bm25(query)
        if not query_tokens:
            return []

        doc_scores = [float(s) for s in self.bm25.get_scores(query_tokens)]

        # Guarantee term frequency matching floor on small corpora where Robertson IDF <= 0
        for idx, c in enumerate(self.chunks):
            chunk_tokens = set(self.tokenized_corpus[idx])
            term_matches = sum(1 for qt in query_tokens if qt in chunk_tokens)
            if term_matches > 0 and doc_scores[idx] <= 0.0:
                doc_scores[idx] = float(term_matches) * 0.5

        # Apply metadata filters
        ranked_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)
        results: List[Dict[str, Any]] = []

        for idx in ranked_indices:
            score = float(doc_scores[idx])
            if score <= 0.0:
                continue

            chunk = self.chunks[idx]
            if not self._matches_filter(chunk, filters):
                continue

            res = dict(chunk)
            res["score"] = score
            results.append(res)
            if len(results) >= limit:
                break

        return results

    def _matches_filter(self, chunk: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
        """Evaluates whether a chunk satisfies the metadata filter criteria."""
        if not filters:
            return True

        # Allowed access levels
        if "allowed_access_levels" in filters and filters["allowed_access_levels"]:
            if chunk.get("access_level") not in filters["allowed_access_levels"]:
                return False

        # Department
        if "department" in filters and filters["department"]:
            req_dept = filters["department"]
            chunk_dept = chunk.get("department", "general")
            if isinstance(req_dept, list):
                if chunk_dept not in req_dept and chunk_dept not in ("general", "all", ""):
                    return False
            else:
                if chunk_dept != req_dept and chunk_dept not in ("general", "all", ""):
                    return False

        if "departments" in filters and filters["departments"]:
            chunk_dept = chunk.get("department", "general")
            if chunk_dept not in filters["departments"] and chunk_dept not in ("general", "all", ""):
                return False

        # Document type
        if "document_type" in filters and filters["document_type"]:
            if chunk.get("document_type") != filters["document_type"]:
                return False

        # Status / versioning (e.g. active vs superseded)
        if "status" in filters and filters["status"]:
            if chunk.get("status") != filters["status"]:
                return False

        # Document ID
        if "document_id" in filters and filters["document_id"]:
            if chunk.get("document_id") != filters["document_id"]:
                return False

        # Revision
        if "revision" in filters and filters["revision"]:
            if chunk.get("revision") != filters["revision"]:
                return False

        return True


bm25_index = BM25Index()
