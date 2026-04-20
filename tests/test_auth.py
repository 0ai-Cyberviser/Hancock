#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
"""Tests for security.auth module."""
import pytest
import os
from unittest.mock import Mock, patch
from security.auth import APIKeyAuth


class TestAPIKeyAuth:
    """Test API key authentication."""

    def test_auth_disabled_when_no_keys(self):
        """Test that auth is disabled when no keys are configured."""
        with patch.dict(os.environ, {"HANCOCK_API_KEYS": ""}, clear=False):
            auth = APIKeyAuth()
            assert not auth.enabled
            with patch("security.auth.request") as mock_request:
                mock_request.headers.get.return_value = ""
                valid, msg = auth.require_api_key()
                assert valid is True
                assert msg == ""

    def test_auth_valid_key(self):
        """Test that valid API key is accepted."""
        with patch.dict(os.environ, {"HANCOCK_API_KEYS": "test-key-123"}, clear=False):
            auth = APIKeyAuth()
            assert auth.enabled
            with patch("security.auth.request") as mock_request:
                mock_request.headers.get.return_value = "test-key-123"
                valid, msg = auth.require_api_key()
                assert valid is True
                assert msg == ""

    def test_auth_invalid_key(self):
        """Test that invalid API key is rejected."""
        with patch.dict(os.environ, {"HANCOCK_API_KEYS": "test-key-123"}, clear=False):
            auth = APIKeyAuth()
            with patch("security.auth.request") as mock_request:
                mock_request.headers.get.return_value = "wrong-key"
                valid, msg = auth.require_api_key()
                assert valid is False
                assert "Invalid API key" in msg

    def test_auth_missing_header(self):
        """Test that missing API key header is rejected."""
        with patch.dict(os.environ, {"HANCOCK_API_KEYS": "test-key-123"}, clear=False):
            auth = APIKeyAuth()
            with patch("security.auth.request") as mock_request:
                mock_request.headers.get.return_value = ""
                valid, msg = auth.require_api_key()
                assert valid is False
                assert "Missing X-API-Key" in msg

    def test_auth_multiple_keys(self):
        """Test that multiple comma-separated keys work."""
        with patch.dict(os.environ, {"HANCOCK_API_KEYS": "key1,key2,key3"}, clear=False):
            auth = APIKeyAuth()
            assert auth.enabled
            assert len(auth.api_keys) == 3

            with patch("security.auth.request") as mock_request:
                # Test each key
                for key in ["key1", "key2", "key3"]:
                    mock_request.headers.get.return_value = key
                    valid, msg = auth.require_api_key()
                    assert valid is True
