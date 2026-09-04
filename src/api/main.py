"""FastAPI Main Application Entrypoint for Sovereign Local RAG."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings
from src.security.sovereign_guard import install_sovereign_guard, SovereignSecurityViolation
from src.api.routes import documents_router, rag_router, system_router
from src.rag.service import rag_service
from src.logging_config import rag_logger, log_security_event


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    rag_logger.info("Starting Sovereign Local Multimodal RAG Service...")
    if settings.SOVEREIGN_MODE:
        install_sovereign_guard()
        rag_logger.info("Sovereign Guard installed. Outbound network access is strictly blocked.")

    # Initialize / warm up BM25 index from disk
    try:
        rag_service.reindex_all()
    except Exception as e:
        rag_logger.info(f"Initial index warmup: {e}")

    yield

    # Shutdown
    rag_logger.info("Shutting down Sovereign Local Multimodal RAG Service.")


app = FastAPI(
    title="Sovereign Multimodal Local RAG API",
    description="Fully on-premises, confidential RAG system for refineries, PSUs, and defense engineering units.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration restricted to local workbench clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SovereignSecurityViolation)
async def sovereign_violation_handler(request: Request, exc: SovereignSecurityViolation):
    """Catches any prohibited external outbound network call attempt."""
    log_security_event("CRITICAL_SECURITY_VIOLATION", {"error": str(exc)}, level="CRITICAL")
    return JSONResponse(
        status_code=403,
        content={
            "error": "SovereignSecurityViolation",
            "message": str(exc),
            "detail": "Outbound network transmission is strictly forbidden in Sovereign Mode."
        }
    )


# Register API Routers
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(system_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        workers=settings.WORKERS
    )
