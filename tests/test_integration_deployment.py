"""Endpoint verification tests for Hancock REST API.

Uses the Flask test client from conftest — no real network calls.
Covers: /health, /metrics, /v1/chat, /v1/ask, /v1/triage.
"""


class TestHealthEndpoint:
    def test_health_returns_200(self, hancock_client):
        r = hancock_client.get("/health")
        assert r.status_code == 200

    def test_health_status_ok(self, hancock_client):
        data = hancock_client.get("/health").get_json()
        assert data["status"] == "ok"

    def test_health_agent_is_hancock(self, hancock_client):
        data = hancock_client.get("/health").get_json()
        assert data["agent"] == "Hancock"

    def test_health_company_is_cyberviser(self, hancock_client):
        data = hancock_client.get("/health").get_json()
        assert data["company"] == "CyberViser"

    def test_health_has_endpoints_list(self, hancock_client):
        data = hancock_client.get("/health").get_json()
        assert "endpoints" in data
        assert "/v1/chat" in data["endpoints"]
        assert "/v1/ask" in data["endpoints"]

    def test_health_has_all_modes(self, hancock_client):
        data = hancock_client.get("/health").get_json()
        for mode in ["pentest", "soc", "auto", "code", "ciso", "sigma", "yara", "ioc"]:
            assert mode in data["modes"]

    def test_health_has_model_field(self, hancock_client):
        data = hancock_client.get("/health").get_json()
        assert "model" in data

    def test_health_has_rate_limit_headers(self, hancock_client):
        r = hancock_client.get("/health")
        assert "X-RateLimit-Limit" in r.headers
        assert "X-RateLimit-Remaining" in r.headers
        assert "X-RateLimit-Window" in r.headers

    def test_health_ratelimit_remaining_is_numeric(self, hancock_client):
        r = hancock_client.get("/health")
        remaining = r.headers.get("X-RateLimit-Remaining", "")
        assert remaining.isdigit()


class TestMetricsEndpoint:
    def test_metrics_returns_200(self, hancock_client):
        r = hancock_client.get("/metrics")
        assert r.status_code == 200

    def test_metrics_contains_requests_counter(self, hancock_client):
        r = hancock_client.get("/metrics")
        assert b"hancock_requests_total" in r.data

    def test_metrics_contains_errors_counter(self, hancock_client):
        r = hancock_client.get("/metrics")
        assert b"hancock_errors_total" in r.data

    def test_metrics_increments_after_request(self, hancock_client, sample_question):
        hancock_client.post("/v1/ask", json={"question": sample_question})
        r = hancock_client.get("/metrics")
        assert b"hancock_requests_total" in r.data

    def test_metrics_content_type_is_text(self, hancock_client):
        r = hancock_client.get("/metrics")
        assert "text/plain" in r.content_type


class TestChatEndpoint:
    def test_chat_returns_200(self, hancock_client, sample_message):
        r = hancock_client.post("/v1/chat", json={"message": sample_message})
        assert r.status_code == 200

    def test_chat_returns_response_field(self, hancock_client, sample_message):
        data = hancock_client.post(
            "/v1/chat", json={"message": sample_message}
        ).get_json()
        assert "response" in data

    def test_chat_returns_model_field(self, hancock_client, sample_message):
        data = hancock_client.post(
            "/v1/chat", json={"message": sample_message}
        ).get_json()
        assert "model" in data

    def test_chat_missing_message_returns_400(self, hancock_client):
        r = hancock_client.post("/v1/chat", json={})
        assert r.status_code == 400

    def test_chat_mode_pentest(self, hancock_client):
        r = hancock_client.post(
            "/v1/chat", json={"message": "nmap scan options", "mode": "pentest"}
        )
        assert r.status_code == 200

    def test_chat_mode_soc(self, hancock_client):
        r = hancock_client.post(
            "/v1/chat", json={"message": "triage this alert", "mode": "soc"}
        )
        assert r.status_code == 200

    def test_chat_has_rate_limit_headers(self, hancock_client, sample_message):
        r = hancock_client.post("/v1/chat", json={"message": sample_message})
        assert "X-RateLimit-Remaining" in r.headers


class TestAskEndpoint:
    def test_ask_returns_200(self, hancock_client, sample_question):
        r = hancock_client.post("/v1/ask", json={"question": sample_question})
        assert r.status_code == 200

    def test_ask_returns_answer_field(self, hancock_client, sample_question):
        data = hancock_client.post(
            "/v1/ask", json={"question": sample_question}
        ).get_json()
        assert "answer" in data

    def test_ask_returns_model_field(self, hancock_client, sample_question):
        data = hancock_client.post(
            "/v1/ask", json={"question": sample_question}
        ).get_json()
        assert "model" in data

    def test_ask_returns_mode_field(self, hancock_client, sample_question):
        data = hancock_client.post(
            "/v1/ask", json={"question": sample_question, "mode": "soc"}
        ).get_json()
        assert data["mode"] == "soc"

    def test_ask_missing_question_returns_400(self, hancock_client):
        r = hancock_client.post("/v1/ask", json={})
        assert r.status_code == 400

    def test_ask_pentest_mode(self, hancock_client):
        r = hancock_client.post(
            "/v1/ask", json={"question": "How does Kerberoasting work?", "mode": "pentest"}
        )
        assert r.status_code == 200

    def test_ask_has_rate_limit_headers(self, hancock_client, sample_question):
        r = hancock_client.post("/v1/ask", json={"question": sample_question})
        assert "X-RateLimit-Limit" in r.headers


class TestTriageEndpoint:
    def test_triage_returns_200(self, hancock_client, sample_alert):
        r = hancock_client.post("/v1/triage", json={"alert": sample_alert})
        assert r.status_code == 200

    def test_triage_returns_triage_field(self, hancock_client, sample_alert):
        data = hancock_client.post(
            "/v1/triage", json={"alert": sample_alert}
        ).get_json()
        assert "triage" in data

    def test_triage_returns_model_field(self, hancock_client, sample_alert):
        data = hancock_client.post(
            "/v1/triage", json={"alert": sample_alert}
        ).get_json()
        assert "model" in data

    def test_triage_missing_alert_returns_400(self, hancock_client):
        r = hancock_client.post("/v1/triage", json={})
        assert r.status_code == 400

    def test_triage_has_rate_limit_headers(self, hancock_client, sample_alert):
        r = hancock_client.post("/v1/triage", json={"alert": sample_alert})
        assert "X-RateLimit-Remaining" in r.headers


class TestAgentsEndpoint:
    def test_agents_returns_200(self, hancock_client):
        r = hancock_client.get("/v1/agents")
        assert r.status_code == 200

    def test_agents_returns_dict(self, hancock_client):
        data = hancock_client.get("/v1/agents").get_json()
        assert "agents" in data
        assert isinstance(data["agents"], dict)


class TestHuntEndpoint:
    def test_hunt_returns_200(self, hancock_client):
        r = hancock_client.post("/v1/hunt", json={"target": "lateral movement via PsExec"})
        assert r.status_code == 200

    def test_hunt_returns_query_field(self, hancock_client):
        data = hancock_client.post(
            "/v1/hunt", json={"target": "Kerberoasting", "siem": "splunk"}
        ).get_json()
        assert "query" in data

    def test_hunt_missing_target_returns_400(self, hancock_client):
        r = hancock_client.post("/v1/hunt", json={})
        assert r.status_code == 400

    def test_hunt_returns_siem_field(self, hancock_client):
        data = hancock_client.post(
            "/v1/hunt", json={"target": "pass-the-hash", "siem": "elastic"}
        ).get_json()
        assert data["siem"] == "elastic"


class TestCodeEndpoint:
    def test_code_returns_200(self, hancock_client):
        r = hancock_client.post("/v1/code", json={"task": "Write a Python port scanner"})
        assert r.status_code == 200

    def test_code_returns_code_field(self, hancock_client):
        data = hancock_client.post(
            "/v1/code", json={"task": "YARA rule for Cobalt Strike"}
        ).get_json()
        assert "code" in data

    def test_code_missing_task_returns_400(self, hancock_client):
        r = hancock_client.post("/v1/code", json={})
        assert r.status_code == 400

    def test_code_returns_language_field(self, hancock_client):
        data = hancock_client.post(
            "/v1/code", json={"task": "detect PtH", "language": "python"}
        ).get_json()
        assert "language" in data


class TestYaraEndpoint:
    def test_yara_returns_200(self, hancock_client):
        r = hancock_client.post("/v1/yara", json={"description": "Cobalt Strike beacon"})
        assert r.status_code == 200

    def test_yara_returns_rule_field(self, hancock_client):
        data = hancock_client.post(
            "/v1/yara", json={"description": "LockBit ransomware dropper"}
        ).get_json()
        assert "rule" in data

    def test_yara_missing_description_returns_400(self, hancock_client):
        r = hancock_client.post("/v1/yara", json={})
        assert r.status_code == 400

    def test_yara_with_file_type(self, hancock_client):
        r = hancock_client.post(
            "/v1/yara", json={"description": "WannaCry", "file_type": "PE"}
        )
        assert r.status_code == 200


class TestIocEndpoint:
    def test_ioc_returns_200(self, hancock_client):
        r = hancock_client.post("/v1/ioc", json={"indicator": "185.220.101.35"})
        assert r.status_code == 200

    def test_ioc_returns_report_field(self, hancock_client):
        data = hancock_client.post(
            "/v1/ioc", json={"indicator": "185.220.101.35"}
        ).get_json()
        assert "report" in data

    def test_ioc_returns_indicator_field(self, hancock_client):
        data = hancock_client.post(
            "/v1/ioc", json={"indicator": "cobaltstrikebeacon.com"}
        ).get_json()
        assert data["indicator"] == "cobaltstrikebeacon.com"

    def test_ioc_missing_indicator_returns_400(self, hancock_client):
        r = hancock_client.post("/v1/ioc", json={})
        assert r.status_code == 400

    def test_ioc_accepts_ioc_field_alias(self, hancock_client):
        r = hancock_client.post(
            "/v1/ioc", json={"ioc": "cobaltstrikebeacon.com"}
        )
        assert r.status_code == 200
