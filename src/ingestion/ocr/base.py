"""Base OCR engine interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union
import numpy as np
from PIL import Image


class OCRResultBox:
    def __init__(self, text: str, confidence: float, bbox: List[float]):
        self.text = text
        self.confidence = confidence
        self.bbox = bbox  # [x0, y0, x1, y1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox
        }


class BaseOCREngine(ABC):
    @abstractmethod
    def process_image(self, image: Union[str, bytes, np.ndarray, Image.Image]) -> List[OCRResultBox]:
        """Runs OCR on an image and returns detected text boxes with bounding boxes and confidence."""
        pass
