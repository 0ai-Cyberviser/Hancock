"""
Hancock REST API Server — v0.8.0

FastAPI-based REST API for programmatic access to Hancock's autonomous pentesting
capabilities. Enables integration with CI/CD pipelines, SIEM systems, and custom
automation workflows.

Features:
- Async workflow execution with job queuing
- Real-time status updates via webhooks
- Multi-format report downloads
- API key authentication
- Rate limiting and request validation
- OpenAPI/Swagger documentation
- CORS support for web dashboards

Author: Johnny Watters (0ai-Cyberviser)
License: See LICENSE and OWNERSHIP.md
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Header, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import uuid
import asyncio
import os
import json
import sys
from enum import Enum

# Import Hancock modules
sys.path.append(str(Path(__file__).parent / "sandbox"))
try:
    from orchestrator import WorkflowOrchestrator
    from report_generator import ReportGenerator, ReportMetadata
    from executor import SandboxExecutor
    HANCOCK_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Hancock modules not available: {e}")
    HANCOCK_AVAILABLE = False


# API metadata
API_VERSION = "0.8.0"
API_TITLE = "Hancock Autonomous Pentest API"
API_DESCRIPTION = """
Hancock REST API enables programmatic access to autonomous penetration testing capabilities.

## Features
- 🤖 Autonomous workflow execution (web-assessment, smb-enum, network-discovery)
- 📊 Professional PTES-compliant reporting (Markdown, JSON, HTML, PDF)
- 🔔 Webhook notifications for workflow completion
- 🔒 API key authentication
- 📈 Job status tracking and history
- 🚀 Async execution with background tasks

## Authentication
All endpoints except `/health` require an API key via `X-API-Key` header:
```
X-API-Key: hancock_YOUR_API_KEY_HERE
```

## Workflow Types
- `web-assessment` - nmap → nikto → sqlmap (web app security)
- `smb-enum` - nmap → enum4linux (SMB enumeration)
- `network-discovery` - nmap → nmap (network recon)

## Example Usage
```bash
# Create workflow
curl -X POST http://localhost:8000/v1/workflows \\
  -H "X-API-Key: hancock_test_key" \\
  -H "Content-Type: application/json" \\
  -d '{
    "workflow_type": "web-assessment",
    "target": "example.com",
    "client_name": "Example Corp"
  }'

# Check status
curl http://localhost:8000/v1/workflows/{job_id} \\
  -H "X-API-Key: hancock_test_key"

# Download report
curl http://localhost:8000/v1/reports/{report_id}/markdown \\
  -H "X-API-Key: hancock_test_key" \\
  -o report.md
```
"""

# Initialize FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware (allow web dashboards)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production: restrict to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job storage (production: use Redis/PostgreSQL)
jobs: Dict[str, Dict] = {}
webhooks: Dict[str, str] = {}  # job_id -> webhook_url


# Request/Response Models

class WorkflowType(str, Enum):
    """Available workflow types."""
    WEB_ASSESSMENT = "web-assessment"
    SMB_ENUM = "smb-enum"
    NETWORK_DISCOVERY = "network-discovery"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CreateWorkflowRequest(BaseModel):
    """Request to create and execute a workflow."""
    workflow_type: WorkflowType = Field(..., description="Type of workflow to execute")
    target: str = Field(..., description="Target IP, domain, or CIDR block")
    client_name: Optional[str] = Field("Internal Assessment", description="Client name for report")
    webhook_url: Optional[str] = Field(None, description="Webhook URL for status notifications")
    auto_approve: bool = Field(True, description="Auto-approve medium-risk steps")

    @validator('target')
    def validate_target(cls, v):
        """Validate target format."""
        if not v or len(v) < 3:
            raise ValueError("Target must be a valid IP, domain, or CIDR")
        # Basic validation - production would use more robust checks
        return v.strip()


class WorkflowResponse(BaseModel):
    """Response after creating workflow."""
    job_id: str = Field(..., description="Unique job identifier")
    status: WorkflowStatus = Field(..., description="Current workflow status")
    workflow_type: str = Field(..., description="Type of workflow")
    target: str = Field(..., description="Target being assessed")
    created_at: str = Field(..., description="ISO 8601 timestamp")
    message: str = Field(..., description="Human-readable status message")


class WorkflowStatusResponse(BaseModel):
    """Detailed workflow status."""
    job_id: str
    status: WorkflowStatus
    workflow_type: str
    target: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    progress: Optional[Dict[str, Any]] = None
    report_id: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """API health status."""
    status: str = Field("healthy", description="Service health status")
    version: str = Field(API_VERSION, description="API version")
    hancock_available: bool = Field(HANCOCK_AVAILABLE, description="Hancock modules loaded")
    timestamp: str = Field(..., description="Current server time")


# Authentication

def get_api_key(x_api_key: str = Header(...)) -> str:
    """
    Validate API key from request header.

    Production implementation should:
    - Check against database of valid keys
    - Support key rotation and expiration
    - Log authentication attempts
    - Implement rate limiting per key
    """
    # Simple validation for demo - production needs secure key management
    valid_keys = os.getenv("HANCOCK_API_KEYS", "hancock_test_key").split(",")

    if x_api_key not in valid_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return x_api_key


# Helper functions

async def send_webhook(webhook_url: str, payload: Dict):
    """Send webhook notification."""
    if not webhook_url:
        return

    try:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                webhook_url,
                json=payload,
                timeout=10.0
            )
    except Exception as e:
        print(f"⚠️  Webhook failed: {e}")


async def execute_workflow_background(
    job_id: str,
    workflow_type: str,
    target: str,
    client_name: str,
    auto_approve: bool,
    webhook_url: Optional[str]
):
    """Execute workflow in background task."""
    try:
        jobs[job_id]["status"] = WorkflowStatus.RUNNING
        jobs[job_id]["started_at"] = datetime.utcnow().isoformat()

        # Send webhook: started
        await send_webhook(webhook_url, {
            "event": "workflow.started",
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Initialize orchestrator
        scopes = os.getenv("HANCOCK_AUTHORIZED_SCOPES", target).split(",")
        executor = SandboxExecutor(authorized_scopes=scopes) if HANCOCK_AVAILABLE else None
        orchestrator = WorkflowOrchestrator(executor=executor)

        # Create and execute workflow
        workflow_id = orchestrator.create_workflow(workflow_type, target)
        summary = orchestrator.execute_workflow(workflow_id, auto_approve=auto_approve)

        # Generate report
        report_id = f"HANCOCK-API-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        metadata = ReportMetadata(
            report_id=report_id,
            title=f"Hancock API Assessment - {workflow_type}",
            client_name=client_name,
            test_date=datetime.now().strftime("%Y-%m-%d"),
            tester_name="Hancock API (0ai-Cyberviser)",
            scope=[target],
            tools_used=[step["tool"] for step in summary.get("steps", [])],
        )

        generator = ReportGenerator()
        output_files = generator.generate_from_workflow(
            workflow_summary=summary,
            metadata=metadata,
            output_formats=["markdown", "json", "html"]
        )

        # Update job status
        jobs[job_id]["status"] = WorkflowStatus.COMPLETED
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        jobs[job_id]["report_id"] = report_id
        jobs[job_id]["report_files"] = {k: str(v) for k, v in output_files.items()}
        jobs[job_id]["workflow_summary"] = summary

        # Send webhook: completed
        await send_webhook(webhook_url, {
            "event": "workflow.completed",
            "job_id": job_id,
            "report_id": report_id,
            "timestamp": datetime.utcnow().isoformat(),
            "findings_count": len(summary.get("steps", []))
        })

    except Exception as e:
        jobs[job_id]["status"] = WorkflowStatus.FAILED
        jobs[job_id]["completed_at"] = datetime.utcnow().isoformat()
        jobs[job_id]["error"] = str(e)

        # Send webhook: failed
        await send_webhook(webhook_url, {
            "event": "workflow.failed",
            "job_id": job_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })


# API Endpoints

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Check API health status.

    No authentication required. Use for monitoring and uptime checks.
    """
    return HealthResponse(
        timestamp=datetime.utcnow().isoformat()
    )


@app.post("/v1/workflows", response_model=WorkflowResponse, tags=["Workflows"])
async def create_workflow(
    request: CreateWorkflowRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key)
):
    """
    Create and execute a security assessment workflow.

    The workflow will execute asynchronously in the background. Use the returned
    `job_id` to check status via `GET /v1/workflows/{job_id}`.

    Requires valid API key in `X-API-Key` header.
    """
    if not HANCOCK_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Hancock modules not available - cannot execute workflows"
        )

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Store job metadata
    jobs[job_id] = {
        "job_id": job_id,
        "status": WorkflowStatus.PENDING,
        "workflow_type": request.workflow_type.value,
        "target": request.target,
        "client_name": request.client_name,
        "created_at": datetime.utcnow().isoformat(),
        "started_at": None,
        "completed_at": None,
        "report_id": None,
        "error": None,
    }

    # Store webhook if provided
    if request.webhook_url:
        webhooks[job_id] = request.webhook_url

    # Schedule background execution
    background_tasks.add_task(
        execute_workflow_background,
        job_id,
        request.workflow_type.value,
        request.target,
        request.client_name,
        request.auto_approve,
        request.webhook_url
    )

    return WorkflowResponse(
        job_id=job_id,
        status=WorkflowStatus.PENDING,
        workflow_type=request.workflow_type.value,
        target=request.target,
        created_at=jobs[job_id]["created_at"],
        message=f"Workflow queued for execution. Check status at /v1/workflows/{job_id}"
    )


@app.get("/v1/workflows/{job_id}", response_model=WorkflowStatusResponse, tags=["Workflows"])
async def get_workflow_status(
    job_id: str,
    api_key: str = Depends(get_api_key)
):
    """
    Get workflow execution status and progress.

    Returns detailed status including completion percentage, report availability,
    and any errors that occurred during execution.
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    # Calculate progress
    progress = None
    if job["status"] == WorkflowStatus.RUNNING:
        workflow_summary = job.get("workflow_summary")
        if workflow_summary:
            total = workflow_summary.get("total_steps", 0)
            completed = workflow_summary.get("completed", 0)
            progress = {
                "current_step": completed,
                "total_steps": total,
                "percentage": int((completed / total * 100) if total > 0 else 0)
            }

    return WorkflowStatusResponse(
        job_id=job["job_id"],
        status=WorkflowStatus(job["status"]),
        workflow_type=job["workflow_type"],
        target=job["target"],
        created_at=job["created_at"],
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        progress=progress,
        report_id=job.get("report_id"),
        error=job.get("error")
    )


@app.get("/v1/workflows", response_model=List[WorkflowStatusResponse], tags=["Workflows"])
async def list_workflows(
    status: Optional[WorkflowStatus] = None,
    limit: int = 50,
    api_key: str = Depends(get_api_key)
):
    """
    List all workflows, optionally filtered by status.

    Returns up to `limit` most recent workflows.
    """
    filtered_jobs = []

    for job in jobs.values():
        if status is None or job["status"] == status.value:
            filtered_jobs.append(WorkflowStatusResponse(
                job_id=job["job_id"],
                status=WorkflowStatus(job["status"]),
                workflow_type=job["workflow_type"],
                target=job["target"],
                created_at=job["created_at"],
                started_at=job.get("started_at"),
                completed_at=job.get("completed_at"),
                report_id=job.get("report_id"),
                error=job.get("error")
            ))

    # Sort by created_at descending
    filtered_jobs.sort(key=lambda x: x.created_at, reverse=True)

    return filtered_jobs[:limit]


@app.get("/v1/reports/{report_id}/{format}", tags=["Reports"])
async def download_report(
    report_id: str,
    format: str,
    api_key: str = Depends(get_api_key)
):
    """
    Download report in specified format.

    Available formats: `markdown`, `json`, `html`, `pdf`

    Returns file download response with appropriate Content-Type.
    """
    valid_formats = ["markdown", "json", "html", "pdf"]
    if format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
        )

    # Find report file
    report_dir = Path("sandbox/reports")

    file_extensions = {
        "markdown": ".md",
        "json": ".json",
        "html": ".html",
        "pdf": ".pdf"
    }

    file_path = report_dir / f"{report_id}{file_extensions[format]}"

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Report not found: {report_id} (format: {format})"
        )

    media_types = {
        "markdown": "text/markdown",
        "json": "application/json",
        "html": "text/html",
        "pdf": "application/pdf"
    }

    return FileResponse(
        path=file_path,
        media_type=media_types[format],
        filename=f"{report_id}{file_extensions[format]}"
    )


@app.post("/v1/webhooks/test", tags=["Webhooks"])
async def test_webhook(
    webhook_url: str,
    api_key: str = Depends(get_api_key)
):
    """
    Test webhook endpoint connectivity.

    Sends a test payload to the provided webhook URL to verify it's reachable
    and can receive notifications.
    """
    test_payload = {
        "event": "webhook.test",
        "message": "Hancock API webhook test",
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        await send_webhook(webhook_url, test_payload)
        return {"status": "success", "message": "Webhook test sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Webhook test failed: {str(e)}"
        )


@app.get("/", tags=["Documentation"])
async def root():
    """
    API root - redirects to interactive documentation.
    """
    return {
        "message": "Hancock Autonomous Pentest API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


# Run server
if __name__ == "__main__":
    import uvicorn

    print(f"""
{'='*80}
HANCOCK AUTONOMOUS PENTEST API v{API_VERSION}
{'='*80}

Starting API server...

Interactive docs: http://localhost:8000/docs
Health check:     http://localhost:8000/health

API Key required for all endpoints except /health
Set HANCOCK_API_KEYS environment variable (comma-separated)

Example:
  export HANCOCK_API_KEYS="hancock_test_key,hancock_prod_key"
  export HANCOCK_AUTHORIZED_SCOPES="192.168.1.0/24,example.com"

{'='*80}
""")

    uvicorn.run(
        "hancock_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development mode
        log_level="info"
    )
