"""Text, Markdown, and CSV extractor."""

from pathlib import Path
from typing import Optional, Dict, Any, List
from src.ingestion.extractors.base import BaseExtractor, ExtractedDocument, ExtractedBlock
from src.logging_config import rag_logger


class TextExtractor(BaseExtractor):
    """Extracts content from plain text (.txt), Markdown (.md), and CSV files."""

    def extract(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> ExtractedDocument:
        metadata = metadata or {}
        rag_logger.info(f"Extracting Text/Markdown: {file_path.name}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception as e:
            rag_logger.error(f"Error reading file {file_path}: {e}")
            content = ""

        blocks: List[ExtractedBlock] = []
        lines = content.splitlines()

        current_section = "General"
        current_subsection = ""
        current_page = 1
        buffer: List[str] = []

        line_count = 0
        for line in lines:
            line_count += 1
            if line_count % 45 == 0:
                current_page += 1

            trimmed = line.strip()
            # Markdown heading detection
            if trimmed.startswith("# ") or trimmed.startswith("## "):
                # Flush previous buffer
                if buffer:
                    blocks.append(ExtractedBlock(
                        text="\n".join(buffer),
                        page_number=current_page,
                        block_type="paragraph",
                        section=current_section,
                        subsection=current_subsection
                    ))
                    buffer = []

                if trimmed.startswith("# "):
                    current_section = trimmed.lstrip("# ").strip()
                    current_subsection = ""
                else:
                    current_subsection = trimmed.lstrip("# ").strip()

                blocks.append(ExtractedBlock(
                    text=trimmed,
                    page_number=current_page,
                    block_type="heading",
                    section=current_section,
                    subsection=current_subsection
                ))
            else:
                if trimmed:
                    buffer.append(trimmed)
                elif buffer:
                    # Paragraph boundary
                    blocks.append(ExtractedBlock(
                        text="\n".join(buffer),
                        page_number=current_page,
                        block_type="paragraph",
                        section=current_section,
                        subsection=current_subsection
                    ))
                    buffer = []

        if buffer:
            blocks.append(ExtractedBlock(
                text="\n".join(buffer),
                page_number=current_page,
                block_type="paragraph",
                section=current_section,
                subsection=current_subsection
            ))

        return ExtractedDocument(
            filename=file_path.name,
            file_type="text",
            total_pages=max(1, current_page),
            blocks=blocks,
            metadata=metadata
        )
