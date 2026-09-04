"""Document management API endpoints."""

import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from src.storage.file_store import file_store
from src.storage.metadata_store import metadata_store
from src.storage.vector_store import vector_store
from src.ingestion.pipeline import ingestion_pipeline
from src.api.schemas import (
    DocumentUploadResponse, DocumentIngestRequest, DocumentIngestResponse,
    DocumentListResponse, DocumentItem
)
from src.logging_config import rag_logger, log_security_event

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    document_type: Optional[str] = Form("General"),
    department: Optional[str] = Form("general"),
    access_level: Optional[str] = Form("internal"),
    revision: Optional[str] = Form(None),
    auto_ingest: bool = Form(True),
):
    """
    Uploads a document to secure local storage and automatically triggers ingestion.
    Runs entirely on-premises without external network transmission.
    """
    doc_id = document_id or str(uuid.uuid4())
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    metadata = {
        "title": title or file.filename,
        "document_type": document_type,
        "department": department,
        "access_level": access_level,
        "revision": revision,
        "uploaded_by": "api_user",
    }

    if auto_ingest:
        result = ingestion_pipeline.ingest_bytes(
            content=content,
            filename=file.filename,
            document_id=doc_id,
            metadata=metadata
        )
        saved_path = file_store.get_file_path(doc_id, file.filename)
        return DocumentUploadResponse(
            document_id=doc_id,
            filename=file.filename,
            file_size_bytes=len(content),
            sha256_hash=metadata_store.get_document(doc_id).get("file_hash", ""),
            message=f"Document uploaded and ingested successfully. ({result.get('total_chunks')} chunks generated)"
        )
    else:
        saved_path, sha256_hash, file_size = file_store.save_file(doc_id, file.filename, content)
        return DocumentUploadResponse(
            document_id=doc_id,
            filename=file.filename,
            file_size_bytes=file_size,
            sha256_hash=sha256_hash,
            message="Document uploaded to secure local file store. Ready for /documents/ingest."
        )


@router.post("/ingest", response_model=DocumentIngestResponse)
async def ingest_document(request: DocumentIngestRequest):
    """Triggers ingestion for an already uploaded local document."""
    doc_id = request.document_id or str(uuid.uuid4())
    file_path = file_store.get_file_path(doc_id, request.filename)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found on disk for ID {doc_id}.")

    result = ingestion_pipeline.ingest_file(
        file_path=file_path,
        document_id=doc_id,
        metadata=request.model_dump()
    )

    return DocumentIngestResponse(**result)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """Lists ingested documents stored in the sovereign knowledge base."""
    docs = metadata_store.list_documents(
        limit=limit,
        offset=offset,
        department=department,
        status=status
    )
    return DocumentListResponse(
        total=len(docs),
        documents=[DocumentItem(**d) for d in docs]
    )


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Fetches details and chunk stats for a specific document."""
    doc = metadata_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")
    return doc


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Securely deletes a document, purging its file on disk, chunks in Qdrant,
    and relational metadata records.
    """
    doc = metadata_store.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found.")

    # 1. Delete vector points in Qdrant
    vector_store.delete_by_document_id(document_id)

    # 2. Delete file on disk
    file_store.delete_document_files(document_id)

    # 3. Delete metadata in SQLite / PostgreSQL
    metadata_store.delete_document(document_id)

    # 4. Audit
    log_security_event(
        "DOCUMENT_PURGED",
        {"document_id": document_id, "filename": doc.get("filename")},
        level="WARNING"
    )

    return {
        "status": "deleted",
        "document_id": document_id,
        "filename": doc.get("filename"),
        "message": "Document and all associated vector embeddings successfully deleted."
    }
