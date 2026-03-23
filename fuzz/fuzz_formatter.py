"""
Fuzz target for the JSONL formatters (formatter/to_mistral_jsonl.py and v2).

Exercises format_kb_pairs(), format_mitre_techniques(), format_cves(),
format_soc_detections(), and validate_sample() with arbitrary JSON data.
"""
import atheris
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from formatter.to_mistral_jsonl import (  # noqa: E402
    format_kb_pairs,
    format_mitre_techniques,
    format_cves,
    validate_sample,
)
from formatter.to_mistral_jsonl_v2 import (  # noqa: E402
    format_kb_pairs as format_kb_pairs_v2,
    format_mitre_techniques as format_mitre_v2,
    format_cves as format_cves_v2,
    format_soc_detections,
    validate_sample as validate_sample_v2,
)


def TestOneInput(data: bytes) -> None:
    """Fuzz all formatter functions with arbitrary JSON."""
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 7)
    payload_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())

    try:
        decoded = json.loads(payload_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    try:
        if choice == 0 and isinstance(decoded, dict):
            format_kb_pairs(decoded)
        elif choice == 1 and isinstance(decoded, dict):
            format_mitre_techniques(decoded)
        elif choice == 2 and isinstance(decoded, list):
            format_cves(decoded)
        elif choice == 3 and isinstance(decoded, dict):
            validate_sample(decoded)
        elif choice == 4 and isinstance(decoded, dict):
            format_kb_pairs_v2(decoded)
        elif choice == 5 and isinstance(decoded, dict):
            format_mitre_v2(decoded)
        elif choice == 6 and isinstance(decoded, list):
            format_cves_v2(decoded)
        elif choice == 7 and isinstance(decoded, list):
            format_soc_detections(decoded)
    except (KeyError, TypeError, IndexError, AttributeError, ValueError):
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
