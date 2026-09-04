"""Base extraction data models and interface."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field


class ExtractedBlock(BaseModel):
    """A semantic block of extracted content from a document."""
    text: str
    page_number: int = 1
    block_type: str = "paragraph"  # heading, paragraph, table, figure, ocr
    section: Optional[str] = None
    subsection: Optional[str] = None
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1]
    confidence: Optional[float] = None
    is_table: bool = False
    is_figure: bool = False
    raw_table_data: Optional[List[List[str]]] = None
    image_path: Optional[str] = None


class ExtractedDocument(BaseModel):
    """Structured extraction result for an ingested document."""
    filename: str
    file_type: str
    total_pages: int = 1
    blocks: List[ExtractedBlock] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_scanned: bool = False

    def get_full_text(self) -> str:
        return "\n\n".join(b.text for b in self.blocks if b.text.strip())


class BaseExtractor(ABC):
    """Abstract interface for all document format extractors."""

    @abstractmethod
    def extract(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> ExtractedDocument:
        """Extracts text, layout structure, tables, and images from the file."""
        pass
