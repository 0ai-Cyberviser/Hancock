#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""Executor Node — Execute approved actions in sandbox."""
from __future__ import annotations
from security.intent_guard import gate_actions
from sandbox.runner import run_tool_safely


class Executor:
    """Executor node for running approved actions."""

    def run(self, state: dict) -> dict:
        """
        Execute approved actions with gating.

        By default, all actions have execute=False (recommendation-only mode).
        Future versions will support explicit approval for execute=True.

        Args:
            state: Current workflow state with actions

        Returns:
            Updated state with findings
        """
        # Gate actions based on scope
        approved = gate_actions(
            state["actions"],
            state["mode"],
            state["scopes"]
        )

        exe_results = []
        for act in approved:
            if act.get("execute", False):
                # Execute in sandbox
                tool = act.get("tool", "")
                args = act.get("args", [])
                kwargs = act.get("kwargs", {})

                result = run_tool_safely(tool, args, kwargs)
                exe_results.append({
                    "action": act,
                    "result": result,
                })
            else:
                # Recommendation only
                exe_results.append({
                    "action": act,
                    "result": {"status": "recommendation_only"},
                })

        state["findings"].extend(exe_results)
        return state


# Global instance
executor = Executor()
