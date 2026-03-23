"""
Fuzz target for webhook HMAC-SHA256 signature verification.

Exercises the signature-checking logic in the /v1/webhook endpoint with
fuzzed payloads, secrets, and signature headers to find timing leaks or
bypass conditions.
"""
import atheris
import hashlib
import hmac
import sys


def _verify_signature(body: bytes, secret: str, sig_header: str) -> bool:
    """
    Reimplements the webhook signature check from hancock_agent.py
    so it can be fuzzed without the full Flask app.
    """
    if not secret:
        return True  # signature checking disabled

    expected = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(sig_header, expected)


def TestOneInput(data: bytes) -> None:
    """Fuzz HMAC verification with arbitrary inputs."""
    fdp = atheris.FuzzedDataProvider(data)

    secret_len = fdp.ConsumeIntInRange(0, 64)
    secret = fdp.ConsumeString(secret_len)
    sig_len = fdp.ConsumeIntInRange(0, 128)
    sig_header = fdp.ConsumeString(sig_len)
    body = fdp.ConsumeBytes(fdp.remaining_bytes())

    try:
        _verify_signature(body, secret, sig_header)
    except (TypeError, ValueError, UnicodeDecodeError):
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
