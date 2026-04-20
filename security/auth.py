#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Authentication Module — API key authentication for Flask.
"""
from __future__ import annotations
import hmac
import os
from flask import request


class APIKeyAuth:
    """
    Simple API key authentication for Flask endpoints.
    Reads API keys from HANCOCK_API_KEYS environment variable (comma-separated).
    """

    def __init__(self):
        """Initialize with API keys from environment."""
        keys_str = os.getenv("HANCOCK_API_KEYS", "")
        self.api_keys = {k.strip() for k in keys_str.split(",") if k.strip()}
        self.enabled = len(self.api_keys) > 0

    def require_api_key(self) -> tuple[bool, str]:
        """
        Check if request has a valid API key in X-API-Key header.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.enabled:
            # No API keys configured, allow all requests
            return True, ""

        api_key = request.headers.get("X-API-Key", "")
        if not api_key:
            return False, "Missing X-API-Key header"

        # Use constant-time comparison to prevent timing attacks
        for valid_key in self.api_keys:
            if hmac.compare_digest(api_key, valid_key):
                return True, ""

        return False, "Invalid API key"
