"""Performance regression tests for Hancock endpoints.

All tests run against Flask's in-process test client (no external network),
with mocked LLM responses. The suite covers:
- Burst behavior around configured rate limits.
- Concurrent webhook HMAC validation under load.
- p50/p95 latency thresholds with CI regression gating.
- Throughput and outlier checks for existing fast paths.

Set ``HANCOCK_PERF_ARTIFACT`` to emit a JSON report for CI artifacts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

LATENCY_THRESHOLD_MS = 200  # max acceptable median latency for legacy checks (ms)
THROUGHPUT_BATCH = 20       # number of requests per throughput test
LATENCY_SAMPLES = 25        # number of samples per latency measurement
OUTLIER_FLOOR_MS = 15       # tolerate small scheduler / fixture jitter on very fast paths
RATE_LIMIT_TEST_VALUE = 6

# Endpoint-specific latency targets for regression gating in CI.
# Values are intentionally conservative for shared CI runners.
LATENCY_TARGETS_MS = {
    "GET /health": {"p50": 40, "p95": 120},
    "GET /metrics": {"p50": 60, "p95": 180},
    "POST /v1/ask": {"p50": 120, "p95": 260},
    "POST /v1/chat": {"p50": 120, "p95": 260},
    "POST /v1/triage": {"p50": 140, "p95": 300},
}

PERFORMANCE_RESULTS: list[dict] = []


def _percentile(data: list[float], pct: float) -> float:
    """Return percentile from *data* for integer-like pct values (e.g., 95)."""
    sorted_data = sorted(data)
    idx = min(int(len(sorted_data) * pct / 100), len(sorted_data) - 1)
    return sorted_data[idx]


def _measure_ms(fn, n: int = LATENCY_SAMPLES, warmup: int = 1) -> list[float]:
    """Return elapsed times in milliseconds for *n* warm calls to *fn*."""
    for _ in range(warmup):
        fn()

    results = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        results.append((time.perf_counter() - t0) * 1000)
    return results


def _record_latency(endpoint_name: str, samples: list[float]) -> dict:
    """Compute, store, and return latency stats for one endpoint."""
    stats = {
        "endpoint": endpoint_name,
        "samples": len(samples),
        "p50_ms": statistics.median(samples),
        "p95_ms": _percentile(samples, 95),
        "max_ms": max(samples),
    }
    PERFORMANCE_RESULTS.append(stats)
    return stats


def _assert_latency_regression(endpoint_name: str, samples: list[float]) -> None:
    """Fail if endpoint p50/p95 exceeds configured target."""
    stats = _record_latency(endpoint_name, samples)
    targets = LATENCY_TARGETS_MS[endpoint_name]

    assert stats["p50_ms"] < targets["p50"], (
        f"{endpoint_name} regression: p50={stats['p50_ms']:.2f}ms "
        f">= target {targets['p50']}ms"
    )
    assert stats["p95_ms"] < targets["p95"], (
        f"{endpoint_name} regression: p95={stats['p95_ms']:.2f}ms "
        f">= target {targets['p95']}ms"
    )


@pytest.fixture(scope="module", autouse=True)
def _emit_perf_artifact_at_end():
    """Write JSON benchmark artifact when requested by CI."""
    yield
    artifact_path = os.getenv("HANCOCK_PERF_ARTIFACT", "").strip()
    if not artifact_path:
        return

    path = Path(artifact_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "latency_targets_ms": LATENCY_TARGETS_MS,
        "results": PERFORMANCE_RESULTS,
        "generated_at_epoch": time.time(),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


@pytest.fixture
def rate_limited_client(mock_openai_client):
    """App client pinned to a small rate limit for deterministic burst tests."""
    import hancock_agent

    with patch.dict(
        os.environ,
        {
            "HANCOCK_RATE_LIMIT": str(RATE_LIMIT_TEST_VALUE),
            "HANCOCK_API_KEY": "",
        },
    ):
        app = hancock_agent.build_app(mock_openai_client, "mistralai/mistral-7b-instruct-v0.3")
        app.testing = True
        with app.test_client() as client:
            yield client


@pytest.fixture
def webhook_hmac_app(mock_openai_client):
    """Flask app configured with webhook secret and high rate limit for concurrency tests."""
    import hancock_agent

    with patch.dict(
        os.environ,
        {
            "HANCOCK_WEBHOOK_SECRET": "perf-hmac-secret",
            "HANCOCK_RATE_LIMIT": "1000",
            "HANCOCK_API_KEY": "",
            "HANCOCK_SLACK_WEBHOOK": "",
            "HANCOCK_TEAMS_WEBHOOK": "",
        },
    ):
        app = hancock_agent.build_app(mock_openai_client, "mistralai/mistral-7b-instruct-v0.3")
        app.testing = True
        yield app


class TestBurstAroundRateLimit:
    """Burst behavior around HANCOCK_RATE_LIMIT for /v1/ask and /v1/chat."""

    def test_ask_burst_respects_rate_limit_boundary(self, rate_limited_client, sample_question):
        statuses = []
        for _ in range(RATE_LIMIT_TEST_VALUE + 1):
            response = rate_limited_client.post("/v1/ask", json={"question": sample_question})
            statuses.append(response.status_code)

        assert statuses[:RATE_LIMIT_TEST_VALUE] == [200] * RATE_LIMIT_TEST_VALUE
        assert statuses[-1] == 429

    def test_chat_burst_respects_rate_limit_boundary(self, rate_limited_client, sample_message):
        statuses = []
        for _ in range(RATE_LIMIT_TEST_VALUE + 1):
            response = rate_limited_client.post("/v1/chat", json={"message": sample_message})
            statuses.append(response.status_code)

        assert statuses[:RATE_LIMIT_TEST_VALUE] == [200] * RATE_LIMIT_TEST_VALUE
        assert statuses[-1] == 429


class TestConcurrentWebhookHMAC:
    """Concurrent webhook requests should enforce HMAC checks correctly."""

    @staticmethod
    def _post_signed_webhook(app, body_bytes: bytes, valid_signature: bool) -> int:
        signature = "sha256=" + hmac.new(
            b"perf-hmac-secret", body_bytes, hashlib.sha256
        ).hexdigest()
        if not valid_signature:
            signature = "sha256=" + "0" * 64

        with app.test_client() as client:
            response = client.post(
                "/v1/webhook",
                data=body_bytes,
                headers={"X-Hancock-Signature": signature},
                content_type="application/json",
            )
            return response.status_code

    def test_webhook_hmac_validation_under_concurrency(self, webhook_hmac_app):
        body = json.dumps(
            {"alert": "Concurrent suspicious logon events", "source": "siem", "severity": "high"}
        ).encode("utf-8")

        total_requests = 120
        valid_requests = 80
        validity = [True] * valid_requests + [False] * (total_requests - valid_requests)

        with ThreadPoolExecutor(max_workers=24) as pool:
            status_codes = list(
                pool.map(
                    lambda is_valid: self._post_signed_webhook(webhook_hmac_app, body, is_valid),
                    validity,
                )
            )

        assert status_codes.count(200) == valid_requests
        assert status_codes.count(401) == total_requests - valid_requests
        assert set(status_codes).issubset({200, 401})


class TestLatencyTargets:
    """p50/p95 latency gates for regression detection in CI."""

    def test_health_latency_targets(self, hancock_client):
        samples = _measure_ms(lambda: hancock_client.get("/health"))
        _assert_latency_regression("GET /health", samples)

    def test_metrics_latency_targets(self, hancock_client):
        samples = _measure_ms(lambda: hancock_client.get("/metrics"))
        _assert_latency_regression("GET /metrics", samples)

    def test_ask_latency_targets(self, hancock_client, sample_question):
        samples = _measure_ms(
            lambda: hancock_client.post("/v1/ask", json={"question": sample_question})
        )
        _assert_latency_regression("POST /v1/ask", samples)

    def test_chat_latency_targets(self, hancock_client, sample_message):
        samples = _measure_ms(
            lambda: hancock_client.post("/v1/chat", json={"message": sample_message})
        )
        _assert_latency_regression("POST /v1/chat", samples)

    def test_triage_latency_targets(self, hancock_client, sample_alert):
        samples = _measure_ms(
            lambda: hancock_client.post("/v1/triage", json={"alert": sample_alert})
        )
        _assert_latency_regression("POST /v1/triage", samples)

    def test_agents_median_latency(self, hancock_client):
        samples = _measure_ms(lambda: hancock_client.get("/v1/agents"))
        assert statistics.median(samples) < LATENCY_THRESHOLD_MS


class TestThroughput:
    """Repeated requests must complete without errors and within a wall-clock budget."""

    def test_health_batch_no_errors(self, hancock_client):
        for _ in range(THROUGHPUT_BATCH):
            r = hancock_client.get("/health")
            assert r.status_code == 200

    def test_health_batch_wall_clock(self, hancock_client):
        t0 = time.perf_counter()
        for _ in range(THROUGHPUT_BATCH):
            hancock_client.get("/health")
        elapsed = time.perf_counter() - t0
        assert elapsed < 5.0, f"{THROUGHPUT_BATCH} health requests took {elapsed:.2f}s"

    def test_ask_batch_no_errors(self, hancock_client, sample_question):
        for _ in range(THROUGHPUT_BATCH):
            r = hancock_client.post("/v1/ask", json={"question": sample_question})
            assert r.status_code == 200

    def test_chat_batch_no_5xx(self, hancock_client, sample_message):
        for _ in range(THROUGHPUT_BATCH):
            r = hancock_client.post("/v1/chat", json={"message": sample_message})
            assert r.status_code < 500

    def test_triage_batch_no_errors(self, hancock_client, sample_alert):
        for _ in range(THROUGHPUT_BATCH):
            r = hancock_client.post("/v1/triage", json={"alert": sample_alert})
            assert r.status_code == 200


class TestLatencyConsistency:
    """Variance between min and max should not be extreme (no runaway outliers)."""

    def test_health_max_vs_min_ratio(self, hancock_client):
        times = _measure_ms(lambda: hancock_client.get("/health"), n=20)
        ratio = max(times) / max(min(times), 0.001)
        assert ratio < 50, f"Latency spread too large: min={min(times):.1f}ms max={max(times):.1f}ms"

    def test_ask_max_within_10x_median(self, hancock_client, sample_question):
        times = _measure_ms(
            lambda: hancock_client.post("/v1/ask", json={"question": sample_question}),
            n=20,
        )
        median = statistics.median(times)
        allowed_max = max(median * 10, OUTLIER_FLOOR_MS)
        assert max(times) < allowed_max, (
            f"Max latency {max(times):.1f}ms exceeded {allowed_max:.1f}ms "
            f"(median {median:.1f}ms)"
        )
