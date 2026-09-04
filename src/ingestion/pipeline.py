"""Master Ingestion Pipeline coordinating extraction, OCR, chunking, and dual indexing."""

import uuid
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from src.storage.file_store import file_store
from src.storage.metadata_store import metadata_store
from src.storage.vector_store import vector_store
from src.retrieval.bm25 import bm25_index
from src.retrieval.embeddings import embedder
from src.ingestion.extractors import get_extractor_for_file, ExtractedDocument
from src.ingestion.chunker import HierarchicalChunker, Chunk, extract_revision
from src.logging_config import rag_logger, log_security_event


class IngestionPipeline:
    """End-to-end ingestion pipeline preserving original files and indexing multi-modal evidence."""

    def __init__(self):
        self.chunker = HierarchicalChunker()

    def ingest_file(
        self,
        file_path: Path,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Ingests a file from local path."""
        with open(file_path, "rb") as f:
            content = f.read()
        return self.ingest_bytes(
            content=content,
            filename=file_path.name,
            document_id=document_id,
            metadata=metadata
        )

    def ingest_bytes(
        self,
        content: bytes,
        filename: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        metadata = dict(metadata or {})
        doc_id = document_id or str(uuid.uuid4())

        rag_logger.info(f"Starting ingestion for document '{filename}' (ID: {doc_id})")

        # 1. Store original file safely to disk
        saved_path, file_hash, file_size = file_store.save_file(
            document_id=doc_id,
            filename=filename,
            content=content
        )

        # 2. Extract content & detect scanned pages
        extractor = get_extractor_for_file(saved_path)
        extracted: ExtractedDocument = extractor.extract(saved_path, metadata=metadata)

        # Infer revision, document type, department if not supplied
        inferred_rev = metadata.get("revision") or extract_revision(filename, "Rev 0")
        doc_type = metadata.get("document_type") or self._infer_doc_type(filename, extracted)
        department = metadata.get("department", "general")
        access_level = metadata.get("access_level", "internal")
        status = metadata.get("status", "active")
        supersedes = metadata.get("supersedes")

        doc_meta = {
            "document_id": doc_id,
            "filename": filename,
            "file_path": str(saved_path),
            "file_hash": file_hash,
            "file_type": extracted.file_type,
            "file_size_bytes": file_size,
            "title": metadata.get("title", filename),
            "document_type": doc_type,
            "department": department,
            "project": metadata.get("project"),
            "access_level": access_level,
            "revision": inferred_rev,
            "version": int(metadata.get("version", 1)),
            "effective_date": metadata.get("effective_date"),
            "status": status,
            "supersedes": supersedes,
        }

        # 3. Hierarchical Chunking
        chunks: List[Chunk] = self.chunker.chunk_document(
            extracted_doc=extracted,
            document_id=doc_id,
            doc_metadata=doc_meta
        )

        if not chunks:
            rag_logger.warning(f"No chunks extracted from document: {filename}")
            return {"document_id": doc_id, "chunks_created": 0, "status": "empty"}

        # 4. Save metadata and chunks to relational store
        metadata_store.save_document(doc_meta)
        chunks_data = [c.model_dump() for c in chunks]
        metadata_store.save_chunks(chunks_data)

        # 5. Embed and index searchable child chunks (and standalone tables/figures) into Qdrant
        # Note: Child chunks (is_parent == False) are embedded for precise retrieval
        searchable_chunks = [c for c in chunks if not c.is_parent]
        if not searchable_chunks:
            searchable_chunks = chunks  # Fallback if only parent exists

        texts_to_embed = [c.text for c in searchable_chunks]
        embeddings = embedder.embed_documents(texts_to_embed)

        searchable_dicts = [c.model_dump() for c in searchable_chunks]
        vector_store.upsert_chunks(searchable_dicts, embeddings)

        # 6. Update BM25 index with new searchable chunks
        bm25_index.add_chunks(searchable_dicts)

        # 7. Audit log
        metadata_store.log_audit(
            event_type="DOCUMENT_INGESTED",
            user_id=metadata.get("uploaded_by", "system"),
            document_id=doc_id,
            details={
                "filename": filename,
                "chunks_count": len(chunks),
                "is_scanned": extracted.is_scanned,
                "revision": inferred_rev,
                "status": status
            }
        )

        rag_logger.info(
            f"Successfully ingested '{filename}' (ID: {doc_id}): "
            f"{len(chunks)} chunks created ({len(searchable_chunks)} indexed for search), "
            f"scanned={extracted.is_scanned}."
        )

        return {
            "document_id": doc_id,
            "filename": filename,
            "document_type": doc_type,
            "revision": inferred_rev,
            "status": status,
            "total_pages": extracted.total_pages,
            "is_scanned": extracted.is_scanned,
            "total_chunks": len(chunks),
            "searchable_chunks": len(searchable_chunks),
        }

    def _infer_doc_type(self, filename: str, extracted: ExtractedDocument) -> str:
        fn_lower = filename.lower()
        if "sop" in fn_lower or "procedure" in fn_lower:
            return "SOP"
        elif "insp" in fn_lower or "report" in fn_lower:
            return "Inspection Report"
        elif "manual" in fn_lower or "eng" in fn_lower or "std" in fn_lower:
            return "Engineering Standard"
        elif "app" in fn_lower or "note" in fn_lower or "approval" in fn_lower:
            return "Approval Note"
        elif "drawing" in fn_lower or "pid" in fn_lower:
            return "Engineering Drawing"
        return "General"


ingestion_pipeline = IngestionPipeline()
