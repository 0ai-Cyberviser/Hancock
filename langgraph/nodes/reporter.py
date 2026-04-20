#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""Reporter Node — Generate final report with findings and remediation."""
from __future__ import annotations
from langgraph.llmRouter import route_model


class Reporter:
    """Reporter node for generating final reports."""

    def run(self, state: dict) -> dict:
        """
        Create a PTES-aligned report with findings and remediation.

        Args:
            state: Current workflow state with findings and risk

        Returns:
            Updated state with final report
        """
        llm = route_model(mode="report")

        prompt = (
            f"Create a concise, professional security report following PTES methodology.\n\n"
            f"Mode: {state['mode']}\n"
            f"Goal: {state['goal']}\n"
            f"Plan: {state.get('plan', [])}\n"
            f"Findings: {state['findings']}\n"
            f"Risk Assessment: {state.get('risk', 'N/A')}\n\n"
            "Include:\n"
            "1. Executive Summary\n"
            "2. Methodology and Tools Used\n"
            "3. Findings (with severity ratings)\n"
            "4. Remediation Recommendations\n"
            "5. Next Steps\n\n"
            "Format as Markdown."
        )

        report = llm.generate(prompt)
        state["report"] = report

        return state


# Global instance
reporter = Reporter()
