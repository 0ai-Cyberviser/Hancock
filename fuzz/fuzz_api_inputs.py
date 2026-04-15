"""
Fuzz target for Hancock REST API input parsing.

Creates a minimal Flask test client and feeds fuzzed JSON payloads to each
API endpoint to exercise request parsing, validation, and error handling
without requiring an actual LLM backend.
"""
import atheris
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Prevent the agent from connecting to real backends during fuzzing
os.environ.setdefault("NVIDIA_API_KEY", "fuzz-test-key")
os.environ.setdefault("HANCOCK_API_KEY", "")
os.environ.setdefault("HANCOCK_WEBHOOK_SECRET", "")

_app = None
_client = None


def _get_client():
    """Lazy-initialize Flask test client once."""
    global _app, _client
    if _client is not None:
        return _client

    import hancock_agent  # noqa: E402

    # build_app requires a client and model name; supply a no-op mock so the
    # fuzzer can exercise request parsing without a real LLM backend.
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

    _app = hancock_agent.build_app(_MockClient(), "mock-model")
    _app.config["TESTING"] = True
    _client = _app.test_client()
    return _client


# Endpoints that accept POST with JSON body
_ENDPOINTS = [
    "/v1/ask",
    "/v1/chat",
    "/v1/triage",
    "/v1/hunt",
    "/v1/respond",
    "/v1/code",
    "/v1/ciso",
    "/v1/sigma",
    "/v1/yara",
    "/v1/ioc",
    "/v1/webhook",
]


def TestOneInput(data: bytes) -> None:
    """Fuzz API endpoints with arbitrary JSON bodies."""
    fdp = atheris.FuzzedDataProvider(data)
    idx = fdp.ConsumeIntInRange(0, len(_ENDPOINTS) - 1)
    payload_bytes = fdp.ConsumeBytes(fdp.remaining_bytes())

    endpoint = _ENDPOINTS[idx]
    client = _get_client()

    client.post(
        endpoint,
        data=payload_bytes,
        content_type="application/json",
    )


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
