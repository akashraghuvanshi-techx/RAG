"""Standalone Agent Tool interface for external AI agents."""

from typing import Optional, Dict, Any, List
from src.rag.service import rag_service
from src.security.access_control import UserContext, ClearanceLevel


def search_knowledge_base(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 10,
    user_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Sovereign Knowledge Base Retrieval Tool for AI Agents.

    Args:
        query: Search prompt, keywords, or equipment tags (e.g. 'pump P-101 inspection findings').
        filters: Optional dictionary of metadata filters:
                 - 'department': e.g. 'mechanical', 'electrical', 'safety'
                 - 'document_type': e.g. 'SOP', 'Inspection Report', 'Engineering Standard'
                 - 'status': 'active' (default) or 'superseded'
                 - 'revision': e.g. 'Rev 5'
        top_k: Number of relevant evidence chunks to return (default 10).
        user_context: Optional security credentials of the invoking agent/user:
                 - 'user_id': str
                 - 'role': 'engineer', 'inspector', 'admin'
                 - 'clearance': 'public', 'internal', 'confidential', 'restricted', 'secret'
                 - 'departments': list of allowed department strings

    Returns:
        Structured dictionary containing:
        - 'query': original query string
        - 'total_results': number of evidence chunks found
        - 'evidence': list of retrieved evidence chunks with text, scores, and metadata
        - 'sources': structured citation list (document name, page, section, revision, relevance score)
    """
    user = None
    if user_context:
        clearance_str = user_context.get("clearance", "confidential").lower()
        clearance_enum = ClearanceLevel.CONFIDENTIAL
        for c in ClearanceLevel:
            if c.value == clearance_str:
                clearance_enum = c
                break

        user = UserContext(
            user_id=user_context.get("user_id", "agent"),
            role=user_context.get("role", "engineer"),
            clearance=clearance_enum,
            departments=user_context.get("departments", ["mechanical", "safety", "general"]),
            allowed_projects=user_context.get("allowed_projects")
        )

    results = rag_service.query(
        query=query,
        filters=filters,
        top_k=top_k,
        user=user,
        generate_answer=False  # Agent handles generation; tool provides structured evidence
    )

    return {
        "query": query,
        "total_results": len(results["evidence"]),
        "sources": results["sources"],
        "evidence": [
            {
                "chunk_id": e.get("chunk_id"),
                "document_id": e.get("document_id"),
                "document_name": e.get("document_name"),
                "page": e.get("page_number"),
                "section": e.get("section"),
                "revision": e.get("revision"),
                "department": e.get("department"),
                "equipment_tags": e.get("equipment_tags", []),
                "relevance_score": round(float(e.get("score", 0.0)), 4),
                "text": e.get("expanded_context") or e.get("text", ""),
                "is_table": e.get("is_table", False),
            }
            for e in results["evidence"]
        ]
    }
