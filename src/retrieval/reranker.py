"""Local Cross-Encoder Reranker."""

from typing import List, Dict, Any, Tuple
from src.config import settings
from src.logging_config import rag_logger


class LocalCrossEncoderReranker:
    """Local Cross-Encoder reranker scoring query-document pairs."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._initialize()

    def _initialize(self):
        if not settings.RERANKER_ENABLED:
            rag_logger.info("Reranker is disabled by configuration.")
            return

        try:
            from sentence_transformers import CrossEncoder
            rag_logger.info(f"Loading local CrossEncoder reranker: {self.model_name}")
            self.model = CrossEncoder(self.model_name, local_files_only=False)
            rag_logger.info("CrossEncoder reranker loaded successfully.")
        except Exception as e:
            rag_logger.warning(
                f"Could not load CrossEncoder '{self.model_name}': {e}. "
                f"Using local lexical cross-scoring fallback."
            )
            self.model = None

    def rank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Reranks candidate chunks for a query using cross-encoder scoring.
        Returns top_k highest scoring candidates with normalized relevance scores.
        """
        if not candidates:
            return []

        if self.model is not None:
            try:
                pairs = [(query, c.get("text", "")) for c in candidates]
                raw_scores = self.model.predict(pairs)

                scored_candidates = []
                for candidate, score in zip(candidates, raw_scores):
                    item = dict(candidate)
                    item["rerank_score"] = float(score)
                    # Sigmoid normalization if needed
                    item["score"] = float(1.0 / (1.0 + pow(2.71828, -float(score))))
                    scored_candidates.append(item)

                scored_candidates.sort(key=lambda x: x["score"], reverse=True)
                return scored_candidates[:top_k]
            except Exception as e:
                rag_logger.error(f"CrossEncoder prediction error: {e}. Using fallback ranker.")

        # Fallback Lexical Cross-Scoring
        scored = []
        q_tokens = set(query.lower().split())
        for c in candidates:
            text = c.get("text", "").lower()
            overlap = sum(1 for t in q_tokens if t in text)
            exact_bonus = 0.3 if query.lower() in text else 0.0
            # Equipment tag bonus
            tag_bonus = 0.0
            for tag in c.get("equipment_tags", []):
                if tag.lower() in query.lower():
                    tag_bonus += 0.25

            base_score = float(c.get("score", 0.5))
            combined_score = (base_score * 0.4) + ((overlap / max(1, len(q_tokens))) * 0.4) + exact_bonus + tag_bonus
            item = dict(c)
            item["score"] = round(min(1.0, combined_score), 4)
            scored.append(item)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


reranker = LocalCrossEncoderReranker(settings.RERANKER_MODEL_NAME)
