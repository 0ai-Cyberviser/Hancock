"""Tests for the auth module and JWT authentication endpoints."""
from __future__ import annotations

import json
import time

import pytest


# ── Unit tests for auth.py ───────────────────────────────────────────────────


class TestRole:
    def test_role_values(self):
        from auth import Role
        assert Role.ADMIN.value == "admin"
        assert Role.ANALYST.value == "analyst"
        assert Role.READONLY.value == "readonly"

    def test_all_roles(self):
        from auth import ALL_ROLES
        assert "admin" in ALL_ROLES
        assert "analyst" in ALL_ROLES
        assert "readonly" in ALL_ROLES


class TestTokenManager:
    @pytest.fixture
    def mgr(self):
        from auth import TokenManager
        return TokenManager(secret="test-jwt-secret-key-for-testing!!", default_ttl=60)

    @pytest.fixture
    def disabled_mgr(self):
        from auth import TokenManager
        return TokenManager(secret="")

    def test_enabled_with_secret(self, mgr):
        assert mgr.enabled is True

    def test_disabled_without_secret(self, disabled_mgr):
        assert disabled_mgr.enabled is False

    def test_issue_and_verify_token(self, mgr):
        from auth import Role
        token = mgr.issue_token("test-user", Role.ANALYST)
        assert isinstance(token, str)
        payload = mgr.verify_token(token)
        assert payload["sub"] == "test-user"
        assert payload["role"] == "analyst"
        assert payload["type"] == "access"
        assert payload["iss"] == "hancock"

    def test_issue_admin_token(self, mgr):
        from auth import Role
        token = mgr.issue_token("admin-user", Role.ADMIN)
        payload = mgr.verify_token(token)
        assert payload["role"] == "admin"

    def test_issue_readonly_token(self, mgr):
        from auth import Role
        token = mgr.issue_token("reader", Role.READONLY)
        payload = mgr.verify_token(token)
        assert payload["role"] == "readonly"

    def test_expired_token_raises(self, mgr):
        from auth import Role
        token = mgr.issue_token("user", Role.ANALYST, ttl=-1)
        with pytest.raises(ValueError, match="Token expired"):
            mgr.verify_token(token)

    def test_wrong_secret_raises(self):
        from auth import TokenManager, Role
        mgr1 = TokenManager(secret="secret-one-that-is-32-chars-long")
        mgr2 = TokenManager(secret="secret-two-that-is-32-chars-long")
        token = mgr1.issue_token("user", Role.ANALYST)
        with pytest.raises(ValueError, match="Invalid token"):
            mgr2.verify_token(token)

    def test_issue_refresh_token(self, mgr):
        from auth import Role
        token = mgr.issue_refresh_token("user", Role.ANALYST)
        payload = mgr.verify_token(token, expected_type="refresh")
        assert payload["type"] == "refresh"
        assert payload["sub"] == "user"

    def test_verify_access_rejects_refresh(self, mgr):
        from auth import Role
        refresh = mgr.issue_refresh_token("user", Role.ANALYST)
        with pytest.raises(ValueError, match="Wrong token type"):
            mgr.verify_token(refresh, expected_type="access")

    def test_refresh_flow(self, mgr):
        from auth import Role
        refresh = mgr.issue_refresh_token("user", Role.ANALYST)
        result = mgr.refresh(refresh)
        assert "access_token" in result
        assert "refresh_token" in result
        assert result["token_type"] == "Bearer"
        assert result["expires_in"] == 60
        # New access token should be valid
        payload = mgr.verify_token(result["access_token"])
        assert payload["sub"] == "user"

    def test_refresh_rejects_access_token(self, mgr):
        from auth import Role
        access = mgr.issue_token("user", Role.ANALYST)
        with pytest.raises(ValueError, match="Wrong token type"):
            mgr.refresh(access)

    def test_disabled_mgr_issue_raises(self, disabled_mgr):
        from auth import Role
        with pytest.raises(RuntimeError, match="JWT not available"):
            disabled_mgr.issue_token("user", Role.ANALYST)

    def test_disabled_mgr_verify_raises(self, disabled_mgr):
        with pytest.raises(RuntimeError, match="JWT not available"):
            disabled_mgr.verify_token("some-token")

    def test_token_has_exp_claim(self, mgr):
        from auth import Role
        token = mgr.issue_token("user", Role.ANALYST, ttl=120)
        payload = mgr.verify_token(token)
        assert payload["exp"] > payload["iat"]
        assert payload["exp"] - payload["iat"] == 120


class TestAuthAuditor:
    def test_log_success(self, caplog):
        import logging
        from auth import AuthAuditor
        auditor = AuthAuditor()
        with caplog.at_level(logging.INFO, logger="hancock.auth"):
            auditor.log_auth_event(
                "success", ip="10.0.0.1", subject="admin",
                method="jwt", endpoint="/v1/chat",
            )
        assert "AUTH SUCCESS" in caplog.text

    def test_log_failure(self, caplog):
        import logging
        from auth import AuthAuditor
        auditor = AuthAuditor()
        with caplog.at_level(logging.WARNING, logger="hancock.auth"):
            auditor.log_auth_event(
                "failure", ip="10.0.0.1", method="bearer",
                endpoint="/v1/chat", reason="Invalid token",
            )
        assert "AUTH FAILURE" in caplog.text


class TestBearerTokenCheck:
    def test_valid_bearer(self):
        from auth import check_bearer_token
        assert check_bearer_token("Bearer my-secret", "my-secret") is True

    def test_invalid_bearer(self):
        from auth import check_bearer_token
        assert check_bearer_token("Bearer wrong", "my-secret") is False

    def test_no_prefix(self):
        from auth import check_bearer_token
        assert check_bearer_token("my-secret", "my-secret") is True

    def test_empty_header(self):
        from auth import check_bearer_token
        assert check_bearer_token("", "my-secret") is False


class TestWebhookSignature:
    def test_valid_signature(self):
        import hmac
        import hashlib
        from auth import check_webhook_signature
        secret = "webhook-secret"
        body = b'{"alert":"test"}'
        sig = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        assert check_webhook_signature(body, sig, secret) is True

    def test_invalid_signature(self):
        from auth import check_webhook_signature
        assert check_webhook_signature(b"body", "sha256=wrong", "secret") is False

    def test_empty_secret_skips_check(self):
        from auth import check_webhook_signature
        assert check_webhook_signature(b"body", "", "") is True


# ── Integration tests for auth API endpoints ──────────────────────────────────


class TestAuthEndpoints:
    @pytest.fixture
    def jwt_app(self):
        """App with both API key and JWT secret configured."""
        from unittest.mock import MagicMock, patch
        import os

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Secured response."
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {
            "HANCOCK_API_KEY": "test-api-key",
            "HANCOCK_JWT_SECRET": "test-jwt-secret-for-integration!",
        }):
            with patch("hancock_agent.OpenAI", return_value=mock_client):
                import hancock_agent
                import importlib
                importlib.reload(hancock_agent)
                app = hancock_agent.build_app(
                    mock_client, "mistralai/mistral-7b-instruct-v0.3"
                )
                app.testing = True
                return app

    def test_issue_token(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "test-user", "role": "analyst"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-api-key"},
        )
        assert r.status_code == 200
        data = r.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] > 0

    def test_issue_token_without_api_key_returns_401(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "user", "role": "analyst"}),
            content_type="application/json",
        )
        assert r.status_code == 401

    def test_issue_token_wrong_api_key_returns_401(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "user", "role": "analyst"}),
            content_type="application/json",
            headers={"Authorization": "Bearer wrong-key"},
        )
        assert r.status_code == 401

    def test_issue_token_missing_subject_returns_400(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"role": "analyst"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-api-key"},
        )
        assert r.status_code == 400
        assert "subject" in r.get_json()["error"]

    def test_issue_token_invalid_role_returns_400(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "user", "role": "superadmin"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-api-key"},
        )
        assert r.status_code == 400
        assert "invalid role" in r.get_json()["error"]

    def test_jwt_token_authenticates_api(self, jwt_app):
        """Full flow: get JWT token, then use it to access /v1/ask."""
        c = jwt_app.test_client()
        # Get JWT token
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "test-user", "role": "analyst"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-api-key"},
        )
        assert r.status_code == 200
        jwt_token = r.get_json()["access_token"]

        # Use JWT token to access API
        r = c.post(
            "/v1/ask",
            data=json.dumps({"question": "test"}),
            content_type="application/json",
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert r.status_code == 200

    def test_refresh_token_flow(self, jwt_app):
        c = jwt_app.test_client()
        # Get initial tokens
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "user", "role": "analyst"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-api-key"},
        )
        refresh_token = r.get_json()["refresh_token"]

        # Refresh
        r = c.post(
            "/v1/auth/refresh",
            data=json.dumps({"refresh_token": refresh_token}),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_missing_token_returns_400(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/refresh",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert r.status_code == 400

    def test_refresh_invalid_token_returns_401(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/refresh",
            data=json.dumps({"refresh_token": "invalid-jwt"}),
            content_type="application/json",
        )
        assert r.status_code == 401

    def test_validate_token(self, jwt_app):
        c = jwt_app.test_client()
        # Get token
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "user", "role": "admin"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-api-key"},
        )
        token = r.get_json()["access_token"]

        # Validate
        r = c.post(
            "/v1/auth/validate",
            data=json.dumps({"token": token}),
            content_type="application/json",
        )
        assert r.status_code == 200
        data = r.get_json()
        assert data["valid"] is True
        assert data["subject"] == "user"
        assert data["role"] == "admin"

    def test_validate_invalid_token_returns_401(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/validate",
            data=json.dumps({"token": "bad-token"}),
            content_type="application/json",
        )
        assert r.status_code == 401
        assert r.get_json()["valid"] is False

    def test_validate_missing_token_returns_400(self, jwt_app):
        c = jwt_app.test_client()
        r = c.post(
            "/v1/auth/validate",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert r.status_code == 400


class TestJWTDisabled:
    @pytest.fixture
    def no_jwt_app(self):
        """App with API key but no JWT secret."""
        from unittest.mock import MagicMock, patch
        import os

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Response."
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {
            "HANCOCK_API_KEY": "test-key",
            "HANCOCK_JWT_SECRET": "",
        }):
            with patch("hancock_agent.OpenAI", return_value=mock_client):
                import hancock_agent
                import importlib
                importlib.reload(hancock_agent)
                app = hancock_agent.build_app(
                    mock_client, "mistralai/mistral-7b-instruct-v0.3"
                )
                app.testing = True
                return app

    def test_auth_token_returns_501(self, no_jwt_app):
        c = no_jwt_app.test_client()
        r = c.post(
            "/v1/auth/token",
            data=json.dumps({"subject": "user"}),
            content_type="application/json",
            headers={"Authorization": "Bearer test-key"},
        )
        assert r.status_code == 501

    def test_auth_refresh_returns_501(self, no_jwt_app):
        c = no_jwt_app.test_client()
        r = c.post(
            "/v1/auth/refresh",
            data=json.dumps({"refresh_token": "tok"}),
            content_type="application/json",
        )
        assert r.status_code == 501

    def test_auth_validate_returns_501(self, no_jwt_app):
        c = no_jwt_app.test_client()
        r = c.post(
            "/v1/auth/validate",
            data=json.dumps({"token": "tok"}),
            content_type="application/json",
        )
        assert r.status_code == 501


class TestMetricsAuth:
    @pytest.fixture
    def metrics_auth_app(self):
        """App with metrics auth enabled."""
        from unittest.mock import MagicMock, patch
        import os

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Response."
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {
            "HANCOCK_API_KEY": "test-key",
            "HANCOCK_METRICS_AUTH": "true",
        }):
            with patch("hancock_agent.OpenAI", return_value=mock_client):
                import hancock_agent
                import importlib
                importlib.reload(hancock_agent)
                app = hancock_agent.build_app(
                    mock_client, "mistralai/mistral-7b-instruct-v0.3"
                )
                app.testing = True
                return app

    def test_metrics_requires_auth(self, metrics_auth_app):
        c = metrics_auth_app.test_client()
        r = c.get("/metrics")
        assert r.status_code == 401

    def test_metrics_with_valid_auth(self, metrics_auth_app):
        c = metrics_auth_app.test_client()
        r = c.get("/metrics", headers={"Authorization": "Bearer test-key"})
        assert r.status_code == 200


class TestHealthEndpointAuth:
    @pytest.fixture
    def auth_app(self):
        """App with both auth mechanisms."""
        from unittest.mock import MagicMock, patch
        import os

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Response."
        mock_client.chat.completions.create.return_value = mock_resp

        with patch.dict(os.environ, {
            "HANCOCK_API_KEY": "test-key",
            "HANCOCK_JWT_SECRET": "test-jwt-secret-at-least-32chars!",
        }):
            with patch("hancock_agent.OpenAI", return_value=mock_client):
                import hancock_agent
                import importlib
                importlib.reload(hancock_agent)
                app = hancock_agent.build_app(
                    mock_client, "mistralai/mistral-7b-instruct-v0.3"
                )
                app.testing = True
                return app

    def test_health_includes_auth_info(self, auth_app):
        c = auth_app.test_client()
        r = c.get("/health")
        assert r.status_code == 200
        data = r.get_json()
        assert "auth" in data
        assert data["auth"]["bearer_token"] is True
        assert data["auth"]["jwt"] is True
        assert "/v1/auth/token" in data["endpoints"]
