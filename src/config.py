"""Configuration management for Sovereign Local Multimodal RAG."""

from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Sovereign Mode
    SOVEREIGN_MODE: bool = Field(default=True, description="Strict local execution, zero outbound calls")

    # Storage paths
    DATA_DIR: Path = Field(default=Path("./data"))
    DOCUMENTS_DIR: Path = Field(default=Path("./data/documents"))
    QDRANT_STORAGE_PATH: Path = Field(default=Path("./data/qdrant"))
    LOG_DIR: Path = Field(default=Path("./logs"))

    # Vector Database
    QDRANT_URL: Optional[str] = Field(default=None, description="Optional remote Qdrant URL; if unset uses embedded local disk")
    QDRANT_API_KEY: Optional[str] = Field(default=None)
    QDRANT_COLLECTION: str = Field(default="sovereign_knowledge_base")

    # Relational Database
    DATABASE_URL: str = Field(default="sqlite:///./data/metadata.db")

    # Embeddings
    EMBEDDING_MODEL_NAME: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = Field(default=384)
    EMBEDDING_BATCH_SIZE: int = Field(default=32)
    USE_FALLBACK_EMBEDDER: bool = Field(default=False, description="Use lightweight local deterministic embedder if model files are missing")

    # Cross-Encoder Reranker
    RERANKER_MODEL_NAME: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2")
    RERANKER_ENABLED: bool = Field(default=True)
    RERANKER_TOP_K: int = Field(default=10)

    # Retrieval parameters
    VECTOR_SEARCH_LIMIT: int = Field(default=30)
    BM25_SEARCH_LIMIT: int = Field(default=30)
    RRF_K: int = Field(default=60)
    MAX_PARENT_EXPANSION_TOKENS: int = Field(default=1500)

    # OCR parameters
    OCR_ENGINE: str = Field(default="rapidocr")
    OCR_CONFIDENCE_THRESHOLD: float = Field(default=0.45)
    OCR_SCANNED_MIN_CHAR_THRESHOLD: int = Field(default=50)

    # Local LLM Serving (optional)
    LLM_ENDPOINT: Optional[str] = Field(default="http://127.0.0.1:11434/v1")
    LLM_MODEL: str = Field(default="llama3:8b")
    LLM_TIMEOUT: int = Field(default=60)

    # Server
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=1)
    LOG_LEVEL: str = Field(default="INFO")

    def initialize_directories(self) -> None:
        """Ensure all required runtime directories exist."""
        for path in [self.DATA_DIR, self.DOCUMENTS_DIR, self.QDRANT_STORAGE_PATH, self.LOG_DIR]:
            path.mkdir(parents=True, exist_ok=True)


# Global singleton settings
settings = Settings()
settings.initialize_directories()
