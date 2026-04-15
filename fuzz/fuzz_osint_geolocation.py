"""
Fuzz target for OSINT geolocation response parsing.

Exercises parsing fallbacks in collectors/osint_geolocation.py with malformed
provider payloads, invalid encodings, and partial structures.
"""
import json
import sys
from pathlib import Path
from unittest import mock

import atheris

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.osint_geolocation import GeoIPLookup  # noqa: E402


class _FakeResponse:
    def __init__(self, payload, status_ok: bool):
        self._payload = payload
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise RuntimeError("http error")

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _decode_payload(raw: bytes):
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Feed intentionally malformed payloads through as a string blob.
        return {"raw": raw.decode("utf-8", errors="ignore")}


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    lookup = GeoIPLookup()

    ip = fdp.ConsumeUnicodeNoSurrogates(64) or "8.8.8.8"

    payload = _decode_payload(fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 4096)))
    status_ok = fdp.ConsumeBool()

    # Patch network calls so fuzzing focuses on response parsing logic.
    with mock.patch("collectors.osint_geolocation.requests.get", return_value=_FakeResponse(payload, status_ok)):
        lookup._lookup_ipapi(ip)
        lookup._lookup_ipinfo(ip)
        lookup._lookup_ipapico(ip)
        lookup.lookup_ip(ip)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
