"""Local LLM Answer Generation and Offline Extractive Synthesizer."""

import httpx
from typing import List, Dict, Any, Optional
from src.config import settings
from src.logging_config import rag_logger
from src.rag.citations import Citation


class LocalAnswerGenerator:
    """Generates answers strictly from retrieved evidence using local LLM or offline synthesis."""

    def __init__(self, endpoint: Optional[str] = None, model: Optional[str] = None):
        self.endpoint = endpoint or settings.LLM_ENDPOINT
        self.model = model or settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT

    def generate_answer(
        self,
        query: str,
        evidence_chunks: List[Dict[str, Any]],
        citations: List[Citation]
    ) -> str:
        """Generates answer using local LLM if available, otherwise extractive synthesis."""
        if not evidence_chunks:
            return "No relevant authorized evidence found in the local knowledge base to answer this query."

        # Try local LLM if configured
        if self.endpoint:
            try:
                answer = self._call_local_llm(query, evidence_chunks, citations)
                if answer:
                    return answer
            except Exception as e:
                rag_logger.warning(f"Local LLM query failed or endpoint offline: {e}. Falling back to deterministic synthesis.")

        # Deterministic Extractive Synthesis
        return self._extractive_synthesize(query, evidence_chunks, citations)

    def _call_local_llm(
        self,
        query: str,
        evidence_chunks: List[Dict[str, Any]],
        citations: List[Citation]
    ) -> Optional[str]:
        """Calls a local OpenAI-compatible endpoint (Ollama, vLLM, llama.cpp)."""
        system_prompt = (
            "You are an on-premises Sovereign AI Assistant for an industrial workbench (refineries/engineering). "
            "Answer the user's question STRICTLY and SOLELY using the retrieved evidence provided below. "
            "Do not fabricate or extrapolate facts. Cite the exact document name, page number, and section for each claim."
        )

        context_parts = []
        for i, c in enumerate(evidence_chunks[:6], start=1):
            doc = c.get("document_name", "Unknown")
            page = c.get("page_number", 1)
            sec = c.get("section", "General")
            rev = c.get("revision", "Rev 0")
            text = c.get("expanded_context") or c.get("text", "")
            context_parts.append(
                f"[Evidence #{i} | Document: {doc} ({rev}), Page: {page}, Section: {sec}]\n{text.strip()}"
            )

        context_text = "\n\n".join(context_parts)
        user_prompt = f"Retrieved Knowledge Base Evidence:\n{context_text}\n\nQuestion: {query}\n\nProvide a detailed, factual answer citing sources:"

        url = f"{self.endpoint.rstrip('/')}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 1024
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                rag_logger.warning(f"Local LLM returned status {resp.status_code}: {resp.text}")
                return None

    def _extractive_synthesize(
        self,
        query: str,
        evidence_chunks: List[Dict[str, Any]],
        citations: List[Citation]
    ) -> str:
        """Produces a structured extractive summary with verified citations."""
        lines = [
            f"### Sovereign Knowledge Base Findings for: '{query}'",
            "",
            "Based on the verified on-premises documents retrieved from the knowledge base:",
            ""
        ]

        for idx, chunk in enumerate(evidence_chunks[:5], start=1):
            doc = chunk.get("document_name", "Document")
            page = chunk.get("page_number", 1)
            sec = chunk.get("section", "General")
            rev = chunk.get("revision", "Rev 0")
            dept = chunk.get("department", "general")
            text = chunk.get("text", "").strip()

            # Clean snippet (take first 300 chars or first paragraphs)
            snippet = text[:400] + ("..." if len(text) > 400 else "")

            lines.append(f"**{idx}. [{doc} — Page {page} | Section: {sec} ({rev})]**")
            lines.append(f"> {snippet}")
            lines.append("")

        lines.append("All statements above are verified directly from authorized local documentation.")
        return "\n".join(lines)


generator = LocalAnswerGenerator()
