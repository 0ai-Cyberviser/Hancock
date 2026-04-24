#!/usr/bin/env python3
"""
Hancock API Client Example — v0.8.0

Demonstrates how to interact with the Hancock REST API programmatically.

Usage:
    python3 examples/api_client_example.py
"""

import requests
import time
import json
from typing import Dict, Optional


class HancockAPIClient:
    """Simple Python client for Hancock API."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = "hancock_test_key"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }

    def health_check(self) -> Dict:
        """Check API health status."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def create_workflow(
        self,
        workflow_type: str,
        target: str,
        client_name: str = "API Client",
        webhook_url: Optional[str] = None,
        auto_approve: bool = True
    ) -> Dict:
        """Create and execute a workflow."""
        payload = {
            "workflow_type": workflow_type,
            "target": target,
            "client_name": client_name,
            "auto_approve": auto_approve
        }

        if webhook_url:
            payload["webhook_url"] = webhook_url

        response = requests.post(
            f"{self.base_url}/v1/workflows",
            headers=self.headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def get_workflow_status(self, job_id: str) -> Dict:
        """Get workflow execution status."""
        response = requests.get(
            f"{self.base_url}/v1/workflows/{job_id}",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    def wait_for_completion(self, job_id: str, timeout: int = 600, poll_interval: int = 5) -> Dict:
        """Poll workflow status until completion or timeout."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_workflow_status(job_id)

            if status["status"] in ["completed", "failed"]:
                return status

            print(f"⏳ Status: {status['status']} | Target: {status['target']}")

            if status.get("progress"):
                prog = status["progress"]
                print(f"   Progress: {prog['current_step']}/{prog['total_steps']} steps ({prog['percentage']}%)")

            time.sleep(poll_interval)

        raise TimeoutError(f"Workflow did not complete within {timeout} seconds")

    def download_report(self, report_id: str, format: str = "markdown", output_path: Optional[str] = None) -> bytes:
        """Download report in specified format."""
        response = requests.get(
            f"{self.base_url}/v1/reports/{report_id}/{format}",
            headers=self.headers
        )
        response.raise_for_status()

        content = response.content

        if output_path:
            with open(output_path, 'wb') as f:
                f.write(content)
            print(f"✅ Report saved to: {output_path}")

        return content

    def list_workflows(self, status: Optional[str] = None, limit: int = 10) -> list:
        """List recent workflows."""
        params = {"limit": limit}
        if status:
            params["status"] = status

        response = requests.get(
            f"{self.base_url}/v1/workflows",
            headers=self.headers,
            params=params
        )
        response.raise_for_status()
        return response.json()


def main():
    """Example usage of Hancock API client."""
    print("="*80)
    print("HANCOCK API CLIENT EXAMPLE")
    print("="*80)
    print()

    # Initialize client
    client = HancockAPIClient(
        base_url="http://localhost:8000",
        api_key="hancock_test_key"
    )

    # Health check
    print("1. Checking API health...")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    print(f"   Version: {health['version']}")
    print(f"   Hancock available: {health['hancock_available']}")
    print()

    # Create workflow
    print("2. Creating web assessment workflow...")
    workflow = client.create_workflow(
        workflow_type="web-assessment",
        target="scanme.nmap.org",
        client_name="Example Corp"
    )
    job_id = workflow["job_id"]
    print(f"   Job ID: {job_id}")
    print(f"   Status: {workflow['status']}")
    print(f"   Message: {workflow['message']}")
    print()

    # Wait for completion
    print("3. Waiting for workflow to complete...")
    try:
        final_status = client.wait_for_completion(job_id, timeout=300)

        print()
        print(f"✅ Workflow completed!")
        print(f"   Status: {final_status['status']}")

        if final_status.get("report_id"):
            report_id = final_status["report_id"]
            print(f"   Report ID: {report_id}")

            # Download reports
            print()
            print("4. Downloading reports...")

            # Markdown report
            client.download_report(
                report_id,
                format="markdown",
                output_path=f"{report_id}.md"
            )

            # JSON report
            client.download_report(
                report_id,
                format="json",
                output_path=f"{report_id}.json"
            )

            # HTML report
            client.download_report(
                report_id,
                format="html",
                output_path=f"{report_id}.html"
            )

        elif final_status.get("error"):
            print(f"   Error: {final_status['error']}")

    except TimeoutError as e:
        print(f"⏱️  {e}")

    # List recent workflows
    print()
    print("5. Listing recent workflows...")
    workflows = client.list_workflows(limit=5)
    print(f"   Found {len(workflows)} workflows:")
    for wf in workflows:
        print(f"   - {wf['job_id']}: {wf['status']} | {wf['workflow_type']} | {wf['target']}")

    print()
    print("="*80)
    print("Example complete!")
    print("="*80)


if __name__ == "__main__":
    main()
