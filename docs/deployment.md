# Deployment Guide

This guide covers all supported deployment targets for Hancock.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Docker](#docker)
- [Docker Compose](#docker-compose)
- [Kubernetes](#kubernetes)
- [Helm](#helm)
- [Terraform (AWS ECS Fargate)](#terraform-aws-ecs-fargate)
- [Fly.io](#flyio)

---

## Prerequisites

- Python 3.10+
- Docker 24+ / Docker Compose v2
- `kubectl` (Kubernetes deployments)
- Helm 3 (Helm deployments)
- Terraform 1.5+ (AWS deployments)

Run the pre-flight check before deploying:

```bash
python deploy/startup_checks.py
```

This validates Python version, required packages, environment variables, and Hancock modules.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `HANCOCK_LLM_BACKEND` | No | `ollama` | Backend: `ollama`, `nvidia`, or `openai` |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL (without `/v1`) |
| `OLLAMA_MODEL` | No | `llama3.1:8b` | Default chat model |
| `OLLAMA_CODER_MODEL` | No | `qwen2.5-coder:7b` | Code generation model |
| `NVIDIA_API_KEY` | Conditional | — | Required when `HANCOCK_LLM_BACKEND=nvidia` |
| `OPENAI_API_KEY` | Conditional | — | Required for `HANCOCK_LLM_BACKEND=openai` and OpenAI fallback |
| `OPENAI_ORG_ID` | No | — | Optional OpenAI organization ID |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | Default OpenAI chat model |
| `OPENAI_CODER_MODEL` | No | `gpt-4o` | OpenAI code generation model |
| `HANCOCK_MODEL` | No | `mistralai/mistral-7b-instruct-v0.3` | NVIDIA model override |
| `HANCOCK_CODER_MODEL` | No | `qwen/qwen2.5-coder-32b-instruct` | NVIDIA coder model override |
| `HANCOCK_API_KEY` | No | — | Bearer token for API authentication |
| `HANCOCK_WEBHOOK_SECRET` | No | — | HMAC secret for webhook signature verification |
| `LOG_LEVEL` | No | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `HANCOCK_PORT` | No | `5000` | Server port |

Store secrets in a `.env` file (never commit it) or use your platform's secrets manager.

For the canonical fallback behavior and precedence order, see **Backend Selection** in the repository `README.md`.

---

## Docker

The root `Dockerfile` builds a production image using Python 3.11-slim with a non-root `hancock` user.

```bash
# Build
docker build -t hancock:latest .

# Run with Ollama backend
docker run -d \
  --name hancock \
  -p 5000:5000 \
  -e HANCOCK_LLM_BACKEND=ollama \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  hancock:latest

# Run with NVIDIA NIM backend
docker run -d \
  --name hancock \
  -p 5000:5000 \
  -e HANCOCK_LLM_BACKEND=nvidia \
  -e NVIDIA_API_KEY=<your-key> \
  hancock:latest
```

The container exposes port `5000` and includes a built-in health check (`GET /health`, 30 s interval, 10 s timeout, 3 retries).

Published images are available at `ghcr.io/cyberviser/hancock` and tagged with semver (e.g., `ghcr.io/cyberviser/hancock:v0.5.0`).

---

## Docker Compose

`docker-compose.yml` in the repository root brings up the full local stack:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `ollama` | `ollama/ollama:latest` | 11434 | Local LLM backend |
| `hancock` | Built from `Dockerfile` | 5000 | AI security agent |

`deploy/docker-compose.yml` includes Prometheus and Grafana in addition to the above.

```bash
# Start all services
docker compose up -d

# Pull a model (first run only)
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull qwen2.5-coder:7b

# View logs
docker compose logs -f hancock

# Stop
docker compose down
```

Override defaults with an env file:

```bash
HANCOCK_API_KEY=secret docker compose up -d
```

---

## Kubernetes

Manifests live in `deploy/k8s/`. Apply them in order:

```bash
# 1. ConfigMap — non-secret configuration
kubectl apply -f deploy/k8s/configmap.yaml

# 2. Secrets — edit the file first to add base64-encoded values
#    kubectl create secret generic hancock-secrets \
#      --from-literal=NVIDIA_API_KEY=<value> \
#      --from-literal=HANCOCK_WEBHOOK_SECRET=<value>
kubectl apply -f deploy/k8s/secret.yaml

# 3. Deployment — 2 replicas, rolling update, resource limits
kubectl apply -f deploy/k8s/deployment.yaml

# 4. Service — ClusterIP, Prometheus scrape annotations
kubectl apply -f deploy/k8s/service.yaml

# 5. HPA — auto-scales 2–10 replicas on CPU 70% / memory 80%
kubectl apply -f deploy/k8s/hpa.yaml
```

### Resource Limits

| Resource | Request | Limit |
|---|---|---|
| CPU | 250m | 1000m |
| Memory | 256Mi | 1Gi |

### Probes

Both liveness and readiness probes hit `GET /health` on port `5000`.

### Security Context

Containers run as a non-root user with `allowPrivilegeEscalation: false`, read-only root filesystem, and all capabilities dropped.

---

## Helm

The Helm chart is at `deploy/helm/`. It wraps the Kubernetes manifests with templated values.

```bash
# Install with default values
helm install hancock ./deploy/helm

# Install with overrides
helm install hancock ./deploy/helm \
  --set replicaCount=3 \
  --set image.tag=v0.5.0 \
  --set autoscaling.enabled=true \
  --set autoscaling.maxReplicas=10

# Upgrade an existing release
helm upgrade hancock ./deploy/helm --set image.tag=v0.6.0

# Uninstall
helm uninstall hancock
```

Key values in `deploy/helm/values.yaml`:

```yaml
replicaCount: 2
image:
  repository: cyberviser/hancock
  tag: latest
service:
  type: ClusterIP
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
```

---

## Terraform (AWS ECS Fargate)

`deploy/terraform/main.tf` provisions the full AWS stack:

- **ECS Fargate** cluster and task definition
- **Application Load Balancer** with target group and health checks
- **Auto-scaling** (2–10 tasks, CPU + memory policies)
- **CloudWatch Alarms** (CPU, memory, unhealthy hosts)
- **AWS Secrets Manager** for `NVIDIA_API_KEY`
- **IAM roles** for task execution and task role
- **Security groups** for ALB → ECS traffic

```bash
cd deploy/terraform

# Initialise providers
terraform init

# Preview the plan
terraform plan

# Apply (creates all AWS resources)
terraform apply

# Destroy when done
terraform destroy
```

Secrets should be populated in AWS Secrets Manager before `terraform apply`. The task definition reads `NVIDIA_API_KEY` from Secrets Manager at runtime — do not hard-code it.

---

## Fly.io

`fly.toml` configures a serverless deployment on [Fly.io](https://fly.io):

- **App:** `hancock-cyberviser`
- **Region:** `iad` (US East; change with `fly regions set`)
- **VM:** 512 MB RAM, shared CPU, 1 vCPU
- **Auto-stop/start:** Scales to zero when idle

```bash
# Authenticate
fly auth login

# Deploy
fly deploy

# Set secrets (required for cloud LLM backends)
fly secrets set NVIDIA_API_KEY=<your-key>
fly secrets set HANCOCK_API_KEY=<your-key>
fly secrets set HANCOCK_LLM_BACKEND=nvidia

# Check status
fly status
fly logs
```

The `/health` endpoint is used as the Fly health check (10 s grace period, 30 s interval).

---

## Graceful Shutdown

`deploy/graceful_shutdown.py` handles `SIGTERM` and `SIGINT` with a configurable drain timeout (default 30 s). It is automatically invoked in container environments and forwards signals to child processes. The Kubernetes `terminationGracePeriodSeconds` is set to `30` to align with this timeout.
