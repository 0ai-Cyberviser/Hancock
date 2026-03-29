"""
Hancock — Deep health check module.

Verifies availability of all runtime dependencies before the server
accepts traffic.  Safe to call repeatedly; results are cached for
*CACHE_TTL* seconds to avoid hammering backends.

Usage:
    from monitoring.health_check import run_health_checks, HealthStatus
    status = run_health_checks()
    if not status.healthy:
        sys.exit(1)
"""
from __future__ import annotations

import importlib
import logging
import os
import socket
import sys
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

CACHE_TTL = int(os.getenv("HEALTH_CACHE_TTL", "30"))  # seconds

_last_result: "HealthStatus | None" = None
_last_check_time: float = 0.0


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    latency_ms: float = 0.0


@dataclass
class HealthStatus:
    healthy: bool
    checks: list[CheckResult] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "timestamp": self.timestamp,
            "checks": [
                {
                    "name": c.name,
                    "ok": c.ok,
                    "detail": c.detail,
                    "latency_ms": round(c.latency_ms, 2),
                }
                for c in self.checks
            ],
        }


# ── Individual checks ─────────────────────────────────────────────────────────

def _check_python_version() -> CheckResult:
    ok = sys.version_info >= (3, 10)
    return CheckResult(
        name="python_version",
        ok=ok,
        detail=f"{sys.version} ({'ok' if ok else 'requires >=3.10'})",
    )


def _check_dependency(package: str, min_version: str = "") -> CheckResult:
    t0 = time.monotonic()
    try:
        mod = importlib.import_module(package)
        ver = getattr(mod, "__version__", "unknown")
        ok  = True
        detail = f"v{ver}"
    except ImportError as exc:
        ok     = False
        detail = str(exc)
    latency_ms = (time.monotonic() - t0) * 1000
    return CheckResult(name=f"dep:{package}", ok=ok, detail=detail, latency_ms=latency_ms)


def _check_ollama_connectivity() -> CheckResult:
    """Check whether the configured Ollama endpoint is reachable."""
    import urllib.request
    import urllib.error

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    normalized_base = base_url.rstrip("/")
    if normalized_base.endswith("/v1"):
        normalized_base = normalized_base[:-3]
    tags_url = normalized_base + "/api/tags"
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(tags_url, timeout=5) as resp:
            ok     = resp.status == 200
            detail = "reachable" if ok else f"HTTP {resp.status}"
    except Exception as exc:
        ok     = False
        detail = str(exc)
    return CheckResult(
        name="backend:ollama",
        ok=ok,
        detail=detail,
        latency_ms=(time.monotonic() - t0) * 1000,
    )


def _check_openai_env() -> CheckResult:
    key = os.getenv("OPENAI_API_KEY", "")
    ok  = bool(key) and not key.startswith("sk-your")
    return CheckResult(
        name="env:openai_api_key",
        ok=ok,
        detail="set" if ok else "not configured (OpenAI fallback disabled)",
    )


def _check_port_available(port: int) -> CheckResult:
    t0 = time.monotonic()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
            # result == 0 means something *is* already listening
            ok     = result != 0
            detail = "available" if ok else f"port {port} already in use"
    except Exception as exc:
        ok     = False
        detail = str(exc)
    return CheckResult(
        name=f"port:{port}",
        ok=ok,
        detail=detail,
        latency_ms=(time.monotonic() - t0) * 1000,
    )


def _check_rate_limiter_state() -> CheckResult:
    """Lightweight check — ensures the rate-limiter module is importable."""
    try:
        import hancock_agent  # noqa: F401
        return CheckResult(name="rate_limiter", ok=True, detail="module importable")
    except Exception as exc:
        return CheckResult(name="rate_limiter", ok=False, detail=str(exc))


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_health_checks(force: bool = False) -> HealthStatus:
    """Run all health checks and return a *HealthStatus*.

    Results are cached for *CACHE_TTL* seconds unless *force* is True.
    """
    global _last_result, _last_check_time

    now = time.monotonic()
    if not force and _last_result is not None and (now - _last_check_time) < CACHE_TTL:
        return _last_result

    backend = os.getenv("HANCOCK_LLM_BACKEND", "ollama").lower()
    port    = int(os.getenv("HANCOCK_PORT", "5000"))

    checks: list[CheckResult] = [
        _check_python_version(),
        _check_dependency("openai"),
        _check_dependency("flask"),
        _check_openai_env(),
    ]

    if backend == "ollama":
        checks.append(_check_ollama_connectivity())

    checks.append(_check_rate_limiter_state())

    healthy = all(c.ok for c in checks if c.name not in {
        # Non-blocking checks — warn but don't fail
        "env:openai_api_key",
        "backend:ollama",
    })

    status        = HealthStatus(healthy=healthy, checks=checks)
    _last_result  = status
    _last_check_time = now
    return status


if __name__ == "__main__":
    import json
    result = run_health_checks(force=True)
    print(json.dumps(result.to_dict(), indent=2))
    sys.exit(0 if result.healthy else 1)
