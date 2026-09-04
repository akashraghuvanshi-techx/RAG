"""System health and metrics API endpoints."""

from fastapi import APIRouter
from src.config import settings
from src.storage.metadata_store import metadata_store
from src.storage.vector_store import vector_store
from src.security.sovereign_guard import verify_offline_status
from src.api.schemas import HealthStatus, MetricsResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Returns system status, sovereign mode state, and database connectivity."""
    offline_info = verify_offline_status()

    # Check vector DB
    try:
        v_count = vector_store.count()
        qdrant_status = f"healthy ({v_count} vectors)"
    except Exception as e:
        qdrant_status = f"error: {str(e)}"

    # Check metadata DB
    try:
        metrics = metadata_store.get_metrics()
        meta_status = f"healthy ({metrics.get('total_documents')} documents)"
    except Exception as e:
        meta_status = f"error: {str(e)}"

    return HealthStatus(
        status="healthy",
        sovereign_mode=settings.SOVEREIGN_MODE,
        guard_active=offline_info.get("guard_active", False),
        qdrant=qdrant_status,
        metadata_db=meta_status,
        ocr_engine=settings.OCR_ENGINE,
        embedding_model=settings.EMBEDDING_MODEL_NAME
    )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics():
    """Returns knowledge base statistics and ingestion metrics."""
    meta_metrics = metadata_store.get_metrics()
    v_count = vector_store.count()

    return MetricsResponse(
        total_documents=meta_metrics.get("total_documents", 0),
        active_documents=meta_metrics.get("active_documents", 0),
        superseded_documents=meta_metrics.get("superseded_documents", 0),
        total_chunks=meta_metrics.get("total_chunks", 0),
        vector_count=v_count,
        sovereign_mode=settings.SOVEREIGN_MODE
    )
