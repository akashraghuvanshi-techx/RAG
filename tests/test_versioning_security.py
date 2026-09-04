"""Tests for Version-Awareness and Security Clearance Filtering."""

import pytest
from src.security.access_control import UserContext, ClearanceLevel, build_access_filter
from src.retrieval.bm25 import BM25Index


def test_clearance_filtering():
    # User with CONFIDENTIAL clearance
    user = UserContext(role="engineer", clearance=ClearanceLevel.CONFIDENTIAL, departments=["mechanical"])
    filters = build_access_filter(user)

    allowed = filters["allowed_access_levels"]
    assert "public" in allowed
    assert "internal" in allowed
    assert "confidential" in allowed
    assert "restricted" not in allowed
    assert "secret" not in allowed


def test_security_access_filtering_in_search():
    index = BM25Index()
    chunks = [
        {"chunk_id": "c_pub", "text": "Public annual safety overview.", "access_level": "public", "department": "general"},
        {"chunk_id": "c_sec", "text": "Secret defense turbine specification.", "access_level": "secret", "department": "defense"},
    ]
    index.build_index(chunks)

    # Guest user with PUBLIC clearance
    user_filter = {"allowed_access_levels": ["public"]}
    results = index.search("specification safety", filters=user_filter)

    # Must NOT retrieve secret document
    retrieved_ids = [r["chunk_id"] for r in results]
    assert "c_pub" in retrieved_ids
    assert "c_sec" not in retrieved_ids


def test_versioning_status_filtering():
    index = BM25Index()
    chunks = [
        {"chunk_id": "c_old", "text": "Cavitation pitting depth 4.5 mm", "status": "superseded", "revision": "Rev 3"},
        {"chunk_id": "c_new", "text": "Cavitation pitting depth 2.5 mm", "status": "active", "revision": "Rev 5"},
    ]
    index.build_index(chunks)

    # Default search for active versions
    active_results = index.search("cavitation pitting", filters={"status": "active"})
    assert len(active_results) == 1
    assert active_results[0]["chunk_id"] == "c_new"

    # Explicit historical search
    old_results = index.search("cavitation pitting", filters={"status": "superseded"})
    assert len(old_results) == 1
    assert old_results[0]["chunk_id"] == "c_old"
