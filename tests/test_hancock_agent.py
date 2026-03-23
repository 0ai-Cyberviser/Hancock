"""
Hancock Agent — Comprehensive Test Suite
Tests for critical fixes and resilience improvements.
Run:  make test   or   pytest tests/test_hancock_agent.py -v
"""
import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_client():
    from unittest.mock import MagicMock
    client = MagicMock()
    resp = MagicMock()
    resp.choices[0].message.content = "Mocked Hancock response."
    client.chat.completions.create.return_value = resp
    return client


@pytest.fixture
def app(mock_client):
    import hancock_agent
    flask_app = hancock_agent.build_app(mock_client, "mistralai/mistral-7b-instruct-v0.3")
    flask_app.testing = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_json_contains_status_ok(self, client):
        data = client.get("/health").get_json()
        assert data["status"] == "ok"

    def test_health_json_contains_modes(self, client):
        data = client.get("/health").get_json()
        assert "modes" in data
        for mode in ["pentest", "soc", "auto", "code", "ciso", "sigma", "yara", "ioc"]:
            assert mode in data["modes"]


# ── Message validation ────────────────────────────────────────────────────────

class TestMessageValidation:
    def test_chat_missing_message_returns_400(self, client):
        r = client.post("/v1/chat", json={})
        assert r.status_code == 400
        assert "message required" in r.get_json()["error"]

    def test_ask_missing_question_returns_400(self, client):
        r = client.post("/v1/ask", json={})
        assert r.status_code == 400

    def test_triage_missing_alert_returns_400(self, client):
        r = client.post("/v1/triage", json={})
        assert r.status_code == 400

    def test_hunt_missing_target_returns_400(self, client):
        r = client.post("/v1/hunt", json={})
        assert r.status_code == 400

    def test_respond_missing_incident_returns_400(self, client):
        r = client.post("/v1/respond", json={})
        assert r.status_code == 400

    def test_code_missing_task_returns_400(self, client):
        r = client.post("/v1/code", json={})
        assert r.status_code == 400

    def test_sigma_missing_description_returns_400(self, client):
        r = client.post("/v1/sigma", json={})
        assert r.status_code == 400

    def test_yara_missing_description_returns_400(self, client):
        r = client.post("/v1/yara", json={})
        assert r.status_code == 400

    def test_ioc_missing_indicator_returns_400(self, client):
        r = client.post("/v1/ioc", json={})
        assert r.status_code == 400

    def test_webhook_missing_alert_returns_400(self, client):
        r = client.post("/v1/webhook", json={})
        assert r.status_code == 400
        assert "alert required" in r.get_json()["error"]


# ── Mode validation ───────────────────────────────────────────────────────────

class TestModeValidation:
    def test_chat_invalid_mode_returns_400(self, client):
        r = client.post("/v1/chat", json={"message": "test", "mode": "invalid_mode"})
        assert r.status_code == 400
        assert "invalid mode" in r.get_json()["error"]

    def test_chat_valid_modes_succeed(self, client):
        for mode in ["pentest", "soc", "auto", "code", "ciso", "sigma", "yara", "ioc"]:
            r = client.post("/v1/chat", json={"message": "test", "mode": mode})
            assert r.status_code == 200, f"mode '{mode}' should return 200"


# ── Rate limiting enforcement ─────────────────────────────────────────────────

class TestRateLimiting:
    @pytest.fixture
    def limited_app(self):
        from unittest.mock import MagicMock, patch
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {"HANCOCK_RATE_LIMIT": "3"}):
            import hancock_agent
            import importlib
            importlib.reload(hancock_agent)
            flask_app = hancock_agent.build_app(mock_client, "model")
            flask_app.testing = True
            return flask_app

    def test_rate_limit_blocks_after_limit_exceeded(self, limited_app):
        c = limited_app.test_client()
        payload = json.dumps({"question": "test"})
        ct = "application/json"
        for _ in range(3):
            r = c.post("/v1/ask", data=payload, content_type=ct)
            assert r.status_code == 200
        r = c.post("/v1/ask", data=payload, content_type=ct)
        assert r.status_code == 429
        assert "Rate limit" in r.get_json()["error"]

    def test_rate_limit_headers_present(self, client):
        r = client.get("/health")
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers
        assert "X-RateLimit-Window" in r.headers


# ── Webhook signature validation ──────────────────────────────────────────────

class TestWebhookSignatureValidation:
    @pytest.fixture
    def hmac_app(self):
        from unittest.mock import MagicMock, patch
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Triage result."
        mock_client.chat.completions.create.return_value = mock_resp
        with patch("hancock_agent.OpenAI", return_value=mock_client):
            import hancock_agent
            flask_app = hancock_agent.build_app(mock_client, "model")
            flask_app.testing = True
            with patch.dict(os.environ, {"HANCOCK_WEBHOOK_SECRET": "test-secret"}):
                yield flask_app.test_client()

    def test_missing_signature_returns_401(self, hmac_app):
        r = hmac_app.post("/v1/webhook",
                          data=json.dumps({"alert": "test alert"}),
                          content_type="application/json")
        assert r.status_code == 401

    def test_invalid_signature_returns_401(self, hmac_app):
        r = hmac_app.post("/v1/webhook",
                          data=json.dumps({"alert": "test alert"}),
                          content_type="application/json",
                          headers={"X-Hancock-Signature": "sha256=invalidsig"})
        assert r.status_code == 401

    def test_valid_signature_succeeds(self, hmac_app):
        import hmac as _hmac, hashlib
        body = json.dumps({"alert": "test alert"}).encode()
        sig = "sha256=" + _hmac.new(b"test-secret", body, hashlib.sha256).hexdigest()
        r = hmac_app.post("/v1/webhook",
                          data=body,
                          content_type="application/json",
                          headers={"X-Hancock-Signature": sig})
        assert r.status_code == 200


# ── Metrics endpoint (Prometheus format) ─────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        r = client.get("/metrics")
        assert r.status_code == 200

    def test_metrics_prometheus_format(self, client):
        r = client.get("/metrics")
        assert b"hancock_requests_total" in r.data
        assert b"hancock_errors_total" in r.data

    def test_metrics_increments_on_request(self, client):
        client.post("/v1/ask",
                    data=json.dumps({"question": "test"}),
                    content_type="application/json")
        r = client.get("/metrics")
        text = r.data.decode()
        for line in text.splitlines():
            if line.startswith("hancock_requests_total "):
                assert int(line.split()[-1]) >= 1
                break


# ── Error response handling ───────────────────────────────────────────────────

class TestErrorResponseHandling:
    def test_empty_model_response_returns_502(self):
        from unittest.mock import MagicMock
        import hancock_agent
        empty_client = MagicMock()
        empty_resp = MagicMock()
        empty_resp.choices[0].message.content = ""
        empty_client.chat.completions.create.return_value = empty_resp
        flask_app = hancock_agent.build_app(empty_client, "model")
        flask_app.testing = True
        c = flask_app.test_client()

        endpoints = [
            ("/v1/chat",    {"message": "hello"}),
            ("/v1/ask",     {"question": "hello"}),
            ("/v1/triage",  {"alert": "suspicious login"}),
            ("/v1/hunt",    {"target": "lateral movement"}),
            ("/v1/respond", {"incident": "ransomware"}),
            ("/v1/code",    {"task": "write a YARA rule"}),
            ("/v1/ciso",    {"question": "What is NIST?"}),
            ("/v1/sigma",   {"description": "PowerShell encoded"}),
            ("/v1/yara",    {"description": "Emotet dropper"}),
            ("/v1/ioc",     {"indicator": "1.2.3.4"}),
        ]
        for path, payload in endpoints:
            r = c.post(path,
                       data=json.dumps(payload),
                       content_type="application/json")
            assert r.status_code == 502, \
                f"{path} should return 502 for empty model response, got {r.status_code}"
            assert "error" in r.get_json()
