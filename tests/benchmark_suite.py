"""
Benchmark harness for Hancock.

Measures p50/p95/p99 latency for key API endpoints using
``time.perf_counter``.  Designed to be run standalone or via pytest.

Run directly::

    python tests/benchmark_suite.py

Run via pytest (mark with --benchmark or similar)::

    pytest tests/benchmark_suite.py -v
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from typing import Callable

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Percentile helpers ────────────────────────────────────────────────────────

def _percentile(data: list[float], pct: float) -> float:
    """Return the *pct*-th percentile of *data* (0–100)."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    index = (pct / 100) * (len(sorted_data) - 1)
    lower = int(index)
    upper = lower + 1
    if upper >= len(sorted_data):
        return sorted_data[-1]
    frac = index - lower
    return sorted_data[lower] + frac * (sorted_data[upper] - sorted_data[lower])


def _run_benchmark(
    fn: Callable[[], None],
    iterations: int = 20,
    label: str = "benchmark",
) -> dict[str, float]:
    """
    Run *fn* ``iterations`` times and return latency statistics.

    Returns a dict with keys: min, max, mean, p50, p95, p99 (all in seconds).
    """
    samples: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples.append(time.perf_counter() - start)

    result = {
        "min": min(samples),
        "max": max(samples),
        "mean": statistics.mean(samples),
        "p50": _percentile(samples, 50),
        "p95": _percentile(samples, 95),
        "p99": _percentile(samples, 99),
        "iterations": iterations,
    }

    print(
        f"\n[benchmark] {label} ({iterations} iterations)\n"
        f"  min={result['min']*1000:.1f}ms  "
        f"p50={result['p50']*1000:.1f}ms  "
        f"p95={result['p95']*1000:.1f}ms  "
        f"p99={result['p99']*1000:.1f}ms  "
        f"max={result['max']*1000:.1f}ms"
    )
    return result


# ── Benchmark test cases ──────────────────────────────────────────────────────

class TestHealthBenchmark:
    ITERATIONS = 30

    def test_health_p99_under_500ms(self, client):
        stats = _run_benchmark(
            lambda: client.get("/health"),
            iterations=self.ITERATIONS,
            label="GET /health",
        )
        assert stats["p99"] < 0.5, (
            f"/health p99={stats['p99']*1000:.1f}ms — must be < 500ms"
        )


class TestChatBenchmark:
    ITERATIONS = 10
    _PAYLOAD = json.dumps({
        "message": "Explain XSS briefly.",
        "mode": "pentest",
    })

    def test_chat_p95_under_5s(self, client):
        stats = _run_benchmark(
            lambda: client.post(
                "/v1/chat",
                data=self._PAYLOAD,
                content_type="application/json",
            ),
            iterations=self.ITERATIONS,
            label="POST /v1/chat",
        )
        assert stats["p95"] < 5.0, (
            f"/v1/chat p95={stats['p95']*1000:.1f}ms — must be < 5000ms"
        )


class TestTriageBenchmark:
    ITERATIONS = 10
    _PAYLOAD = json.dumps({
        "alert": "Login brute-force from 10.0.0.99",
        "source": "SIEM",
    })

    def test_triage_p95_under_5s(self, client):
        stats = _run_benchmark(
            lambda: client.post(
                "/v1/triage",
                data=self._PAYLOAD,
                content_type="application/json",
            ),
            iterations=self.ITERATIONS,
            label="POST /v1/triage",
        )
        assert stats["p95"] < 5.0, (
            f"/v1/triage p95={stats['p95']*1000:.1f}ms — must be < 5000ms"
        )


# ── Standalone runner ─────────────────────────────────────────────────────────

def _run_standalone() -> None:
    """Run benchmarks standalone without pytest."""
    from unittest.mock import MagicMock

    mock_client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.content = "Mocked response"
    mock_client.chat.completions.create.return_value = resp

    import hancock_agent
    app = hancock_agent.build_app(mock_client, "mistralai/mistral-7b-instruct-v0.3")
    app.testing = True
    tc = app.test_client()

    _run_benchmark(lambda: tc.get("/health"), 50, "GET /health")
    _run_benchmark(
        lambda: tc.post(
            "/v1/chat",
            data=json.dumps({
                "message": "Brief XSS explanation",
                "mode": "pentest",
            }),
            content_type="application/json",
        ),
        20,
        "POST /v1/chat",
    )


if __name__ == "__main__":
    _run_standalone()
