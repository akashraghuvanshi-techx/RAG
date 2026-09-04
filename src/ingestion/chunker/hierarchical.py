"""Hierarchical Chunking with Parent-Child Relationships and Industrial Entity Extraction."""

import re
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from src.ingestion.extractors.base import ExtractedDocument, ExtractedBlock


class Chunk(BaseModel):
    """A granular chunk of document text ready for embedding and indexing."""
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    document_name: str
    chunk_index: int
    page_number: int = 1
    section: str = "General"
    subsection: str = ""
    parent_chunk_id: Optional[str] = None
    text: str
    token_count: int = 0

    # Categorical metadata
    document_type: str = "General"
    revision: str = "Rev 0"
    version: int = 1
    effective_date: Optional[str] = None
    department: str = "general"
    project: Optional[str] = None
    access_level: str = "internal"
    status: str = "active"

    # Entities and modal flags
    equipment_tags: List[str] = Field(default_factory=list)
    bbox: Optional[List[float]] = None
    ocr_confidence: Optional[float] = None
    is_table: bool = False
    is_figure: bool = False
    is_parent: bool = False


# Industrial Tag & Standard Regex Patterns
EQUIPMENT_TAG_PATTERN = re.compile(r"\b([PVEFTCKM]|TK|CV|MOV|PSV|HEX)-\d{3,4}[A-Z]?\b", re.IGNORECASE)
INDUSTRY_STANDARD_PATTERN = re.compile(r"\b(API\s*\d{3,4}[A-Z]?|ASME\s*(?:B31\.[13]|Section\s*VIII|[A-Z0-9.]+)|ISO\s*\d{4,5}|ASTM\s*[A-Z0-9.]+|IS\s*\d{3,5})\b", re.IGNORECASE)
REVISION_PATTERN = re.compile(r"(?:^|[\s_.-])Rev(?:ision)?\.?\s*(\d+)\b", re.IGNORECASE)


def extract_equipment_tags(text: str) -> List[str]:
    """Extracts industrial equipment tags (e.g. P-101, V-204) and standards (API 610, ASME B31.3)."""
    tags = set()
    for match in EQUIPMENT_TAG_PATTERN.finditer(text):
        tags.add(match.group(0).upper())
    for match in INDUSTRY_STANDARD_PATTERN.finditer(text):
        tags.add(re.sub(r"\s+", " ", match.group(0)).upper())
    return sorted(list(tags))


def extract_revision(text: str, default: str = "Rev 0") -> str:
    """Extracts revision number from text or filename."""
    match = REVISION_PATTERN.search(text)
    if match:
        return f"Rev {match.group(1)}"
    return default


class HierarchicalChunker:
    """
    Splits extracted document blocks into hierarchical parent and child chunks.
    Preserves document structure: Document -> Section -> Subsection -> Paragraph/Table.
    """

    def __init__(self, target_child_size: int = 250, child_overlap: int = 40):
        self.target_child_size = target_child_size
        self.child_overlap = child_overlap

    def chunk_document(
        self,
        extracted_doc: ExtractedDocument,
        document_id: str,
        doc_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        doc_metadata = doc_metadata or {}
        doc_name = doc_metadata.get("filename", extracted_doc.filename)
        doc_type = doc_metadata.get("document_type", "General")
        department = doc_metadata.get("department", "general")
        access_level = doc_metadata.get("access_level", "internal")
        revision = doc_metadata.get("revision") or extract_revision(doc_name, "Rev 0")
        version = doc_metadata.get("version", 1)
        effective_date = doc_metadata.get("effective_date")
        status = doc_metadata.get("status", "active")
        project = doc_metadata.get("project")

        all_chunks: List[Chunk] = []
        chunk_counter = 0

        # 1. Group blocks by (page_number, section)
        sections: Dict[str, List[ExtractedBlock]] = {}
        for block in extracted_doc.blocks:
            sec_key = f"{block.page_number}::{block.section or 'General'}"
            if sec_key not in sections:
                sections[sec_key] = []
            sections[sec_key].append(block)

        # 2. For each section, build Parent Chunk + Child Chunks
        for sec_key, sec_blocks in sections.items():
            if not sec_blocks:
                continue

            page_num = sec_blocks[0].page_number
            section_title = sec_blocks[0].section or "General"
            sec_full_text = "\n\n".join(b.text for b in sec_blocks if b.text.strip())

            if not sec_full_text.strip():
                continue

            # Check for tables or figures that should be intact chunks
            table_or_figure_blocks = [b for b in sec_blocks if b.is_table or b.is_figure]
            prose_blocks = [b for b in sec_blocks if not b.is_table and not b.is_figure]

            # Create Parent Chunk for the section
            parent_chunk_id = str(uuid.uuid4())
            parent_tags = extract_equipment_tags(sec_full_text)
            chunk_counter += 1

            parent_chunk = Chunk(
                chunk_id=parent_chunk_id,
                document_id=document_id,
                document_name=doc_name,
                chunk_index=chunk_counter,
                page_number=page_num,
                section=section_title,
                subsection="",
                parent_chunk_id=None,
                text=sec_full_text,
                token_count=len(sec_full_text.split()),
                document_type=doc_type,
                revision=revision,
                version=version,
                effective_date=effective_date,
                department=department,
                project=project,
                access_level=access_level,
                status=status,
                equipment_tags=parent_tags,
                is_parent=True
            )
            all_chunks.append(parent_chunk)

            # 3. Create Child Chunks for prose content
            if prose_blocks:
                combined_prose = "\n\n".join(b.text for b in prose_blocks if b.text.strip())
                words = combined_prose.split()

                if len(words) <= self.target_child_size:
                    # Single child chunk
                    chunk_counter += 1
                    child_tags = extract_equipment_tags(combined_prose)
                    child_chunk = Chunk(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        document_name=doc_name,
                        chunk_index=chunk_counter,
                        page_number=page_num,
                        section=section_title,
                        subsection=prose_blocks[0].subsection or "",
                        parent_chunk_id=parent_chunk_id,
                        text=combined_prose,
                        token_count=len(words),
                        document_type=doc_type,
                        revision=revision,
                        version=version,
                        effective_date=effective_date,
                        department=department,
                        project=project,
                        access_level=access_level,
                        status=status,
                        equipment_tags=child_tags,
                        is_parent=False
                    )
                    all_chunks.append(child_chunk)
                else:
                    # Sliding window child chunks with overlap
                    start = 0
                    while start < len(words):
                        end = min(start + self.target_child_size, len(words))
                        chunk_words = words[start:end]
                        chunk_text = " ".join(chunk_words)

                        chunk_counter += 1
                        child_tags = extract_equipment_tags(chunk_text)

                        child_chunk = Chunk(
                            chunk_id=str(uuid.uuid4()),
                            document_id=document_id,
                            document_name=doc_name,
                            chunk_index=chunk_counter,
                            page_number=page_num,
                            section=section_title,
                            subsection="",
                            parent_chunk_id=parent_chunk_id,
                            text=chunk_text,
                            token_count=len(chunk_words),
                            document_type=doc_type,
                            revision=revision,
                            version=version,
                            effective_date=effective_date,
                            department=department,
                            project=project,
                            access_level=access_level,
                            status=status,
                            equipment_tags=child_tags,
                            is_parent=False
                        )
                        all_chunks.append(child_chunk)

                        if end == len(words):
                            break
                        start += (self.target_child_size - self.child_overlap)

            # 4. Handle dedicated Table / Figure chunks
            for tf_block in table_or_figure_blocks:
                chunk_counter += 1
                tf_tags = extract_equipment_tags(tf_block.text)
                tf_chunk = Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    document_name=doc_name,
                    chunk_index=chunk_counter,
                    page_number=tf_block.page_number,
                    section=tf_block.section or section_title,
                    subsection=tf_block.subsection or "",
                    parent_chunk_id=parent_chunk_id,
                    text=tf_block.text,
                    token_count=len(tf_block.text.split()),
                    document_type=doc_type,
                    revision=revision,
                    version=version,
                    effective_date=effective_date,
                    department=department,
                    project=project,
                    access_level=access_level,
                    status=status,
                    equipment_tags=tf_tags,
                    bbox=tf_block.bbox,
                    ocr_confidence=tf_block.confidence,
                    is_table=tf_block.is_table,
                    is_figure=tf_block.is_figure,
                    is_parent=False
                )
                all_chunks.append(tf_chunk)

        return all_chunks
