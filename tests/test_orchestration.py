"""Tests for orchestration_controller and hancock_pipeline orchestration functions."""
import sys
import os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration_controller import (
    OrchestrationController,
    OrchestrationReport,
    StepResult,
)


# ── OrchestrationController unit tests ──────────────────────────────


class TestStepResult:
    def test_defaults(self):
        r = StepResult(tool="t", status="success")
        assert r.duration_s == 0.0
        assert r.detail == ""
        assert r.data is None

    def test_fields(self):
        r = StepResult(tool="nmap", status="error", detail="timeout", duration_s=1.5)
        assert r.tool == "nmap"
        assert r.status == "error"
        assert r.detail == "timeout"


class TestOrchestrationReport:
    def test_empty_report(self):
        rpt = OrchestrationReport()
        assert rpt.passed == 0
        assert rpt.failed == 0
        assert rpt.skipped == 0

    def test_counts(self):
        rpt = OrchestrationReport(steps=[
            StepResult(tool="a", status="success"),
            StepResult(tool="b", status="error"),
            StepResult(tool="c", status="skipped"),
            StepResult(tool="d", status="success"),
        ])
        assert rpt.passed == 2
        assert rpt.failed == 1
        assert rpt.skipped == 1

    def test_summary_format(self):
        rpt = OrchestrationReport(
            steps=[StepResult(tool="x", status="success")],
            total_duration_s=1.234,
        )
        s = rpt.summary()
        assert "1 passed" in s
        assert "0 failed" in s
        assert "1.2" in s  # formatted to 1 decimal


class TestOrchestrationController:
    def test_register_and_list(self):
        ctl = OrchestrationController()
        ctl.register_tool("a", lambda: None)
        ctl.register_tool("b", lambda: None)
        assert set(ctl.registered_tools()) == {"a", "b"}

    def test_allowlist_enforcement(self):
        ctl = OrchestrationController(allowlist=["allowed"])
        ctl.register_tool("allowed", lambda: "ok")
        ctl.register_tool("blocked", lambda: "ok")

        r1 = ctl.coordinate_tool_integration("allowed")
        assert r1.status == "success"
        assert r1.data == "ok"

        r2 = ctl.coordinate_tool_integration("blocked")
        assert r2.status == "skipped"
        assert "not in the allowlist" in r2.detail

    def test_unregistered_tool_skipped(self):
        ctl = OrchestrationController(allowlist=["ghost"])
        r = ctl.coordinate_tool_integration("ghost")
        assert r.status == "skipped"
        assert "not registered" in r.detail

    def test_tool_exception_captured(self):
        def _fail():
            raise RuntimeError("boom")

        ctl = OrchestrationController(allowlist=["fail"])
        ctl.register_tool("fail", _fail)
        r = ctl.coordinate_tool_integration("fail")
        assert r.status == "error"
        assert "boom" in r.detail
        assert r.duration_s >= 0

    def test_allow_tool_dynamically(self):
        ctl = OrchestrationController()
        assert not ctl.is_tool_allowed("new")
        ctl.allow_tool("new")
        assert ctl.is_tool_allowed("new")
        # idempotent
        ctl.allow_tool("new")
        assert ctl.allowlist.count("new") == 1

    def test_run_all_returns_report(self):
        ctl = OrchestrationController(allowlist=["a", "b"])
        ctl.register_tool("a", lambda: 1)
        ctl.register_tool("b", lambda: 2)
        rpt = ctl.run_all()
        assert isinstance(rpt, OrchestrationReport)
        assert rpt.passed == 2
        assert rpt.failed == 0
        assert rpt.total_duration_s >= 0

    def test_run_all_custom_tools_order(self):
        order = []
        ctl = OrchestrationController(allowlist=["x", "y", "z"])
        ctl.register_tool("x", lambda: order.append("x"))
        ctl.register_tool("y", lambda: order.append("y"))
        ctl.register_tool("z", lambda: order.append("z"))
        ctl.run_all(tools=["z", "x"])
        assert order == ["z", "x"]

    def test_run_all_with_params(self):
        def adder(a=0, b=0):
            return a + b

        ctl = OrchestrationController(allowlist=["add"])
        ctl.register_tool("add", adder)
        rpt = ctl.run_all(params={"add": {"a": 3, "b": 4}})
        assert rpt.steps[0].data == 7

    def test_coordinate_with_params(self):
        def echo(**kwargs):
            return kwargs

        ctl = OrchestrationController(allowlist=["echo"])
        ctl.register_tool("echo", echo)
        r = ctl.coordinate_tool_integration("echo", {"msg": "hi"})
        assert r.data == {"msg": "hi"}


# ── hancock_pipeline orchestration integration tests ────────────────


class TestPipelineOrchestration:
    """Test that pipeline orchestration helpers build controllers correctly."""

    def test_assessment_tools_constant(self):
        from hancock_pipeline import ASSESSMENT_TOOLS
        assert "nmap" in ASSESSMENT_TOOLS
        assert "osint" in ASSESSMENT_TOOLS
        assert "graphql" in ASSESSMENT_TOOLS

    def test_data_collection_tools_constant(self):
        from hancock_pipeline import DATA_COLLECTION_TOOLS
        assert "kb" in DATA_COLLECTION_TOOLS
        assert "soc_collector" in DATA_COLLECTION_TOOLS
        assert "graphql_kb" in DATA_COLLECTION_TOOLS
        assert "formatter_v3" in DATA_COLLECTION_TOOLS

    @patch("hancock_pipeline._build_assessment_controller")
    def test_run_automated_assessment_delegates(self, mock_build):
        from hancock_pipeline import run_automated_assessment
        mock_ctl = MagicMock()
        mock_ctl.run_all.return_value = OrchestrationReport(
            steps=[StepResult(tool="nmap", status="success")]
        )
        mock_build.return_value = mock_ctl

        rpt = run_automated_assessment("10.0.0.1")
        mock_build.assert_called_once_with("10.0.0.1", tools=None)
        mock_ctl.run_all.assert_called_once()
        assert rpt.passed == 1

    @patch("hancock_pipeline._build_data_collection_controller")
    def test_run_automated_data_collection_delegates(self, mock_build):
        from hancock_pipeline import run_automated_data_collection
        mock_ctl = MagicMock()
        mock_ctl.run_all.return_value = OrchestrationReport()
        mock_build.return_value = mock_ctl

        rpt = run_automated_data_collection()
        mock_build.assert_called_once()
        assert isinstance(rpt, OrchestrationReport)

    @patch("hancock_pipeline.run_automated_assessment")
    def test_run_full_assessment_wraps_orchestration(self, mock_assess):
        from hancock_pipeline import run_full_assessment
        mock_assess.return_value = OrchestrationReport(
            steps=[StepResult(tool="nmap", status="success")]
        )
        run_full_assessment("example.com")
        mock_assess.assert_called_once_with("example.com")


class TestPipelineBuildControllers:
    """Test that _build_*_controller helpers register the right tools."""

    def test_build_assessment_controller_registers_tools(self):
        from hancock_pipeline import _build_assessment_controller, ASSESSMENT_TOOLS
        ctl = _build_assessment_controller("10.0.0.1")
        for t in ASSESSMENT_TOOLS:
            assert t in ctl.registered_tools()
            assert ctl.is_tool_allowed(t)

    def test_build_data_collection_controller_registers_tools(self):
        from hancock_pipeline import (
            _build_data_collection_controller,
            DATA_COLLECTION_TOOLS,
        )
        ctl = _build_data_collection_controller()
        for t in DATA_COLLECTION_TOOLS:
            assert t in ctl.registered_tools()
            assert ctl.is_tool_allowed(t)

    def test_custom_tool_subset(self):
        from hancock_pipeline import _build_assessment_controller
        ctl = _build_assessment_controller("10.0.0.1", tools=["nmap"])
        assert ctl.is_tool_allowed("nmap")
        assert not ctl.is_tool_allowed("burp")


class TestPipelineNewWrappers:
    """Test the new collector wrapper functions."""

    @patch("hancock_pipeline.run_graphql_security")
    def test_graphql_security_returns_dict(self, mock_fn):
        mock_fn.return_value = {"target": "http://x", "findings": []}
        from hancock_pipeline import run_graphql_security
        result = run_graphql_security("http://x")
        assert isinstance(result, dict)

    @patch("collectors.graphql_security_kb.collect", return_value=42)
    def test_graphql_kb_returns_count(self, mock_collect):
        from hancock_pipeline import run_graphql_kb
        assert run_graphql_kb() == 42

    @patch("collectors.soc_collector.collect")
    def test_soc_collector_calls_collect(self, mock_collect):
        from hancock_pipeline import run_soc_collector
        run_soc_collector()
        mock_collect.assert_called_once()


class TestPipelineCLI:
    """Test CLI argument parsing for new flags."""

    def test_assess_flag(self):
        from hancock_pipeline import main
        with patch("hancock_pipeline.run_automated_assessment") as mock_assess:
            mock_assess.return_value = OrchestrationReport()
            with patch("sys.argv", ["hancock_pipeline.py", "--assess", "10.0.0.1"]):
                main()
            mock_assess.assert_called_once_with("10.0.0.1")

    def test_collect_all_flag(self):
        from hancock_pipeline import main
        with patch("hancock_pipeline.run_automated_data_collection") as mock_collect:
            mock_collect.return_value = OrchestrationReport()
            with patch("sys.argv", ["hancock_pipeline.py", "--collect-all"]):
                main()
            mock_collect.assert_called_once()

    def test_phase_default_is_3(self):
        """When neither --assess nor --collect-all is given, phase defaults to 3."""
        from hancock_pipeline import main
        with patch("hancock_pipeline.run_kb") as mk, \
             patch("hancock_pipeline.run_soc_kb"), \
             patch("hancock_pipeline.run_mitre"), \
             patch("hancock_pipeline.run_nvd"), \
             patch("hancock_pipeline.run_kev"), \
             patch("hancock_pipeline.run_ghsa"), \
             patch("hancock_pipeline.run_atomic"), \
             patch("hancock_pipeline.run_formatter_v3"):
            with patch("sys.argv", ["hancock_pipeline.py"]):
                main()
            mk.assert_called_once()
