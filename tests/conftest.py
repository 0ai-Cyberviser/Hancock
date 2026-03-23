"""
Shared pytest fixtures for the Hancock test suite.

Provides:
- A mock Flask app via ``build_app``
- A mock OpenAI client
- Temporary directory helpers
"""
from __future__ import annotations

import os
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def mock_openai_client():
    """A session-scoped mock OpenAI client that returns a canned response."""
    client = MagicMock()
    response = MagicMock()
    response.choices[0].message.content = "Mocked Hancock response for testing."
    client.chat.completions.create.return_value = response
    return client


@pytest.fixture
def flask_app(mock_openai_client):
    """
    A function-scoped Flask test application.

    Builds the Hancock Flask app with the mocked OpenAI client so
    tests do not make real API calls.
    """
    import hancock_agent
    app = hancock_agent.build_app(
        mock_openai_client,
        "mistralai/mistral-7b-instruct-v0.3",
    )
    app.testing = True
    return app


@pytest.fixture
def client(flask_app):
    """Return a Flask test client for the mocked app."""
    return flask_app.test_client()


@pytest.fixture
def tmp_data_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
