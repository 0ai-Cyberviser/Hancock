#!/usr/bin/env python3
"""
Hancock Multi-Tool Orchestration Demo — v0.6.0

Demonstrates intelligent workflow chaining with the WorkflowOrchestrator.

Usage:
    python3 sandbox/demo_orchestrator.py
"""

import os
import sys
from pathlib import Path

# Add sandbox to path
sys.path.append(str(Path(__file__).parent))

from orchestrator import WorkflowOrchestrator
from executor import SandboxExecutor

def demo_dry_run():
    """Demo orchestrator in dry-run mode (no actual tool execution)."""
    print("=" * 80)
    print("HANCOCK MULTI-TOOL ORCHESTRATOR DEMO — DRY RUN")
    print("=" * 80)
    print()

    # Create orchestrator without executor (dry-run mode)
    orchestrator = WorkflowOrchestrator()

    print("Available workflow templates:")
    for template in orchestrator.list_templates():
        print(f"  ✓ {template}")
    print()

    # Create web assessment workflow
    print("Creating web-assessment workflow...")
    workflow_id = orchestrator.create_workflow(
        template_name="web-assessment",
        target="scanme.nmap.org"
    )
    print(f"Workflow created: {workflow_id}\n")

    # Execute workflow
    print("Executing workflow (dry-run mode)...\n")
    summary = orchestrator.execute_workflow(workflow_id, auto_approve=True)

    # Display summary
    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print(f"Status: {summary['status']}")
    print(f"Target: {summary['target']}")
    print(f"Total steps: {summary['total_steps']}")
    print(f"Completed: {summary['completed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Total time: {summary['total_time']:.2f}s")
    print()

    print("Per-step breakdown:")
    for step in summary['steps']:
        icon = "✅" if step['status'] == "completed" else "❌"
        elapsed = step.get('elapsed', 0)
        print(f"  {icon} {step['tool']}: {step['description']}")
        print(f"     Risk: {step['risk_level']}/10 | Time: {elapsed:.2f}s")
    print()

    print("=" * 80)
    print("Demo complete! Run with real tools:")
    print("  export HANCOCK_AUTHORIZED_SCOPES='192.168.1.0/24'")
    print("  python3 sandbox/demo_orchestrator.py --live")
    print("=" * 80)

def demo_live():
    """Demo orchestrator with real tool execution in sandbox."""
    print("=" * 80)
    print("HANCOCK MULTI-TOOL ORCHESTRATOR DEMO — LIVE MODE")
    print("=" * 80)
    print()

    # Check for authorized scopes
    scopes = os.getenv("HANCOCK_AUTHORIZED_SCOPES", "").split(",")
    if not scopes or scopes == [""]:
        print("❌ Error: HANCOCK_AUTHORIZED_SCOPES not configured")
        print("Set authorized targets: export HANCOCK_AUTHORIZED_SCOPES='192.168.1.0/24'")
        return

    print(f"Authorized scopes: {', '.join(scopes)}\n")

    # Create executor and orchestrator
    executor = SandboxExecutor(authorized_scopes=scopes)
    orchestrator = WorkflowOrchestrator(executor=executor)

    # Create network discovery workflow
    print("Creating network-discovery workflow...")
    workflow_id = orchestrator.create_workflow(
        template_name="network-discovery",
        target=scopes[0]
    )
    print(f"Workflow created: {workflow_id}\n")

    # Execute workflow
    print("Executing workflow (LIVE MODE)...\n")
    summary = orchestrator.execute_workflow(workflow_id, auto_approve=True)

    # Display summary
    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)
    print(f"Status: {summary['status']}")
    print(f"Target: {summary['target']}")
    print(f"Completed: {summary['completed']}/{summary['total_steps']} steps")
    print()

    print("Results:")
    for step in summary['steps']:
        if step['result']:
            print(f"\n{step['tool']} output:")
            print(step['result'].get('output', 'No output')[:500])
    print()

    print("=" * 80)
    print("Live demo complete!")
    print("=" * 80)

if __name__ == "__main__":
    if "--live" in sys.argv:
        demo_live()
    else:
        demo_dry_run()
