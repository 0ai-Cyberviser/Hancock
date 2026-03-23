"""
Deep dependency / backend health checks for Hancock with TTL caching.

Each check is a callable that returns a dict:
    {"status": "ok"|"degraded"|"error", "latency_ms": float, "detail": str}

Results are cached for TTL_SECONDS to avoid hammering backends on every poll.
"""

import time
import threading
import urllib.request
import urllib.error

TTL_SECONDS = 30

_cache_lock = threading.Lock()
_cache: dict = {}  # key -> {"result": dict, "expires_at": float}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cached(key, fn):
    """Return cached result for *key*, or call *fn* and cache its result."""
    now = time.monotonic()
    with _cache_lock:
        entry = _cache.get(key)
        if entry and entry["expires_at"] > now:
            return entry["result"]

    result = fn()

    with _cache_lock:
        _cache[key] = {"result": result, "expires_at": now + TTL_SECONDS}

    return result


def _http_ping(url, timeout=5):
    """Return latency_ms and HTTP status for a simple GET to *url*."""
    start = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec B310
            status = resp.status
        latency_ms = (time.monotonic() - start) * 1000
        return latency_ms, status
    except urllib.error.URLError as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return latency_ms, str(exc.reason)
    except Exception as exc:
        latency_ms = (time.monotonic() - start) * 1000
        return latency_ms, str(exc)


# ---------------------------------------------------------------------------
# Individual health-check functions
# ---------------------------------------------------------------------------

def check_ollama(base_url="http://localhost:11434"):
    """Check whether Ollama model server is reachable."""
    def _run():
        latency_ms, result = _http_ping(f"{base_url}/api/tags")
        if isinstance(result, int) and result == 200:
            return {"status": "ok", "latency_ms": round(latency_ms, 2),
                    "detail": "Ollama reachable"}
        return {"status": "error", "latency_ms": round(latency_ms, 2),
                "detail": f"Ollama unreachable: {result}"}
    return _cached("ollama", _run)


def check_nvidia_nim(base_url="http://localhost:8000"):
    """Check whether the NVIDIA NIM inference endpoint is reachable."""
    def _run():
        latency_ms, result = _http_ping(f"{base_url}/v1/models")
        if isinstance(result, int) and result == 200:
            return {"status": "ok", "latency_ms": round(latency_ms, 2),
                    "detail": "NVIDIA NIM reachable"}
        return {"status": "error", "latency_ms": round(latency_ms, 2),
                "detail": f"NVIDIA NIM unreachable: {result}"}
    return _cached("nvidia_nim", _run)


def check_memory():
    """Check current process memory usage and warn if above threshold."""
    def _run():
        threshold_bytes = 512 * 1024 * 1024  # 512 MiB
        rss = 0
        try:
            import resource
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
        except Exception:
            try:
                import psutil
                rss = psutil.Process().memory_info().rss
            except Exception:
                return {"status": "ok", "latency_ms": 0,
                        "detail": "memory check unavailable"}
        status = "ok" if rss < threshold_bytes else "degraded"
        detail = f"RSS {rss // (1024 * 1024)} MiB"
        return {"status": status, "latency_ms": 0, "detail": detail}
    return _cached("memory", _run)


def check_disk():
    """Warn when free disk space drops below 1 GiB."""
    def _run():
        try:
            import shutil
            usage = shutil.disk_usage("/")
            free_gib = usage.free / (1024 ** 3)
            status = "ok" if free_gib >= 1.0 else "degraded"
            detail = f"{free_gib:.1f} GiB free"
            return {"status": status, "latency_ms": 0, "detail": detail}
        except Exception as exc:
            return {"status": "error", "latency_ms": 0, "detail": str(exc)}
    return _cached("disk", _run)


def check_prometheus(base_url="http://localhost:9090"):
    """Check whether a local Prometheus instance is reachable."""
    def _run():
        latency_ms, result = _http_ping(f"{base_url}/-/healthy")
        if isinstance(result, int) and result == 200:
            return {"status": "ok", "latency_ms": round(latency_ms, 2),
                    "detail": "Prometheus reachable"}
        return {"status": "degraded", "latency_ms": round(latency_ms, 2),
                "detail": f"Prometheus unreachable: {result}"}
    return _cached("prometheus", _run)


# ---------------------------------------------------------------------------
# Aggregate check
# ---------------------------------------------------------------------------

ALL_CHECKS = {
    "ollama": check_ollama,
    "nvidia_nim": check_nvidia_nim,
    "memory": check_memory,
    "disk": check_disk,
    "prometheus": check_prometheus,
}


def run_all_checks():
    """Run every registered health check and return an aggregate report."""
    results = {}
    overall = "ok"

    for name, fn in ALL_CHECKS.items():
        try:
            result = fn()
        except Exception as exc:
            result = {"status": "error", "latency_ms": 0, "detail": str(exc)}
        results[name] = result
        if result["status"] == "error":
            overall = "error"
        elif result["status"] == "degraded" and overall != "error":
            overall = "degraded"

    return {"overall": overall, "checks": results,
            "timestamp": time.time()}


def invalidate_cache():
    """Clear all cached health-check results (useful for testing)."""
    with _cache_lock:
        _cache.clear()
