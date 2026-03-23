"""
Hancock — Integration tests for deployment health.

Verifies that the Flask app starts correctly and all endpoints are reachable
with proper responses.  Uses the mock backend so no real LLM is needed.

Run:
    pytest tests/test_integration_deployment.py -v
"""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="module")
def deploy_client():
    import hancock_agent
    mock_client = MagicMock()
    mock_resp   = MagicMock()
    mock_resp.choices[0].message.content = "Integration test response."
    mock_client.chat.completions.create.return_value = mock_resp

    app = hancock_agent.build_app(mock_client, "integration-test-model")
    app.testing = True
    return app.test_client()


def _post(client, url: str, body: dict):
    return client.post(url, data=json.dumps(body), content_type="application/json")


# ── Server startup verification ───────────────────────────────────────────────

class TestStartupVerification:
    def test_app_builds_without_error(self):
        """build_app() must succeed with a mock client."""
        import hancock_agent
        mock = MagicMock()
        mock.chat.completions.create.return_value = MagicMock()
        mock.chat.completions.create.return_value.choices[0].message.content = "ok"
        app = hancock_agent.build_app(mock, "test-model")
        assert app is not None

    def test_health_endpoint_returns_ok(self, deploy_client):
        r = deploy_client.get("/health")
        assert r.status_code == 200
        data = r.get_json()
        assert data["status"] == "ok"
        assert data["agent"]  == "Hancock"
        assert "model" in data

    def test_all_expected_endpoints_listed(self, deploy_client):
        data = deploy_client.get("/health").get_json()
        expected = [
            "/v1/chat", "/v1/ask", "/v1/triage", "/v1/hunt", "/v1/respond",
            "/v1/code", "/v1/ciso", "/v1/sigma", "/v1/yara", "/v1/ioc",
            "/v1/agents", "/v1/webhook", "/metrics",
        ]
        for ep in expected:
            assert ep in data["endpoints"], f"Endpoint {ep!r} missing from /health"


# ── Endpoint availability checks ──────────────────────────────────────────────

class TestEndpointAvailability:
    def test_metrics_endpoint(self, deploy_client):
        r = deploy_client.get("/metrics")
        assert r.status_code == 200
        assert b"hancock_requests_total" in r.data

    def test_agents_endpoint(self, deploy_client):
        r = deploy_client.get("/v1/agents")
        assert r.status_code == 200
        agents = r.get_json()["agents"]
        for mode in ["pentest", "soc", "auto", "code", "ciso", "sigma", "yara", "ioc"]:
            assert mode in agents

    def test_chat_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/chat", {"message": "test", "mode": "auto"})
        assert r.status_code == 200
        assert "response" in r.get_json()

    def test_ask_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/ask", {"question": "What is CVSS?"})
        assert r.status_code == 200
        assert "answer" in r.get_json()

    def test_triage_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/triage", {"alert": "Mimikatz on DC01"})
        assert r.status_code == 200
        assert "triage" in r.get_json()

    def test_hunt_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/hunt", {"target": "lateral movement"})
        assert r.status_code == 200
        assert "query" in r.get_json()

    def test_respond_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/respond", {"incident": "ransomware"})
        assert r.status_code == 200
        assert "playbook" in r.get_json()

    def test_code_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/code", {"task": "Write a port scanner"})
        assert r.status_code == 200
        assert "code" in r.get_json()

    def test_ciso_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/ciso", {"question": "What is DORA?"})
        assert r.status_code == 200
        assert "advice" in r.get_json()

    def test_sigma_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/sigma", {"description": "PowerShell encoded cmd"})
        assert r.status_code == 200
        assert "rule" in r.get_json()

    def test_yara_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/yara", {"description": "Mimikatz"})
        assert r.status_code == 200
        assert "rule" in r.get_json()

    def test_ioc_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/ioc", {"indicator": "185.220.101.1"})
        assert r.status_code == 200
        assert "report" in r.get_json()

    def test_webhook_endpoint(self, deploy_client):
        r = _post(deploy_client, "/v1/webhook",
                  {"alert": "Suspicious login", "source": "splunk", "severity": "high"})
        assert r.status_code == 200
        assert r.get_json()["status"] == "triaged"


# ── Error handling verification ───────────────────────────────────────────────

class TestErrorHandling:
    def test_missing_required_field_returns_400(self, deploy_client):
        endpoints_and_fields = [
            ("/v1/chat",    {}),
            ("/v1/ask",     {}),
            ("/v1/triage",  {}),
            ("/v1/hunt",    {}),
            ("/v1/respond", {}),
            ("/v1/code",    {}),
            ("/v1/ciso",    {}),
            ("/v1/sigma",   {}),
            ("/v1/yara",    {}),
            ("/v1/ioc",     {}),
            ("/v1/webhook", {}),
        ]
        for url, body in endpoints_and_fields:
            r = _post(deploy_client, url, body)
            assert r.status_code == 400, f"{url} should return 400 for empty body, got {r.status_code}"

    def test_rate_limit_headers_present(self, deploy_client):
        r = deploy_client.get("/health")
        assert "X-RateLimit-Limit"     in r.headers
        assert "X-RateLimit-Remaining" in r.headers
        assert "X-RateLimit-Window"    in r.headers
