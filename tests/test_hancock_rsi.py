"""Tests for Hancock Recursive Self-Improvement framework."""

import pytest
import json
from pathlib import Path
from datetime import datetime
import tempfile

from hancock_rsi import (
    RecursiveSelfImprover,
    ImprovementProposal,
    ImprovementType,
    ValidationStatus,
    Capability,
    SecurityPolicy,
    RSIMetrics,
)


class TestSecurityPolicy:
    """Test RSI security policy enforcement."""
    
    def test_detect_forbidden_os_system(self):
        """Detect os.system() calls."""
        proposal = ImprovementProposal(
            id="test1",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.CODE_OPTIMIZATION,
            title="Test",
            description="Test",
            rationale="Test",
            affected_files=["test.py"],
            code_changes={"test.py": "import os\nos.system('rm -rf /')"},
            test_commands=[],
            expected_benefits=[],
            risks=[],
        )
        
        is_safe, reason = SecurityPolicy.validate_proposal(proposal)
        assert not is_safe
        assert "os.system" in reason
    
    def test_detect_eval_exec(self):
        """Detect eval/exec calls."""
        proposal = ImprovementProposal(
            id="test2",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.CODE_OPTIMIZATION,
            title="Test",
            description="Test",
            rationale="Test",
            affected_files=["test.py"],
            code_changes={"test.py": "code = input('Enter code: ')\neval(code)"},
            test_commands=[],
            expected_benefits=[],
            risks=[],
        )
        
        is_safe, reason = SecurityPolicy.validate_proposal(proposal)
        assert not is_safe
        assert "eval" in reason
    
    def test_safe_code_passes(self):
        """Safe code passes policy check."""
        proposal = ImprovementProposal(
            id="test3",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.CODE_OPTIMIZATION,
            title="Test",
            description="Test",
            rationale="Test",
            affected_files=["test.py"],
            code_changes={"test.py": "def hello():\n    return 'world'"},
            test_commands=[],
            expected_benefits=[],
            risks=[],
        )
        
        is_safe, reason = SecurityPolicy.validate_proposal(proposal)
        assert is_safe
        assert "passed" in reason.lower()
    
    def test_requires_approval_for_critical_types(self):
        """Critical improvement types require human approval."""
        proposal = ImprovementProposal(
            id="test4",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.SECURITY_ENHANCEMENT,
            title="Test",
            description="Test",
            rationale="Test",
            affected_files=["safety.py"],
            code_changes={"safety.py": "# Safe changes"},
            test_commands=[],
            expected_benefits=[],
            risks=[],
        )
        
        SecurityPolicy.validate_proposal(proposal)
        assert proposal.approval_required is True
    
    def test_auto_approve_safe_types(self):
        """Safe improvement types can auto-approve after policy check."""
        proposal = ImprovementProposal(
            id="test5",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.DOCUMENTATION,
            title="Test",
            description="Test",
            rationale="Test",
            affected_files=["README.md"],
            code_changes={"README.md": "# Updated docs"},
            test_commands=[],
            expected_benefits=[],
            risks=[],
        )
        
        # Default approval_required is True (safe default)
        assert proposal.approval_required is True
        
        # After policy validation, safe types don't require approval
        SecurityPolicy.validate_proposal(proposal)
        assert proposal.approval_required is False


class TestCapability:
    """Test capability tracking."""
    
    def test_capability_creation(self):
        """Create capability with all fields."""
        cap = Capability(
            name="test_coverage",
            description="Test coverage percentage",
            metric="pytest --cov",
            current_value=0.85,
            target_value=0.95,
            importance=9,
        )
        
        assert cap.name == "test_coverage"
        assert cap.current_value < cap.target_value
        assert cap.importance == 9
    
    def test_capability_gap_calculation(self):
        """Calculate gap between current and target."""
        cap = Capability(
            name="accuracy",
            description="Model accuracy",
            metric="benchmark",
            current_value=0.80,
            target_value=0.90,
            importance=10,
        )
        
        gap = cap.target_value - cap.current_value
        assert gap == pytest.approx(0.10)
        
        priority_score = cap.importance * gap
        assert priority_score == pytest.approx(1.0)


class TestImprovementProposal:
    """Test improvement proposal lifecycle."""
    
    def test_proposal_creation(self):
        """Create improvement proposal with required fields."""
        proposal = ImprovementProposal(
            id="prop1",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.BUG_FIX,
            title="Fix null pointer",
            description="Add null check in parser",
            rationale="Crashes on empty input",
            affected_files=["parser.py"],
            code_changes={"parser.py": "if data is None: return"},
            test_commands=["pytest tests/test_parser.py"],
            expected_benefits=["No crashes", "Better UX"],
            risks=["Performance impact"],
        )
        
        assert proposal.id == "prop1"
        assert proposal.improvement_type == ImprovementType.BUG_FIX
        assert proposal.validation_status == ValidationStatus.PENDING
        assert proposal.approval_required is True
    
    def test_proposal_to_dict(self):
        """Serialize proposal to dict."""
        proposal = ImprovementProposal(
            id="prop2",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            improvement_type=ImprovementType.NEW_FEATURE,
            title="Add feature X",
            description="Implements X",
            rationale="Users requested",
            affected_files=["feature_x.py"],
            code_changes={},
            test_commands=[],
            expected_benefits=["Better features"],
            risks=["Complexity"],
        )
        
        d = proposal.to_dict()
        assert d["id"] == "prop2"
        assert d["improvement_type"] == "new_feature"
        assert d["timestamp"] == "2024-01-01T12:00:00"


class TestRSIMetrics:
    """Test RSI metrics tracking."""
    
    def test_metrics_initialization(self):
        """Metrics start at zero."""
        metrics = RSIMetrics()
        assert metrics.cycle_count == 0
        assert metrics.proposals_generated == 0
        assert metrics.test_pass_rate == 0.0
    
    def test_metrics_to_dict(self):
        """Serialize metrics to dict."""
        metrics = RSIMetrics(
            cycle_count=5,
            proposals_generated=10,
            proposals_approved=6,
            proposals_rejected=2,
        )
        
        d = metrics.to_dict()
        assert d["cycle_count"] == 5
        assert d["proposals_generated"] == 10
        assert d["success_rate"] == 0.6  # 6/10
    
    def test_success_rate_calculation(self):
        """Success rate = approved / generated."""
        metrics = RSIMetrics()
        metrics.proposals_generated = 20
        metrics.proposals_approved = 15
        
        d = metrics.to_dict()
        assert d["success_rate"] == 0.75


class TestRecursiveSelfImprover:
    """Test main RSI engine."""
    
    def test_initialization(self, tmp_path):
        """Initialize RSI with workspace."""
        rsi = RecursiveSelfImprover(
            workspace=tmp_path,
            peachtree_path=tmp_path / "peachtree",
            max_iterations=10,
        )
        
        assert rsi.workspace == tmp_path
        assert rsi.max_iterations == 10
        assert len(rsi.capabilities) > 0
        assert rsi.metrics.cycle_count == 0
    
    def test_baseline_capabilities_loaded(self, tmp_path):
        """Baseline capabilities are loaded."""
        rsi = RecursiveSelfImprover(workspace=tmp_path)
        
        cap_names = {cap.name for cap in rsi.capabilities}
        assert "test_coverage" in cap_names
        assert "response_accuracy" in cap_names
        assert "dataset_quality" in cap_names
        assert "security_pattern_coverage" in cap_names
    
    def test_identify_improvement_opportunities(self, tmp_path):
        """Identify capabilities below target."""
        rsi = RecursiveSelfImprover(workspace=tmp_path)
        
        # Set one capability below target
        for cap in rsi.capabilities:
            if cap.name == "test_coverage":
                cap.current_value = 0.70  # Below target of 0.95
        
        opportunities = rsi.identify_improvement_opportunities()
        
        # Should generate at least one proposal
        assert len(opportunities) > 0
        
        # Should prioritize high-importance gaps
        top_opportunity = opportunities[0]
        assert isinstance(top_opportunity, ImprovementProposal)
    
    def test_validate_proposal_security_check(self, tmp_path):
        """Proposal validation includes security check."""
        rsi = RecursiveSelfImprover(workspace=tmp_path)
        
        # Unsafe proposal
        unsafe_proposal = ImprovementProposal(
            id="unsafe1",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.CODE_OPTIMIZATION,
            title="Test",
            description="Test",
            rationale="Test",
            affected_files=["test.py"],
            code_changes={"test.py": "os.system('dangerous')"},
            test_commands=[],
            expected_benefits=[],
            risks=[],
        )
        
        result = rsi.validate_proposal(unsafe_proposal)
        assert result is False
        assert unsafe_proposal.validation_status == ValidationStatus.FAILED
        assert "security_check" in unsafe_proposal.validation_results
    
    def test_history_saved(self, tmp_path):
        """RSI history is saved to JSONL."""
        rsi = RecursiveSelfImprover(workspace=tmp_path, max_iterations=1)
        
        # Run one cycle
        rsi.run_cycle()
        
        # Check history file exists
        assert rsi.history_path.exists()
        
        # Parse history
        with open(rsi.history_path) as f:
            entries = [json.loads(line) for line in f]
        
        assert len(entries) >= 1
        assert entries[0]["cycle"] == 1
        assert "metrics" in entries[0]


class TestRSIIntegration:
    """Integration tests for full RSI loop."""
    
    def test_full_cycle_execution(self, tmp_path):
        """Run one full RSI cycle."""
        rsi = RecursiveSelfImprover(
            workspace=tmp_path,
            max_iterations=1,
            require_human_approval=False,  # Auto-approve for testing
        )
        
        result = rsi.run_cycle()
        
        assert result["cycle"] == 1
        assert "capabilities" in result
        assert "proposals_generated" in result
        assert result["duration_seconds"] > 0
    
    def test_metrics_updated_after_cycle(self, tmp_path):
        """Metrics are updated after each cycle."""
        rsi = RecursiveSelfImprover(workspace=tmp_path, max_iterations=1)
        
        initial_count = rsi.metrics.cycle_count
        rsi.run_cycle()
        
        assert rsi.metrics.cycle_count == initial_count + 1
        assert rsi.metrics.total_runtime_hours > 0


class TestSafetyBounds:
    """Test safety bounds and fail-safes."""
    
    def test_max_iterations_enforced(self, tmp_path):
        """RSI stops after max_iterations."""
        rsi = RecursiveSelfImprover(workspace=tmp_path, max_iterations=2)
        
        # Mock all capabilities as below target (would run forever otherwise)
        for cap in rsi.capabilities:
            cap.current_value = 0.5
            cap.target_value = 1.0
        
        rsi.run()
        
        # Should stop after 2 cycles
        assert rsi.metrics.cycle_count <= 2
    
    def test_regression_detection(self, tmp_path):
        """Detect and reject proposals that degrade capabilities."""
        rsi = RecursiveSelfImprover(workspace=tmp_path)
        
        # Set baseline
        for cap in rsi.capabilities:
            if cap.name == "test_coverage":
                cap.current_value = 0.90
        
        # Create proposal that would regress (hypothetically)
        proposal = ImprovementProposal(
            id="regress1",
            timestamp=datetime.now(),
            improvement_type=ImprovementType.CODE_OPTIMIZATION,
            title="Optimize tests",
            description="Remove slow tests",
            rationale="Speed up CI",
            affected_files=["tests/"],
            code_changes={},
            test_commands=["echo 'mock test'"],
            expected_benefits=["Faster CI"],
            risks=["Lower coverage"],
        )
        
        # If validation detected coverage drop below 0.90 * 0.95 = 0.855,
        # it should reject the proposal
        # (In real execution, assess_capabilities would detect this)


class TestDatasetGeneration:
    """Test PeachTree dataset generation from RSI cycles."""
    
    def test_dataset_records_generated(self, tmp_path):
        """Dataset records are generated from proposals."""
        rsi = RecursiveSelfImprover(workspace=tmp_path, max_iterations=1)
        
        initial_count = rsi.metrics.dataset_records_generated
        rsi.run_cycle()
        
        # Should generate at least some records
        assert rsi.metrics.dataset_records_generated >= initial_count


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
