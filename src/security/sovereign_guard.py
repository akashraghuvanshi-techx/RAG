"""Sovereign Guard: Enforces strict zero-outbound network policy in SOVEREIGN_MODE."""

import os
import socket
import ipaddress
from typing import Set, Tuple, Optional
from src.config import settings
from src.logging_config import log_security_event, security_logger

_original_connect = socket.socket.connect
_guard_installed = False

# Permitted local loopback hosts and IP networks
ALLOWED_HOSTS: Set[str] = {"127.0.0.1", "localhost", "::1", "0.0.0.0"}


class SovereignSecurityViolation(ConnectionRefusedError):
    """Raised when an outbound network call is attempted in SOVEREIGN_MODE."""
    pass


def is_local_address(host: str) -> bool:
    """Checks if a target host is local loopback or local private subnet."""
    if host.lower() in ALLOWED_HOSTS:
        return True

    # Check for IP address
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            return True
    except ValueError:
        pass

    return False


def _guarded_connect(self, address):
    """Monitored socket connect function."""
    if not settings.SOVEREIGN_MODE:
        return _original_connect(self, address)

    host = address[0] if isinstance(address, (tuple, list)) else str(address)
    port = address[1] if isinstance(address, (tuple, list)) and len(address) > 1 else None

    # Check address
    if is_local_address(str(host)):
        return _original_connect(self, address)

    # Outbound access blocked!
    event_data = {
        "target_host": str(host),
        "target_port": port,
        "action": "BLOCKED",
        "reason": "SOVEREIGN_MODE active. External network connections are prohibited.",
    }
    log_security_event("OUTBOUND_NETWORK_ATTEMPT_BLOCKED", event_data, level="CRITICAL")

    raise SovereignSecurityViolation(
        f"[SOVEREIGN_GUARD] Blocked external outbound connection attempt to {host}:{port}. "
        f"External calls are forbidden in sovereign mode."
    )


def install_sovereign_guard() -> None:
    """Installs the fail-closed network interception guard."""
    global _guard_installed
    if _guard_installed:
        return

    # Set offline environment variables for Hugging Face and other libraries
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    socket.socket.connect = _guarded_connect
    _guard_installed = True

    log_security_event(
        "SOVEREIGN_GUARD_INITIALIZED",
        {"status": "ACTIVE", "mode": "FAIL_CLOSED", "allowed_hosts": list(ALLOWED_HOSTS)},
        level="INFO"
    )


def uninstall_sovereign_guard() -> None:
    """Restores standard socket connect (for testing only)."""
    global _guard_installed
    socket.socket.connect = _original_connect
    _guard_installed = False


def verify_offline_status() -> dict:
    """Returns the current sovereign offline status and environmental checks."""
    return {
        "sovereign_mode_enabled": settings.SOVEREIGN_MODE,
        "guard_active": _guard_installed,
        "hf_hub_offline": os.environ.get("HF_HUB_OFFLINE") == "1",
        "transformers_offline": os.environ.get("TRANSFORMERS_OFFLINE") == "1",
        "allowed_hosts": list(ALLOWED_HOSTS),
    }
