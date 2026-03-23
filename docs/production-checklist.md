# Production Readiness Checklist

Complete all items before going live.

---

## Environment & secrets

- [ ] `OPENAI_API_KEY` or `NVIDIA_API_KEY` set in secret manager (not in code or `.env`)
- [ ] `HANCOCK_WEBHOOK_SECRET` set to a strong random value (`openssl rand -hex 32`)
- [ ] `.env` file is in `.gitignore` and never committed
- [ ] Secrets rotated and old values revoked
- [ ] K8s Secrets / AWS Secrets Manager used (not ConfigMaps for sensitive values)
- [ ] `HANCOCK_LOG_JSON=true` for machine-parseable logs
- [ ] `HANCOCK_LOG_LEVEL=WARNING` or `ERROR` in production (reduce log volume)

---

## Networking & TLS

- [ ] TLS termination configured at the load balancer (ALB / ingress)
- [ ] HTTP → HTTPS redirect enforced
- [ ] HSTS header set (at least 6 months)
- [ ] Firewall rules allow only 443 (and 80 → 443 redirect) inbound
- [ ] Internal service-to-service traffic uses mTLS or VPN
- [ ] Ollama port (11434) is NOT exposed publicly

---

## Rate limiting & quotas

- [ ] `HANCOCK_RATE_LIMIT` tuned for expected traffic (default: 60 req/min/IP)
- [ ] API gateway / WAF rate limiting configured upstream
- [ ] OpenAI / NVIDIA NIM quota verified for expected peak RPS
- [ ] Ollama resource limits set (GPU memory, CPU)

---

## Availability & scaling

- [ ] Minimum 2 replicas deployed (no single point of failure)
- [ ] HPA configured with sensible min/max and CPU target
- [ ] Health probes tested manually (`/health` returns `{"status": "ok"}`)
- [ ] Liveness probe `initialDelaySeconds` ≥ model load time
- [ ] `PodDisruptionBudget` created to prevent all pods being evicted at once
- [ ] Multi-AZ deployment (at least 2 availability zones)
- [ ] Circuit breaker / retry logic for LLM backend calls

---

## Observability

- [ ] Prometheus scraping `/metrics` on all Hancock pods
- [ ] Grafana dashboard imported and tested
- [ ] All alerting rules loaded and firing to correct channel
- [ ] Log aggregation pipeline tested (search for a known log message)
- [ ] Alert for `HancockDown` tested (stop the pod, confirm alert fires)
- [ ] Distributed tracing set up (optional: OpenTelemetry)

---

## Security

- [ ] Container runs as non-root user (UID 1000)
- [ ] `readOnlyRootFilesystem: true` in K8s security context
- [ ] `allowPrivilegeEscalation: false`
- [ ] All `capabilities` dropped
- [ ] Trivy or Grype scan of final image — no critical/high unfixed CVEs
- [ ] Bandit SAST scan passes (no HIGH severity findings)
- [ ] `pip-audit` shows no known vulnerabilities in dependencies
- [ ] Network policy restricts ingress/egress to required services only
- [ ] RBAC: Hancock service account has minimal permissions

---

## Backups & data

- [ ] Ollama model data volume backed up (or models pulled on startup)
- [ ] JSONL fine-tune data backed up off-node
- [ ] Backup / restore procedure tested
- [ ] Data retention policy documented

---

## Operational

- [ ] `deploy/startup_checks.py` passes without errors
- [ ] Runbook written for common failure scenarios
- [ ] On-call rotation configured
- [ ] Rollback procedure tested (`helm rollback` or `kubectl rollout undo`)
- [ ] Change management process documented
- [ ] Incident response playbook linked from monitoring dashboard

---

## Final sign-off

| Area | Owner | Date | Approved |
|------|-------|------|---------|
| Security | | | ☐ |
| Reliability | | | ☐ |
| Observability | | | ☐ |
| Compliance | | | ☐ |
