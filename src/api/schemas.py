"""Pydantic API Schemas for Requests and Responses."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# Document Ingestion Schemas
class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    file_size_bytes: int
    sha256_hash: str
    message: str


class DocumentIngestRequest(BaseModel):
    document_id: Optional[str] = None
    filename: str
    title: Optional[str] = None
    document_type: Optional[str] = "General"  # SOP, Inspection Report, etc.
    department: Optional[str] = "general"
    project: Optional[str] = None
    access_level: Optional[str] = "internal"
    revision: Optional[str] = None
    version: Optional[int] = 1
    effective_date: Optional[str] = None
    status: Optional[str] = "active"
    supersedes: Optional[str] = None


class DocumentIngestResponse(BaseModel):
    document_id: str
    filename: str
    document_type: str
    revision: str
    status: str
    total_pages: int
    is_scanned: bool
    total_chunks: int
    searchable_chunks: int


class DocumentItem(BaseModel):
    document_id: str
    filename: str
    title: Optional[str] = None
    document_type: str
    department: str
    access_level: str
    revision: str
    version: int
    status: str
    created_at: Optional[str] = None


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentItem]


# RAG Search and Query Schemas
class SearchFilter(BaseModel):
    department: Optional[str] = None
    document_type: Optional[str] = None
    status: Optional[str] = None
    revision: Optional[str] = None
    document_id: Optional[str] = None


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[SearchFilter] = None
    user_id: Optional[str] = "system"
    user_role: Optional[str] = "engineer"
    clearance: Optional[str] = "confidential"


class SearchResultChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page: int
    section: Optional[str] = "General"
    revision: Optional[str] = "Rev 0"
    department: Optional[str] = "general"
    text: str
    score: float
    is_table: bool = False
    equipment_tags: List[str] = Field(default_factory=list)


class RAGSearchResponse(BaseModel):
    query: str
    results: List[SearchResultChunk]


class CitationSource(BaseModel):
    document_id: str
    document_name: str
    page: int
    section: str
    chunk_id: str
    relevance_score: float
    revision: str
    department: Optional[str] = None
    equipment_tags: List[str] = Field(default_factory=list)
    preview: Optional[str] = None


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    filters: Optional[SearchFilter] = None
    user_id: Optional[str] = "system"
    user_role: Optional[str] = "engineer"
    clearance: Optional[str] = "confidential"
    generate_answer: bool = True


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    sources: List[CitationSource]
    evidence: List[SearchResultChunk]


# Health & Metrics
class HealthStatus(BaseModel):
    status: str
    sovereign_mode: bool
    guard_active: bool
    qdrant: str
    metadata_db: str
    ocr_engine: str
    embedding_model: str


class MetricsResponse(BaseModel):
    total_documents: int
    active_documents: int
    superseded_documents: int
    total_chunks: int
    vector_count: int
    sovereign_mode: bool
