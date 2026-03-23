"""
Fuzz target for MITRE ATT&CK data parsing (collectors/mitre_collector.py).

Simulates the JSON bundle structure returned by the MITRE CTI GitHub
fallback and feeds it through the technique-extraction logic that
parses nested dicts and lists.
"""
import atheris
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _parse_technique(obj: dict) -> dict | None:
    """
    Extracted parsing logic from mitre_collector.fetch_via_github().

    We inline the parsing rather than importing fetch_via_github directly
    because the original function also makes HTTP requests.
    """
    if obj.get("type") != "attack-pattern":
        return None
    if obj.get("revoked") or obj.get("x_mitre_deprecated"):
        return None

    return {
        "id": obj.get("id", ""),
        "name": obj.get("name", ""),
        "description": obj.get("description", ""),
        "kill_chain_phases": [
            p["phase_name"] for p in obj.get("kill_chain_phases", [])
        ],
        "platforms": obj.get("x_mitre_platforms", []),
        "detection": obj.get("x_mitre_detection", ""),
        "mitre_id": next(
            (
                ref["external_id"]
                for ref in obj.get("external_references", [])
                if ref.get("source_name") == "mitre-attack"
            ),
            "",
        ),
    }


def TestOneInput(data: bytes) -> None:
    """Fuzz MITRE technique parser with arbitrary JSON."""
    try:
        decoded = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return

    if isinstance(decoded, dict):
        # Fuzz single technique object
        try:
            _parse_technique(decoded)
        except (KeyError, TypeError, IndexError, AttributeError, ValueError):
            pass
    elif isinstance(decoded, list):
        # Fuzz a list of technique objects (simulates bundle["objects"])
        for obj in decoded[:50]:  # Limit to prevent excessive iteration
            if isinstance(obj, dict):
                try:
                    _parse_technique(obj)
                except (KeyError, TypeError, IndexError, AttributeError, ValueError):
                    pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
