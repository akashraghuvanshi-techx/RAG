"""Integration tests for FastAPI REST Endpoints."""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["sovereign_mode"] is True


def test_metrics_endpoint(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_documents" in data
    assert "total_chunks" in data


def test_upload_and_search_flow(client, tmp_path):
    # Create test text document
    test_file = tmp_path / "test_procedure.txt"
    test_file.write_text(
        "# SECTION 1: TURBINE INSPECTION\nGas turbine GT-501 vibration trip limit is 7.5 mm/s RMS under API 616.",
        encoding="utf-8"
    )

    with open(test_file, "rb") as f:
        upload_resp = client.post(
            "/documents/upload",
            files={"file": ("test_procedure.txt", f, "text/plain")},
            data={"document_type": "Procedure", "department": "mechanical", "access_level": "confidential"}
        )

    assert upload_resp.status_code == 200
    doc_id = upload_resp.json()["document_id"]

    # Search for GT-501
    search_resp = client.post(
        "/rag/search",
        json={"query": "GT-501 vibration limit", "top_k": 5}
    )
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    assert len(results) > 0
    assert any("GT-501" in r["text"] for r in results)

    # Clean up
    del_resp = client.delete(f"/documents/{doc_id}")
    assert del_resp.status_code == 200
