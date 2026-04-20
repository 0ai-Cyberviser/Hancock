#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
"""Tests for sandbox.runner module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sandbox.runner import run_tool_safely
from sandbox.profiles import TOOL_PROFILES


class TestSandboxRunner:
    """Test sandboxed tool execution."""

    def test_blocked_tool(self):
        """Test that non-whitelisted tool is blocked."""
        result = run_tool_safely("unknown_tool", [], {})
        assert result["status"] == "blocked"
        assert "not whitelisted" in result["reason"]

    @patch("sandbox.runner.subprocess.run")
    def test_successful_execution(self, mock_run):
        """Test successful tool execution."""
        mock_run.return_value = Mock(
            stdout="nmap scan complete",
            stderr="",
            returncode=0
        )

        result = run_tool_safely("nmap", ["-V"], {})
        assert result["status"] == "ok"
        assert result["rc"] == 0
        assert "nmap scan complete" in result["stdout"]

    @patch("sandbox.runner.subprocess.run")
    def test_timeout_handling(self, mock_run):
        """Test timeout handling."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("docker", 90)

        result = run_tool_safely("nmap", ["-sV", "192.168.1.1"], {})
        assert result["status"] == "error"
        assert "timed out" in result["error"]

    @patch("sandbox.runner.subprocess.run")
    def test_execution_error(self, mock_run):
        """Test execution error handling."""
        mock_run.side_effect = Exception("Docker daemon not running")

        result = run_tool_safely("nmap", ["-V"], {})
        assert result["status"] == "error"
        assert "Docker daemon" in result["error"]

    @patch("sandbox.runner.subprocess.run")
    def test_security_flags(self, mock_run):
        """Test that security flags are properly applied."""
        mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

        run_tool_safely("nmap", ["-V"], {})

        # Verify subprocess.run was called
        assert mock_run.called
        call_args = mock_run.call_args[0][0]

        # Check for security flags
        assert "--read-only" in call_args
        assert "--cap-drop" in call_args
        assert "ALL" in call_args
        assert "--security-opt" in call_args
        assert "no-new-privileges" in call_args

    @patch("sandbox.runner.subprocess.run")
    def test_network_isolation(self, mock_run):
        """Test that network isolation is enforced."""
        mock_run.return_value = Mock(stdout="", stderr="", returncode=0)

        run_tool_safely("nmap", [], {})

        call_args = mock_run.call_args[0][0]
        assert "--network" in call_args
        # Check that "none" appears after "--network"
        network_idx = call_args.index("--network")
        assert call_args[network_idx + 1] == "none"

    def test_all_whitelisted_tools(self):
        """Test that all whitelisted tools have valid profiles."""
        for tool_name in TOOL_PROFILES:
            profile = TOOL_PROFILES[tool_name]
            assert "image" in profile
            assert "entrypoint" in profile
            assert "network" in profile
            assert "timeout" in profile
            assert profile["timeout"] > 0
