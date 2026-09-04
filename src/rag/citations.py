"""Structured Provenance and Citation Generation."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Verifiable source citation from retrieved evidence."""
    document_id: str
    document_name: str
    page: int
    section: str = "General"
    chunk_id: str
    relevance_score: float
    revision: str = "Rev 0"
    department: Optional[str] = None
    equipment_tags: List[str] = Field(default_factory=list)
    preview: Optional[str] = None


class CitationBuilder:
    """Builds clean, deduplicated, and verifiable citations from retrieved chunks."""

    @staticmethod
    def build_citations(evidence_chunks: List[Dict[str, Any]]) -> List[Citation]:
        citations: List[Citation] = []
        seen_provenance = set()

        for chunk in evidence_chunks:
            doc_id = chunk.get("document_id", "")
            doc_name = chunk.get("document_name", "Unknown Document")
            page = int(chunk.get("page_number", 1))
            section = chunk.get("section") or "General"
            chunk_id = chunk.get("chunk_id", "")
            score = round(float(chunk.get("score", 0.0)), 3)
            revision = chunk.get("revision", "Rev 0")
            dept = chunk.get("department")
            tags = chunk.get("equipment_tags", [])
            text = chunk.get("text", "")

            # Deduplication key by document, page, and section
            prov_key = f"{doc_id}::p{page}::{section}"
            if prov_key in seen_provenance:
                continue
            seen_provenance.add(prov_key)

            preview = (text[:150] + "...") if len(text) > 150 else text

            citations.append(Citation(
                document_id=doc_id,
                document_name=doc_name,
                page=page,
                section=section,
                chunk_id=chunk_id,
                relevance_score=score,
                revision=revision,
                department=dept,
                equipment_tags=tags,
                preview=preview
            ))

        return citations
