"""
Pytest fixtures shared across all Hancock test modules.
"""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── OpenAI mock factory ───────────────────────────────────────────────────────

def make_mock_client(response_text: str = "Mocked Hancock response.") -> MagicMock:
    """Return a fully-configured mock OpenAI client."""
    mock_client = MagicMock()
    mock_resp   = MagicMock()
    mock_resp.choices[0].message.content = response_text
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_client


# ── Flask app fixture ─────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mock_openai_client() -> MagicMock:
    return make_mock_client()


@pytest.fixture(scope="session")
def app(mock_openai_client):
    import hancock_agent
    flask_app = hancock_agent.build_app(mock_openai_client, "test-model")
    flask_app.testing = True
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


# ── Authenticated client ──────────────────────────────────────────────────────

@pytest.fixture
def auth_headers():
    """Authorization header dict with a test API key."""
    return {"Authorization": "Bearer test-key-123"}


@pytest.fixture
def authed_client(app, monkeypatch):
    """Flask test client with API key auth pre-configured."""
    monkeypatch.setenv("HANCOCK_API_KEY", "test-key-123")
    # Re-build the app so the new env var is picked up
    import hancock_agent
    flask_app = hancock_agent.build_app(make_mock_client(), "test-model")
    flask_app.testing = True
    return flask_app.test_client()


# ── Helper to post JSON ───────────────────────────────────────────────────────

def post_json(client, url: str, payload: dict, headers: dict | None = None):
    return client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        headers=headers or {},
    )
