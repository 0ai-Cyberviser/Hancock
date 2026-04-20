#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Intent Guard — Intent verification and action gating for safe agentic operations.
"""
from __future__ import annotations
from typing import List, Dict, Any
from .authz import Scope

# Disallowed intents that indicate unauthorized or malicious activity
DISALLOWED = {
    "ransomware", "ddos", "unauthorized", "bypass payment",
    "exploit prod without permission", "denial of service",
    "mass scan", "attack", "unauthorized access"
}


def verify_intent_and_scope(goal: str, mode: str, scopes: List[Scope]) -> None:
    """
    Verify that the user's goal and mode are authorized and within scope.

    Raises PermissionError if:
    - Goal contains disallowed keywords
    - No authorized scope is provided
    - Mode is unknown

    Args:
        goal: User's stated goal/objective
        mode: Operational mode (pentest, soc, etc.)
        scopes: List of authorization scopes

    Raises:
        PermissionError: If intent or scope validation fails
    """
    # Check for disallowed intents
    goal_lower = goal.lower()
    for term in DISALLOWED:
        if term in goal_lower:
            raise PermissionError(f"Intent not authorized by policy: detected '{term}'")

    # Verify authorized scope is present
    scope_names = [s.name for s in scopes]
    if "authorized" not in scope_names:
        raise PermissionError("No authorized testing scope provided.")

    # Verify mode is valid
    valid_modes = {
        "pentest", "soc", "sigma", "yara", "ioc",
        "osint", "graphql", "code", "ciso", "auto"
    }
    if mode not in valid_modes:
        raise PermissionError(f"Unknown mode: {mode}")


def gate_actions(actions: List[Dict[str, Any]], mode: str, scopes: List[Scope]) -> List[Dict[str, Any]]:
    """
    Gate actions based on scope and mode. By default, all actions have execute=False
    for safety. Future versions will allow explicit execution approval.

    Args:
        actions: List of proposed actions
        mode: Operational mode
        scopes: Authorization scopes

    Returns:
        List of gated actions with execute flags
    """
    # Default: all actions are in recommendation-only mode (execute=False)
    # Future enhancement: check for 'exec_low_risk' scope and whitelist
    allowed = []
    for action in actions:
        stage = action.get("stage", "unknown")
        suggestions = action.get("suggestions", "")
        allowed.append({
            "stage": stage,
            "suggestions": suggestions,
            "execute": False,  # Default: recommendation-only
        })
    return allowed
