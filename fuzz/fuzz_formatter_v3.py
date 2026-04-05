"""
Fuzz target for v3 dataset formatter (collectors/formatter_v3.py).

Exercises format_nvd_cves(), format_kev_entries(), format_ghsa_advisories(),
and format_atomic_tests() with arbitrary JSON data to find crashes caused
by unexpected types, missing keys, or malformed nested structures.
"""
import atheris
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.formatter_v3 import (  # noqa: E402
    format_nvd_cves,
    format_kev_entries,
    format_ghsa_advisories,
    format_atomic_tests,
)


def TestOneInput(data: bytes) -> None:
    """Fuzz v3 formatter functions with arbitrary JSON."""
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 3)
    payload_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())

    try:
        decoded = json.loads(payload_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if not isinstance(decoded, list):
        return

    # Limit list length to prevent excessive iteration
    decoded = decoded[:50]

    try:
        if choice == 0:
            format_nvd_cves(decoded)
        elif choice == 1:
            format_kev_entries(decoded)
        elif choice == 2:
            format_ghsa_advisories(decoded)
        elif choice == 3:
            format_atomic_tests(decoded)
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
