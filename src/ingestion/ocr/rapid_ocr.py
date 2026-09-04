"""Local OCR engine using RapidOCR (PaddleOCR ONNX port)."""

from typing import List, Union, Optional
from pathlib import Path
import numpy as np
from PIL import Image
from src.ingestion.ocr.base import BaseOCREngine, OCRResultBox
from src.config import settings
from src.logging_config import rag_logger


class RapidOCREngine(BaseOCREngine):
    """Fully local, high-performance ONNX OCR engine."""

    def __init__(self):
        self._engine = None
        self._initialize()

    def _initialize(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
            rag_logger.info("RapidOCR (ONNX local engine) initialized successfully.")
        except Exception as e:
            rag_logger.warning(f"Failed to initialize RapidOCR: {e}. Fallback mode active.")
            self._engine = None

    def process_image(self, image: Union[str, bytes, np.ndarray, Image.Image, Path]) -> List[OCRResultBox]:
        """Runs OCR on the given image and extracts text, bounding boxes, and confidence."""
        if self._engine is None:
            return []

        # Convert PIL Image or Path to numpy array if needed
        img_input = image
        if isinstance(image, Path):
            img_input = str(image)
        elif isinstance(image, Image.Image):
            img_input = np.array(image.convert("RGB"))
        elif isinstance(image, bytes):
            import io
            pil_img = Image.open(io.BytesIO(image)).convert("RGB")
            img_input = np.array(pil_img)

        try:
            result, _ = self._engine(img_input)
            if not result:
                return []

            boxes: List[OCRResultBox] = []
            for item in result:
                # item structure: [box_points, text, score]
                # box_points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                raw_box, text, score = item[0], item[1], float(item[2])
                if score < settings.OCR_CONFIDENCE_THRESHOLD:
                    continue

                xs = [p[0] for p in raw_box]
                ys = [p[1] for p in raw_box]
                bbox = [min(xs), min(ys), max(xs), max(ys)]

                boxes.append(OCRResultBox(text=text.strip(), confidence=score, bbox=bbox))

            return boxes
        except Exception as e:
            rag_logger.error(f"OCR processing failed: {e}")
            return []


# Global singleton OCR engine
ocr_engine = RapidOCREngine()
