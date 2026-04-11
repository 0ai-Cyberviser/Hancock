"""
Fuzz target for Atomic Red Team test parser (collectors/atomic_collector.py).

Exercises parse_atomic_tests() with arbitrary dict inputs to find crashes
caused by unexpected regex matches, missing keys, or malformed YAML text.
"""
import atheris
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.atomic_collector import parse_atomic_tests  # noqa: E402


def TestOneInput(data: bytes) -> None:
    """Fuzz parse_atomic_tests with arbitrary data."""
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 1)
    remaining = fdp.ConsumeBytes(fdp.remaining_bytes())

    try:
        if choice == 0:
            # Fuzz with arbitrary JSON dict (simulating fetch_atomic_yaml output)
            decoded = json.loads(remaining)
            if isinstance(decoded, dict):
                parse_atomic_tests(decoded)
        else:
            # Fuzz with raw YAML-like text in the expected dict structure
            text = remaining.decode("utf-8", errors="replace")
            parse_atomic_tests({
                "raw_yaml": text,
                "technique_id": "T1059.001",
            })
    except (KeyError, TypeError, IndexError, AttributeError, ValueError,
            json.JSONDecodeError, UnicodeDecodeError, re.error):
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
