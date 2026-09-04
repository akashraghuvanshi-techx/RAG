"""Tests for hierarchical chunking, parent-child linkage, and industrial tag extraction."""

import pytest
from src.ingestion.extractors.base import ExtractedDocument, ExtractedBlock
from src.ingestion.chunker import HierarchicalChunker, extract_equipment_tags, extract_revision


def test_equipment_tag_extraction():
    sample_text = (
        "Emergency inspection on pump P-101 and vessel V-204 according to API 610 "
        "and ASME B31.3. Valve CV-401 showed cavitation in Rev 5."
    )
    tags = extract_equipment_tags(sample_text)
    assert "P-101" in tags
    assert "V-204" in tags
    assert "API 610" in tags
    assert "ASME B31.3" in tags
    assert "CV-401" in tags


def test_revision_extraction():
    assert extract_revision("SOP-MEC-PUMP-001_Rev5.pdf") == "Rev 5"
    assert extract_revision("Maintenance Guide Revision 3.docx") == "Rev 3"
    assert extract_revision("General Document.pdf") == "Rev 0"


def test_hierarchical_chunking_parent_child():
    blocks = [
        ExtractedBlock(
            text="SECTION 1.0: PUMP SPECIFICATIONS\nPump P-101 is a critical heavy duty hydrocarbon feed pump.",
            page_number=1,
            block_type="paragraph",
            section="SECTION 1.0: PUMP SPECIFICATIONS"
        ),
        ExtractedBlock(
            text="SECTION 2.0: VIBRATION LIMITS\nVibration velocity shall not exceed 4.5 mm/s RMS under API 610.",
            page_number=1,
            block_type="paragraph",
            section="SECTION 2.0: VIBRATION LIMITS"
        )
    ]
    extracted_doc = ExtractedDocument(
        filename="Test_SOP.pdf",
        file_type="pdf",
        total_pages=1,
        blocks=blocks
    )

    chunker = HierarchicalChunker(target_child_size=100)
    chunks = chunker.chunk_document(extracted_doc, document_id="doc-123", doc_metadata={"department": "mechanical"})

    # Should contain parent chunks and child chunks
    parent_chunks = [c for c in chunks if c.is_parent]
    child_chunks = [c for c in chunks if not c.is_parent]

    assert len(parent_chunks) == 2
    assert len(child_chunks) == 2

    # Check parent-child linkage
    for child in child_chunks:
        assert child.parent_chunk_id is not None
        assert any(p.chunk_id == child.parent_chunk_id for p in parent_chunks)
        assert child.department == "mechanical"
