"""Tests for all document extractors (PDF, DOCX, XLSX, TXT, Image)."""

import pytest
from pathlib import Path
from evaluation.synthetic_generator import generate_synthetic_documents
from src.ingestion.extractors import get_extractor_for_file


@pytest.fixture(scope="module")
def sample_files(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("test_corpus")
    files = generate_synthetic_documents(out_dir)
    return files


def test_docx_extractor(sample_files):
    file_path = sample_files["sop_rev3"]
    extractor = get_extractor_for_file(file_path)
    doc = extractor.extract(file_path)

    assert doc.file_type == "docx"
    assert len(doc.blocks) > 0
    full_text = doc.get_full_text()
    assert "SOP-MEC-PUMP-001" in full_text
    assert "4.5 mm" in full_text


def test_pdf_extractor_native(sample_files):
    file_path = sample_files["sop_rev5"]
    extractor = get_extractor_for_file(file_path)
    doc = extractor.extract(file_path)

    assert doc.file_type == "pdf"
    assert doc.total_pages == 2
    full_text = doc.get_full_text()
    assert "P-101" in full_text
    assert "2.5 mm" in full_text
    assert "Plan 53A" in full_text


def test_xlsx_extractor(sample_files):
    file_path = sample_files["equipment_register"]
    extractor = get_extractor_for_file(file_path)
    doc = extractor.extract(file_path)

    assert doc.file_type == "xlsx"
    assert len(doc.blocks) > 0
    table_block = doc.blocks[0]
    assert table_block.is_table is True
    assert "P-101" in table_block.text
    assert "V-204" in table_block.text


def test_text_extractor(tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("# Chapter 1\nInspection finding note.\n\n# Chapter 2\nSecond section.", encoding="utf-8")
    extractor = get_extractor_for_file(txt_file)
    doc = extractor.extract(txt_file)

    assert doc.file_type == "text"
    assert len(doc.blocks) >= 2
    assert "Chapter 1" in doc.get_full_text()
