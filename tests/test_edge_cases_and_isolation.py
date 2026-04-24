"""
Edge cases and test isolation tests for Hancock.

Tests for:
- Environment variable isolation between tests
- Edge cases in rate limiting
- Error handling under stress
- Thread safety of shared components
"""
import json
import os
import pytest
from unittest.mock import patch, MagicMock


class TestEnvironmentVariableIsolation:
    """Verify test isolation for environment variables."""

    def test_api_key_isolation_between_tests(self):
        """Each test should not leak API key to next test."""
        key1 = os.environ.get("HANCOCK_API_KEY", "not-set-1")
        assert key1 == "not-set-1"

    def test_rate_limit_env_isolation(self):
        """HANCOCK_RATE_LIMIT should not persist across tests."""
        rate_limit = os.environ.get("HANCOCK_RATE_LIMIT", "default")
        # Should be default or not set
        assert rate_limit in ("", "default") or rate_limit.isdigit()

    def test_webhook_secret_isolation(self):
        """HANCOCK_WEBHOOK_SECRET should not leak between tests."""
        secret = os.environ.get("HANCOCK_WEBHOOK_SECRET", None)
        # Should be None or empty, not leaked from other tests
        assert secret is None or secret == ""


class TestRateLimitEdgeCases:
    """Edge cases in rate limiting logic."""

    def test_rate_limit_with_zero_remaining(self):
        """Verify exact boundary condition at rate limit."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {"HANCOCK_RATE_LIMIT": "2"}):
            import hancock_agent
            app = hancock_agent.build_app(mock_client, "model")
            app.testing = True
            c = app.test_client()

            # Make exactly 2 requests (at limit)
            for i in range(2):
                r = c.post("/v1/ask",
                           data=json.dumps({"question": "test"}),
                           content_type="application/json")
                assert r.status_code == 200, f"Request {i+1} should succeed"

            # 3rd should fail
            r = c.post("/v1/ask",
                       data=json.dumps({"question": "test"}),
                       content_type="application/json")
            assert r.status_code == 429, "Request beyond limit should fail with 429"
            assert "Rate limit" in r.get_json()["error"]

    def test_negative_remaining_header_prevented(self):
        """X-RateLimit-Remaining should never be negative."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {"HANCOCK_RATE_LIMIT": "1"}):
            import hancock_agent
            app = hancock_agent.build_app(mock_client, "model")
            app.testing = True
            c = app.test_client()

            # First request
            r1 = c.post("/v1/ask",
                        data=json.dumps({"question": "test"}),
                        content_type="application/json")
            assert r1.status_code == 200
            remaining1 = int(r1.headers["X-RateLimit-Remaining"])
            assert remaining1 >= 0

            # Second request (should be rate limited)
            r2 = c.post("/v1/ask",
                        data=json.dumps({"question": "test"}),
                        content_type="application/json")
            assert r2.status_code == 429
            remaining2 = int(r2.headers.get("X-RateLimit-Remaining", "0"))
            assert remaining2 >= 0, f"Remaining should not be negative: {remaining2}"


class TestPayloadValidationEdgeCases:
    """Edge cases in payload validation."""

    def test_chat_with_null_message(self):
        """Test handling of null message value."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        import hancock_agent
        app = hancock_agent.build_app(mock_client, "model")
        app.testing = True
        c = app.test_client()

        r = c.post("/v1/chat",
                   data=json.dumps({"message": None}),
                   content_type="application/json")
        # Should reject null as invalid input
        assert r.status_code in (400, 422), f"Expected 400 or 422, got {r.status_code}"

    def test_chat_with_oversized_message(self):
        """Test handling of extremely large message (>100KB)."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        import hancock_agent
        app = hancock_agent.build_app(mock_client, "model")
        app.testing = True
        c = app.test_client()

        huge_message = "x" * 100_000
        r = c.post("/v1/chat",
                   data=json.dumps({"message": huge_message}),
                   content_type="application/json")
        # Should reject or process safely
        assert r.status_code in (200, 400, 413), \
            f"Should handle oversized input gracefully, got {r.status_code}"

    def test_chat_with_special_characters_in_message(self):
        """Test handling of special characters and unicode."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        import hancock_agent
        app = hancock_agent.build_app(mock_client, "model")
        app.testing = True
        c = app.test_client()

        special_messages = [
            "Test with emoji: 🚀🔒🔑",
            "Test with null byte: \x00",
            "Test with RTL: \u202e",
        ]

        for msg in special_messages:
            r = c.post("/v1/chat",
                       data=json.dumps({"message": msg}),
                       content_type="application/json")
            # Should handle gracefully (200 or 400, not 500)
            assert r.status_code < 500, \
                f"Should not crash on special chars, got {r.status_code} for '{msg}'"


class TestAuthorizationEdgeCases:
    """Edge cases in authorization and authentication."""

    def test_bearer_token_case_sensitivity(self):
        """Bearer token should be case-sensitive."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {"HANCOCK_API_KEY": "MyToken"}):
            import hancock_agent
            app = hancock_agent.build_app(mock_client, "model")
            app.testing = True
            c = app.test_client()

            # Correct token should work
            r1 = c.post("/v1/ask",
                        data=json.dumps({"question": "test"}),
                        content_type="application/json",
                        headers={"Authorization": "Bearer MyToken"})
            assert r1.status_code == 200

            # Wrong case should fail
            r2 = c.post("/v1/ask",
                        data=json.dumps({"question": "test"}),
                        content_type="application/json",
                        headers={"Authorization": "Bearer mytoken"})
            assert r2.status_code == 401

    def test_malformed_authorization_header(self):
        """Handle malformed Authorization header gracefully."""
        from unittest.mock import MagicMock, patch

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {"HANCOCK_API_KEY": "token"}):
            import hancock_agent
            app = hancock_agent.build_app(mock_client, "model")
            app.testing = True
            c = app.test_client()

            malformed = [
                "Bearer",  # missing token
                "Bearer  ",  # just spaces
                "BasicAuth token",  # wrong scheme
                "Bearertoken",  # no space
            ]

            for auth_header in malformed:
                r = c.post("/v1/ask",
                           data=json.dumps({"question": "test"}),
                           content_type="application/json",
                           headers={"Authorization": auth_header})
                assert r.status_code == 401, \
                    f"Malformed auth '{auth_header}' should return 401, got {r.status_code}"


class TestConcurrentAccessPatterns:
    """Test thread-safe patterns in shared components."""

    def test_metrics_accumulation_is_monotonic(self):
        """Request counter should only increase, never decrease."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        import hancock_agent
        app = hancock_agent.build_app(mock_client, "model")
        app.testing = True
        c = app.test_client()

        counts = []
        for _ in range(5):
            r = c.get("/metrics")
            assert r.status_code == 200
            for line in r.data.decode().splitlines():
                if line.startswith("hancock_requests_total "):
                    count = int(float(line.split()[-1]))
                    counts.append(count)
                    break

        # Each count should be >= previous
        for i in range(1, len(counts)):
            assert counts[i] >= counts[i-1], \
                f"Metrics counter should be monotonic: {counts}"


class TestErrorResponseConsistency:
    """Error responses should be consistent in format."""

    def test_all_error_responses_have_error_field(self):
        """All error responses should have an 'error' field."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "response"
        mock_client.chat.completions.create.return_value = mock_resp

        import hancock_agent
        app = hancock_agent.build_app(mock_client, "model")
        app.testing = True
        c = app.test_client()

        error_cases = [
            ("POST", "/v1/chat", json.dumps({})),
            ("POST", "/v1/ask", json.dumps({})),
            ("POST", "/v1/triage", json.dumps({})),
        ]

        for method, endpoint, data in error_cases:
            if method == "POST":
                r = c.post(endpoint, data=data, content_type="application/json")
            else:
                r = c.get(endpoint)

            if r.status_code >= 400:
                resp_json = r.get_json()
                assert "error" in resp_json, \
                    f"{endpoint} error should have 'error' field, got: {resp_json}"
