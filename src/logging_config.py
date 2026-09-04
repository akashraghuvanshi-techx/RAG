"""Structured dual logging for Sovereign RAG and Security Auditing."""

import logging
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from logging.handlers import RotatingFileHandler
from src.config import settings


class JsonFormatter(logging.Formatter):
    """Formats log records as structured JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry.update(record.extra_data)
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def setup_logging():
    """Initializes RAG application loggers and security audit loggers."""
    log_dir = settings.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    rag_log_file = log_dir / "rag.log"
    sec_log_file = log_dir / "security.log"

    # Main RAG Logger
    rag_logger = logging.getLogger("sovereign_rag")
    rag_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    rag_logger.propagate = False

    # Security Audit Logger
    sec_logger = logging.getLogger("sovereign_security")
    sec_logger.setLevel(logging.INFO)
    sec_logger.propagate = False

    # Clear existing handlers if re-run
    if rag_logger.handlers:
        rag_logger.handlers.clear()
    if sec_logger.handlers:
        sec_logger.handlers.clear()

    json_formatter = JsonFormatter()
    plain_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler for RAG
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(plain_formatter)
    rag_logger.addHandler(console_handler)

    # Rotating File Handler for RAG
    rag_file_handler = RotatingFileHandler(
        rag_log_file, maxBytes=25 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    rag_file_handler.setFormatter(json_formatter)
    rag_logger.addHandler(rag_file_handler)

    # Security Log File Handler
    sec_file_handler = RotatingFileHandler(
        sec_log_file, maxBytes=25 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    sec_file_handler.setFormatter(json_formatter)
    sec_logger.addHandler(sec_file_handler)

    # Console for Security Alerts
    sec_console_handler = logging.StreamHandler(sys.stderr)
    sec_console_handler.setFormatter(plain_formatter)
    sec_logger.addHandler(sec_console_handler)

    return rag_logger, sec_logger


rag_logger, security_logger = setup_logging()


def log_security_event(event_type: str, details: dict, level: str = "INFO"):
    """Logs security and sovereignty audit events."""
    extra = {"event_type": event_type, "details": details}
    msg = f"SECURITY_EVENT: {event_type} - {json.dumps(details)}"
    lvl = getattr(logging, level.upper(), logging.INFO)
    security_logger.log(lvl, msg, extra={"extra_data": extra})
