"""Pluggable interface for local Vision-Language Models (VLM)."""

from abc import ABC, abstractmethod
from typing import Optional, Union, Dict, Any
from pathlib import Path
from PIL import Image


class BaseVisionModel(ABC):
    """Abstract interface for local on-premise vision models (e.g., LLaVA, SmolVLM, Qwen2-VL)."""

    @abstractmethod
    def analyze(self, image: Union[str, bytes, Path, Image.Image], prompt: Optional[str] = None) -> str:
        """
        Analyzes an image (drawing, P&ID, photograph, diagram) and returns a textual description.
        Runs strictly locally without external cloud API calls.
        """
        pass


class MockLocalVisionModel(BaseVisionModel):
    """Default placeholder vision model that generates descriptive metadata when heavy VLM is offline."""

    def analyze(self, image: Union[str, bytes, Path, Image.Image], prompt: Optional[str] = None) -> str:
        return (
            "[Visual Inspection Asset: P&ID / Engineering Photograph / Layout Diagram. "
            "Local VLM plug-in available for detailed visual feature description.]"
        )


# Global instance
vision_model: BaseVisionModel = MockLocalVisionModel()
