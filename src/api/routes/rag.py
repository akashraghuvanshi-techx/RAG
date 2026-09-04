"""RAG retrieval and query API endpoints."""

from fastapi import APIRouter, HTTPException
from src.rag.service import rag_service
from src.security.access_control import UserContext, ClearanceLevel
from src.api.schemas import (
    RAGSearchRequest, RAGSearchResponse, SearchResultChunk,
    RAGQueryRequest, RAGQueryResponse, CitationSource
)

router = APIRouter(prefix="/rag", tags=["RAG"])


def _parse_user_context(req_user_id: str, req_role: str, req_clearance: str) -> UserContext:
    clearance_enum = ClearanceLevel.CONFIDENTIAL
    for c in ClearanceLevel:
        if c.value == (req_clearance or "").lower():
            clearance_enum = c
            break
    return UserContext(
        user_id=req_user_id or "system",
        role=req_role or "engineer",
        clearance=clearance_enum
    )


@router.post("/search", response_model=RAGSearchResponse)
async def search_rag(request: RAGSearchRequest):
    """
    Hybrid semantic + BM25 keyword search with metadata access filtering.
    Returns ranked evidence chunks with relevance scores.
    """
    user = _parse_user_context(request.user_id, request.user_role, request.clearance)
    filters = request.filters.model_dump(exclude_none=True) if request.filters else {}

    results = rag_service.search(
        query=request.query,
        filters=filters,
        top_k=request.top_k,
        user=user
    )

    formatted = [
        SearchResultChunk(
            chunk_id=r.get("chunk_id", ""),
            document_id=r.get("document_id", ""),
            document_name=r.get("document_name", ""),
            page=r.get("page_number", 1),
            section=r.get("section", "General"),
            revision=r.get("revision", "Rev 0"),
            department=r.get("department", "general"),
            text=r.get("expanded_context") or r.get("text", ""),
            score=round(float(r.get("score", 0.0)), 4),
            is_table=r.get("is_table", False),
            equipment_tags=r.get("equipment_tags", [])
        )
        for r in results
    ]

    return RAGSearchResponse(query=request.query, results=formatted)


@router.post("/query", response_model=RAGQueryResponse)
async def query_rag(request: RAGQueryRequest):
    """
    High-level RAG Query:
    Retrieves evidence, expands parent context, synthesizes answer, and formats structured citations.
    """
    user = _parse_user_context(request.user_id, request.user_role, request.clearance)
    filters = request.filters.model_dump(exclude_none=True) if request.filters else {}

    response = rag_service.query(
        query=request.query,
        filters=filters,
        top_k=request.top_k,
        user=user,
        generate_answer=request.generate_answer
    )

    evidence_formatted = [
        SearchResultChunk(
            chunk_id=r.get("chunk_id", ""),
            document_id=r.get("document_id", ""),
            document_name=r.get("document_name", ""),
            page=r.get("page_number", 1),
            section=r.get("section", "General"),
            revision=r.get("revision", "Rev 0"),
            department=r.get("department", "general"),
            text=r.get("expanded_context") or r.get("text", ""),
            score=round(float(r.get("score", 0.0)), 4),
            is_table=r.get("is_table", False),
            equipment_tags=r.get("equipment_tags", [])
        )
        for r in response.get("evidence", [])
    ]

    sources_formatted = [CitationSource(**s) for s in response.get("sources", [])]

    return RAGQueryResponse(
        query=request.query,
        answer=response.get("answer", ""),
        sources=sources_formatted,
        evidence=evidence_formatted
    )


@router.post("/reindex")
async def reindex_rag():
    """Reindexes all stored documents into Qdrant and BM25 index."""
    result = rag_service.reindex_all()
    return result
