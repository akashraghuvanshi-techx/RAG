"""Microsoft Word (.docx) extractor."""

from pathlib import Path
from typing import Optional, Dict, Any, List
import docx
from src.ingestion.extractors.base import BaseExtractor, ExtractedDocument, ExtractedBlock
from src.logging_config import rag_logger


class DocxExtractor(BaseExtractor):
    """Extracts text, headings, and tables from Word documents."""

    def extract(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> ExtractedDocument:
        metadata = metadata or {}
        doc = docx.Document(file_path)
        blocks: List[ExtractedBlock] = []

        current_section = "General"
        current_subsection = ""
        current_page = 1  # DOCX is reflowable, estimated by paragraph count

        rag_logger.info(f"Extracting DOCX: {file_path.name}")

        # Iterate through paragraphs and tables in order of appearance
        para_count = 0
        for element in doc.element.body:
            if element.tag.endswith("p"):
                # Paragraph
                p = docx.text.paragraph.Paragraph(element, doc)
                text = p.text.strip()
                if not text:
                    continue

                para_count += 1
                if para_count % 15 == 0:
                    current_page += 1

                style_name = p.style.name.lower() if p.style else ""
                if "heading 1" in style_name or "title" in style_name:
                    current_section = text
                    blocks.append(ExtractedBlock(
                        text=text,
                        page_number=current_page,
                        block_type="heading",
                        section=current_section
                    ))
                elif "heading 2" in style_name or "heading 3" in style_name:
                    current_subsection = text
                    blocks.append(ExtractedBlock(
                        text=text,
                        page_number=current_page,
                        block_type="heading",
                        section=current_section,
                        subsection=current_subsection
                    ))
                else:
                    blocks.append(ExtractedBlock(
                        text=text,
                        page_number=current_page,
                        block_type="paragraph",
                        section=current_section,
                        subsection=current_subsection
                    ))

            elif element.tag.endswith("tbl"):
                # Table
                tbl = docx.table.Table(element, doc)
                rows_data = []
                for row in tbl.rows:
                    rows_data.append([c.text.strip().replace("\n", " ") for c in row.cells])

                if rows_data and len(rows_data) > 1:
                    headers = rows_data[0]
                    sep = ["---"] * len(headers)
                    lines = [
                        "| " + " | ".join(headers) + " |",
                        "| " + " | ".join(sep) + " |"
                    ]
                    for r in rows_data[1:]:
                        lines.append("| " + " | ".join(r) + " |")

                    table_md = "\n".join(lines)
                    blocks.append(ExtractedBlock(
                        text=table_md,
                        page_number=current_page,
                        block_type="table",
                        section=current_section,
                        subsection=current_subsection,
                        is_table=True,
                        raw_table_data=rows_data
                    ))

        return ExtractedDocument(
            filename=file_path.name,
            file_type="docx",
            total_pages=max(1, current_page),
            blocks=blocks,
            metadata=metadata
        )
