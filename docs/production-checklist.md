# Hancock Production Checklist

Pre-deployment verification, security hardening, and operational readiness.

---

## Pre-Deployment Verification

### Environment

- [ ] Python 3.10+ installed on the target host
- [ ] `.env` file configured from `.env.example` (never committed to git)
- [ ] `HANCOCK_LLM_BACKEND` set to the correct backend
- [ ] Backend credentials verified (NVIDIA API key / OpenAI key)
- [ ] `HANCOCK_API_KEY` set to a cryptographically-random value
- [ ] `HANCOCK_WEBHOOK_SECRET` set if webhooks are used
- [ ] Startup checks pass: `python deploy/startup_checks.py`

### Networking

- [ ] Port 5000 (API) is reachable from intended clients
- [ ] Port 8001 (metrics) is restricted to Prometheus only
- [ ] TLS termination configured at load balancer / reverse proxy
- [ ] CORS headers configured if browser clients are used

### Docker / Kubernetes

- [ ] Docker image built from `deploy/docker/Dockerfile` (multi-stage)
- [ ] Image scanned for vulnerabilities (Trivy): zero CRITICAL findings
- [ ] Container runs as non-root user (`hancock`, UID 1000)
- [ ] Read-only root filesystem enabled where possible
- [ ] Liveness and readiness probes configured
- [ ] Resource requests and limits set
- [ ] HPA configured for auto-scaling

---

## Security Hardening

### Authentication

- [ ] `HANCOCK_API_KEY` configured (do NOT leave empty in production)
- [ ] API key is ≥ 32 bytes of random data:
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] API key rotated every 90 days
- [ ] Webhook HMAC secret configured: `HANCOCK_WEBHOOK_SECRET`

### Network security

- [ ] HTTPS enforced for all API traffic
- [ ] Ollama port (11434) not exposed to the public internet
- [ ] Metrics port (8001) firewalled — accessible only from Prometheus
- [ ] Rate limiting configured: `HANCOCK_RATE_LIMIT=60` (adjust for your traffic)

### Secrets management

- [ ] No secrets in Docker images or Kubernetes manifests
- [ ] Secrets stored in Kubernetes Secrets or AWS Secrets Manager
- [ ] `.env` file excluded from version control (`.gitignore`)
- [ ] Service accounts use least-privilege IAM roles

### Dependency security

- [ ] Run `pip-audit` to check for known vulnerabilities:
  ```bash
  pip install pip-audit && pip-audit
  ```
- [ ] Run `bandit` for SAST:
  ```bash
  bandit -r hancock_agent.py -ll
  ```
- [ ] Dependencies pinned to specific versions in `requirements.txt`

---

## Load Testing Requirements

Before go-live, verify the system handles expected traffic:

- [ ] `locust` load test with expected concurrent users
- [ ] p99 latency < 5 seconds under load
- [ ] Error rate < 1% under normal load
- [ ] System recovers gracefully after burst traffic
- [ ] Rate limiter tested: confirm 429 responses at threshold

```bash
locust -f tests/load_test_locust.py --headless \
  --host http://localhost:5000 \
  --users 50 --spawn-rate 5 --run-time 120s
```

---

## Monitoring Setup

- [ ] Prometheus scraping `http://hancock:8001/metrics` every 15s
- [ ] Grafana dashboard imported from `monitoring/grafana_dashboard.json`
- [ ] Alerting rules loaded from `monitoring/alerting_rules.yaml`
- [ ] Alertmanager configured to route to on-call channel
- [ ] Test alerts fire correctly with `ALERTS{alertname="..."}` query
- [ ] Dashboard reviewed — all panels showing data

---

## Incident Response

### Runbook: High error rate

1. Check `/metrics` endpoint for error counts by endpoint
2. Review container logs: `kubectl logs -n hancock -l app=hancock --tail=100`
3. Check Ollama / NVIDIA NIM backend health
4. If model backend is down: set `HANCOCK_LLM_BACKEND=openai` as temporary fallback
5. Scale down to 0, then back up to flush bad state: `kubectl scale deployment hancock --replicas=0`

### Runbook: High latency

1. Check `hancock_model_availability` gauge — is backend reachable?
2. Check Ollama model loaded: `ollama list`
3. Check CPU/GPU utilisation on the model host
4. Reduce concurrent requests via `HANCOCK_RATE_LIMIT`
5. Scale horizontally if CPU-bound

### Runbook: Rate limit exhaustion

1. Identify the source IP from logs
2. Check if legitimate traffic spike or abuse
3. Temporarily increase `HANCOCK_RATE_LIMIT`
4. Block abusive IP at firewall/WAF level

---

## Rollback Procedure

### Kubernetes

```bash
# Roll back to previous deployment
kubectl rollout undo deployment/hancock -n hancock

# Roll back to specific revision
kubectl rollout history deployment/hancock -n hancock
kubectl rollout undo deployment/hancock --to-revision=2 -n hancock
```

### Docker Compose

```bash
# Pin to previous image tag
docker compose down
HANCOCK_IMAGE_TAG=0.4.0 docker compose up -d
```

### Terraform (ECS)

```bash
cd deploy/terraform
terraform apply -var="image_tag=0.4.0"
```

---

## Post-Deployment Verification

```bash
# 1. Health check
curl -s http://localhost:5000/health | jq .

# 2. API test
curl -s -X POST http://localhost:5000/v1/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HANCOCK_API_KEY" \
  -d '{"question": "What is Log4Shell?"}' | jq .answer

# 3. Metrics check
curl -s http://localhost:8001/metrics | grep hancock_requests

# 4. Webhook test
curl -s -X POST http://localhost:5000/v1/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $HANCOCK_API_KEY" \
  -d '{"alert": "Test alert", "source": "test", "severity": "low"}' | jq .
```
