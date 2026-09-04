"""Extractors package with format dispatcher."""

from pathlib import Path
from typing import Dict, Type
from src.ingestion.extractors.base import BaseExtractor, ExtractedDocument, ExtractedBlock
from src.ingestion.extractors.pdf_extractor import PDFExtractor
from src.ingestion.extractors.docx_extractor import DocxExtractor
from src.ingestion.extractors.xlsx_extractor import XlsxExtractor
from src.ingestion.extractors.pptx_extractor import PptxExtractor
from src.ingestion.extractors.text_extractor import TextExtractor
from src.ingestion.extractors.image_extractor import ImageExtractor

EXTRACTOR_REGISTRY: Dict[str, Type[BaseExtractor]] = {
    ".pdf": PDFExtractor,
    ".docx": DocxExtractor,
    ".doc": DocxExtractor,
    ".xlsx": XlsxExtractor,
    ".xls": XlsxExtractor,
    ".pptx": PptxExtractor,
    ".ppt": PptxExtractor,
    ".txt": TextExtractor,
    ".md": TextExtractor,
    ".markdown": TextExtractor,
    ".csv": TextExtractor,
    ".log": TextExtractor,
    ".png": ImageExtractor,
    ".jpg": ImageExtractor,
    ".jpeg": ImageExtractor,
    ".tiff": ImageExtractor,
    ".tif": ImageExtractor,
    ".bmp": ImageExtractor,
}


def get_extractor_for_file(file_path: Path) -> BaseExtractor:
    """Returns the matching extractor instance for the given file extension."""
    suffix = file_path.suffix.lower()
    extractor_cls = EXTRACTOR_REGISTRY.get(suffix)
    if not extractor_cls:
        # Fallback to TextExtractor
        return TextExtractor()
    return extractor_cls()


__all__ = [
    "BaseExtractor",
    "ExtractedDocument",
    "ExtractedBlock",
    "PDFExtractor",
    "DocxExtractor",
    "XlsxExtractor",
    "PptxExtractor",
    "TextExtractor",
    "ImageExtractor",
    "get_extractor_for_file",
]
