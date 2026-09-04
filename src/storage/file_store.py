"""Local filesystem preservation of original documents."""

import hashlib
import shutil
from pathlib import Path
from typing import Tuple, Optional
from src.config import settings
from src.logging_config import rag_logger


class LocalFileStore:
    """Manages secure on-disk preservation of original documents."""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or settings.DOCUMENTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, document_id: str, filename: str, content: bytes) -> Tuple[Path, str, int]:
        """
        Saves original document bytes to disk under document_id.
        Returns: (file_path, sha256_hash, size_in_bytes)
        """
        doc_folder = self.base_dir / document_id
        doc_folder.mkdir(parents=True, exist_ok=True)

        # Sanitize filename
        clean_filename = Path(filename).name
        target_path = doc_folder / clean_filename

        sha256 = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)

        with open(target_path, "wb") as f:
            f.write(content)

        rag_logger.info(
            f"Stored original document: {clean_filename} (ID: {document_id}, "
            f"Size: {size_bytes} bytes, SHA256: {sha256[:12]}...)"
        )
        return target_path, sha256, size_bytes

    def get_file_path(self, document_id: str, filename: Optional[str] = None) -> Optional[Path]:
        """Locates the original file path for a given document_id."""
        doc_folder = self.base_dir / document_id
        if not doc_folder.exists():
            return None

        if filename:
            file_path = doc_folder / Path(filename).name
            if file_path.exists():
                return file_path

        # Find first file in folder
        files = list(doc_folder.glob("*"))
        for f in files:
            if f.is_file():
                return f
        return None

    def delete_document_files(self, document_id: str) -> bool:
        """Deletes all preserved files for a document_id."""
        doc_folder = self.base_dir / document_id
        if doc_folder.exists():
            shutil.rmtree(doc_folder, ignore_errors=True)
            rag_logger.info(f"Deleted file store directory for document: {document_id}")
            return True
        return False


file_store = LocalFileStore()
