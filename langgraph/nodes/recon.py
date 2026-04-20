#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""Recon Node — Suggest reconnaissance actions based on plan."""
from __future__ import annotations
from langgraph.llmRouter import route_model


class Recon:
    """Recon node for suggesting reconnaissance actions."""

    def run(self, state: dict) -> dict:
        """
        Suggest low-risk, authorized recon actions.

        Args:
            state: Current workflow state with plan

        Returns:
            Updated state with recon actions
        """
        llm = route_model(mode="recon")

        # Simple tool catalog (in production, this would query real tools)
        tools = ["nmap", "subfinder", "amass", "whois", "nslookup"]

        prompt = (
            f"Plan: {state.get('plan', [])}\n"
            f"Mode: {state['mode']}\n\n"
            f"Suggest low-risk, authorized reconnaissance actions using available tools: {tools}\n"
            "Focus on passive and non-intrusive techniques."
        )

        suggestions = llm.generate(prompt)

        # Add to actions list
        state["actions"].append({
            "stage": "recon",
            "suggestions": suggestions,
        })

        return state


# Global instance
recon = Recon()
