#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Rate Limiting Module — Simple in-memory rate limiter for Flask.
"""
from __future__ import annotations
import time
import threading
from flask import request
from typing import Dict, List


class SimpleRateLimiter:
    """
    Simple in-memory rate limiter for Flask endpoints.
    Tracks requests per IP address with sliding window.
    """

    def __init__(self, limit_per_minute: int = 30, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            limit_per_minute: Maximum requests per window
            window_seconds: Time window in seconds (default 60)
        """
        self.limit = limit_per_minute
        self.window = window_seconds
        self._counts: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def check_rate_limit(self) -> tuple[bool, int]:
        """
        Check if the current request exceeds rate limit.

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        now = time.time()
        ip = request.remote_addr or "unknown"

        with self._lock:
            # Get timestamps for this IP
            timestamps = self._counts.get(ip, [])

            # Remove expired timestamps
            timestamps = [t for t in timestamps if now - t < self.window]

            # Check if limit exceeded
            if len(timestamps) >= self.limit:
                return False, 0

            # Add current timestamp
            timestamps.append(now)
            self._counts[ip] = timestamps

            # Clean up old IPs periodically
            if len(self._counts) > 10000:
                self._cleanup_stale_ips(now)

            remaining = max(0, self.limit - len(timestamps))
            return True, remaining

    def _cleanup_stale_ips(self, now: float) -> None:
        """Remove IPs with no recent requests (internal use)."""
        stale = [
            ip for ip, timestamps in self._counts.items()
            if not timestamps or now - timestamps[-1] > 3600
        ]
        for ip in stale:
            del self._counts[ip]
