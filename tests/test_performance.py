"""
Performance regression tests for Hancock.

Verifies that key endpoints respond within acceptable latency budgets.
These tests are designed to catch gross regressions (not micro-optimisation).

Timing budgets (generous to avoid CI flakiness):
  /health      < 1.0 s
  /v1/chat     < 5.0 s  (mock client — no real model call)
  /v1/triage   < 5.0 s  (mock client)
"""
from __future__ import annotations

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Timing helper ─────────────────────────────────────────────────────────────

_HEALTH_BUDGET_S = 1.0
_CHAT_BUDGET_S = 5.0
_TRIAGE_BUDGET_S = 5.0


class TestHealthPerformance:
    def test_health_latency(self, client):
        start = time.perf_counter()
        r = client.get("/health")
        elapsed = time.perf_counter() - start

        assert r.status_code == 200
        assert elapsed < _HEALTH_BUDGET_S, (
            f"/health took {elapsed:.3f}s — budget is {_HEALTH_BUDGET_S}s"
        )

    def test_health_throughput_10_requests(self, client):
        """Ten sequential /health calls should complete within 3 s total."""
        start = time.perf_counter()
        for _ in range(10):
            r = client.get("/health")
            assert r.status_code == 200
        elapsed = time.perf_counter() - start
        assert elapsed < 3.0, (
            f"10x /health took {elapsed:.3f}s — expected < 3.0s"
        )


class TestChatPerformance:
    def test_chat_latency(self, client):
        payload = json.dumps({
            "message": "What is SQL injection?",
            "mode": "pentest",
        })
        start = time.perf_counter()
        r = client.post(
            "/v1/chat",
            data=payload,
            content_type="application/json",
        )
        elapsed = time.perf_counter() - start

        assert r.status_code == 200
        assert elapsed < _CHAT_BUDGET_S, (
            f"/v1/chat took {elapsed:.3f}s — budget is {_CHAT_BUDGET_S}s"
        )


class TestTriagePerformance:
    def test_triage_latency(self, client):
        payload = json.dumps({
            "alert": "Suspicious outbound connection to 185.220.101.1:443",
            "source": "EDR",
        })
        start = time.perf_counter()
        r = client.post(
            "/v1/triage",
            data=payload,
            content_type="application/json",
        )
        elapsed = time.perf_counter() - start

        assert r.status_code == 200
        assert elapsed < _TRIAGE_BUDGET_S, (
            f"/v1/triage took {elapsed:.3f}s — budget is {_TRIAGE_BUDGET_S}s"
        )
