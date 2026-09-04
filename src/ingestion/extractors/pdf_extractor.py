"""PyMuPDF extractor with automatic scanned document detection and local OCR routing."""

import io
from pathlib import Path
from typing import Optional, Dict, Any, List
import pymupdf  # PyMuPDF
from src.ingestion.extractors.base import BaseExtractor, ExtractedDocument, ExtractedBlock
from src.ingestion.ocr.rapid_ocr import ocr_engine
from src.ingestion.vision.base import vision_model
from src.config import settings
from src.logging_config import rag_logger


class PDFExtractor(BaseExtractor):
    """Extracts text, layout, tables, and runs local OCR for scanned PDFs."""

    def extract(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> ExtractedDocument:
        metadata = metadata or {}
        doc = pymupdf.open(file_path)
        total_pages = len(doc)
        blocks: List[ExtractedBlock] = []
        is_scanned_doc = False

        current_section = "General"
        current_subsection = ""

        rag_logger.info(f"Extracting PDF: {file_path.name} ({total_pages} pages)")

        for page_num in range(1, total_pages + 1):
            page = doc[page_num - 1]
            raw_text = page.get_text("text").strip()

            # 1. Check for native tables
            table_rects = []
            try:
                tables = page.find_tables()
                if tables and tables.tables:
                    for tab in tables.tables:
                        df_rows = tab.extract()
                        if df_rows and len(df_rows) > 1:
                            # Format table as clean markdown
                            headers = [str(c or "").strip() for c in df_rows[0]]
                            sep = ["---"] * len(headers)
                            md_table_lines = [
                                "| " + " | ".join(headers) + " |",
                                "| " + " | ".join(sep) + " |"
                            ]
                            for row in df_rows[1:]:
                                md_table_lines.append("| " + " | ".join(str(c or "").strip() for c in row) + " |")

                            table_text = "\n".join(md_table_lines)
                            table_rects.append(tab.bbox)
                            blocks.append(ExtractedBlock(
                                text=table_text,
                                page_number=page_num,
                                block_type="table",
                                section=current_section,
                                subsection=current_subsection,
                                bbox=list(tab.bbox),
                                is_table=True,
                                raw_table_data=df_rows
                            ))
            except Exception as e:
                rag_logger.debug(f"Native table extraction note on page {page_num}: {e}")

            # 2. Check if the page is scanned (text length < threshold)
            if len(raw_text) < settings.OCR_SCANNED_MIN_CHAR_THRESHOLD:
                is_scanned_doc = True
                rag_logger.info(f"Page {page_num} in {file_path.name} appears scanned. Triggering local OCR...")

                # Render page to high-res image
                pix = page.get_pixmap(dpi=200)
                img_bytes = pix.tobytes("png")
                ocr_results = ocr_engine.process_image(img_bytes)

                if ocr_results:
                    # Group OCR text into logical paragraphs/findings
                    ocr_lines = [item.text for item in ocr_results if item.text]
                    full_ocr_text = "\n".join(ocr_lines)
                    avg_confidence = sum(item.confidence for item in ocr_results) / len(ocr_results)

                    blocks.append(ExtractedBlock(
                        text=full_ocr_text,
                        page_number=page_num,
                        block_type="ocr",
                        section=current_section,
                        subsection=current_subsection,
                        confidence=round(avg_confidence, 3),
                        bbox=[0, 0, pix.width, pix.height]
                    ))
                else:
                    # Fallback if OCR detected nothing
                    if raw_text:
                        blocks.append(ExtractedBlock(
                            text=raw_text,
                            page_number=page_num,
                            block_type="paragraph",
                            section=current_section,
                        ))
            else:
                # 3. Native Text Extraction with structural block parsing
                page_blocks = page.get_text("blocks")
                # Sort blocks vertically then horizontally
                page_blocks.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))

                for b in page_blocks:
                    # b: (x0, y0, x1, y1, text, block_no, block_type)
                    if len(b) < 5:
                        continue
                    b_text = b[4].strip()
                    if not b_text:
                        continue

                    # Check if block overlaps an already extracted table
                    b_rect = pymupdf.Rect(b[0], b[1], b[2], b[3])
                    overlaps_table = any(b_rect.intersects(pymupdf.Rect(tr)) for tr in table_rects)
                    if overlaps_table:
                        continue

                    # Detect section / chapter headers (short uppercase lines or numbered patterns)
                    lines = [line.strip() for line in b_text.split("\n") if line.strip()]
                    first_line = lines[0] if lines else ""

                    if len(lines) <= 2 and (
                        first_line.isupper() or
                        first_line.lower().startswith(("section", "chapter", "part", "annexure", "sop")) or
                        (len(first_line) < 60 and any(first_line.startswith(p) for p in ["1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10."]))
                    ):
                        current_section = first_line
                        blocks.append(ExtractedBlock(
                            text=b_text,
                            page_number=page_num,
                            block_type="heading",
                            section=current_section,
                            bbox=[b[0], b[1], b[2], b[3]]
                        ))
                    else:
                        blocks.append(ExtractedBlock(
                            text=b_text,
                            page_number=page_num,
                            block_type="paragraph",
                            section=current_section,
                            subsection=current_subsection,
                            bbox=[b[0], b[1], b[2], b[3]]
                        ))

            # 4. Extract embedded images (engineering diagrams, photos)
            try:
                images = page.get_images(full=True)
                for img_idx, img_info in enumerate(images):
                    xref = img_info[0]
                    base_image = doc.extract_image(xref)
                    if base_image and len(base_image.get("image", b"")) > 4096:  # ignore tiny icons
                        img_bytes = base_image["image"]
                        desc = vision_model.analyze(img_bytes)
                        blocks.append(ExtractedBlock(
                            text=f"[Diagram/Image on Page {page_num}]: {desc}",
                            page_number=page_num,
                            block_type="figure",
                            section=current_section,
                            is_figure=True
                        ))
            except Exception as e:
                rag_logger.debug(f"Image extraction note on page {page_num}: {e}")

        doc.close()
        return ExtractedDocument(
            filename=file_path.name,
            file_type="pdf",
            total_pages=total_pages,
            blocks=blocks,
            metadata=metadata,
            is_scanned=is_scanned_doc
        )
