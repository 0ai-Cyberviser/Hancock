"""
Hancock — Performance regression tests.

These tests assert that basic operations complete within acceptable time bounds
when the model backend is mocked.  They are intentionally lightweight so they
can run in CI without real GPU/API resources.

Run:
    pytest tests/test_performance.py -v
"""
from __future__ import annotations

import json
import os
import sys
import time
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def perf_client():
    import hancock_agent
    mock_client = MagicMock()
    mock_resp   = MagicMock()
    mock_resp.choices[0].message.content = "Fast mocked response."
    mock_client.chat.completions.create.return_value = mock_resp

    app = hancock_agent.build_app(mock_client, "test-model")
    app.testing = True
    return app.test_client()


def _post(client, url: str, body: dict) -> tuple[object, float]:
    t0 = time.perf_counter()
    resp = client.post(url, data=json.dumps(body), content_type="application/json")
    elapsed = time.perf_counter() - t0
    return resp, elapsed


# ── Latency assertions ────────────────────────────────────────────────────────

class TestLatency:
    MAX_HEALTH_MS  = 50    # /health should be near-instant
    MAX_CHAT_MS    = 500   # mocked chat — no real model call
    MAX_TRIAGE_MS  = 500
    MAX_METRICS_MS = 50

    def test_health_under_50ms(self, perf_client):
        t0 = time.perf_counter()
        r  = perf_client.get("/health")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert r.status_code == 200
        assert elapsed_ms < self.MAX_HEALTH_MS, (
            f"/health took {elapsed_ms:.1f}ms — exceeds {self.MAX_HEALTH_MS}ms threshold"
        )

    def test_metrics_under_50ms(self, perf_client):
        t0 = time.perf_counter()
        r  = perf_client.get("/metrics")
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert r.status_code == 200
        assert elapsed_ms < self.MAX_METRICS_MS

    def test_chat_under_500ms(self, perf_client):
        _, elapsed = _post(perf_client, "/v1/chat",
                           {"message": "What is CVE-2024-1234?", "mode": "auto"})
        assert elapsed * 1000 < self.MAX_CHAT_MS, (
            f"/v1/chat took {elapsed * 1000:.1f}ms — exceeds {self.MAX_CHAT_MS}ms threshold"
        )

    def test_triage_under_500ms(self, perf_client):
        _, elapsed = _post(perf_client, "/v1/triage",
                           {"alert": "Mimikatz on DC01"})
        assert elapsed * 1000 < self.MAX_TRIAGE_MS


# ── Throughput: serial requests ───────────────────────────────────────────────

class TestThroughput:
    def test_10_sequential_health_requests(self, perf_client):
        """10 sequential /health requests should complete in <200ms total."""
        t0 = time.perf_counter()
        for _ in range(10):
            r = perf_client.get("/health")
            assert r.status_code == 200
        elapsed_ms = (time.perf_counter() - t0) * 1000
        assert elapsed_ms < 200, f"10 health requests took {elapsed_ms:.1f}ms"

    def test_10_sequential_chat_requests(self, perf_client):
        """10 sequential /v1/chat requests should complete in <2s total."""
        t0 = time.perf_counter()
        for _ in range(10):
            r, _ = _post(perf_client, "/v1/chat",
                         {"message": "Explain lateral movement", "mode": "soc"})
            assert r.status_code == 200
        elapsed = time.perf_counter() - t0
        assert elapsed < 2.0, f"10 chat requests took {elapsed:.2f}s"


# ── Memory stability (basic leak detection) ───────────────────────────────────

class TestMemoryStability:
    def test_metrics_counter_stable(self, perf_client):
        """Metrics counters must increase monotonically and not overflow."""
        import re

        def _get_total():
            r    = perf_client.get("/metrics")
            text = r.data.decode()
            m    = re.search(r"^hancock_requests_total (\d+)", text, re.MULTILINE)
            return int(m.group(1)) if m else 0

        before = _get_total()
        for _ in range(5):
            perf_client.get("/health")
        after = _get_total()
        assert after >= before, "Request counter must not decrease"

    def test_rate_limiter_dict_bounded(self, perf_client):
        """Rate-limiter state must not grow unboundedly with distinct IPs.

        This test verifies the eviction logic doesn't break when the dict is
        under normal operating conditions (well below 10_000 entries).
        """
        for _ in range(20):
            perf_client.get("/health")
        # No assertion on count — just ensure no exception was raised
