#!/usr/bin/env python3
"""Lint docs and repo-facing metadata for stale references."""
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

SURFACE_FILES: tuple[str, ...] = (
    ".github/FUNDING.yml",
    ".github/ISSUE_TEMPLATE/config.yml",
    ".github/agents/0ai.agent.md",
    ".github/pull_request_template.md",
    "BUSINESS_PROPOSAL.md",
    "CONTRIBUTING.md",
    "LAUNCH.md",
    "OUTREACH_TEMPLATES.md",
    "OWNERSHIP.md",
    "PUBLIC_SURFACE.md",
    "README.md",
    "SECURITY.md",
    "SUPPORT.md",
    "deploy/docker/Dockerfile",
    "deploy/helm/Chart.yaml",
    "deploy/helm/hancock/Chart.yaml",
    "docs/404.html",
    "docs/api.html",
    "docs/contact.html",
    "docs/demo.html",
    "docs/graphql-security-guide.md",
    "docs/graphql-security-quickstart.md",
    "docs/index.html",
    "docs/openapi.yaml",
    "docs/pricing.html",
    "docs/robots.txt",
    "docs/sitemap.xml",
    "docs/sponsors.html",
    "docs/train.html",
    "fuzz/oss-fuzz/project.yaml",
    "netlify.toml",
    "pyproject.toml",
    "spaces_README.md",
    "spaces_app.py",
)

DISALLOWED_SURFACES: dict[str, str] = {
    "cyberviser.ai": "Use the portfolio hub or repo-local docs instead of the retired cyberviser.ai host.",
    "cyberviser.netlify.app": "Do not point users to the retired Netlify surface.",
    "cyberviser.github.io/Hancock/": "Use the portfolio hub instead of the retired Hancock microsite URL.",
    "contact@cyberviser.ai": "Use the maintained support mailbox instead of the retired contact@cyberviser.ai address.",
    "security@cyberviser.ai": "Use the maintained security mailbox instead of the retired security@cyberviser.ai address.",
}


def main() -> int:
    failures: list[str] = []

    for rel_path, checks in CHECKS.items():
        file_path = ROOT / rel_path
        text = file_path.read_text(encoding="utf-8")
        for needle, message in checks:
            if needle in text:
                failures.append(f"{rel_path}: found '{needle}' ({message})")

    for rel_path in SURFACE_FILES:
        file_path = ROOT / rel_path
        text = file_path.read_text(encoding="utf-8")
        for needle, message in DISALLOWED_SURFACES.items():
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
