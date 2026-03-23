"""Benchmark suite: p50 / p95 / p99 latency measurement for Hancock endpoints.

Uses the Flask test client backed by a mock OpenAI client — no real network calls.

Run as pytest:
    pytest tests/benchmark_suite.py -v -s

Run standalone for a summary table:
    python tests/benchmark_suite.py
"""
from __future__ import annotations

import os
import sys
import statistics
import time
from typing import Callable, List
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Benchmark parameters ───────────────────────────────────────────────────────
WARMUP_CALLS = 5
BENCH_ITERATIONS = 50
P99_THRESHOLD_MS = 500


# ── Helpers ────────────────────────────────────────────────────────────────────

def _percentile(data: List[float], pct: float) -> float:
    """Return the *pct*-th percentile of *data* (0–100)."""
    sorted_data = sorted(data)
    idx = min(int(len(sorted_data) * pct / 100), len(sorted_data) - 1)
    return sorted_data[idx]


def _run_benchmark(fn: Callable, n: int = BENCH_ITERATIONS) -> dict:
    """Warm up then collect *n* latency samples; return stats dict (ms)."""
    for _ in range(WARMUP_CALLS):
        fn()
    times: List[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t0) * 1000)
    return {
        "min":  min(times),
        "p50":  statistics.median(times),
        "p95":  _percentile(times, 95),
        "p99":  _percentile(times, 99),
        "max":  max(times),
        "mean": statistics.mean(times),
    }


def _build_test_client():
    """Create a Flask test client backed by a mock OpenAI client."""
    mock_ai = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.content = "Benchmark mock response."
    mock_ai.chat.completions.create.return_value = resp
    import hancock_agent
    app = hancock_agent.build_app(mock_ai, "mistralai/mistral-7b-instruct-v0.3")
    app.testing = True
    return app.test_client()


# ── Module-scoped fixture ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def bench_client():
    """Module-scoped Flask test client — shared across all benchmark tests."""
    return _build_test_client()


# ── p99 regression tests ───────────────────────────────────────────────────────

class TestP99Latency:
    """p99 latency must stay under P99_THRESHOLD_MS to catch regressions."""

    def test_health_p99(self, bench_client):
        stats = _run_benchmark(lambda: bench_client.get("/health"))
        print(
            f"\n/health   p50={stats['p50']:.1f}ms "
            f"p95={stats['p95']:.1f}ms  p99={stats['p99']:.1f}ms"
        )
        assert stats["p99"] < P99_THRESHOLD_MS

    def test_metrics_p99(self, bench_client):
        stats = _run_benchmark(lambda: bench_client.get("/metrics"))
        print(
            f"\n/metrics  p50={stats['p50']:.1f}ms "
            f"p95={stats['p95']:.1f}ms  p99={stats['p99']:.1f}ms"
        )
        assert stats["p99"] < P99_THRESHOLD_MS

    def test_ask_p99(self, bench_client):
        stats = _run_benchmark(
            lambda: bench_client.post(
                "/v1/ask", json={"question": "What is Log4Shell?"}
            )
        )
        print(
            f"\n/v1/ask   p50={stats['p50']:.1f}ms "
            f"p95={stats['p95']:.1f}ms  p99={stats['p99']:.1f}ms"
        )
        assert stats["p99"] < P99_THRESHOLD_MS

    def test_chat_p99(self, bench_client):
        stats = _run_benchmark(
            lambda: bench_client.post(
                "/v1/chat", json={"message": "Explain XSS briefly."}
            )
        )
        print(
            f"\n/v1/chat  p50={stats['p50']:.1f}ms "
            f"p95={stats['p95']:.1f}ms  p99={stats['p99']:.1f}ms"
        )
        assert stats["p99"] < P99_THRESHOLD_MS

    def test_triage_p99(self, bench_client):
        stats = _run_benchmark(
            lambda: bench_client.post(
                "/v1/triage", json={"alert": "Mimikatz detected on DC01"}
            )
        )
        print(
            f"\n/v1/triage p50={stats['p50']:.1f}ms "
            f"p95={stats['p95']:.1f}ms  p99={stats['p99']:.1f}ms"
        )
        assert stats["p99"] < P99_THRESHOLD_MS

    def test_agents_p99(self, bench_client):
        stats = _run_benchmark(lambda: bench_client.get("/v1/agents"))
        print(
            f"\n/v1/agents p50={stats['p50']:.1f}ms "
            f"p95={stats['p95']:.1f}ms  p99={stats['p99']:.1f}ms"
        )
        assert stats["p99"] < P99_THRESHOLD_MS


# ── Standalone runner ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    c = _build_test_client()

    endpoints = [
        ("GET  /health",    lambda: c.get("/health")),
        ("GET  /metrics",   lambda: c.get("/metrics")),
        ("GET  /v1/agents", lambda: c.get("/v1/agents")),
        ("POST /v1/ask",    lambda: c.post("/v1/ask",    json={"question": "Log4Shell?"})),
        ("POST /v1/chat",   lambda: c.post("/v1/chat",   json={"message": "XSS?"})),
        ("POST /v1/triage", lambda: c.post("/v1/triage", json={"alert": "Mimikatz"})),
    ]

    print(f"\n{'Endpoint':<24} {'p50':>8} {'p95':>8} {'p99':>8} {'max':>8}")
    print("-" * 64)
    for name, fn in endpoints:
        s = _run_benchmark(fn)
        print(
            f"{name:<24} {s['p50']:>7.1f}ms {s['p95']:>7.1f}ms "
            f"{s['p99']:>7.1f}ms {s['max']:>7.1f}ms"
        )
