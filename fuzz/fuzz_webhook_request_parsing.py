"""
Fuzz target for webhook request signature + body handling paths.

Builds a minimal Flask test client and fuzzes /v1/webhook with varied headers,
encodings, content types, and oversized JSON-like payloads.
"""
import os
import sys
from pathlib import Path

import atheris

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force webhook signature path on.
os.environ.setdefault("NVIDIA_API_KEY", "fuzz-test-key")
os.environ["HANCOCK_WEBHOOK_SECRET"] = "fuzz-secret"
os.environ.setdefault("HANCOCK_API_KEY", "")

_app = None
_client = None


class _MockClient:
    class chat:
        class completions:
            @staticmethod
            def create(**kwargs):
                class _Choice:
                    class message:
                        content = "mock"

                class _Resp:
                    choices = [_Choice()]

                return _Resp()


def _get_client():
    global _app, _client
    if _client is not None:
        return _client

    import hancock_agent  # noqa: E402

    _app = hancock_agent.build_app(_MockClient(), "mock-model")
    _app.config["TESTING"] = True
    _client = _app.test_client()
    return _client


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    client = _get_client()

    body_len = fdp.ConsumeIntInRange(0, 32768)
    body = fdp.ConsumeBytes(body_len)
    sig_header = fdp.ConsumeUnicodeNoSurrogates(256)
    content_type = fdp.PickValueInList([
        "application/json",
        "application/json; charset=utf-8",
        "text/plain",
        "application/octet-stream",
        "application/json; charset=latin-1",
    ])

    headers = {"X-Hancock-Signature": sig_header}

    try:
        client.post(
            "/v1/webhook",
            data=body,
            headers=headers,
            content_type=content_type,
        )
    except Exception:
        pass


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
