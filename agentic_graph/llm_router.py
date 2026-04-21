#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
LLM Router — Route to appropriate model based on mode.

For v0.3.1, this uses existing Ollama/NIM backends.
Future versions will add confidence scoring and fallbacks.
"""
from __future__ import annotations
from typing import Any


class SimpleLLMRouter:
    """Simple LLM router that will use existing Hancock backends."""

    def route_model(self, mode: str = "plan"):
        """
        Route to appropriate model based on mode.
        Returns a simple wrapper around the model.
        """
        # For now, return a simple mock that can be replaced with actual LLM calls
        return SimpleLLM()


class SimpleLLM:
    """Simple LLM wrapper for generating responses."""

    def generate(self, prompt: str) -> str:
        """
        Generate a response to the prompt.
        For v0.3.1, this is a placeholder that returns a formatted response.
        Future versions will integrate with hancock_agent.py's chat() function.
        """
        # Placeholder implementation
        # In production, this would call hancock_agent.chat() or similar
        return f"[AI Generated Response to: {prompt[:100]}...]"


# Global instance for convenience
_router = SimpleLLMRouter()


def route_model(mode: str = "plan") -> SimpleLLM:
    """Get LLM for the specified mode."""
    return _router.route_model(mode)
