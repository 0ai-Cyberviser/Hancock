# Deployment Guide

This guide covers all supported deployment methods for Hancock.

## Prerequisites

- Docker 24+ and Docker Compose v2+
- (Kubernetes) kubectl 1.28+, Helm 3.12+
- (Terraform) Terraform 1.5+, AWS CLI v2

---

## Docker (local / single-node)

### Quick start

```bash
# 1. Copy and populate the environment file
cp .env.example .env
#    Set OPENAI_API_KEY or configure Ollama

# 2. Build and start all services
docker compose -f deploy/docker-compose.yml up -d

# 3. Verify Hancock is healthy
curl http://localhost:5000/health
```

### Multi-stage Dockerfile

The production `deploy/Dockerfile` uses a two-stage build:

| Stage | Purpose |
|-------|---------|
| `builder` | Installs Python deps into `/install` |
| `runtime` | Copies only the installed packages; no build tools |

The resulting image runs as **non-root user 1000** and has a built-in
health check on `/health`.

### Building manually

```bash
docker build -f deploy/Dockerfile -t hancock:local .
docker run -p 5000:5000 --env-file .env hancock:local
```

---

## Kubernetes

All manifests live in `deploy/k8s/`.

### Apply manifests

```bash
# Create namespace (optional)
kubectl create namespace hancock

# Apply ConfigMap and Secret (edit secret.yaml first!)
kubectl apply -f deploy/k8s/configmap.yaml -n hancock
kubectl apply -f deploy/k8s/secret.yaml    -n hancock

# Deploy application
kubectl apply -f deploy/k8s/deployment.yaml -n hancock
kubectl apply -f deploy/k8s/service.yaml    -n hancock
kubectl apply -f deploy/k8s/hpa.yaml        -n hancock

# Check rollout
kubectl rollout status deployment/hancock -n hancock
```

### Resource limits

| Resource | Request | Limit |
|----------|---------|-------|
| CPU | 250 m | 2 cores |
| Memory | 512 MiB | 2 GiB |

### Health probes

| Probe | Path | Initial delay |
|-------|------|---------------|
| Liveness | `/health` | 30 s |
| Readiness | `/health` | 10 s |

---

## Helm

The chart lives in `deploy/helm/hancock/`.

### Install

```bash
helm install hancock deploy/helm/hancock \
  --namespace hancock \
  --create-namespace \
  --set image.tag=v0.6.0 \
  --set existingSecret=hancock-secrets
```

### Upgrade

```bash
helm upgrade hancock deploy/helm/hancock \
  --namespace hancock \
  --set image.tag=v0.7.0
```

### Key values

| Value | Default | Description |
|-------|---------|-------------|
| `replicaCount` | `2` | Initial replica count |
| `image.tag` | `latest` | Container image tag |
| `autoscaling.enabled` | `true` | Enable HPA |
| `autoscaling.maxReplicas` | `10` | HPA max replicas |
| `existingSecret` | `""` | Name of a pre-existing K8s Secret |

---

## Terraform (AWS ECS Fargate)

Terraform configs live in `deploy/terraform/`.

### Prerequisites

- AWS credentials configured (`aws configure` or IAM role)
- Existing VPC with `Tier=public` and `Tier=private` subnet tags

### Deploy

```bash
cd deploy/terraform

terraform init
terraform plan \
  -var="vpc_id=vpc-xxxxxxxx" \
  -var="nvidia_api_key_secret_arn=arn:aws:secretsmanager:..." \
  -out=plan.tfplan

terraform apply plan.tfplan
```

### Outputs

| Output | Description |
|--------|-------------|
| `alb_dns_name` | Public DNS for the load balancer |
| `ecs_cluster_name` | ECS cluster name |
| `cloudwatch_log_group` | CloudWatch log group |

---

## Startup checks

Before the Hancock server starts accepting traffic, run:

```bash
python deploy/startup_checks.py
```

This validates:
- Required environment variables are set
- LLM backend (Ollama / OpenAI) is reachable
- Sufficient disk space (≥ 500 MiB free)

Use `--warn` to log failures without aborting (useful in dev).

---

## Graceful shutdown

Hancock registers SIGTERM/SIGINT handlers via `deploy/graceful_shutdown.py`.
When a shutdown signal is received:

1. `shutdown_event` is set → new requests return 503
2. The process waits up to `HANCOCK_DRAIN_TIMEOUT` seconds (default 30)
3. Cleanup callbacks execute (close DB connections, flush buffers, etc.)
4. Process exits 0

Adjust the drain window:

```bash
export HANCOCK_DRAIN_TIMEOUT=60
```
