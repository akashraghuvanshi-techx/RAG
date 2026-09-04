"""Relational metadata storage using SQLAlchemy (SQLite / PostgreSQL)."""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    create_engine, Column, String, Integer, Float, Text, DateTime,
    ForeignKey, Boolean, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from src.config import settings
from src.logging_config import rag_logger

Base = declarative_base()


class DocumentModel(Base):
    __tablename__ = "documents"

    document_id = Column(String(64), primary_key=True, index=True)
    filename = Column(String(256), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    file_type = Column(String(32), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)

    title = Column(String(256), nullable=True)
    document_type = Column(String(64), default="General", index=True)  # SOP, Inspection, Manual, etc.
    department = Column(String(64), default="general", index=True)
    project = Column(String(64), nullable=True, index=True)
    access_level = Column(String(32), default="internal", index=True)  # public, internal, confidential, etc.

    revision = Column(String(32), default="Rev 0", index=True)
    version = Column(Integer, default=1)
    effective_date = Column(String(32), nullable=True)
    status = Column(String(32), default="active", index=True)  # active, superseded, draft, archived
    supersedes = Column(String(64), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    chunks = relationship("ChunkModel", back_populates="document", cascade="all, delete-orphan")


class ChunkModel(Base):
    __tablename__ = "chunks"

    chunk_id = Column(String(64), primary_key=True, index=True)
    document_id = Column(String(64), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)

    page_number = Column(Integer, default=1, index=True)
    section = Column(String(256), nullable=True)
    subsection = Column(String(256), nullable=True)
    parent_chunk_id = Column(String(64), nullable=True, index=True)

    text = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)

    # Metadata copied for fast relational search
    document_name = Column(String(256), nullable=True)
    document_type = Column(String(64), default="General")
    department = Column(String(64), default="general", index=True)
    access_level = Column(String(32), default="internal", index=True)
    revision = Column(String(32), default="Rev 0")
    status = Column(String(32), default="active", index=True)

    # JSON fields
    equipment_tags = Column(Text, default="[]")  # List[str] e.g. ["P-101", "API 610"]
    bbox = Column(Text, nullable=True)            # Coordinates or layout box
    ocr_confidence = Column(Float, nullable=True)
    is_table = Column(Boolean, default=False)
    is_figure = Column(Boolean, default=False)

    document = relationship("DocumentModel", back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_doc_page", "document_id", "page_number"),
    )


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    event_type = Column(String(64), nullable=False, index=True)
    user_id = Column(String(64), default="system")
    document_id = Column(String(64), nullable=True)
    details = Column(Text, default="{}")


class MetadataStore:
    """Manages metadata persistence using SQLAlchemy with SQLite or PostgreSQL."""

    def __init__(self, db_url: Optional[str] = None):
        url = db_url or settings.DATABASE_URL
        # Ensure SQLite directory exists
        if url.startswith("sqlite:///"):
            sqlite_path = url.replace("sqlite:///", "")
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            url,
            connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
            pool_pre_ping=True
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        rag_logger.info(f"Initialized MetadataStore connected to: {url.split('@')[-1] if '@' in url else url}")

    def get_session(self):
        return self.SessionLocal()

    def save_document(self, doc_data: Dict[str, Any]) -> DocumentModel:
        """Saves or updates a document metadata record."""
        session = self.SessionLocal()
        try:
            doc_id = doc_data["document_id"]
            existing = session.query(DocumentModel).filter_by(document_id=doc_id).first()
            if existing:
                for k, v in doc_data.items():
                    setattr(existing, k, v)
                existing.updated_at = datetime.now(timezone.utc)
                doc = existing
            else:
                doc = DocumentModel(**doc_data)
                session.add(doc)
            session.commit()
            session.refresh(doc)
            return doc
        finally:
            session.close()

    def save_chunks(self, chunks_data: List[Dict[str, Any]]) -> int:
        """Batch inserts chunk metadata."""
        if not chunks_data:
            return 0
        session = self.SessionLocal()
        try:
            chunk_objs = []
            for c in chunks_data:
                data = dict(c)
                if isinstance(data.get("equipment_tags"), list):
                    data["equipment_tags"] = json.dumps(data["equipment_tags"])
                if isinstance(data.get("bbox"), (list, dict)):
                    data["bbox"] = json.dumps(data["bbox"])
                chunk_objs.append(ChunkModel(**data))
            session.bulk_save_objects(chunk_objs)
            session.commit()
            return len(chunk_objs)
        finally:
            session.close()

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            doc = session.query(DocumentModel).filter_by(document_id=document_id).first()
            if not doc:
                return None
            return {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "file_hash": doc.file_hash,
                "file_type": doc.file_type,
                "file_size_bytes": doc.file_size_bytes,
                "title": doc.title,
                "document_type": doc.document_type,
                "department": doc.department,
                "project": doc.project,
                "access_level": doc.access_level,
                "revision": doc.revision,
                "version": doc.version,
                "effective_date": doc.effective_date,
                "status": doc.status,
                "supersedes": doc.supersedes,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }
        finally:
            session.close()

    def list_documents(
        self,
        limit: int = 50,
        offset: int = 0,
        department: Optional[str] = None,
        status: Optional[str] = None,
        allowed_access_levels: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            query = session.query(DocumentModel)
            if department:
                query = query.filter(DocumentModel.department == department)
            if status:
                query = query.filter(DocumentModel.status == status)
            if allowed_access_levels:
                query = query.filter(DocumentModel.access_level.in_(allowed_access_levels))

            docs = query.order_by(DocumentModel.created_at.desc()).offset(offset).limit(limit).all()
            result = []
            for doc in docs:
                result.append({
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "title": doc.title,
                    "document_type": doc.document_type,
                    "department": doc.department,
                    "access_level": doc.access_level,
                    "revision": doc.revision,
                    "version": doc.version,
                    "status": doc.status,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                })
            return result
        finally:
            session.close()

    def delete_document(self, document_id: str) -> bool:
        session = self.SessionLocal()
        try:
            doc = session.query(DocumentModel).filter_by(document_id=document_id).first()
            if not doc:
                return False
            session.delete(doc)
            session.commit()
            return True
        finally:
            session.close()

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        session = self.SessionLocal()
        try:
            chunk = session.query(ChunkModel).filter_by(chunk_id=chunk_id).first()
            if not chunk:
                return None
            return {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "subsection": chunk.subsection,
                "parent_chunk_id": chunk.parent_chunk_id,
                "text": chunk.text,
                "document_name": chunk.document_name,
                "document_type": chunk.document_type,
                "department": chunk.department,
                "access_level": chunk.access_level,
                "revision": chunk.revision,
                "status": chunk.status,
                "equipment_tags": json.loads(chunk.equipment_tags) if chunk.equipment_tags else [],
                "bbox": json.loads(chunk.bbox) if chunk.bbox else None,
                "ocr_confidence": chunk.ocr_confidence,
                "is_table": chunk.is_table,
                "is_figure": chunk.is_figure,
            }
        finally:
            session.close()

    def get_parent_chunk(self, parent_chunk_id: str) -> Optional[Dict[str, Any]]:
        return self.get_chunk(parent_chunk_id)

    def log_audit(self, event_type: str, user_id: str = "system", document_id: Optional[str] = None, details: Optional[Dict] = None) -> None:
        session = self.SessionLocal()
        try:
            audit = AuditLogModel(
                event_type=event_type,
                user_id=user_id,
                document_id=document_id,
                details=json.dumps(details or {})
            )
            session.add(audit)
            session.commit()
        finally:
            session.close()

    def get_metrics(self) -> Dict[str, Any]:
        session = self.SessionLocal()
        try:
            doc_count = session.query(DocumentModel).count()
            chunk_count = session.query(ChunkModel).count()
            active_docs = session.query(DocumentModel).filter_by(status="active").count()
            superseded_docs = session.query(DocumentModel).filter_by(status="superseded").count()
            return {
                "total_documents": doc_count,
                "active_documents": active_docs,
                "superseded_documents": superseded_docs,
                "total_chunks": chunk_count,
            }
        finally:
            session.close()


metadata_store = MetadataStore()
