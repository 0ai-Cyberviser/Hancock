"""Tests for the enhanced OrchestrationController."""

import time
import threading
import pytest

from orchestration_controller import (
    OrchestrationController,
    ToolConfig,
    ToolCategory,
    ExecutionStatus,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _echo_handler(params):
    """Simple handler that echoes params back."""
    return {"echo": params}


def _failing_handler(params):
    """Handler that always raises."""
    raise RuntimeError("Simulated failure")


def _slow_handler(params):
    """Handler that sleeps for longer than any reasonable timeout."""
    time.sleep(10)
    return {"done": True}


def _counter_handler_factory():
    """Return a handler that counts invocations (thread-safe)."""
    lock = threading.Lock()
    count = {"value": 0}

    def handler(params):
        with lock:
            count["value"] += 1
            current = count["value"]
        if current <= 2:
            raise RuntimeError(f"Attempt {current} fails")
        return {"attempt": current}

    return handler, count


@pytest.fixture
def controller():
    """Controller with echo and failing tools registered."""
    ctrl = OrchestrationController(allowlist=["echo", "counter"])
    ctrl.register_tool(ToolConfig(
        name="echo",
        handler=_echo_handler,
        description="Echo handler",
        category=ToolCategory.UTILITY,
        timeout=5,
        max_retries=0,
    ))
    return ctrl


# ── Registration ──────────────────────────────────────────────────────────────

class TestToolRegistration:
    def test_register_tool(self, controller):
        cfg = controller.get_tool("echo")
        assert cfg is not None
        assert cfg.name == "echo"
        assert cfg.description == "Echo handler"

    def test_register_duplicate_raises(self, controller):
        with pytest.raises(ValueError, match="already registered"):
            controller.register_tool(ToolConfig(
                name="echo", handler=_echo_handler,
            ))

    def test_unregister_tool(self, controller):
        assert controller.unregister_tool("echo") is True
        assert controller.get_tool("echo") is None

    def test_unregister_missing_tool(self, controller):
        assert controller.unregister_tool("nonexistent") is False

    def test_list_tools(self, controller):
        tools = controller.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "echo"
        assert tools[0]["allowed"] is True

    def test_list_tools_by_category(self, controller):
        controller.register_tool(ToolConfig(
            name="scanner",
            handler=_echo_handler,
            category=ToolCategory.RECON,
        ))
        controller.allow_tool("scanner")
        recon_tools = controller.list_tools(category=ToolCategory.RECON)
        assert len(recon_tools) == 1
        assert recon_tools[0]["name"] == "scanner"

        utility_tools = controller.list_tools(category=ToolCategory.UTILITY)
        assert len(utility_tools) == 1
        assert utility_tools[0]["name"] == "echo"


# ── Allowlist ─────────────────────────────────────────────────────────────────

class TestAllowlist:
    def test_is_tool_allowed(self, controller):
        assert controller.is_tool_allowed("echo") is True
        assert controller.is_tool_allowed("blocked") is False

    def test_allow_tool(self, controller):
        controller.allow_tool("new_tool")
        assert controller.is_tool_allowed("new_tool") is True

    def test_block_tool(self, controller):
        controller.block_tool("echo")
        assert controller.is_tool_allowed("echo") is False

    def test_block_nonexistent(self, controller):
        # Should not raise
        controller.block_tool("nonexistent")


# ── Execution ─────────────────────────────────────────────────────────────────

class TestExecution:
    def test_execute_success(self, controller):
        result = controller.execute("echo", {"key": "value"})
        assert result["status"] == ExecutionStatus.SUCCESS
        assert result["result"]["echo"] == {"key": "value"}
        assert "execution_id" in result
        assert result["duration_ms"] >= 0

    def test_execute_empty_params(self, controller):
        result = controller.execute("echo")
        assert result["status"] == ExecutionStatus.SUCCESS
        assert result["result"]["echo"] == {}

    def test_execute_blocked_tool(self, controller):
        result = controller.execute("not_allowed", {"target": "x"})
        assert result["status"] == ExecutionStatus.BLOCKED
        assert "not in the allowlist" in result["error"]

    def test_execute_unregistered_tool(self, controller):
        result = controller.execute("counter", {"x": 1})
        assert result["status"] == ExecutionStatus.FAILURE
        assert "not registered" in result["error"]

    def test_execute_failure_no_retry(self, controller):
        controller.register_tool(ToolConfig(
            name="failer",
            handler=_failing_handler,
            max_retries=0,
            timeout=5,
        ))
        controller.allow_tool("failer")
        result = controller.execute("failer")
        assert result["status"] == ExecutionStatus.FAILURE
        assert "Simulated failure" in result["error"]

    def test_execute_with_retry_success(self, controller):
        handler, count = _counter_handler_factory()
        controller.register_tool(ToolConfig(
            name="counter",
            handler=handler,
            max_retries=3,
            timeout=5,
        ))
        result = controller.execute("counter", {})
        assert result["status"] == ExecutionStatus.SUCCESS
        assert count["value"] == 3  # failed 2 times, succeeded on 3rd

    def test_execute_timeout(self, controller):
        controller.register_tool(ToolConfig(
            name="slow",
            handler=_slow_handler,
            timeout=1,
            max_retries=0,
        ))
        controller.allow_tool("slow")
        result = controller.execute("slow")
        assert result["status"] == ExecutionStatus.TIMEOUT
        assert "timed out" in result["error"]

    def test_backward_compat_method(self, controller):
        result = controller.coordinate_tool_integration("echo", {"a": 1})
        assert result["status"] == ExecutionStatus.SUCCESS


# ── Caching ───────────────────────────────────────────────────────────────────

class TestCaching:
    def test_cached_result(self, controller):
        call_count = {"n": 0}

        def counting_handler(params):
            call_count["n"] += 1
            return {"count": call_count["n"]}

        controller.register_tool(ToolConfig(
            name="cached_tool",
            handler=counting_handler,
            cache_ttl=60,
            timeout=5,
        ))
        controller.allow_tool("cached_tool")

        r1 = controller.execute("cached_tool", {"key": "val"})
        r2 = controller.execute("cached_tool", {"key": "val"})

        assert r1["status"] == ExecutionStatus.SUCCESS
        assert r2["status"] == ExecutionStatus.CACHED
        assert call_count["n"] == 1  # handler called only once

    def test_different_params_no_cache(self, controller):
        call_count = {"n": 0}

        def counting_handler(params):
            call_count["n"] += 1
            return {"count": call_count["n"]}

        controller.register_tool(ToolConfig(
            name="cached2",
            handler=counting_handler,
            cache_ttl=60,
            timeout=5,
        ))
        controller.allow_tool("cached2")

        controller.execute("cached2", {"a": 1})
        controller.execute("cached2", {"a": 2})
        assert call_count["n"] == 2

    def test_invalidate_cache(self, controller):
        call_count = {"n": 0}

        def counting_handler(params):
            call_count["n"] += 1
            return {"count": call_count["n"]}

        controller.register_tool(ToolConfig(
            name="cached3",
            handler=counting_handler,
            cache_ttl=60,
            timeout=5,
        ))
        controller.allow_tool("cached3")

        controller.execute("cached3", {"x": 1})
        evicted = controller.invalidate_cache("cached3")
        assert evicted == 1

        r2 = controller.execute("cached3", {"x": 1})
        assert r2["status"] == ExecutionStatus.SUCCESS
        assert call_count["n"] == 2

    def test_invalidate_all_cache(self, controller):
        controller.register_tool(ToolConfig(
            name="cached4",
            handler=_echo_handler,
            cache_ttl=60,
            timeout=5,
        ))
        controller.allow_tool("cached4")
        controller.execute("cached4", {"x": 1})
        evicted = controller.invalidate_cache()
        assert evicted >= 1


# ── History / Audit ───────────────────────────────────────────────────────────

class TestHistory:
    def test_history_recorded(self, controller):
        controller.execute("echo", {"x": 1})
        history = controller.get_history()
        assert len(history) == 1
        assert history[0]["tool_name"] == "echo"
        assert history[0]["status"] == ExecutionStatus.SUCCESS

    def test_history_filter_by_tool(self, controller):
        controller.execute("echo", {"x": 1})
        controller.execute("unknown", {"x": 2})  # blocked

        echo_history = controller.get_history(tool_name="echo")
        assert len(echo_history) == 1

    def test_history_filter_by_status(self, controller):
        controller.execute("echo", {"x": 1})
        controller.execute("not_allowed", {})

        blocked = controller.get_history(status=ExecutionStatus.BLOCKED)
        assert len(blocked) == 1

    def test_history_limit(self, controller):
        for i in range(10):
            controller.execute("echo", {"i": i})
        history = controller.get_history(limit=3)
        assert len(history) == 3

    def test_history_newest_first(self, controller):
        controller.execute("echo", {"i": 0})
        controller.execute("echo", {"i": 1})
        history = controller.get_history()
        # Newest first
        assert history[0]["started_at"] >= history[1]["started_at"]

    def test_clear_history(self, controller):
        controller.execute("echo", {"x": 1})
        count = controller.clear_history()
        assert count == 1
        assert controller.get_history() == []

    def test_max_history_eviction(self):
        ctrl = OrchestrationController(allowlist=["echo"], max_history=5)
        ctrl.register_tool(ToolConfig(
            name="echo", handler=_echo_handler, timeout=5,
        ))
        for i in range(10):
            ctrl.execute("echo", {"i": i})
        history = ctrl.get_history(limit=100)
        assert len(history) == 5


# ── Null allowlist ────────────────────────────────────────────────────────────

class TestNullAllowlist:
    def test_empty_allowlist_blocks_all(self):
        ctrl = OrchestrationController(allowlist=[])
        ctrl.register_tool(ToolConfig(
            name="echo", handler=_echo_handler, timeout=5,
        ))
        result = ctrl.execute("echo")
        assert result["status"] == ExecutionStatus.BLOCKED

    def test_none_allowlist_blocks_all(self):
        ctrl = OrchestrationController(allowlist=None)
        ctrl.register_tool(ToolConfig(
            name="echo", handler=_echo_handler, timeout=5,
        ))
        result = ctrl.execute("echo")
        assert result["status"] == ExecutionStatus.BLOCKED
