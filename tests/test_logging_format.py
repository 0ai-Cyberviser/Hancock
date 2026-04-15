"""Structured logging and request-ID behavior tests."""

from __future__ import annotations

import json

from monitoring.logging_config import JsonFormatter


def test_x_request_id_is_accepted_and_echoed_in_error_response(hancock_client):
    """Client-provided X-Request-ID should flow through headers and error payload."""
    request_id = "req-integration-test-001"
    response = hancock_client.post(
        "/v1/ask",
        json={"question": ""},
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["request_id"] == request_id
    assert response.headers["X-Request-ID"] == request_id


def test_request_completed_log_has_required_structured_fields(hancock_client, caplog):
    """Ensure request log entries include endpoint/mode/backend/status/latency."""
    caplog.set_level("INFO", logger="hancock.request")
    response = hancock_client.post("/v1/ask", json={"question": "hello", "mode": "auto"})
    assert response.status_code == 200

    completed_records = [
        record for record in caplog.records
        if record.name == "hancock.request" and getattr(record, "event", "") == "request_completed"
    ]
    assert completed_records, "Expected at least one request_completed log record"

    record = completed_records[-1]
    payload = json.loads(JsonFormatter().format(record))

    assert payload["event"] == "request_completed"
    assert payload["endpoint"] == "/v1/ask"
    assert payload["mode"] == "auto"
    assert payload["backend"]
    assert payload["status"] == 200
    assert isinstance(payload["latency_ms"], (int, float))
    assert payload["request_id"].strip()
