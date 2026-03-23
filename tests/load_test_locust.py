"""Locust load testing profiles for Hancock REST API.

Usage (requires ``locust`` to be installed):
    locust -f tests/load_test_locust.py --host=http://localhost:5000
    locust -f tests/load_test_locust.py --host=http://localhost:5000 \\
           --headless -u 50 -r 5 --run-time 60s

The module is also importable by pytest; a smoke test verifies the
import succeeds (or is skipped gracefully when locust is not installed).
"""
from __future__ import annotations

import pytest

try:
    from locust import HttpUser, between, constant_pacing, task
    _LOCUST_AVAILABLE = True
except ImportError:
    _LOCUST_AVAILABLE = False


# ── Smoke test ─────────────────────────────────────────────────────────────────

@pytest.mark.skipif(not _LOCUST_AVAILABLE, reason="locust not installed")
def test_locust_classes_importable():
    """Verify Locust user classes can be imported without error."""
    assert _LOCUST_AVAILABLE


# ── Load profiles (only defined when locust is available) ────────────────────

if _LOCUST_AVAILABLE:

    class HealthOnlyUser(HttpUser):
        """Minimal smoke profile — hits /health exclusively."""
        wait_time = between(0.5, 1.5)

        @task
        def health(self):
            self.client.get("/health")

    class ReadOnlyUser(HttpUser):
        """Read-only workload — health and metrics only (no AI calls)."""
        wait_time = between(0.2, 1.0)

        @task(3)
        def health(self):
            self.client.get("/health")

        @task(1)
        def metrics(self):
            self.client.get("/metrics")

    class TypicalAnalystUser(HttpUser):
        """Typical analyst workload — mixed read + AI endpoint calls."""
        wait_time = between(1, 3)

        @task(2)
        def health(self):
            self.client.get("/health")

        @task(5)
        def ask_question(self):
            self.client.post(
                "/v1/ask",
                json={"question": "What is CVE-2021-44228?", "mode": "auto"},
                headers={"Content-Type": "application/json"},
            )

        @task(5)
        def chat(self):
            self.client.post(
                "/v1/chat",
                json={"message": "Explain SQL injection briefly.", "mode": "auto"},
                headers={"Content-Type": "application/json"},
            )

        @task(3)
        def triage(self):
            self.client.post(
                "/v1/triage",
                json={"alert": "Mimikatz.exe detected on DC01 — process: lsass.exe"},
                headers={"Content-Type": "application/json"},
            )

        @task(1)
        def metrics(self):
            self.client.get("/metrics")

    class SpikeUser(HttpUser):
        """Spike profile — constant pacing to validate rate limiting."""
        wait_time = constant_pacing(0.1)   # 10 RPS per user

        @task
        def ask(self):
            self.client.post(
                "/v1/ask",
                json={"question": "ping", "mode": "auto"},
                headers={"Content-Type": "application/json"},
            )

    class SOCAnalystUser(HttpUser):
        """SOC-heavy workload — triage, hunt, and IOC lookup dominant."""
        wait_time = between(2, 5)

        @task(6)
        def triage_alert(self):
            self.client.post(
                "/v1/triage",
                json={"alert": "Suspicious PowerShell execution on WKSTN42"},
                headers={"Content-Type": "application/json"},
            )

        @task(4)
        def hunt(self):
            self.client.post(
                "/v1/hunt",
                json={"target": "lateral movement via PsExec", "siem": "splunk"},
                headers={"Content-Type": "application/json"},
            )

        @task(2)
        def ioc_lookup(self):
            self.client.post(
                "/v1/ioc",
                json={"indicator": "185.220.101.35", "type": "ip"},
                headers={"Content-Type": "application/json"},
            )

        @task(1)
        def health_check(self):
            self.client.get("/health")

    class PentesterUser(HttpUser):
        """Pentest-heavy workload — code generation and ask dominant."""
        wait_time = between(2, 6)

        @task(5)
        def ask_pentest(self):
            self.client.post(
                "/v1/ask",
                json={"question": "How does Kerberoasting work?", "mode": "pentest"},
                headers={"Content-Type": "application/json"},
            )

        @task(3)
        def code_generation(self):
            self.client.post(
                "/v1/code",
                json={"task": "Write a Python port scanner using asyncio"},
                headers={"Content-Type": "application/json"},
            )

        @task(2)
        def yara_rule(self):
            self.client.post(
                "/v1/yara",
                json={"description": "Detect Cobalt Strike beacon in memory"},
                headers={"Content-Type": "application/json"},
            )

        @task(1)
        def health_check(self):
            self.client.get("/health")
