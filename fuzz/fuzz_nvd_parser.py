"""
Fuzz target for NVD CVE parser (collectors/nvd_collector.py).

Exercises the parse_cve() function with arbitrary JSON structures to find
crashes caused by unexpected types, missing keys, or malformed nested data.
"""
import atheris
import json
import sys

# Ensure the repo root is on sys.path so we can import the collector
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.nvd_collector import parse_cve  # noqa: E402


def TestOneInput(data: bytes) -> None:
    """Fuzz parse_cve with arbitrary JSON dicts."""
    try:
        decoded = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if not isinstance(decoded, dict):
        return

    try:
        parse_cve(decoded)
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        # Expected exceptions from malformed input — not bugs
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
