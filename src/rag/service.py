"""High-level Sovereign RAG Service coordinating search, citations, and answer synthesis."""

from typing import List, Dict, Any, Optional
from src.retrieval.hybrid import hybrid_retriever
from src.retrieval.expansion import context_expander
from src.retrieval.bm25 import bm25_index
from src.retrieval.embeddings import embedder
from src.storage.metadata_store import metadata_store
from src.storage.vector_store import vector_store
from src.security.access_control import UserContext, build_access_filter
from src.rag.citations import CitationBuilder, Citation
from src.rag.generator import generator
from src.logging_config import rag_logger, log_security_event


class RAGService:
    """Unified RAG service exposing search, query, and reindexing."""

    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        user: Optional[UserContext] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes hybrid search enforcing access control and returning evidence chunks with scores.
        """
        combined_filters = dict(filters or {})

        # Enforce security-aware filtering based on user role and clearance
        security_filter = build_access_filter(user)
        for k, v in security_filter.items():
            if v is not None and k not in combined_filters:
                combined_filters[k] = v

        candidates = hybrid_retriever.search(
            query=query,
            filters=combined_filters,
            top_k=top_k
        )

        # Context expansion (retrieves parent sections for top chunks)
        expanded_candidates = context_expander.expand_candidates(candidates)

        # Audit query
        metadata_store.log_audit(
            event_type="RAG_SEARCH",
            user_id=user.user_id if user else "anonymous",
            details={"query": query, "results_count": len(expanded_candidates)}
        )

        return expanded_candidates

    def query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10,
        user: Optional[UserContext] = None,
        generate_answer: bool = True
    ) -> Dict[str, Any]:
        """
        Full RAG query flow:
        1. Hybrid retrieve evidence chunks with security enforcement
        2. Expand parent context
        3. Build structured, verifiable citations
        4. Synthesize local answer
        """
        evidence = self.search(
            query=query,
            filters=filters,
            top_k=top_k,
            user=user
        )

        citations: List[Citation] = CitationBuilder.build_citations(evidence)

        answer = ""
        if generate_answer:
            answer = generator.generate_answer(
                query=query,
                evidence_chunks=evidence,
                citations=citations
            )

        return {
            "query": query,
            "answer": answer,
            "sources": [c.model_dump() for c in citations],
            "evidence": evidence
        }

    def reindex_all(self) -> Dict[str, Any]:
        """Rebuilds Qdrant vector index and BM25 index from relational metadata store."""
        rag_logger.info("Initiating full knowledge base reindexing...")
        session = metadata_store.get_session()
        try:
            from src.storage.metadata_store import ChunkModel
            # Fetch all child/searchable chunks
            chunks = session.query(ChunkModel).filter(ChunkModel.parent_chunk_id.isnot(None)).all()
            if not chunks:
                chunks = session.query(ChunkModel).all()

            chunk_dicts = [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "document_name": c.document_name,
                    "page_number": c.page_number,
                    "section": c.section,
                    "subsection": c.subsection,
                    "parent_chunk_id": c.parent_chunk_id,
                    "text": c.text,
                    "department": c.department,
                    "document_type": c.document_type,
                    "access_level": c.access_level,
                    "revision": c.revision,
                    "status": c.status,
                    "equipment_tags": c.equipment_tags,
                }
                for c in chunks
            ]

            if chunk_dicts:
                # Rebuild embeddings
                texts = [c["text"] for c in chunk_dicts]
                embs = embedder.embed_documents(texts)
                vector_store.upsert_chunks(chunk_dicts, embs)
                bm25_index.build_index(chunk_dicts)

            rag_logger.info(f"Reindexed {len(chunk_dicts)} chunks across Qdrant and BM25.")
            return {"status": "success", "total_reindexed": len(chunk_dicts)}
        finally:
            session.close()


rag_service = RAGService()
