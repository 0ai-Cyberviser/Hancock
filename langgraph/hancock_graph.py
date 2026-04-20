#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock LangGraph Core — Agentic orchestration with LangGraph.

Provides a stateful workflow:
  Planner → Recon → Executor → Critic → Reporter

Features:
- Intent verification before execution
- Scope-based authorization
- Safe defaults (execute=False by default)
- Integration with existing Hancock modes
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
try:
    from langgraph.graph import StateGraph, END
except ImportError:
    StateGraph = None
    END = None

from security.intent_guard import verify_intent_and_scope
from security.authz import Scope


class HancockState(BaseModel):
    """State for Hancock agentic workflow."""
    user_id: str
    scopes: List[Scope] = Field(default_factory=list)
    mode: str
    goal: str
    history: List[Any] = Field(default_factory=list)
    plan: Optional[List[str]] = None
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    report: Optional[str] = None
    risk: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


def build_graph():
    """Build and compile the LangGraph workflow."""
    if StateGraph is None:
        raise ImportError("langgraph not installed. Install with: pip install langgraph")

    from langgraph.nodes import planner, recon, executor, critic, reporter

    g = StateGraph(HancockState)

    g.add_node("planner", planner.run)
    g.add_node("recon", recon.run)
    g.add_node("executor", executor.run)
    g.add_node("critic", critic.run)
    g.add_node("reporter", reporter.run)

    g.set_entry_point("planner")

    g.add_edge("planner", "recon")
    g.add_edge("recon", "executor")
    g.add_edge("executor", "critic")
    g.add_edge("critic", "reporter")
    g.add_edge("reporter", END)

    return g.compile()


def run_hancock_loop(state: HancockState) -> HancockState:
    """
    Execute the Hancock agentic loop with security checks.

    Args:
        state: Initial state with user_id, scopes, mode, goal

    Returns:
        Updated state with report and risk assessment

    Raises:
        PermissionError: If intent verification fails
        ImportError: If langgraph is not installed
    """
    # Verify intent and scope before execution
    verify_intent_and_scope(state.goal, state.mode, state.scopes)

    # Build and execute graph
    graph = build_graph()
    result = graph.invoke(state.dict())

    # Return updated state
    return HancockState(**result)
