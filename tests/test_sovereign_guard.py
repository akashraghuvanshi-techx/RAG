"""Tests for Sovereign Mode and Fail-Closed Network Interception."""

import socket
import pytest
from src.security.sovereign_guard import (
    install_sovereign_guard, uninstall_sovereign_guard,
    SovereignSecurityViolation, is_local_address, verify_offline_status
)


def test_is_local_address():
    assert is_local_address("127.0.0.1") is True
    assert is_local_address("localhost") is True
    assert is_local_address("::1") is True
    assert is_local_address("192.168.1.100") is True
    assert is_local_address("10.0.0.5") is True
    assert is_local_address("8.8.8.8") is False
    assert is_local_address("api.openai.com") is False


def test_fail_closed_socket_interception():
    install_sovereign_guard()
    status = verify_offline_status()
    assert status["guard_active"] is True

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)

    with pytest.raises(SovereignSecurityViolation) as excinfo:
        s.connect(("142.250.190.46", 80))  # External Google IP

    assert "Blocked external outbound connection" in str(excinfo.value)
    s.close()
