# Sovereign Multimodal Local RAG System
> **Production-Grade, Fully Local, Self-Hosted RAG Architecture for Refineries, PSUs, Defense Units, and Sovereign Workbenches.**

---

## 1. Executive Summary

This system implements a **Local Sovereign Multimodal Hybrid RAG** system designed to run on-premises in high-security, air-gapped enterprise environments.

### Core Architectural Invariants
* **100% Local & Sovereign**: Never transmits documents, embeddings, queries, images, or answers to external APIs (OpenAI, Anthropic, Google, Azure, AWS).
* **Fail-Closed Security Guard**: Built-in network interceptor (`SovereignGuard`) blocks and audits any unauthorized outbound TCP connections.
* **Hybrid Multimodal Retrieval**: Combines semantic dense vector search (Qdrant) with industrial-grade BM25 keyword matching for exact equipment tags (`P-101`, `V-204`, `API 610`, `ASME B31.3`), fused via **Reciprocal Rank Fusion (RRF)**.
* **Local Cross-Encoder Reranking**: Re-scores top candidates using an on-premises cross-encoder.
* **Hierarchical Chunking & Parent Expansion**: Preserves `Document -> Page -> Section -> Subsection -> Chunk` hierarchy with parent-child linkage and surrounding context expansion.
* **Scanned Industrial Document Processing**: Detects scanned pages and performs local OCR using `RapidOCR` (ONNX PaddleOCR port), preserving bounding boxes, confidence, and page provenance.
* **Strict Provenance & Structured Citations**: Cites verified document IDs, page numbers, sections, and revisions. Never hallucinates citations.
* **Security & Version Awareness**: Role-based access control (RBAC) and classification level filtering (`public`, `internal`, `confidential`, `restricted`, `secret`) enforced at retrieval time. Prefers active revisions (`Rev 5`) while supporting explicit historical searches (`Rev 3`).
* **Standalone AI Agent Tool**: Exposes `search_knowledge_base(query, filters, top_k)` for integration with agent workflows.

---

## 2. System Architecture

```
                    +-----------------------------+
                    |   User / Sovereign Agent    |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    |       FastAPI Backend       |
                    |   (/documents, /rag, ...)   |
                    +--------------+--------------+
                                   |
              +--------------------+--------------------+
              |                                         |
              v                                         v
+---------------------------+             +---------------------------+
| Ingestion Pipeline        |             | Hybrid Retrieval Engine   |
| - File Validation         |             | - Access Control Filter   |
| - Format Extractors:      |             | - Version Status Filter   |
|   * PDF / Scanned PDF     |             | - Semantic Search (Qdrant)|
|   * Word (.docx)          |             | - BM25 (Tags: P-101, etc.)|
|   * Excel (.xlsx)         |             | - Reciprocal Rank Fusion  |
|   * PowerPoint (.pptx)    |             | - Local Reranker          |
|   * Plain Text & Markdown |             | - Parent Context Expansion|
| - RapidOCR (Paddle ONNX)  |             | - Extractive Synthesizer  |
| - Hierarchical Chunker    |             | - Verifiable Citations    |
| - Local Embedding Engine  |             +---------------------------+
| - Dual Store (Qdrant+SQL) |
+---------------------------+
```

---

## 3. Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Backend Framework** | FastAPI + Uvicorn | Async, type-annotated, high-throughput REST API |
| **Vector Database** | Qdrant (`qdrant-client`) | Embedded local disk storage by default, or standalone server |
| **Relational Metadata Store** | SQLAlchemy (SQLite / PostgreSQL) | ACID metadata, versioning, audit logging |
| **Keyword Search** | BM25 (`rank-bm25`) | High precision for exact tags (`P-101`, `API 610`) |
| **PDF & Layout Extraction** | PyMuPDF (`fitz`) | High-performance text, tables, and page rendering |
| **Scanned Document OCR** | RapidOCR (`rapidocr-onnxruntime`) | Fully local ONNX PaddleOCR with bounding boxes |
| **Word Extraction** | `python-docx` | Headings, paragraphs, and tables |
| **Excel Extraction** | `openpyxl` | Equipment registers, logs, and cell coordinates |
| **PowerPoint Extraction** | `python-pptx` | Slides, text frames, notes, and tables |
| **Embeddings** | Sentence Transformers | Local dense vectors (`all-MiniLM-L6-v2`) |
| **Reranker** | Cross-Encoder | Local query-candidate pair reranking |
| **Security Guard** | Python Socket Interceptor | Fail-closed network isolation verification |

---

## 4. Quickstart Guide

### Prerequisites
* Python 3.10+ (Tested on Python 3.11 and 3.14 on Windows/Linux)
* pip package manager

### 1. Installation
Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Key configuration settings:
```ini
SOVEREIGN_MODE=true
QDRANT_STORAGE_PATH=./data/qdrant
DATABASE_URL=sqlite:///./data/metadata.db
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
RERANKER_MODEL_NAME=cross-encoder/ms-marco-MiniLM-L-6-v2
```

### 3. Run Automated Tests
Execute the unit and integration test suite:
```bash
pytest tests/ -v
```

### 4. Run Benchmark Evaluation
Run the 20-case industrial benchmark evaluation:
```bash
python -m evaluation.run_evaluation
```

### 5. Run Refinery Demo Scenario
Execute the end-to-end refinery inspection demo:
```bash
python -m demo.demo_refinery_scenario
```

### 6. Start the FastAPI Server
Start the local REST API server:
```bash
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```
Interactive OpenAPI documentation will be available at `http://localhost:8000/docs`.

---

## 5. API Reference

### Document Management

#### Upload & Ingest Document
```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@./data/synthetic_corpus/SOP-MEC-PUMP-001_Rev5.pdf" \
  -F "document_type=SOP" \
  -F "department=mechanical" \
  -F "access_level=confidential" \
  -F "revision=Rev 5" \
  -F "auto_ingest=true"
```

#### List Ingested Documents
```bash
curl -X GET "http://localhost:8000/documents?limit=20"
```

#### Delete Document
```bash
curl -X DELETE "http://localhost:8000/documents/{document_id}"
```

---

### RAG Search & Query

#### Hybrid Search (`POST /rag/search`)
```bash
curl -X POST "http://localhost:8000/rag/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "pump P-101 inspection findings and measured pit depth",
    "top_k": 5,
    "filters": {
      "department": "mechanical"
    }
  }'
```

#### High-Level Query with Citations (`POST /rag/query`)
```bash
curl -X POST "http://localhost:8000/rag/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the maximum allowable cavitation pitting depth for P-101?",
    "top_k": 5,
    "generate_answer": true
  }'
```

---

### System Health & Metrics

#### Health Check
```bash
curl -X GET "http://localhost:8000/health"
```

#### Knowledge Base Metrics
```bash
curl -X GET "http://localhost:8000/metrics"
```

---

## 6. AI Agent Integration

The RAG engine is decoupled from agent logic. Agents interact via the clean Python tool function:

```python
from src.rag.agent_tool import search_knowledge_base

# Agent calls the knowledge base
evidence = search_knowledge_base(
    query="emergency inspection measured pit depth pump P-101",
    filters={"document_type": "Inspection Report"},
    top_k=3,
    user_context={
        "user_id": "engineer_01",
        "role": "engineer",
        "clearance": "confidential",
        "departments": ["mechanical"]
    }
)

# Returns structured evidence and citations:
# evidence["sources"] -> [ { "document_name": "...", "page": 1, "section": "...", ... } ]
# evidence["evidence"] -> [ { "text": "...", "relevance_score": 0.94, ... } ]
```

---

## 7. Sovereign Mode & Network Verification

When `SOVEREIGN_MODE=true` is enabled:
1. Python's underlying socket library is monkey-patched with a fail-closed guard.
2. Any attempt to open a network socket to an external non-loopback IP raises `SovereignSecurityViolation`.
3. Outbound attempts are intercepted and recorded in `logs/security.log`.
4. Environment variables `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` ensure models never poll Hugging Face.

To verify offline isolation on Linux containers, run with:
```bash
docker run --network none sovereign_rag_service
```
The entire RAG pipeline will continue functioning with zero external connectivity.

---

## 8. Directory Structure

```
.
├── src/
│   ├── config.py                 # Pydantic Settings
│   ├── logging_config.py          # Rotating dual logs (rag.log, security.log)
│   ├── security/
│   │   ├── access_control.py      # RBAC & clearance filtering
│   │   └── sovereign_guard.py     # Socket fail-closed network interception
│   ├── storage/
│   │   ├── file_store.py          # Secure original document file store
│   │   ├── metadata_store.py      # SQLAlchemy relational metadata store
│   │   └── vector_store.py        # Qdrant client (embedded disk / server)
│   ├── ingestion/
│   │   ├── pipeline.py            # Master coordinator
│   │   ├── extractors/            # PDF, DOCX, XLSX, PPTX, Text, Image
│   │   ├── ocr/                   # RapidOCR local ONNX engine
│   │   ├── vision/                # Pluggable VisionModel interface
│   │   └── chunker/               # Hierarchical chunker & equipment tag regex
│   ├── retrieval/
│   │   ├── embeddings.py          # SentenceTransformers & offline fallback
│   │   ├── bm25.py                # BM25 keyword indexer
│   │   ├── hybrid.py              # Hybrid RRF fusion
│   │   ├── reranker.py            # Local Cross-Encoder reranker
│   │   └── expansion.py           # Parent / context expansion
│   ├── rag/
│   │   ├── service.py             # RAG service facade
│   │   ├── generator.py           # Local LLM / extractive synthesizer
│   │   ├── citations.py           # Provenance citation builder
│   │   └── agent_tool.py          # search_knowledge_base() tool
│   └── api/
│       ├── main.py                # FastAPI entrypoint
│       ├── schemas.py             # Pydantic API schemas
│       └── routes/                # documents, rag, system endpoints
├── tests/                         # Full automated test suite
├── evaluation/                    # 20-case industrial benchmark dataset & runner
├── demo/                          # Refinery P-101 demo scenario
├── docker/                        # Dockerfile and compose definitions
├── .env.example
├── requirements.txt
└── README.md
```
# RAG
