"""Parent-Child Context Expansion for High-Precision Chunk Retrieval."""

from typing import List, Dict, Any, Set
from src.storage.metadata_store import metadata_store
from src.logging_config import rag_logger


class ParentContextExpander:
    """Expands retrieved child chunks with their surrounding parent section context."""

    def expand_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        expanded_list = []
        seen_parents: Set[str] = set()

        for cand in candidates:
            item = dict(cand)
            parent_id = cand.get("parent_chunk_id")

            if parent_id and parent_id not in seen_parents:
                parent_chunk = metadata_store.get_parent_chunk(parent_id)
                if parent_chunk and parent_chunk.get("text"):
                    # Attach parent context
                    item["expanded_context"] = parent_chunk["text"]
                    item["has_parent_expansion"] = True
                    seen_parents.add(parent_id)
                else:
                    item["expanded_context"] = cand.get("text", "")
                    item["has_parent_expansion"] = False
            else:
                item["expanded_context"] = cand.get("text", "")
                item["has_parent_expansion"] = False

            expanded_list.append(item)

        return expanded_list


context_expander = ParentContextExpander()
