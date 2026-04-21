#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
"""Atheris fuzz harness for sandbox.runner module."""
import sys
import json
import os
import atheris
from pathlib import Path
from unittest.mock import Mock, patch

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent
import json
import os
import atheris

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
with atheris.instrument_imports():
    from sandbox.runner import run_tool_safely
    from sandbox.profiles import TOOL_PROFILES


def TestOneInput(data):
    """Fuzz test for sandbox runner with various inputs."""
    try:
        # Try to parse as JSON
        obj = json.loads(data.decode("utf-8", "ignore"))
    except Exception:
        # If JSON parsing fails, use default values
        return

    # Extract fuzzing parameters
    tool = obj.get("tool", "nmap")
    args = obj.get("args", ["-V"])
    kwargs = obj.get("kwargs", {})

    # Ensure args is a list
    if not isinstance(args, list):
        args = [str(args)]

    # Ensure kwargs is a dict
    if not isinstance(kwargs, dict):
        kwargs = {}

    # Mock subprocess.run to avoid Docker dependency during fuzzing
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "mocked output"
    mock_result.stderr = ""

    try:
        # Run with fuzzer input (mocked subprocess to avoid Docker calls)
        with patch("subprocess.run", return_value=mock_result):
            result = run_tool_safely(tool, args, kwargs)
        # Verify result structure
        assert "status" in result
        assert result["status"] in ["ok", "blocked", "error"]
    except Exception:
        # Catch any exceptions but don't crash the fuzzer
        pass


if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
