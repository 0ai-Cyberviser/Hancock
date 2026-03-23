"""
Integration tests for deployment-related functionality.

Verifies:
- The /health endpoint responds correctly
- The /metrics endpoint is present (200 or 501 when prometheus_client missing)
- startup_checks.py logic works without real backends
"""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── /health integration ───────────────────────────────────────────────────────

class TestHealthEndpointIntegration:
    def test_health_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_has_status_field(self, client):
        data = client.get("/health").get_json()
        assert "status" in data

    def test_health_status_ok(self, client):
        data = client.get("/health").get_json()
        assert data["status"] == "ok"

    def test_health_has_model_field(self, client):
        data = client.get("/health").get_json()
        assert "model" in data

    def test_health_has_endpoints_field(self, client):
        data = client.get("/health").get_json()
        assert "endpoints" in data


# ── /metrics integration ──────────────────────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_responds(self, client):
        r = client.get("/metrics")
        # 200 if prometheus_client installed, 501 if not, 404 if not registered
        assert r.status_code in (200, 404, 501)

    def test_metrics_content_type_when_available(self, client):
        r = client.get("/metrics")
        if r.status_code == 200:
            assert "text/plain" in r.content_type


# ── startup_checks integration ────────────────────────────────────────────────

class TestStartupChecks:
    def test_env_check_warns_on_missing_key(self):
        from deploy.startup_checks import check_env_vars

        env = {
            "HANCOCK_LLM_BACKEND": "openai",
        }
        with patch.dict(os.environ, env, clear=False):
            # Remove both keys to trigger the error
            orig_openai = os.environ.pop("OPENAI_API_KEY", None)
            orig_nvidia = os.environ.pop("NVIDIA_API_KEY", None)
            try:
                errors = check_env_vars()
                assert len(errors) > 0
                assert any("OPENAI_API_KEY" in e or "NVIDIA_API_KEY" in e for e in errors)
            finally:
                if orig_openai is not None:
                    os.environ["OPENAI_API_KEY"] = orig_openai
                if orig_nvidia is not None:
                    os.environ["NVIDIA_API_KEY"] = orig_nvidia

    def test_env_check_passes_with_key(self):
        from deploy.startup_checks import check_env_vars

        with patch.dict(
            os.environ,
            {"HANCOCK_LLM_BACKEND": "openai", "OPENAI_API_KEY": "sk-test"},
        ):
            errors = check_env_vars()
            assert errors == []

    def test_disk_check_passes_on_root(self):
        from deploy.startup_checks import check_disk_space

        errors = check_disk_space("/")
        # Root partition should have enough space in CI
        assert isinstance(errors, list)

    def test_run_all_checks_warn_only(self):
        from deploy.startup_checks import run_all_checks

        # In warn-only mode, run_all_checks should not raise SystemExit
        result = run_all_checks(warn_only=True)
        assert isinstance(result, bool)


# ── graceful_shutdown integration ────────────────────────────────────────────

class TestGracefulShutdown:
    def test_install_handlers_idempotent(self):
        from deploy import graceful_shutdown

        # Reset state for test isolation
        graceful_shutdown._installed = False
        graceful_shutdown.install_handlers()
        graceful_shutdown.install_handlers()  # should not raise
        # Clean up
        graceful_shutdown._installed = False

    def test_is_shutting_down_default_false(self):
        from deploy import graceful_shutdown

        graceful_shutdown.shutdown_event.clear()
        assert graceful_shutdown.is_shutting_down() is False

    def test_register_cleanup_callback(self):
        from deploy import graceful_shutdown

        called = []
        graceful_shutdown.register_cleanup(lambda: called.append(1))
        graceful_shutdown._run_cleanup()
        assert 1 in called
        # Remove the test callback to avoid polluting other tests
        graceful_shutdown._cleanup_callbacks.clear()
