#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Sandbox Runner — Secure Docker-based tool execution with least privilege.

Provides sandboxed execution of security tools with:
- Read-only root filesystem
- No new privileges
- All capabilities dropped
- Network isolation (default none)
- Resource limits (CPU, memory)
- Process isolation
"""
from __future__ import annotations
import subprocess
import shlex
import logging
from typing import Dict, Any, List
from .profiles import TOOL_PROFILES

logger = logging.getLogger(__name__)


def run_tool_safely(tool: str, args: List[str], kwargs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a tool in a sandboxed Docker container with strict security controls.

    Security features:
    - Read-only root filesystem (--read-only)
    - No new privileges (--security-opt no-new-privileges)
    - All capabilities dropped (--cap-drop ALL)
    - Network isolation (default --network none)
    - Resource limits (--cpus, --memory, --pids-limit)

    Args:
        tool: Tool name (must exist in TOOL_PROFILES)
        args: Command-line arguments for the tool
        kwargs: Additional options (currently unused)

    Returns:
        Dict with keys:
        - status: "ok", "blocked", or "error"
        - stdout: Tool output (last 20KB)
        - stderr: Error output (last 8KB)
        - rc: Return code (if status="ok")
        - reason: Error reason (if status="blocked" or "error")
    """
    # Check if tool is whitelisted
    prof = TOOL_PROFILES.get(tool)
    if not prof:
        logger.warning(f"Attempted to execute non-whitelisted tool: {tool}")
        return {
            "status": "blocked",
            "reason": "tool not whitelisted",
        }

    # Build Docker command with security controls
    docker_cmd = [
        "docker", "run", "--rm",
        "--network", prof["network"],
        "--cpus", prof.get("cpus", "1"),
        "--memory", prof.get("memory", "512m"),
        "--read-only",
        "--pids-limit", "128",
        "--security-opt", "no-new-privileges",
        "--cap-drop", "ALL",
    ]

    # Add volumes if specified
    for vol in prof.get("volumes", []):
        docker_cmd.extend(["-v", vol])

    # Add image
    docker_cmd.append(prof["image"])

    # Build tool command with shell quoting for safety
    tool_cmd = prof["entrypoint"]
    if args:
        tool_cmd += " " + " ".join(shlex.quote(str(a)) for a in args)

    # Add tool command to Docker command
    docker_cmd.extend(shlex.split(tool_cmd))

    # Execute with timeout
    timeout = prof.get("timeout", 120)
    try:
        logger.info(f"Executing sandboxed tool: {tool} with timeout {timeout}s")
        result = subprocess.run(
            docker_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "status": "ok",
            "stdout": result.stdout[-20000:],  # Last 20KB
            "stderr": result.stderr[-8000:],   # Last 8KB
            "rc": result.returncode,
        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Tool {tool} timed out after {timeout}s")
        return {
            "status": "error",
            "error": f"Tool timed out after {timeout}s",
        }
    except Exception as e:
        logger.error(f"Error executing tool {tool}: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }
