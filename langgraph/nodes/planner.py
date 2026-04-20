#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""Planner Node — Generate step-by-step plan based on goal and mode."""
from __future__ import annotations
from typing import Any
from langgraph.llmRouter import route_model


class Planner:
    """Planner node for generating execution plans."""

    def run(self, state: dict) -> dict:
        """
        Generate a safe, authorized step plan based on mode and goal.

        Args:
            state: Current workflow state

        Returns:
            Updated state with plan
        """
        llm = route_model(mode="plan")
        prompt = (
            f"Mode: {state['mode']}\n"
            f"Goal: {state['goal']}\n"
            f"History: {state['history']}\n\n"
            "Produce a safe, authorized step-by-step plan (bulleted list) "
            "for achieving this goal within the constraints of the mode."
        )
        plan_text = llm.generate(prompt)

        # Parse plan into list of steps
        plan = [
            line.strip("- ").strip()
            for line in plan_text.splitlines()
            if line.strip() and line.strip().startswith("-")
        ]

        if not plan:
            # Fallback if parsing fails
            plan = ["Review scope and authorization", "Identify safe reconnaissance steps", "Document findings"]

        state["plan"] = plan
        return state


# Global instance
planner = Planner()
