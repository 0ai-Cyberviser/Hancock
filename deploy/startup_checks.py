"""
Hancock — Startup pre-flight checks.

Run before starting the server to catch misconfiguration early.
Exits with code 1 if any blocking check fails.

Usage:
    python deploy/startup_checks.py          # check and exit
    python deploy/startup_checks.py --warn   # print warnings but always exit 0
"""
from __future__ import annotations

import argparse
import importlib
import os
import socket
import sys
from typing import NamedTuple

# Ensure project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class CheckResult(NamedTuple):
    name: str
    passed: bool
    message: str
    blocking: bool = True


def _check_env_var(name: str, *, required: bool = True) -> CheckResult:
    val = os.getenv(name, "")
    if required and not val:
        return CheckResult(name, False, f"Required env var {name!r} is not set", blocking=True)
    if val and "your" in val.lower():
        return CheckResult(name, False, f"{name!r} still contains placeholder value", blocking=False)
    return CheckResult(name, True, "ok")


def _check_import(package: str, *, blocking: bool = True) -> CheckResult:
    try:
        importlib.import_module(package)
        return CheckResult(f"import:{package}", True, "ok")
    except ImportError as exc:
        return CheckResult(f"import:{package}", False, str(exc), blocking=blocking)


def _check_port_free(port: int) -> CheckResult:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex(("127.0.0.1", port)) == 0:
                return CheckResult(f"port:{port}", False,
                                   f"Port {port} is already in use", blocking=True)
    except OSError:
        pass
    return CheckResult(f"port:{port}", True, "available")


def _check_ollama() -> CheckResult:
    import urllib.request
    import urllib.error
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    # Normalise base URL and strip an explicit `/v1` suffix if present.
    normalized_base = base_url.rstrip("/")
    if normalized_base.endswith("/v1"):
        normalized_base = normalized_base[:-3]
    tags_url = normalized_base + "/api/tags"
    try:
        with urllib.request.urlopen(tags_url, timeout=5):
            return CheckResult("ollama:connectivity", True, "reachable")
    except Exception as exc:
        return CheckResult("ollama:connectivity", False, str(exc), blocking=False)


def run_checks(warn_only: bool = False) -> list[CheckResult]:
    """Run all startup checks.

    When *warn_only* is True, all checks are returned as non-blocking
    (``blocking=False``) so the caller can still start the server.
    """
    backend = os.getenv("HANCOCK_LLM_BACKEND", "ollama").lower()
    port    = int(os.getenv("HANCOCK_PORT", "5000"))

    checks: list[CheckResult] = [
        _check_import("openai"),
        _check_import("flask"),
        _check_port_free(port),
    ]

    if backend == "nvidia":
        checks.append(_check_env_var("NVIDIA_API_KEY", required=True))
    elif backend == "openai":
        checks.append(_check_env_var("OPENAI_API_KEY", required=True))
    elif backend == "ollama":
        checks.append(_check_ollama())

    if warn_only:
        checks = [
            CheckResult(c.name, c.passed, c.message, blocking=False)
            for c in checks
        ]

    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="Hancock startup pre-flight checks")
    parser.add_argument("--warn", action="store_true",
                        help="Print warnings but exit 0 regardless of results")
    args = parser.parse_args()

    results = run_checks(warn_only=args.warn)

    all_passed = True
    for r in results:
        icon   = "✅" if r.passed else ("⚠️ " if not r.blocking else "❌")
        status = "PASS" if r.passed else ("WARN" if not r.blocking else "FAIL")
        print(f"  {icon}  [{status}]  {r.name}: {r.message}")
        if not r.passed and r.blocking:
            all_passed = False

    print()
    if all_passed:
        print("✅  All checks passed — Hancock is ready to start.")
    elif args.warn:
        print("⚠️   Some checks failed (warn-only mode) — starting anyway.")
    else:
        print("❌  Startup checks failed — resolve the issues above before starting Hancock.")
        sys.exit(1)


if __name__ == "__main__":
    main()
