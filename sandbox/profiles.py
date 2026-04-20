#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Sandbox Tool Profiles — Security profiles for Docker-based tool execution.
"""
from __future__ import annotations
from typing import Dict, List, Any

# Tool security profiles with Docker isolation settings
TOOL_PROFILES: Dict[str, Dict[str, Any]] = {
    "nmap": {
        "image": "ghcr.io/cyberviser/hancock-nmap:latest",
        "entrypoint": "nmap",
        "network": "none",  # Default no outbound, require explicit override via scope
        "cpus": "1",
        "memory": "512m",
        "timeout": 90,
        "volumes": [],
    },
    "sqlmap": {
        "image": "ghcr.io/cyberviser/hancock-sqlmap:latest",
        "entrypoint": "sqlmap",
        "network": "none",
        "cpus": "1",
        "memory": "512m",
        "timeout": 120,
        "volumes": [],
    },
}
