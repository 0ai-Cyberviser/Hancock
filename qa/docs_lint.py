#!/usr/bin/env python3
"""Lint canonical docs for stale backend and endpoint references."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CHECKS: dict[str, list[tuple[str, str]]] = {
    "README.md": [
        ("nvidia_nim", "Use HANCOCK_LLM_BACKEND=nvidia, not nvidia_nim."),
        ("OLLAMA_URL", "Use OLLAMA_BASE_URL env var name."),
    ],
    "docs/deployment.md": [
        ("nvidia_nim", "Use HANCOCK_LLM_BACKEND=nvidia, not nvidia_nim."),
        ("OLLAMA_URL", "Use OLLAMA_BASE_URL env var name."),
        ("`PORT`", "Use HANCOCK_PORT env var name."),
    ],
    "docs/production-checklist.md": [
        ("nvidia_nim", "Use HANCOCK_LLM_BACKEND=nvidia, not nvidia_nim."),
        ("/models", "Use /v1/agents endpoint name."),
        ("`/chat`", "Use /v1/chat endpoint name."),
    ],
}


def main() -> int:
    failures: list[str] = []

    for rel_path, checks in CHECKS.items():
        file_path = ROOT / rel_path
        text = file_path.read_text(encoding="utf-8")
        for needle, message in checks:
            if needle in text:
                failures.append(f"{rel_path}: found '{needle}' ({message})")

    if failures:
        print("Docs lint failed:")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("Docs lint passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
