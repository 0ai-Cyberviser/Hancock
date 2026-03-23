# Hancock Deployment Guide

Comprehensive guide for deploying Hancock in development, Docker, Kubernetes, and cloud environments.

---

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Terraform / AWS Fargate](#terraform--aws-fargate)
5. [Environment Variables](#environment-variables)
6. [Configuration Options](#configuration-options)

---

## Local Development

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) (for local LLM)

### Quick start

```bash
# 1. Clone and set up environment
git clone https://github.com/0ai-Cyberviser/Hancock
cd Hancock
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 3. Configure
cp .env.example .env
# Edit .env — set HANCOCK_LLM_BACKEND and API keys

# 4. Run startup checks
python deploy/startup_checks.py

# 5. Start the server
python hancock_agent.py --server --port 5000
```

The API is available at `http://localhost:5000`.

### CLI mode

```bash
python hancock_agent.py          # interactive CLI
python hancock_agent.py --model llama3.2  # specific model
```

---

## Docker Deployment

### Single container (Ollama backend)

```bash
# Build image
docker build -t cyberviser/hancock:latest -f deploy/docker/Dockerfile .

# Run with Ollama
docker run -d \
  --name hancock \
  -p 5000:5000 \
  -e HANCOCK_LLM_BACKEND=ollama \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  cyberviser/hancock:latest
```

### Full stack with Prometheus + Grafana

```bash
cd deploy/docker
docker compose up -d

# Services:
#   Hancock API  → http://localhost:5000
#   Prometheus   → http://localhost:9090
#   Grafana      → http://localhost:3000 (admin / hancock-admin)
```

### Environment variables for Docker

```env
HANCOCK_LLM_BACKEND=ollama        # ollama | nvidia | openai
OLLAMA_BASE_URL=http://ollama:11434
HANCOCK_API_KEY=                  # leave empty to disable auth
LOG_FORMAT=json                   # json | text
PROMETHEUS_ENABLED=true
METRICS_PORT=8001
```

---

## Kubernetes Deployment

### Prerequisites

- `kubectl` configured against your cluster
- Container registry access (Docker Hub or ECR)

### Deploy Hancock

```bash
# Create namespace and deploy
kubectl apply -f deploy/kubernetes/hancock-deployment.yaml

# Deploy Prometheus
kubectl apply -f deploy/kubernetes/prometheus-deployment.yaml

# Deploy Grafana
kubectl apply -f deploy/kubernetes/grafana-deployment.yaml

# Check status
kubectl get pods -n hancock
kubectl get svc  -n hancock
```

### Helm deployment

```bash
# Install with default values
helm install hancock deploy/helm/hancock \
  --namespace hancock --create-namespace

# Install with custom values
helm install hancock deploy/helm/hancock \
  --namespace hancock --create-namespace \
  --set secrets.openaiApiKey=sk-... \
  --set config.llmBackend=openai \
  --set replicaCount=3

# Upgrade
helm upgrade hancock deploy/helm/hancock -n hancock

# Uninstall
helm uninstall hancock -n hancock
```

### Verify deployment

```bash
# Port-forward to test locally
kubectl port-forward svc/hancock 5000:80 -n hancock

# Health check
curl http://localhost:5000/health
```

---

## Terraform / AWS Fargate

### Prerequisites

- Terraform 1.5+
- AWS CLI configured
- ECR repository created

### Deploy

```bash
cd deploy/terraform

# Initialize
terraform init

# Plan
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
terraform plan

# Apply
terraform apply

# Output ALB DNS
terraform output alb_dns_name
```

### Push Docker image to ECR

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account_id>.dkr.ecr.us-east-1.amazonaws.com

docker build -t hancock:latest -f deploy/docker/Dockerfile .
docker tag hancock:latest <ecr_url>:latest
docker push <ecr_url>:latest
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HANCOCK_LLM_BACKEND` | `ollama` | LLM backend: `ollama`, `nvidia`, `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.1:8b` | Default Ollama model |
| `OLLAMA_CODER_MODEL` | `qwen2.5-coder:7b` | Coder model for `/v1/code` |
| `NVIDIA_API_KEY` | — | NVIDIA NIM API key |
| `OPENAI_API_KEY` | — | OpenAI API key (fallback) |
| `HANCOCK_API_KEY` | — | Bearer token for API auth (empty = disabled) |
| `HANCOCK_RATE_LIMIT` | `60` | Requests per minute per IP |
| `HANCOCK_PORT` | `5000` | HTTP server port |
| `HANCOCK_WEBHOOK_SECRET` | — | HMAC-SHA256 secret for webhook signature verification |
| `HANCOCK_SLACK_WEBHOOK` | — | Slack incoming webhook URL |
| `HANCOCK_TEAMS_WEBHOOK` | — | Microsoft Teams incoming webhook URL |
| `LOG_LEVEL` | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `text` | Log format: `text` or `json` |
| `LOG_TO_FILE` | `false` | Write logs to file |
| `LOG_FILE_PATH` | `/var/log/hancock.log` | Log file path |
| `PROMETHEUS_ENABLED` | `true` | Enable Prometheus metrics |
| `METRICS_PORT` | `8001` | Prometheus metrics port |

---

## Configuration Options

### LLM Backend Selection

**Option A — Ollama (local, recommended for dev)**
```env
HANCOCK_LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```

**Option B — NVIDIA NIM (cloud)**
```env
HANCOCK_LLM_BACKEND=nvidia
NVIDIA_API_KEY=nvapi-...
```

**Option C — OpenAI (cloud fallback)**
```env
HANCOCK_LLM_BACKEND=openai
OPENAI_API_KEY=sk-...
```

### Authentication

```env
# Generate a secure token
HANCOCK_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Use in requests:
# Authorization: Bearer <token>
```

### Webhook Security

```env
HANCOCK_WEBHOOK_SECRET=your-shared-secret-here

# Sign payloads:
# X-Hancock-Signature: sha256=<hmac_hex>
```
