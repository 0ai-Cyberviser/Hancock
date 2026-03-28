#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Orchestration Controller — Manages automated security tool execution.

Provides a registry-based approach for coordinating security tools with
allowlist enforcement, execution tracking, and structured result collection.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class StepResult:
    """Result of a single orchestration step."""

    tool: str
    status: str  # "success", "skipped", "error"
    duration_s: float = 0.0
    detail: str = ""
    data: Any = None


@dataclass
class OrchestrationReport:
    """Aggregated report from an orchestration run."""

    steps: list[StepResult] = field(default_factory=list)
    total_duration_s: float = 0.0

    @property
    def passed(self) -> int:
        return sum(1 for s in self.steps if s.status == "success")

    @property
    def failed(self) -> int:
        return sum(1 for s in self.steps if s.status == "error")

    @property
    def skipped(self) -> int:
        return sum(1 for s in self.steps if s.status == "skipped")

    def summary(self) -> str:
        return (
            f"[orchestration] {self.passed} passed, {self.failed} failed, "
            f"{self.skipped} skipped in {self.total_duration_s:.1f}s"
        )


class OrchestrationController:
    """Registry-based controller for automated security tool orchestration.

    Tools are registered with a name and callable, then executed in order.
    Only tools present in the allowlist may run; unregistered or disallowed
    tools are skipped with a clear status message.
    """

    def __init__(self, allowlist: list[str] | None = None) -> None:
        self.allowlist: list[str] = list(allowlist or [])
        self._registry: dict[str, Callable[..., Any]] = {}

    # ------------------------------------------------------------------
    # Registry helpers
    # ------------------------------------------------------------------
    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        """Register a callable under *name* so it can be executed later."""
        self._registry[name] = fn

    def registered_tools(self) -> list[str]:
        """Return the names of all registered tools."""
        return list(self._registry.keys())

    # ------------------------------------------------------------------
    # Allowlist helpers
    # ------------------------------------------------------------------
    def is_tool_allowed(self, tool_name: str) -> bool:
        return tool_name in self.allowlist

    def allow_tool(self, tool_name: str) -> None:
        if tool_name not in self.allowlist:
            self.allowlist.append(tool_name)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def coordinate_tool_integration(
        self,
        tool_name: str,
        params: dict[str, Any] | None = None,
    ) -> StepResult:
        """Execute a single registered tool if it is on the allowlist.

        Returns a :class:`StepResult` with status and optional payload.
        """
        if not self.is_tool_allowed(tool_name):
            return StepResult(
                tool=tool_name,
                status="skipped",
                detail=f"Tool '{tool_name}' is not in the allowlist",
            )

        fn = self._registry.get(tool_name)
        if fn is None:
            return StepResult(
                tool=tool_name,
                status="skipped",
                detail=f"Tool '{tool_name}' is not registered",
            )

        start = time.monotonic()
        try:
            result = fn(**(params or {}))
            elapsed = time.monotonic() - start
            return StepResult(
                tool=tool_name,
                status="success",
                duration_s=elapsed,
                data=result,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return StepResult(
                tool=tool_name,
                status="error",
                duration_s=elapsed,
                detail=str(exc),
            )

    def run_all(
        self,
        tools: list[str] | None = None,
        params: Optional[dict[str, dict[str, Any]]] = None,
    ) -> OrchestrationReport:
        """Execute multiple tools in sequence and collect results.

        Parameters
        ----------
        tools:
            Ordered list of tool names to run.  Defaults to the allowlist.
        params:
            Per-tool keyword arguments, keyed by tool name.
        """
        params = params or {}
        tools = tools or list(self.allowlist)
        report = OrchestrationReport()
        overall_start = time.monotonic()

        for name in tools:
            step = self.coordinate_tool_integration(name, params.get(name))
            report.steps.append(step)
            status_icon = {"success": "✓", "error": "✗", "skipped": "–"}.get(
                step.status, "?"
            )
            print(
                f"  {status_icon} {name}: {step.status}"
                + (f" ({step.detail})" if step.detail else "")
            )

        report.total_duration_s = time.monotonic() - overall_start
        print(report.summary())
        return report


if __name__ == "__main__":
    # Quick smoke test
    ctl = OrchestrationController(allowlist=["demo"])
    ctl.register_tool("demo", lambda: {"ok": True})
    result = ctl.coordinate_tool_integration("demo")
    print(f"demo → {result}")
    report = ctl.run_all()
    print(report.summary())