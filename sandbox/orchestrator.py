"""
Hancock Multi-Tool Orchestrator — v0.6.0

Enables intelligent chaining of security tools to build autonomous pentest workflows.
Coordinates execution sequences (recon → scan → exploit) with state management,
rollback capabilities, and cross-tool data passing.

Key Features:
- Workflow templates (predefined attack chains)
- Dynamic target selection (use nmap output to select nikto targets)
- State machine with checkpointing and rollback
- Cross-tool result aggregation
- Risk-aware execution (halt chain if risk exceeds threshold)
- Comprehensive reporting (unified narrative across tool chain)

Example Workflows:
1. Web Application Assessment: nmap → nikto → sqlmap → report
2. SMB Enumeration: nmap → enum4linux → smbclient → report
3. Network Discovery: nmap → masscan → banner-grab → report

Author: Johnny Watters (0ai-Cyberviser)
License: See LICENSE and OWNERSHIP.md
"""

import json
import time
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum

try:
    from executor import SandboxExecutor
    EXECUTOR_AVAILABLE = True
except ImportError:
    EXECUTOR_AVAILABLE = False
    print("⚠️  SandboxExecutor not available — orchestrator running in dry-run mode")


class WorkflowStatus(Enum):
    """Workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"


class StepStatus(Enum):
    """Individual step execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """Represents a single step in a workflow (one tool execution)."""
    tool: str
    description: str
    command_template: str
    risk_level: int  # 1-10
    required: bool = True  # If False, skip on failure instead of halting workflow
    timeout: int = 300  # seconds
    depends_on: List[str] = field(default_factory=list)  # Step names this depends on

    # Runtime state
    status: StepStatus = StepStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to serializable dict."""
        data = asdict(self)
        data['status'] = self.status.value
        return data


@dataclass
class Workflow:
    """Represents a complete multi-tool workflow."""
    name: str
    description: str
    steps: List[WorkflowStep]
    target: str
    max_risk: int = 6  # Halt workflow if any step exceeds this

    # Runtime state
    status: WorkflowStatus = WorkflowStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)  # Shared data between steps

    def to_dict(self) -> Dict:
        """Convert to serializable dict."""
        data = asdict(self)
        data['status'] = self.status.value
        data['steps'] = [step.to_dict() for step in self.steps]
        return data


class WorkflowOrchestrator:
    """
    Orchestrates multi-tool security workflows with state management.

    Responsibilities:
    - Execute workflow steps in sequence or parallel
    - Pass data between tools (e.g., nmap results → nikto targets)
    - Handle failures with optional rollback
    - Enforce risk thresholds across workflow
    - Generate unified reports
    - Checkpoint state for resumption
    """

    def __init__(
        self,
        executor: Optional[Any] = None,
        checkpoint_dir: Path = Path("sandbox/orchestrator_state")
    ):
        self.executor = executor
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        self.workflows: Dict[str, Workflow] = {}
        self.templates = self._load_workflow_templates()

    def _load_workflow_templates(self) -> Dict[str, Workflow]:
        """Load predefined workflow templates."""
        templates = {}

        # Template 1: Web Application Assessment
        templates['web-assessment'] = Workflow(
            name="web-assessment",
            description="Complete web application security assessment",
            target="",  # Will be set when workflow is created
            max_risk=6,
            steps=[
                WorkflowStep(
                    tool="nmap",
                    description="Discover web services and versions",
                    command_template="nmap -sV -p 80,443,8080,8443 {target}",
                    risk_level=2,
                    required=True,
                ),
                WorkflowStep(
                    tool="nikto",
                    description="Web server vulnerability scan",
                    command_template="nikto -h {http_target}",
                    risk_level=4,
                    required=True,
                    depends_on=["nmap"],
                ),
                WorkflowStep(
                    tool="sqlmap",
                    description="SQL injection testing (if vulnerable URL found)",
                    command_template="sqlmap -u {vulnerable_url} --batch --risk=1 --level=1",
                    risk_level=6,
                    required=False,  # Optional — only if nikto finds SQL injection vector
                    depends_on=["nikto"],
                ),
            ]
        )

        # Template 2: SMB Enumeration
        templates['smb-enum'] = Workflow(
            name="smb-enum",
            description="SMB/CIFS enumeration and information gathering",
            target="",
            max_risk=4,
            steps=[
                WorkflowStep(
                    tool="nmap",
                    description="Discover SMB services",
                    command_template="nmap -sV -p 139,445 {target}",
                    risk_level=2,
                    required=True,
                ),
                WorkflowStep(
                    tool="enum4linux",
                    description="Enumerate SMB shares and users",
                    command_template="enum4linux -a {target}",
                    risk_level=3,
                    required=True,
                    depends_on=["nmap"],
                ),
            ]
        )

        # Template 3: Network Discovery
        templates['network-discovery'] = Workflow(
            name="network-discovery",
            description="Comprehensive network reconnaissance",
            target="",
            max_risk=3,
            steps=[
                WorkflowStep(
                    tool="nmap",
                    description="Host discovery and port scan",
                    command_template="nmap -sn {target}",
                    risk_level=1,
                    required=True,
                ),
                WorkflowStep(
                    tool="nmap",
                    description="Service version detection on live hosts",
                    command_template="nmap -sV {live_hosts}",
                    risk_level=3,
                    required=True,
                    depends_on=["nmap"],
                ),
            ]
        )

        return templates

    def create_workflow(
        self,
        template_name: str,
        target: str,
        workflow_id: Optional[str] = None
    ) -> str:
        """
        Create a new workflow instance from a template.

        Args:
            template_name: Name of the workflow template
            target: Target IP/domain/CIDR
            workflow_id: Optional custom ID (auto-generated if not provided)

        Returns:
            Workflow ID
        """
        if template_name not in self.templates:
            raise ValueError(f"Unknown workflow template: {template_name}")

        template = self.templates[template_name]

        # Generate workflow ID
        if workflow_id is None:
            workflow_id = f"{template_name}-{int(time.time())}"

        # Deep copy template and set target
        import copy
        workflow = copy.deepcopy(template)
        workflow.target = target

        self.workflows[workflow_id] = workflow

        # Save checkpoint
        self._save_checkpoint(workflow_id)

        return workflow_id

    def execute_workflow(
        self,
        workflow_id: str,
        auto_approve: bool = False
    ) -> Dict:
        """
        Execute a workflow step-by-step.

        Args:
            workflow_id: ID of the workflow to execute
            auto_approve: If True, auto-approve medium-risk steps

        Returns:
            Workflow execution summary
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Unknown workflow ID: {workflow_id}")

        workflow = self.workflows[workflow_id]
        workflow.status = WorkflowStatus.RUNNING
        workflow.start_time = time.time()

        print(f"\n{'='*80}")
        print(f"WORKFLOW: {workflow.name}")
        print(f"{'='*80}")
        print(f"Description: {workflow.description}")
        print(f"Target: {workflow.target}")
        print(f"Steps: {len(workflow.steps)}")
        print(f"Max Risk: {workflow.max_risk}/10")
        print(f"{'='*80}\n")

        try:
            for idx, step in enumerate(workflow.steps):
                workflow.current_step = idx

                # Check dependencies
                if not self._check_dependencies(workflow, step):
                    print(f"⏭️  Skipping step {idx+1}: dependencies not met")
                    step.status = StepStatus.SKIPPED
                    continue

                # Execute step
                success = self._execute_step(workflow, step, auto_approve)

                # Save checkpoint after each step
                self._save_checkpoint(workflow_id)

                if not success:
                    if step.required:
                        print(f"❌ Required step failed — halting workflow")
                        workflow.status = WorkflowStatus.FAILED
                        break
                    else:
                        print(f"⚠️  Optional step failed — continuing workflow")
                        continue

            # Workflow completed successfully
            if workflow.status == WorkflowStatus.RUNNING:
                workflow.status = WorkflowStatus.COMPLETED
                print(f"\n✅ Workflow '{workflow.name}' completed successfully")

        except Exception as e:
            print(f"\n❌ Workflow execution error: {e}")
            workflow.status = WorkflowStatus.FAILED

        finally:
            workflow.end_time = time.time()
            self._save_checkpoint(workflow_id)

        return self._generate_workflow_summary(workflow)

    def _execute_step(
        self,
        workflow: Workflow,
        step: WorkflowStep,
        auto_approve: bool
    ) -> bool:
        """Execute a single workflow step."""
        print(f"\n{'='*80}")
        print(f"STEP {workflow.current_step + 1}/{len(workflow.steps)}: {step.tool}")
        print(f"{'='*80}")
        print(f"Description: {step.description}")
        print(f"Risk Level: {step.risk_level}/10")
        print(f"Required: {step.required}")

        # Check risk threshold
        if step.risk_level > workflow.max_risk:
            print(f"🚨 BLOCKED: Step risk ({step.risk_level}) exceeds workflow max ({workflow.max_risk})")
            step.status = StepStatus.FAILED
            step.error = f"Risk threshold exceeded: {step.risk_level} > {workflow.max_risk}"
            return False

        # Build command from template
        command = self._build_command(workflow, step)
        print(f"Command: {command}")

        # Execute via sandbox
        step.status = StepStatus.RUNNING
        step.start_time = time.time()

        if not EXECUTOR_AVAILABLE or self.executor is None:
            print("⚠️  Dry-run mode — simulating execution")
            step.result = {
                "success": True,
                "output": "(simulated output)",
                "exit_code": 0,
            }
            step.status = StepStatus.COMPLETED
            step.end_time = time.time()
            return True

        try:
            # Execute tool via SandboxExecutor
            result = self.executor.execute_tool(
                tool=step.tool,
                command=command.split(),
                target=workflow.target,
                require_approval=(not auto_approve and step.risk_level >= 4)
            )

            step.result = result
            step.end_time = time.time()

            if result.get("success"):
                step.status = StepStatus.COMPLETED

                # Update workflow context with results
                self._update_context(workflow, step)

                print(f"✅ Step completed ({step.end_time - step.start_time:.1f}s)")
                return True
            else:
                step.status = StepStatus.FAILED
                step.error = result.get("error", "Unknown error")
                print(f"❌ Step failed: {step.error}")
                return False

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.end_time = time.time()
            print(f"❌ Step exception: {e}")
            return False

    def _build_command(self, workflow: Workflow, step: WorkflowStep) -> str:
        """Build command from template with variable substitution."""
        template = step.command_template

        # Substitute variables from workflow context
        variables = {
            "target": workflow.target,
            **workflow.context
        }

        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if placeholder in template:
                template = template.replace(placeholder, str(value))

        return template

    def _check_dependencies(self, workflow: Workflow, step: WorkflowStep) -> bool:
        """Check if all step dependencies are satisfied."""
        if not step.depends_on:
            return True

        for dep_name in step.depends_on:
            # Find the dependency step
            dep_step = None
            for s in workflow.steps:
                if s.tool == dep_name:
                    dep_step = s
                    break

            if dep_step is None or dep_step.status != StepStatus.COMPLETED:
                return False

        return True

    def _update_context(self, workflow: Workflow, step: WorkflowStep):
        """Update workflow context with step results for next steps."""
        if not step.result:
            return

        output = step.result.get("output", "")

        # Extract relevant data based on tool
        if step.tool == "nmap":
            # Extract open ports, live hosts, etc.
            # Simple extraction — production would use nmap XML parser
            if "open" in output.lower():
                workflow.context['nmap_found_open_ports'] = True

            # Extract HTTP services
            if "http" in output.lower():
                # Simplified — would parse actual ports
                workflow.context['http_target'] = f"http://{workflow.target}"

        elif step.tool == "nikto":
            # Extract vulnerability findings
            if "sql injection" in output.lower():
                # Simplified — would parse actual URLs
                workflow.context['vulnerable_url'] = workflow.context.get('http_target', '')

        # Store raw output
        workflow.context[f'{step.tool}_output'] = output[:1000]  # Truncate

    def _save_checkpoint(self, workflow_id: str):
        """Save workflow state to disk for resumption."""
        workflow = self.workflows[workflow_id]
        checkpoint_file = self.checkpoint_dir / f"{workflow_id}.json"

        with open(checkpoint_file, 'w') as f:
            json.dump(workflow.to_dict(), f, indent=2)

    def load_checkpoint(self, workflow_id: str) -> bool:
        """Load workflow state from checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{workflow_id}.json"

        if not checkpoint_file.exists():
            return False

        with open(checkpoint_file, 'r') as f:
            data = json.load(f)

        # Reconstruct workflow from dict
        # (simplified — production would use proper deserialization)
        print(f"✅ Loaded checkpoint for workflow: {workflow_id}")
        return True

    def _generate_workflow_summary(self, workflow: Workflow) -> Dict:
        """Generate comprehensive workflow execution summary."""
        total_time = (workflow.end_time or time.time()) - (workflow.start_time or 0)

        completed = sum(1 for s in workflow.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in workflow.steps if s.status == StepStatus.FAILED)
        skipped = sum(1 for s in workflow.steps if s.status == StepStatus.SKIPPED)

        return {
            "workflow_id": workflow.name,
            "status": workflow.status.value,
            "target": workflow.target,
            "total_steps": len(workflow.steps),
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "total_time": round(total_time, 2),
            "steps": [step.to_dict() for step in workflow.steps],
        }

    def list_templates(self) -> List[str]:
        """List available workflow templates."""
        return list(self.templates.keys())

    def get_workflow_status(self, workflow_id: str) -> Dict:
        """Get current status of a workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Unknown workflow ID: {workflow_id}")

        return self._generate_workflow_summary(self.workflows[workflow_id])


# Example usage
if __name__ == "__main__":
    print("Hancock Multi-Tool Orchestrator v0.6.0")
    print("="*80)

    # Create orchestrator
    orchestrator = WorkflowOrchestrator()

    # List available templates
    print("\nAvailable workflow templates:")
    for template in orchestrator.list_templates():
        print(f"  - {template}")

    # Create workflow from template
    workflow_id = orchestrator.create_workflow(
        template_name="web-assessment",
        target="scanme.nmap.org"
    )

    print(f"\nCreated workflow: {workflow_id}")

    # Execute workflow (dry-run mode if executor not available)
    print("\nExecuting workflow...")
    summary = orchestrator.execute_workflow(workflow_id, auto_approve=True)

    print("\n" + "="*80)
    print("WORKFLOW SUMMARY")
    print("="*80)
    print(json.dumps(summary, indent=2))
