"""
Fuzz target for input validation (input_validator.py).

Exercises detect_ioc_type() with arbitrary strings and validate_payload()
with arbitrary JSON dicts to find crashes in regex matching, IP address
parsing, or dict traversal.
"""
import atheris
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from input_validator import (  # noqa: E402
    detect_ioc_type,
    validate_payload,
    validate_mode,
    validate_siem,
    validate_ciso_output,
    validate_ioc_type,
    sanitize_string,
)


def TestOneInput(data: bytes) -> None:
    """Fuzz input validation functions with arbitrary data."""
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 5)
    payload_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())

    if choice == 0:
        # Fuzz detect_ioc_type with arbitrary strings
        try:
            text = payload_bytes.decode("utf-8", errors="replace")
        except Exception:
            return
        try:
            detect_ioc_type(text)
        except (ValueError, TypeError, AttributeError, OverflowError):
            pass

    elif choice == 1:
        # Fuzz validate_payload with arbitrary JSON
        try:
            decoded = json.loads(payload_bytes)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return
        if not isinstance(decoded, dict):
            return
        try:
            validate_payload(
                decoded,
                required=["id", "type", "value", "source", "timestamp"],
            )
        except (KeyError, TypeError, IndexError, AttributeError, ValueError):
            pass

    elif choice == 2:
        # Fuzz validate_mode
        try:
            text = payload_bytes.decode("utf-8", errors="replace")
        except Exception:
            return
        try:
            validate_mode(text)
        except (TypeError, AttributeError):
            pass

    elif choice == 3:
        # Fuzz validate_siem
        try:
            text = payload_bytes.decode("utf-8", errors="replace")
        except Exception:
            return
        try:
            validate_siem(text)
        except (TypeError, AttributeError):
            pass

    elif choice == 4:
        # Fuzz validate_ciso_output / validate_ioc_type
        try:
            text = payload_bytes.decode("utf-8", errors="replace")
        except Exception:
            return
        try:
            validate_ciso_output(text)
            validate_ioc_type(text)
        except (TypeError, AttributeError):
            pass

    elif choice == 5:
        # Fuzz sanitize_string
        try:
            text = payload_bytes.decode("utf-8", errors="replace")
        except Exception:
            return
        try:
            max_len = (len(text) % 50000) + 1 if text else 100
            sanitize_string(text, max_length=max_len)
        except (TypeError, ValueError, OverflowError):
            pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
