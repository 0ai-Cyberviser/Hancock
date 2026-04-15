"""Latency and throughput regression tests for Hancock endpoints.

All tests run against the Flask test client — no real network calls.
A test fails if the measured median latency exceeds LATENCY_THRESHOLD_MS,
or if any response during a throughput batch returns an error status.
"""
import statistics
import time


LATENCY_THRESHOLD_MS = 200  # max acceptable median latency (ms)
THROUGHPUT_BATCH = 20       # number of requests per throughput test
LATENCY_SAMPLES = 15        # number of samples per latency measurement
OUTLIER_FLOOR_MS = 10       # tolerate small scheduler / fixture jitter on very fast paths


def _measure_ms(fn, n=LATENCY_SAMPLES, warmup=1):
    """Return a list of elapsed times in milliseconds for *n* warm calls to *fn*."""
    for _ in range(warmup):
        fn()
    results = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        results.append((time.perf_counter() - t0) * 1000)
    return results


class TestEndpointLatency:
    """Median latency for each endpoint must stay under the regression threshold."""

    def test_health_median_latency(self, hancock_client):
        times = _measure_ms(lambda: hancock_client.get("/health"))
        assert statistics.median(times) < LATENCY_THRESHOLD_MS

    def test_metrics_median_latency(self, hancock_client):
        times = _measure_ms(lambda: hancock_client.get("/metrics"))
        assert statistics.median(times) < LATENCY_THRESHOLD_MS

    def test_ask_median_latency(self, hancock_client, sample_question):
        times = _measure_ms(
            lambda: hancock_client.post("/v1/ask", json={"question": sample_question})
        )
        assert statistics.median(times) < LATENCY_THRESHOLD_MS

    def test_chat_median_latency(self, hancock_client, sample_message):
        times = _measure_ms(
            lambda: hancock_client.post("/v1/chat", json={"message": sample_message})
        )
        assert statistics.median(times) < LATENCY_THRESHOLD_MS

    def test_triage_median_latency(self, hancock_client, sample_alert):
        times = _measure_ms(
            lambda: hancock_client.post("/v1/triage", json={"alert": sample_alert})
        )
        assert statistics.median(times) < LATENCY_THRESHOLD_MS

    def test_agents_median_latency(self, hancock_client):
        times = _measure_ms(lambda: hancock_client.get("/v1/agents"))
        assert statistics.median(times) < LATENCY_THRESHOLD_MS


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
