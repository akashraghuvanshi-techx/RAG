"""OCR engine package."""
from src.ingestion.ocr.base import BaseOCREngine, OCRResultBox
from src.ingestion.ocr.rapid_ocr import ocr_engine, RapidOCREngine

__all__ = ["BaseOCREngine", "OCRResultBox", "ocr_engine", "RapidOCREngine"]
