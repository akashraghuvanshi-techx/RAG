"""Standalone image extractor with local OCR and Vision Model integration."""

from pathlib import Path
from typing import Optional, Dict, Any, List
from PIL import Image
from src.ingestion.extractors.base import BaseExtractor, ExtractedDocument, ExtractedBlock
from src.ingestion.ocr.rapid_ocr import ocr_engine
from src.ingestion.vision.base import vision_model
from src.logging_config import rag_logger


class ImageExtractor(BaseExtractor):
    """Extracts text and visual descriptions from engineering drawings, photos, and scans."""

    def extract(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> ExtractedDocument:
        metadata = metadata or {}
        rag_logger.info(f"Extracting Image: {file_path.name}")

        with Image.open(file_path) as img:
            width, height = img.size
            format_name = img.format

        # 1. Local OCR for text, labels, equipment tags
        ocr_results = ocr_engine.process_image(file_path)
        blocks: List[ExtractedBlock] = []

        if ocr_results:
            ocr_text = "\n".join(item.text for item in ocr_results if item.text)
            avg_conf = sum(item.confidence for item in ocr_results) / len(ocr_results)
            blocks.append(ExtractedBlock(
                text=ocr_text,
                page_number=1,
                block_type="ocr",
                section="Image Text / Diagram Annotations",
                confidence=round(avg_conf, 3),
                bbox=[0, 0, width, height],
                image_path=str(file_path)
            ))

        # 2. Local Vision Model analysis
        with open(file_path, "rb") as f:
            img_bytes = f.read()

        visual_desc = vision_model.analyze(img_bytes)
        blocks.append(ExtractedBlock(
            text=f"[Image Metadata: {format_name} {width}x{height}px]\n{visual_desc}",
            page_number=1,
            block_type="figure",
            section="Visual Content Description",
            is_figure=True,
            image_path=str(file_path)
        ))

        return ExtractedDocument(
            filename=file_path.name,
            file_type="image",
            total_pages=1,
            blocks=blocks,
            metadata=metadata,
            is_scanned=True
        )
