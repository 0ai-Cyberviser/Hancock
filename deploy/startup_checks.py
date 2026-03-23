#!/usr/bin/env python3
"""
deploy/startup_checks.py — Pre-flight validation for the Hancock agent.

Checks performed:
  1. Python version >= 3.10
  2. Required third-party imports are available
  3. Required environment variables are set
  4. Hancock source modules can be imported

Exit codes:
  0  — all checks passed
  1  — one or more checks failed
"""
from __future__ import annotations

import importlib
import os
import sys


REQUIRED_PYTHON = (3, 10)

REQUIRED_PACKAGES = [
    "flask",
    "openai",
    "dotenv",
    "requests",
    "prometheus_client",
]

REQUIRED_ENV_VARS = [
    "NVIDIA_API_KEY",
]

OPTIONAL_ENV_VARS = [
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "LOG_LEVEL",
]


def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}", file=sys.stderr)


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}", file=sys.stderr)


def check_python_version() -> bool:
    current = sys.version_info[:2]
    if current >= REQUIRED_PYTHON:
        _ok(f"Python {sys.version.split()[0]} (>= {'.'.join(map(str, REQUIRED_PYTHON))})")
        return True
    _fail(
        f"Python {sys.version.split()[0]} is too old — "
        f">= {'.'.join(map(str, REQUIRED_PYTHON))} required"
    )
    return False


def check_imports() -> bool:
    all_ok = True
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
            _ok(f"import {pkg}")
        except ImportError as exc:
            _fail(f"import {pkg} — {exc}")
            all_ok = False
    return all_ok


def check_env_vars() -> bool:
    all_ok = True
    for var in REQUIRED_ENV_VARS:
        val = os.environ.get(var)
        if val:
            _ok(f"{var} is set")
        else:
            _fail(f"{var} is not set (required)")
            all_ok = False
    for var in OPTIONAL_ENV_VARS:
        val = os.environ.get(var)
        if val:
            _ok(f"{var} is set")
        else:
            _warn(f"{var} is not set (optional)")
    return all_ok


def check_hancock_modules() -> bool:
    modules = ["hancock_constants"]
    all_ok = True
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    for mod in modules:
        try:
            importlib.import_module(mod)
            _ok(f"hancock module: {mod}")
        except ImportError as exc:
            _fail(f"hancock module {mod} — {exc}")
            all_ok = False
    return all_ok


def main() -> int:
    print("=== Hancock pre-flight checks ===")
    results = [
        check_python_version(),
        check_imports(),
        check_env_vars(),
        check_hancock_modules(),
    ]
    passed = all(results)
    print()
    if passed:
        print("All checks passed — Hancock is ready to start.")
        return 0
    print("One or more checks FAILED — review the errors above.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
