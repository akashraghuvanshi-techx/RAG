"""API routes package."""
from src.api.routes.documents import router as documents_router
from src.api.routes.rag import router as rag_router
from src.api.routes.system import router as system_router

__all__ = ["documents_router", "rag_router", "system_router"]
