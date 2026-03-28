"""
Fuzz target for GHSA advisory parser (collectors/ghsa_collector.py).

Exercises the parse_advisory() function with arbitrary JSON structures to find
crashes from unexpected types, missing keys, or malformed nested data.
"""
import atheris
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.ghsa_collector import parse_advisory  # noqa: E402


def TestOneInput(data: bytes) -> None:
    """Fuzz parse_advisory with arbitrary JSON dicts."""
    try:
        decoded = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if not isinstance(decoded, dict):
        return

    try:
        parse_advisory(decoded)
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        # Expected exceptions from malformed input — not bugs
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
