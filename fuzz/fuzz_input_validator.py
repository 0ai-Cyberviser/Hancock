"""
Fuzz target for input validation (input_validator.py).

Exercises detect_ioc_type(), validate_payload(), validate_mode(),
validate_siem(), validate_ciso_output(), validate_ioc_type(), and
sanitize_string() with arbitrary data to find crashes or unexpected
behaviour in the validation logic.
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
    """Fuzz input_validator functions with arbitrary data."""
    fdp = atheris.FuzzedDataProvider(data)
    choice = fdp.ConsumeIntInRange(0, 6)

    try:
        if choice == 0:
            # Fuzz detect_ioc_type with arbitrary strings
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            detect_ioc_type(text)

        elif choice == 1:
            # Fuzz validate_payload with arbitrary JSON dicts
            remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
            decoded = json.loads(remaining)
            if isinstance(decoded, dict):
                validate_payload(decoded, required=["alert", "message"])

        elif choice == 2:
            # Fuzz validate_payload with random required fields
            remaining = fdp.ConsumeBytes(fdp.remaining_bytes())
            decoded = json.loads(remaining)
            if isinstance(decoded, dict):
                fields = list(decoded.keys())[:5]
                validate_payload(decoded, required=fields)

        elif choice == 3:
            # Fuzz validate_mode
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            validate_mode(text)

        elif choice == 4:
            # Fuzz validate_siem
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            validate_siem(text)

        elif choice == 5:
            # Fuzz validate_ciso_output and validate_ioc_type
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            validate_ciso_output(text)
            validate_ioc_type(text)

        elif choice == 6:
            # Fuzz sanitize_string with arbitrary lengths
            max_len = fdp.ConsumeIntInRange(0, 100_000)
            text = fdp.ConsumeUnicodeNoSurrogates(fdp.remaining_bytes())
            sanitize_string(text, max_length=max_len)

    except (json.JSONDecodeError, UnicodeDecodeError, TypeError,
            ValueError, AttributeError):
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
