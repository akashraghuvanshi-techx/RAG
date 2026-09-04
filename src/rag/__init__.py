"""RAG package."""
from src.rag.service import rag_service, RAGService
from src.rag.citations import CitationBuilder, Citation
from src.rag.generator import generator, LocalAnswerGenerator
from src.rag.agent_tool import search_knowledge_base

__all__ = [
    "rag_service",
    "RAGService",
    "CitationBuilder",
    "Citation",
    "generator",
    "LocalAnswerGenerator",
    "search_knowledge_base",
]
