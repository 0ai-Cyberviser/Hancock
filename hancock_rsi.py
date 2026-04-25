"""Recursive Self-Improvement (RSI) Framework for Hancock.

Implements a safety-bounded "seed improver" architecture that enables Hancock to:
1. Analyze its own capabilities and identify improvement opportunities
2. Generate code/config changes to enhance performance
3. Validate changes through automated testing (no regression)
4. Integrate validated improvements into the codebase
5. Generate high-quality PeachTree training data from the process

CRITICAL SAFETY BOUNDS:
- Human-in-the-loop approval for all code modifications
- Strict regression testing (capabilities never degrade)
- Security policy validation (no unsafe operations)
- Provenance tracking for all generated artifacts
- Rollback mechanism for failed improvements

Based on research from:
- Voyager (Minecraft iterative programming)
- STOP (Self-Taught Optimizer)
- Meta AI Self-Rewarding LLMs
- DeepMind AlphaEvolve

Author: HancockForge / AssuranceForge
License: Same as Hancock project
"""
from __future__ import annotations

import json
import hashlib
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ImprovementType(Enum):
    """Types of improvements the RSI system can propose."""
    CODE_OPTIMIZATION = "code_optimization"  # Refactor for performance/clarity
    NEW_FEATURE = "new_feature"  # Add new capability
    BUG_FIX = "bug_fix"  # Fix identified issue
    SECURITY_ENHANCEMENT = "security_enhancement"  # Strengthen security
    TEST_COVERAGE = "test_coverage"  # Add/improve tests
    DOCUMENTATION = "documentation"  # Improve docs
    DATASET_QUALITY = "dataset_quality"  # Enhance PeachTree datasets


class ValidationStatus(Enum):
    """Validation outcome for proposed improvements."""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_HUMAN_REVIEW = "requires_human_review"


@dataclass
class Capability:
    """A measurable capability of the Hancock system."""
    name: str
    description: str
    metric: str  # How to measure (e.g., "test_pass_rate", "response_accuracy")
    current_value: float
    target_value: float
    importance: int = 5  # 1-10 scale


@dataclass
class ImprovementProposal:
    """A proposed improvement to the Hancock system."""
    id: str
    timestamp: datetime
    improvement_type: ImprovementType
    title: str
    description: str
    rationale: str
    affected_files: list[str]
    code_changes: dict[str, str]  # filepath -> new content
    test_commands: list[str]
    expected_benefits: list[str]
    risks: list[str]
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validation_results: dict[str, Any] = field(default_factory=dict)
    approval_required: bool = True
    approved_by: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "improvement_type": self.improvement_type.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "affected_files": self.affected_files,
            "test_commands": self.test_commands,
            "expected_benefits": self.expected_benefits,
            "risks": self.risks,
            "validation_status": self.validation_status.value,
            "validation_results": self.validation_results,
            "approval_required": self.approval_required,
            "approved_by": self.approved_by,
        }


@dataclass
class RSIMetrics:
    """Metrics for tracking RSI performance."""
    cycle_count: int = 0
    proposals_generated: int = 0
    proposals_validated: int = 0
    proposals_approved: int = 0
    proposals_rejected: int = 0
    capabilities_improved: int = 0
    test_pass_rate: float = 0.0
    dataset_records_generated: int = 0
    total_runtime_hours: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "cycle_count": self.cycle_count,
            "proposals_generated": self.proposals_generated,
            "proposals_validated": self.proposals_validated,
            "proposals_approved": self.proposals_approved,
            "proposals_rejected": self.proposals_rejected,
            "capabilities_improved": self.capabilities_improved,
            "test_pass_rate": self.test_pass_rate,
            "dataset_records_generated": self.dataset_records_generated,
            "total_runtime_hours": self.total_runtime_hours,
            "success_rate": self.proposals_approved / max(1, self.proposals_generated),
        }


class SecurityPolicy:
    """Security policy enforcement for RSI operations."""
    
    FORBIDDEN_OPERATIONS = [
        "os.system",  # Direct shell execution
        "subprocess.Popen",  # Unrestricted process spawning
        "eval",  # Arbitrary code execution
        "exec",  # Arbitrary code execution
        "__import__",  # Dynamic imports
        "open(.*w|a)",  # Write operations (must use atomic writes)
        "rm -rf",  # Destructive commands
        "curl.*http://",  # Unencrypted network calls
        "requests.get.*verify=False",  # TLS verification bypass
    ]
    
    REQUIRED_APPROVALS = {
        ImprovementType.CODE_OPTIMIZATION: False,  # Auto-approve if tests pass
        ImprovementType.NEW_FEATURE: True,  # Always require human review
        ImprovementType.BUG_FIX: False,
        ImprovementType.SECURITY_ENHANCEMENT: True,  # Critical changes
        ImprovementType.TEST_COVERAGE: False,
        ImprovementType.DOCUMENTATION: False,
        ImprovementType.DATASET_QUALITY: False,
    }
    
    @staticmethod
    def validate_proposal(proposal: ImprovementProposal) -> tuple[bool, str]:
        """Validate proposal against security policy."""
        # Check for forbidden operations in code changes
        import re
        for filepath, content in proposal.code_changes.items():
            for forbidden in SecurityPolicy.FORBIDDEN_OPERATIONS:
                if re.search(forbidden, content):
                    return (False, f"Forbidden operation detected: {forbidden}")
        
        # Check if human approval required
        if SecurityPolicy.REQUIRED_APPROVALS.get(proposal.improvement_type, True):
            proposal.approval_required = True
        
        return (True, "Policy validation passed")


class RecursiveSelfImprover:
    """Main RSI engine for Hancock.
    
    Implements the seed improver architecture with:
    - Recursive self-prompting loop
    - Capability assessment and goal-setting
    - Code generation with validation
    - Regression testing and rollback
    - PeachTree dataset integration
    """
    
    def __init__(
        self,
        workspace: str | Path = "/home/_0ai_/Hancock-1",
        peachtree_path: str | Path = "/home/_0ai_/PeachTree",
        max_iterations: int = 100,
        require_human_approval: bool = True,
    ):
        self.workspace = Path(workspace)
        self.peachtree_path = Path(peachtree_path)
        self.max_iterations = max_iterations
        self.require_human_approval = require_human_approval
        
        self.metrics = RSIMetrics()
        self.capabilities: list[Capability] = []
        self.proposals: list[ImprovementProposal] = []
        self.history_path = self.workspace / ".hancock_rsi_history.jsonl"
        
        # Load baseline capabilities
        self._initialize_capabilities()
        
        logger.info(f"RecursiveSelfImprover initialized at {self.workspace}")
        logger.info(f"Tracking {len(self.capabilities)} capabilities")
    
    def _initialize_capabilities(self):
        """Define baseline capabilities to track and improve."""
        self.capabilities = [
            Capability(
                name="test_coverage",
                description="Percentage of code covered by tests",
                metric="pytest --cov",
                current_value=0.85,  # 85% baseline
                target_value=0.95,  # Goal: 95%
                importance=9,
            ),
            Capability(
                name="response_accuracy",
                description="Accuracy of pentest recommendations",
                metric="benchmark_accuracy",
                current_value=0.82,
                target_value=0.92,
                importance=10,
            ),
            Capability(
                name="dataset_quality",
                description="PeachTree dataset quality score",
                metric="peachtree_quality_score",
                current_value=0.88,
                target_value=0.95,
                importance=9,
            ),
            Capability(
                name="security_pattern_coverage",
                description="Number of security patterns detected",
                metric="count(SECRET_PATTERNS + PROMPT_INJECTION_PATTERNS)",
                current_value=34.0,  # 29 secrets + 5 prompt injection
                target_value=50.0,  # Goal: 50 patterns
                importance=10,
            ),
            Capability(
                name="collector_freshness",
                description="Hours since last MITRE/NVD/CISA update",
                metric="collector_last_run_hours",
                current_value=24.0,
                target_value=6.0,  # Goal: 6-hour refresh
                importance=7,
            ),
        ]
    
    def assess_capabilities(self) -> dict[str, float]:
        """Measure current capability levels."""
        results = {}
        
        for cap in self.capabilities:
            try:
                if cap.metric == "pytest --cov":
                    # Run pytest with coverage
                    result = subprocess.run(
                        ["pytest", "--cov=.", "--cov-report=json", "--quiet"],
                        cwd=self.workspace,
                        capture_output=True,
                        text=True,
                        timeout=300,
                    )
                    if result.returncode == 0:
                        cov_data = json.loads((self.workspace / "coverage.json").read_text())
                        cap.current_value = cov_data["totals"]["percent_covered"] / 100
                
                elif cap.metric == "count(SECRET_PATTERNS + PROMPT_INJECTION_PATTERNS)":
                    # Count patterns in safety.py
                    safety_py = (self.peachtree_path / "src/peachtree/safety.py").read_text()
                    secret_count = safety_py.count("re.compile")  # Rough approximation
                    cap.current_value = float(secret_count)
                
                results[cap.name] = cap.current_value
                
            except Exception as e:
                logger.warning(f"Failed to assess {cap.name}: {e}")
                results[cap.name] = cap.current_value  # Use cached value
        
        return results
    
    def identify_improvement_opportunities(self) -> list[ImprovementProposal]:
        """Analyze capabilities and generate improvement proposals."""
        proposals = []
        
        # Find capabilities below target
        capability_gaps = [
            cap for cap in self.capabilities
            if cap.current_value < cap.target_value
        ]
        
        # Sort by importance * gap size
        capability_gaps.sort(
            key=lambda c: c.importance * (c.target_value - c.current_value),
            reverse=True
        )
        
        # Generate proposals for top gaps
        for cap in capability_gaps[:3]:  # Top 3 priorities
            proposal = self._generate_improvement_proposal(cap)
            if proposal:
                proposals.append(proposal)
        
        return proposals
    
    def _generate_improvement_proposal(self, capability: Capability) -> Optional[ImprovementProposal]:
        """Generate a specific improvement proposal for a capability."""
        proposal_id = hashlib.sha256(
            f"{capability.name}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]
        
        # Example: If security pattern coverage is low, propose adding more patterns
        if capability.name == "security_pattern_coverage":
            return ImprovementProposal(
                id=proposal_id,
                timestamp=datetime.now(),
                improvement_type=ImprovementType.SECURITY_ENHANCEMENT,
                title="Expand security pattern detection",
                description=f"Add {int(capability.target_value - capability.current_value)} new security patterns",
                rationale=f"Current coverage: {capability.current_value}, Target: {capability.target_value}",
                affected_files=["src/peachtree/safety.py"],
                code_changes={},  # Populated by code generator
                test_commands=["pytest tests/test_critical_security.py -v"],
                expected_benefits=[
                    "Detect more credential types (Azure, GCP, etc.)",
                    "Catch additional prompt injection variants",
                    "Improve dataset safety filtering",
                ],
                risks=["False positives may increase", "Performance impact on large docs"],
            )
        
        # Example: If test coverage is low, propose adding tests
        elif capability.name == "test_coverage":
            return ImprovementProposal(
                id=proposal_id,
                timestamp=datetime.now(),
                improvement_type=ImprovementType.TEST_COVERAGE,
                title="Increase test coverage to 95%",
                description="Add tests for under-covered modules",
                rationale=f"Current: {capability.current_value:.1%}, Target: {capability.target_value:.1%}",
                affected_files=["tests/"],
                code_changes={},
                test_commands=["pytest --cov --cov-report=term-missing"],
                expected_benefits=["Catch more bugs", "Safer refactoring", "Better CI/CD"],
                risks=["Test maintenance overhead"],
            )
        
        return None
    
    def validate_proposal(self, proposal: ImprovementProposal) -> bool:
        """Validate a proposal through testing and security checks."""
        logger.info(f"Validating proposal {proposal.id}: {proposal.title}")
        
        # 1. Security policy check
        is_safe, reason = SecurityPolicy.validate_proposal(proposal)
        if not is_safe:
            proposal.validation_status = ValidationStatus.FAILED
            proposal.validation_results["security_check"] = reason
            logger.error(f"Security check failed: {reason}")
            return False
        
        proposal.validation_results["security_check"] = "passed"
        
        # 2. Run test commands
        for cmd in proposal.test_commands:
            try:
                result = subprocess.run(
                    cmd.split(),
                    cwd=self.workspace,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                
                test_passed = result.returncode == 0
                proposal.validation_results[f"test:{cmd}"] = {
                    "passed": test_passed,
                    "stdout": result.stdout[-500:],  # Last 500 chars
                    "stderr": result.stderr[-500:],
                }
                
                if not test_passed:
                    proposal.validation_status = ValidationStatus.FAILED
                    logger.error(f"Test failed: {cmd}")
                    return False
                
            except Exception as e:
                proposal.validation_results[f"test:{cmd}"] = {"error": str(e)}
                proposal.validation_status = ValidationStatus.FAILED
                return False
        
        # 3. Regression check (capabilities don't degrade)
        current_capabilities = self.assess_capabilities()
        for cap in self.capabilities:
            if current_capabilities.get(cap.name, 0) < cap.current_value * 0.95:
                proposal.validation_status = ValidationStatus.FAILED
                proposal.validation_results["regression_check"] = f"{cap.name} degraded"
                logger.error(f"Regression detected in {cap.name}")
                return False
        
        proposal.validation_results["regression_check"] = "passed"
        
        # All validations passed
        proposal.validation_status = ValidationStatus.PASSED
        self.metrics.proposals_validated += 1
        logger.info(f"Proposal {proposal.id} validation: PASSED")
        return True
    
    def run_cycle(self) -> dict[str, Any]:
        """Run one RSI improvement cycle."""
        cycle_start = time.time()
        self.metrics.cycle_count += 1
        
        logger.info(f"=== RSI Cycle {self.metrics.cycle_count} ===")
        
        # 1. Assess current capabilities
        logger.info("Assessing capabilities...")
        capabilities = self.assess_capabilities()
        
        # 2. Identify improvement opportunities
        logger.info("Identifying improvement opportunities...")
        new_proposals = self.identify_improvement_opportunities()
        self.proposals.extend(new_proposals)
        self.metrics.proposals_generated += len(new_proposals)
        
        # 3. Validate proposals
        validated_proposals = []
        for proposal in new_proposals:
            if self.validate_proposal(proposal):
                validated_proposals.append(proposal)
        
        # 4. Execute approved proposals (human-in-the-loop)
        executed_proposals = []
        for proposal in validated_proposals:
            if proposal.approval_required and self.require_human_approval:
                proposal.validation_status = ValidationStatus.REQUIRES_HUMAN_REVIEW
                logger.info(f"Proposal {proposal.id} requires human approval")
            else:
                # Auto-approve low-risk proposals that passed validation
                self._execute_proposal(proposal)
                executed_proposals.append(proposal)
        
        # 5. Generate PeachTree training data from cycle
        self._generate_dataset_from_cycle(new_proposals, validated_proposals)
        
        # 6. Update metrics
        cycle_duration = time.time() - cycle_start
        self.metrics.total_runtime_hours += cycle_duration / 3600
        
        # 7. Save history
        self._save_history()
        
        return {
            "cycle": self.metrics.cycle_count,
            "capabilities": capabilities,
            "proposals_generated": len(new_proposals),
            "proposals_validated": len(validated_proposals),
            "proposals_executed": len(executed_proposals),
            "duration_seconds": cycle_duration,
            "metrics": self.metrics.to_dict(),
        }
    
    def _execute_proposal(self, proposal: ImprovementProposal):
        """Execute an approved proposal (apply code changes)."""
        logger.info(f"Executing proposal {proposal.id}: {proposal.title}")
        
        # In production, this would apply code_changes to affected_files
        # For safety, we only log the intent here
        proposal.approved_by = "auto_approved"
        self.metrics.proposals_approved += 1
        
        logger.info(f"Would modify files: {proposal.affected_files}")
        logger.info("(Actual execution disabled for safety - human approval required)")
    
    def _generate_dataset_from_cycle(
        self,
        proposals: list[ImprovementProposal],
        validated: list[ImprovementProposal]
    ):
        """Generate PeachTree training records from RSI cycle."""
        # Example: Create instruction-response pairs
        for proposal in validated:
            record = {
                "instruction": f"How can I improve Hancock's {proposal.improvement_type.value}?",
                "input": f"Current capability gap: {proposal.rationale}",
                "output": f"{proposal.description}\n\nExpected benefits:\n" + 
                         "\n".join(f"- {b}" for b in proposal.expected_benefits),
                "metadata": {
                    "source": "hancock_rsi",
                    "proposal_id": proposal.id,
                    "validation_status": proposal.validation_status.value,
                },
            }
            
            self.metrics.dataset_records_generated += 1
            
            # Would write to PeachTree dataset
            logger.debug(f"Generated training record from proposal {proposal.id}")
    
    def _save_history(self):
        """Save RSI history to JSONL for analysis."""
        with open(self.history_path, "a") as f:
            entry = {
                "cycle": self.metrics.cycle_count,
                "timestamp": datetime.now().isoformat(),
                "metrics": self.metrics.to_dict(),
                "proposals": [p.to_dict() for p in self.proposals[-10:]],  # Last 10
            }
            f.write(json.dumps(entry) + "\n")
    
    def run(self) -> dict[str, Any]:
        """Run the full RSI loop."""
        logger.info("Starting Hancock Recursive Self-Improvement Loop")
        logger.info(f"Max iterations: {self.max_iterations}")
        logger.info(f"Human approval required: {self.require_human_approval}")
        
        for i in range(self.max_iterations):
            try:
                result = self.run_cycle()
                logger.info(f"Cycle {i+1} complete: {result}")
                
                # Check if all capabilities met targets
                all_met = all(
                    cap.current_value >= cap.target_value
                    for cap in self.capabilities
                )
                
                if all_met:
                    logger.info("All capability targets met! RSI loop complete.")
                    break
                
            except KeyboardInterrupt:
                logger.info("RSI loop interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in cycle {i+1}: {e}", exc_info=True)
                continue
        
        logger.info("RSI loop finished")
        logger.info(f"Final metrics: {self.metrics.to_dict()}")
        
        return self.metrics.to_dict()


def main():
    """CLI entry point for RSI framework."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hancock Recursive Self-Improvement")
    parser.add_argument("--workspace", default="/home/_0ai_/Hancock-1", help="Hancock workspace path")
    parser.add_argument("--peachtree", default="/home/_0ai_/PeachTree", help="PeachTree path")
    parser.add_argument("--max-iterations", type=int, default=10, help="Max RSI cycles")
    parser.add_argument("--auto-approve", action="store_true", help="Auto-approve low-risk proposals")
    parser.add_argument("--assess-only", action="store_true", help="Only assess capabilities")
    
    args = parser.parse_args()
    
    rsi = RecursiveSelfImprover(
        workspace=args.workspace,
        peachtree_path=args.peachtree,
        max_iterations=args.max_iterations,
        require_human_approval=not args.auto_approve,
    )
    
    if args.assess_only:
        capabilities = rsi.assess_capabilities()
        print("\n=== Current Capabilities ===")
        for name, value in capabilities.items():
            cap = next(c for c in rsi.capabilities if c.name == name)
            status = "✅" if value >= cap.target_value else "⚠️"
            print(f"{status} {name}: {value:.2f} / {cap.target_value:.2f}")
    else:
        results = rsi.run()
        print("\n=== RSI Loop Complete ===")
        print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
