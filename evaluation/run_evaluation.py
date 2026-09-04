"""Automated Evaluation Runner for Sovereign RAG Benchmark."""

import time
import json
from pathlib import Path
from typing import Dict, Any, List
from evaluation.synthetic_generator import generate_synthetic_documents
from evaluation.dataset import EVALUATION_DATASET, EvaluationCase
from src.ingestion.pipeline import ingestion_pipeline
from src.rag.service import rag_service
from src.security.access_control import UserContext, ClearanceLevel
from src.logging_config import rag_logger


def run_benchmark(corpus_dir: Path = Path("./data/synthetic_corpus")) -> Dict[str, Any]:
    print("=" * 75)
    print("  SOVEREIGN MULTIMODAL LOCAL RAG SYSTEM — BENCHMARK EVALUATION")
    print("=" * 75)

    # 1. Generate synthetic documents
    print("\n[Step 1/3] Generating synthetic industrial corpus...")
    files = generate_synthetic_documents(corpus_dir)
    print(f"Generated {len(files)} industrial files: {[f.name for f in files.values()]}")

    # 2. Ingest documents into Sovereign Knowledge Base
    print("\n[Step 2/3] Ingesting documents into Sovereign Knowledge Base...")
    ingestion_results = {}
    for key, file_path in files.items():
        t0 = time.time()
        # Set metadata based on file
        meta = {"department": "mechanical", "access_level": "confidential"}
        if "Rev3" in file_path.name:
            meta["status"] = "superseded"
            meta["revision"] = "Rev 3"
        elif "Rev5" in file_path.name:
            meta["status"] = "active"
            meta["revision"] = "Rev 5"
        elif "API610" in file_path.name:
            meta["access_level"] = "restricted"
            meta["department"] = "engineering"
        elif "scanned" in file_path.name:
            meta["document_type"] = "Inspection Report"
            meta["access_level"] = "confidential"

        res = ingestion_pipeline.ingest_file(file_path=file_path, metadata=meta)
        elapsed = time.time() - t0
        ingestion_results[file_path.name] = res
        print(f"  ✓ Ingested {file_path.name:<32} in {elapsed:.2f}s | {res['total_chunks']} chunks (Scanned={res['is_scanned']})")

    # 3. Run Benchmark Queries
    print(f"\n[Step 3/3] Running {len(EVALUATION_DATASET)} Evaluation Test Cases...")
    results_summary: List[Dict[str, Any]] = []
    latencies: List[float] = []

    correct_doc_retrieval = 0
    correct_citation = 0
    entity_matches = 0

    user = UserContext(
        user_id="eval_lead",
        role="admin",
        clearance=ClearanceLevel.RESTRICTED,
        departments=["mechanical", "engineering", "operations", "safety", "general"]
    )

    for case in EVALUATION_DATASET:
        t_start = time.perf_counter()
        rag_res = rag_service.query(
            query=case.query,
            top_k=5,
            user=user,
            generate_answer=True
        )
        latency_ms = (time.perf_counter() - t_start) * 1000.0
        latencies.append(latency_ms)

        retrieved_docs = [e.get("document_name", "") for e in rag_res.get("evidence", [])]
        citations = rag_res.get("sources", [])
        citation_docs = [c.get("document_name", "") for c in citations]
        combined_text = " ".join([e.get("text", "") for e in rag_res.get("evidence", [])]) + " " + rag_res.get("answer", "")

        # Check retrieval precision@k
        doc_hit = any(case.expected_document.lower() in d.lower() for d in retrieved_docs)
        if doc_hit:
            correct_doc_retrieval += 1

        # Check citation accuracy
        cit_hit = any(case.expected_document.lower() in d.lower() for d in citation_docs)
        if cit_hit:
            correct_citation += 1

        # Check entity recall
        found_entities = [ent for ent in case.expected_entities if ent.lower() in combined_text.lower()]
        entity_recall = len(found_entities) / max(1, len(case.expected_entities))
        if entity_recall >= 0.5:
            entity_matches += 1

        status_mark = "✓ PASS" if (doc_hit and entity_recall >= 0.5) else "✗ FAIL"
        print(f"  [{case.query_id}] {status_mark} | Latency: {latency_ms:5.1f}ms | Expected: {case.expected_document:<28} | Hits: {len(retrieved_docs)}")

        results_summary.append({
            "query_id": case.query_id,
            "category": case.category,
            "query": case.query,
            "expected_document": case.expected_document,
            "retrieved_documents": retrieved_docs[:3],
            "document_hit": doc_hit,
            "citation_hit": cit_hit,
            "entity_recall": round(entity_recall, 2),
            "latency_ms": round(latency_ms, 2)
        })

    # Summary Statistics
    total_q = len(EVALUATION_DATASET)
    precision_k = (correct_doc_retrieval / total_q) * 100.0
    citation_accuracy = (correct_citation / total_q) * 100.0
    entity_accuracy = (entity_matches / total_q) * 100.0
    p50_latency = sorted(latencies)[int(len(latencies) * 0.5)]
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]

    print("\n" + "=" * 75)
    print("  EVALUATION RESULTS SUMMARY")
    print("=" * 75)
    print(f"  Total Test Cases:       {total_q}")
    print(f"  Document Hit Rate @5:   {precision_k:.1f}% ({correct_doc_retrieval}/{total_q})")
    print(f"  Citation Provenance:    {citation_accuracy:.1f}% ({correct_citation}/{total_q})")
    print(f"  Factual Entity Recall:  {entity_accuracy:.1f}% ({entity_matches}/{total_q})")
    print(f"  Median Latency (p50):   {p50_latency:.1f} ms")
    print(f"  95th-Percentile (p95):  {p95_latency:.1f} ms")
    print("=" * 75)

    report = {
        "total_test_cases": total_q,
        "precision_at_5": precision_k,
        "citation_accuracy": citation_accuracy,
        "entity_accuracy": entity_accuracy,
        "latency_p50_ms": round(p50_latency, 1),
        "latency_p95_ms": round(p95_latency, 1),
        "cases": results_summary
    }

    report_path = Path("./logs/evaluation_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Detailed benchmark report saved to {report_path}\n")

    return report


if __name__ == "__main__":
    run_benchmark()
