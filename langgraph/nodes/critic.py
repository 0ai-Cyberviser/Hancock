#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""Critic Node — Evaluate findings for safety and accuracy."""
from __future__ import annotations
from langgraph.llmRouter import route_model


class Critic:
    """Critic node for evaluating findings."""

    def run(self, state: dict) -> dict:
        """
        Evaluate findings for safety, accuracy, and false positives.

        Args:
            state: Current workflow state with findings

        Returns:
            Updated state with risk assessment
        """
        llm = route_model(mode="critic")

        prompt = (
            f"Evaluate the following findings for safety, accuracy, and potential false positives:\n\n"
            f"Findings: {state['findings']}\n\n"
            "Return:\n"
            "1. Risk assessment (low/medium/high)\n"
            "2. Notes on false positives or misconfigurations\n"
            "3. Recommendations for next steps"
        )

        analysis = llm.generate(prompt)
        state["risk"] = analysis

        return state


# Global instance
critic = Critic()
