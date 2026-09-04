"""Vector database abstraction using Qdrant (local embedded or standalone server)."""

import uuid
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny
from src.config import settings
from src.logging_config import rag_logger


class QdrantVectorStore:
    """Manages Qdrant vector database operations with payload filtering."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        dimension: Optional[int] = None,
        storage_path: Optional[str] = None,
        url: Optional[str] = None,
    ):
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.dimension = dimension or settings.EMBEDDING_DIMENSION

        # Determine connection mode: remote server or embedded disk
        self.is_remote = bool(url or settings.QDRANT_URL)
        if self.is_remote:
            server_url = url or settings.QDRANT_URL
            rag_logger.info(f"Connecting to remote Qdrant server at: {server_url}")
            self.client = QdrantClient(url=server_url, api_key=settings.QDRANT_API_KEY)
        else:
            path = storage_path or str(settings.QDRANT_STORAGE_PATH)
            rag_logger.info(f"Initializing embedded Qdrant on local disk at: {path}")
            self.client = QdrantClient(path=path)

        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """Creates the collection and indexes if they do not exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                rag_logger.info(f"Creating Qdrant collection: {self.collection_name} (dim={self.dimension})")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
                )
                if getattr(self, "is_remote", False):
                    indexed_fields = ["document_id", "access_level", "department", "document_type", "status"]
                    for field in indexed_fields:
                        try:
                            self.client.create_payload_index(
                                collection_name=self.collection_name,
                                field_name=field,
                                field_schema=rest.PayloadSchemaType.KEYWORD
                            )
                        except Exception:
                            pass
        except Exception as e:
            rag_logger.warning(f"Collection verification check: {e}")

    def upsert_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]) -> int:
        """Inserts or updates vector points with full metadata payload."""
        if not chunks or not embeddings or len(chunks) != len(embeddings):
            return 0

        points = []
        for chunk, emb in zip(chunks, embeddings):
            # Ensure valid UUID for Qdrant point_id
            point_id = chunk["chunk_id"]
            try:
                uuid.UUID(point_id)
            except ValueError:
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id))

            payload = {
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "document_name": chunk.get("document_name", ""),
                "page_number": chunk.get("page_number", 1),
                "section": chunk.get("section", ""),
                "subsection": chunk.get("subsection", ""),
                "text": chunk.get("text", ""),
                "department": chunk.get("department", "general"),
                "document_type": chunk.get("document_type", "General"),
                "access_level": chunk.get("access_level", "internal"),
                "revision": chunk.get("revision", "Rev 0"),
                "status": chunk.get("status", "active"),
                "parent_chunk_id": chunk.get("parent_chunk_id"),
                "equipment_tags": chunk.get("equipment_tags", []),
                "ocr_confidence": chunk.get("ocr_confidence"),
                "is_table": chunk.get("is_table", False),
            }

            points.append(PointStruct(id=point_id, vector=emb, payload=payload))

        # Batch upsert
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(collection_name=self.collection_name, points=batch)

        rag_logger.info(f"Upserted {len(points)} points into Qdrant collection: {self.collection_name}")
        return len(points)

    def search(
        self,
        query_vector: List[float],
        limit: int = 30,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes dense vector similarity search with security and metadata filtering.
        """
        qdrant_filter = self._build_qdrant_filter(filters)

        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=limit,
            with_payload=True
        )

        results = []
        for hit in search_result:
            payload = hit.payload or {}
            results.append({
                "chunk_id": payload.get("chunk_id", str(hit.id)),
                "document_id": payload.get("document_id", ""),
                "document_name": payload.get("document_name", ""),
                "page_number": payload.get("page_number", 1),
                "section": payload.get("section", ""),
                "subsection": payload.get("subsection", ""),
                "text": payload.get("text", ""),
                "score": float(hit.score),
                "department": payload.get("department", ""),
                "document_type": payload.get("document_type", ""),
                "access_level": payload.get("access_level", ""),
                "revision": payload.get("revision", ""),
                "status": payload.get("status", "active"),
                "parent_chunk_id": payload.get("parent_chunk_id"),
                "equipment_tags": payload.get("equipment_tags", []),
            })
        return results

    def _build_qdrant_filter(self, filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """Translates search filters into Qdrant filter conditions."""
        if not filters:
            return None

        must_conditions = []

        # Access levels (security filtering)
        if "allowed_access_levels" in filters and filters["allowed_access_levels"]:
            must_conditions.append(
                FieldCondition(
                    key="access_level",
                    match=MatchAny(any=filters["allowed_access_levels"])
                )
            )

        # Department filtering
        if "department" in filters and filters["department"]:
            dept = filters["department"]
            if isinstance(dept, list):
                must_conditions.append(FieldCondition(key="department", match=MatchAny(any=dept)))
            else:
                must_conditions.append(FieldCondition(key="department", match=MatchValue(value=dept)))
        elif "departments" in filters and filters["departments"]:
            must_conditions.append(FieldCondition(key="department", match=MatchAny(any=filters["departments"])))

        # Document type filtering
        if "document_type" in filters and filters["document_type"]:
            must_conditions.append(FieldCondition(key="document_type", match=MatchValue(value=filters["document_type"])))

        # Status / Versioning filtering (e.g. active vs superseded)
        if "status" in filters and filters["status"]:
            must_conditions.append(FieldCondition(key="status", match=MatchValue(value=filters["status"])))

        # Specific document_id
        if "document_id" in filters and filters["document_id"]:
            must_conditions.append(FieldCondition(key="document_id", match=MatchValue(value=filters["document_id"])))

        # Revision filtering
        if "revision" in filters and filters["revision"]:
            must_conditions.append(FieldCondition(key="revision", match=MatchValue(value=filters["revision"])))

        if not must_conditions:
            return None

        return Filter(must=must_conditions)

    def delete_by_document_id(self, document_id: str) -> None:
        """Deletes all chunks belonging to a document."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=rest.FilterSelector(
                filter=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            )
        )
        rag_logger.info(f"Deleted points from Qdrant for document_id: {document_id}")

    def count(self) -> int:
        """Returns total vector count."""
        try:
            info = self.client.get_collection(collection_name=self.collection_name)
            return info.points_count or 0
        except Exception:
            return 0


vector_store = QdrantVectorStore()
