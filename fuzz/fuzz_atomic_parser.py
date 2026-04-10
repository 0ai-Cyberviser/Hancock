"""
Fuzz target for Atomic Red Team test parser (collectors/atomic_collector.py).

Exercises parse_atomic_tests() with arbitrary dict inputs to find crashes
in regex-based YAML content parsing, key access, and string operations.
"""
import atheris
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.atomic_collector import parse_atomic_tests  # noqa: E402


def TestOneInput(data: bytes) -> None:
    """Fuzz parse_atomic_tests with arbitrary dicts."""
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 1)
    payload_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())

    if choice == 0:
        # Fuzz with a JSON dict (structured input)
        try:
            decoded = json.loads(payload_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if not isinstance(decoded, dict):
            return
        try:
            parse_atomic_tests(decoded)
        except (KeyError, TypeError, IndexError, AttributeError, ValueError):
            pass
    else:
        # Fuzz with arbitrary raw_yaml content
        try:
            text = payload_bytes.decode("utf-8", errors="replace")
        except Exception:
            return
        raw = {"raw_yaml": text, "technique_id": "T0000"}
        try:
            parse_atomic_tests(raw)
        except (KeyError, TypeError, IndexError, AttributeError, ValueError):
            pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
