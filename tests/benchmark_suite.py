"""
Hancock — Benchmark suite.

Measures response-time statistics for all API endpoints using the mock
backend.  Outputs a JSON report to benchmarks/results/.

Run:
    pytest tests/benchmark_suite.py -v -s
    # or standalone:
    python tests/benchmark_suite.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS_DIR = Path(__file__).parent.parent / "benchmarks" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Client factory ────────────────────────────────────────────────────────────

def _make_test_client():
    import hancock_agent
    mock_client = MagicMock()
    mock_resp   = MagicMock()
    mock_resp.choices[0].message.content = "Benchmark response payload."
    mock_client.chat.completions.create.return_value = mock_resp
    app = hancock_agent.build_app(mock_client, "bench-model")
    app.testing = True
    return app.test_client()


# ── Benchmark runner ──────────────────────────────────────────────────────────

def _run_bench(client, method: str, url: str, body: dict | None,
               n: int = 50) -> dict[str, Any]:
    samples: list[float] = []
    errors  = 0

    for _ in range(n):
        t0 = time.perf_counter()
        if method == "GET":
            resp = client.get(url)
        else:
            resp = client.post(url, data=json.dumps(body or {}),
                               content_type="application/json")
        elapsed = (time.perf_counter() - t0) * 1000  # ms
        samples.append(elapsed)
        if resp.status_code >= 400:
            errors += 1

    samples.sort()
    p95_idx = min(int(n * 0.95), len(samples) - 1)
    p99_idx = min(int(n * 0.99), len(samples) - 1)
    return {
        "url":         url,
        "method":      method,
        "n":           n,
        "errors":      errors,
        "error_rate":  round(errors / n, 4),
        "p50_ms":      round(statistics.median(samples), 2),
        "p95_ms":      round(samples[p95_idx], 2),
        "p99_ms":      round(samples[p99_idx], 2),
        "min_ms":      round(min(samples), 2),
        "max_ms":      round(max(samples), 2),
        "mean_ms":     round(statistics.mean(samples), 2),
        "stdev_ms":    round(statistics.stdev(samples), 2) if len(samples) > 1 else 0.0,
    }


# ── Benchmark cases ───────────────────────────────────────────────────────────

BENCHMARKS = [
    ("GET",  "/health",      None),
    ("GET",  "/metrics",     None),
    ("POST", "/v1/chat",     {"message": "Explain lateral movement", "mode": "auto"}),
    ("POST", "/v1/ask",      {"question": "What is Log4Shell?"}),
    ("POST", "/v1/triage",   {"alert": "Mimikatz detected on DC01"}),
    ("POST", "/v1/hunt",     {"target": "kerberoasting", "siem": "splunk"}),
    ("POST", "/v1/respond",  {"incident": "ransomware"}),
    ("POST", "/v1/code",     {"task": "Write a port scanner in Python"}),
    ("POST", "/v1/ciso",     {"question": "What is DORA compliance?"}),
    ("POST", "/v1/sigma",    {"description": "PowerShell encoded command execution"}),
    ("POST", "/v1/yara",     {"description": "Mimikatz credential dumper"}),
    ("POST", "/v1/ioc",      {"indicator": "185.220.101.1"}),
]


def run_all_benchmarks(n: int = 50) -> dict[str, Any]:
    results = []
    for method, url, body in BENCHMARKS:
        # Fresh app instance per endpoint to avoid rate-limiter interference
        client = _make_test_client()
        print(f"  Benchmarking {method} {url} ({n} requests)...", end="", flush=True)
        result = _run_bench(client, method, url, body, n=n)
        results.append(result)
        print(f"  p50={result['p50_ms']}ms  p99={result['p99_ms']}ms  errors={result['errors']}")

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_per_endpoint": n,
        "results": results,
    }


# ── pytest integration ────────────────────────────────────────────────────────

import pytest  # noqa: E402


@pytest.fixture
def bench_client():
    return _make_test_client()


@pytest.mark.parametrize("method,url,body", BENCHMARKS)
def test_endpoint_benchmark(bench_client, method: str, url: str, body: dict | None):
    """Each endpoint must respond within 1 second for a single mocked request."""
    result = _run_bench(bench_client, method, url, body, n=10)
    assert result["error_rate"] == 0, f"{url} had errors: {result['errors']}/{result['n']}"
    assert result["p99_ms"] < 1000, f"{url} p99 latency {result['p99_ms']}ms exceeds 1000ms"


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Hancock benchmark suite")
    parser.add_argument("--n", type=int, default=50, help="Requests per endpoint")
    args = parser.parse_args()

    print(f"\n[Hancock] Running benchmarks ({args.n} requests per endpoint)...\n")
    report = run_all_benchmarks(n=args.n)

    out_file = RESULTS_DIR / f"bench_{report['timestamp'].replace(':', '-')}.json"
    with out_file.open("w") as fh:
        json.dump(report, fh, indent=2)

    print(f"\n[Hancock] Benchmark report saved to {out_file}")
