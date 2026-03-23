"""
Hancock health checker — deep dependency/backend health checks.

Checks Ollama, OpenAI reachability, disk space, and memory usage.
Results are TTL-cached to avoid hammering backends on every request.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from typing import Any

logger = logging.getLogger(__name__)

# Default TTL for cached health results (seconds)
_DEFAULT_TTL: int = 30

# Try optional imports
try:
    import urllib.request
    import urllib.error
    _URLLIB_AVAILABLE = True
except ImportError:  # pragma: no cover
    _URLLIB_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    _PSUTIL_AVAILABLE = False


class HealthChecker:
    """
    Deep health checker with TTL-cached results.

    Usage::

        checker = HealthChecker(ttl=30)
        status = checker.check_all()
    """

    def __init__(self, ttl: int = _DEFAULT_TTL) -> None:
        self.ttl = ttl
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _is_fresh(self, key: str) -> bool:
        if key not in self._cache:
            return False
        ts, _ = self._cache[key]
        return (time.monotonic() - ts) < self.ttl

    def _get_cached(self, key: str) -> dict[str, Any]:
        _, result = self._cache[key]
        return result

    def _store(self, key: str, result: dict[str, Any]) -> dict[str, Any]:
        self._cache[key] = (time.monotonic(), result)
        return result

    # ── Individual checks ─────────────────────────────────────────────────────

    def check_ollama(self) -> dict[str, Any]:
        """Check Ollama backend availability."""
        key = "ollama"
        if self._is_fresh(key):
            return self._get_cached(key)

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        url = f"{base_url}/api/tags"
        result: dict[str, Any] = {"name": "ollama", "url": url}

        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                result["status"] = "healthy" if resp.status == 200 else "degraded"
                result["http_status"] = resp.status
        except Exception as exc:
            result["status"] = "unhealthy"
            result["error"] = str(exc)

        return self._store(key, result)

    def check_openai(self) -> dict[str, Any]:
        """Check OpenAI API reachability (connectivity only, no auth)."""
        key = "openai"
        if self._is_fresh(key):
            return self._get_cached(key)

        result: dict[str, Any] = {"name": "openai", "url": "https://api.openai.com"}

        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                method="GET",
            )
            req.add_header("Authorization", "Bearer invalid-key-connectivity-check")
            try:
                urllib.request.urlopen(req, timeout=5)
                result["status"] = "healthy"
            except urllib.error.HTTPError as http_err:
                # 401 means we reached the server — connectivity is fine
                if http_err.code == 401:
                    result["status"] = "healthy"
                    result["note"] = "reachable (auth not validated)"
                else:
                    result["status"] = "degraded"
                    result["http_status"] = http_err.code
        except Exception as exc:
            result["status"] = "unhealthy"
            result["error"] = str(exc)

        return self._store(key, result)

    def check_disk(self, path: str = "/") -> dict[str, Any]:
        """Check available disk space."""
        key = f"disk:{path}"
        if self._is_fresh(key):
            return self._get_cached(key)

        result: dict[str, Any] = {"name": "disk", "path": path}
        try:
            usage = shutil.disk_usage(path)
            used_pct = (usage.used / usage.total) * 100
            result["total_gb"] = round(usage.total / 1e9, 2)
            result["used_gb"] = round(usage.used / 1e9, 2)
            result["free_gb"] = round(usage.free / 1e9, 2)
            result["used_pct"] = round(used_pct, 1)
            result["status"] = "healthy" if used_pct < 90 else "degraded"
        except Exception as exc:
            result["status"] = "unhealthy"
            result["error"] = str(exc)

        return self._store(key, result)

    def check_memory(self) -> dict[str, Any]:
        """Check available system memory."""
        key = "memory"
        if self._is_fresh(key):
            return self._get_cached(key)

        result: dict[str, Any] = {"name": "memory"}

        if _PSUTIL_AVAILABLE:
            try:
                mem = psutil.virtual_memory()
                result["total_gb"] = round(mem.total / 1e9, 2)
                result["available_gb"] = round(mem.available / 1e9, 2)
                result["used_pct"] = mem.percent
                result["status"] = "healthy" if mem.percent < 90 else "degraded"
            except Exception as exc:
                result["status"] = "unhealthy"
                result["error"] = str(exc)
        else:
            # Fallback without psutil
            result["status"] = "unknown"
            result["note"] = "psutil not installed; install for memory metrics"

        return self._store(key, result)

    # ── Aggregate check ───────────────────────────────────────────────────────

    def check_all(self) -> dict[str, Any]:
        """Run all health checks and return an aggregate status."""
        backend = os.getenv("HANCOCK_LLM_BACKEND", "openai").lower()

        checks = [self.check_disk(), self.check_memory()]
        if backend == "ollama":
            checks.append(self.check_ollama())
        else:
            checks.append(self.check_openai())

        statuses = [c.get("status", "unknown") for c in checks]

        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {
            "status": overall,
            "checks": {c["name"]: c for c in checks},
        }
