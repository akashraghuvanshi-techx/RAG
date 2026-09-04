"""Tests for Structured Citations and Provenance tracking."""

import pytest
from src.rag.citations import CitationBuilder


def test_citation_builder_deduplication():
    evidence = [
        {
            "chunk_id": "c1",
            "document_id": "doc-001",
            "document_name": "SOP-MEC-PUMP-001_Rev5.pdf",
            "page_number": 1,
            "section": "SECTION 3.1: IMPELLER CAVITATION",
            "score": 0.94,
            "revision": "Rev 5",
            "text": "Cavitation pit depth threshold is 2.5 mm."
        },
        # Duplicate provenance (same doc, page, and section)
        {
            "chunk_id": "c2",
            "document_id": "doc-001",
            "document_name": "SOP-MEC-PUMP-001_Rev5.pdf",
            "page_number": 1,
            "section": "SECTION 3.1: IMPELLER CAVITATION",
            "score": 0.88,
            "revision": "Rev 5",
            "text": "Additional notes on impeller erosion."
        },
        # Different page
        {
            "chunk_id": "c3",
            "document_id": "doc-001",
            "document_name": "SOP-MEC-PUMP-001_Rev5.pdf",
            "page_number": 2,
            "section": "SECTION 4.2: SEAL FLUSH",
            "score": 0.82,
            "revision": "Rev 5",
            "text": "Mechanical seal API Plan 53A."
        }
    ]

    citations = CitationBuilder.build_citations(evidence)
    assert len(citations) == 2
    assert citations[0].page == 1
    assert citations[0].relevance_score == 0.94
    assert citations[1].page == 2
