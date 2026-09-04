"""Local embedding engine supporting SentenceTransformers and deterministic offline fallback."""

from typing import List, Union
import numpy as np
import hashlib
from src.config import settings
from src.logging_config import rag_logger


class BaseEmbedder:
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


class DeterministicFallbackEmbedder(BaseEmbedder):
    """
    Lightweight, completely self-contained deterministic vectorizer.
    Useful for testing or air-gapped environments without downloaded HF model weights.
    Uses Murmur/SHA n-gram term hashing with L2-normalization to 384 dimensions.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _hash_vector(self, text: str) -> List[float]:
        vec = np.zeros(self.dimension, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            return vec.tolist()

        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            val = ((h >> 8) % 1000) / 500.0 - 1.0
            vec[idx] += val

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._hash_vector(t) for t in texts]


class LocalSentenceTransformerEmbedder(BaseEmbedder):
    """Local Sentence Transformers embedding model."""

    def __init__(self, model_name: str, dimension: int = 384):
        self.model_name = model_name
        self.dimension = dimension
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            rag_logger.info(f"Loading local embedding model: {self.model_name}")
            # local_files_only=True when sovereign mode to ensure no internet attempt
            self.model = SentenceTransformer(self.model_name, local_files_only=False)
            rag_logger.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            rag_logger.warning(
                f"Could not load SentenceTransformer '{self.model_name}': {e}. "
                f"Falling back to deterministic local embedder."
            )
            self.model = None

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self.model is None or settings.USE_FALLBACK_EMBEDDER:
            return DeterministicFallbackEmbedder(self.dimension).embed_documents(texts)

        try:
            embeddings = self.model.encode(
                texts,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            return embeddings.tolist()
        except Exception as e:
            rag_logger.error(f"Embedding generation error: {e}. Using fallback.")
            return DeterministicFallbackEmbedder(self.dimension).embed_documents(texts)


def get_embedder() -> BaseEmbedder:
    """Factory function for embedding engine."""
    if settings.USE_FALLBACK_EMBEDDER:
        return DeterministicFallbackEmbedder(settings.EMBEDDING_DIMENSION)
    return LocalSentenceTransformerEmbedder(
        settings.EMBEDDING_MODEL_NAME, settings.EMBEDDING_DIMENSION
    )


embedder = get_embedder()
