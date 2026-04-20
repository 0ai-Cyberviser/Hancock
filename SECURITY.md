# Security Policy

This repository is operated by Johnny Watters (`0ai-Cyberviser`) as part of the `0AI` company portfolio.

If you discover a security vulnerability or a safety issue, do not open a public issue first.

Report privately to:

- 0ai@cyberviserai.com
- cyberviser@proton.me

Please include:

- affected repository
- impact summary
- reproduction details
- any suggested remediation

If the issue belongs to upstream code in a forked repository, report upstream as well when appropriate.

---

## Security Features (v0.3.1)

### Intent Verification & Authorization
- **Intent Guard**: `security/intent_guard.py` blocks unsafe intents (ransomware, DDoS, unauthorized access)
- **Scope Enforcement**: All agentic operations require explicit `authorized` scope
- **Mode Validation**: Only valid modes (pentest, soc, sigma, yara, ioc, osint, graphql, code, ciso, auto) are permitted

### API Security
- **API Key Authentication**: Required for agentic endpoints via `X-API-Key` header (configured via `HANCOCK_API_KEYS`)
- **Rate Limiting**: In-memory rate limiter (default 30 req/min for agentic endpoint, 60 req/min global)
- **Bearer Token Auth**: Existing endpoints support `Authorization: Bearer <HANCOCK_API_KEY>`

### Sandboxed Tool Execution
- **Least Privilege**: `sandbox/runner.py` uses Docker with:
  - `--read-only` (read-only root filesystem)
  - `--cap-drop ALL` (all capabilities dropped)
  - `--security-opt no-new-privileges`
  - `--network none` (default no outbound, require explicit override)
  - `--pids-limit 128`
  - Resource limits: `--cpus`, `--memory`

### Human-in-the-Loop
- **Recommendation-Only Mode**: Executor gate defaults to `execute=False`
- **Execution Gating**: Future versions will support explicit approval for `execute=True` per-action under specific scope

### Framework Compliance
- **NIST CSF/800-53**: AC-2 (Account Management), AC-6 (Least Privilege), AU-2 (Audit Events), SI-4 (System Monitoring), SC-7 (Boundary Protection), SC-39 (Process Isolation)
- **MITRE ATT&CK**: Authorized TTP simulation only (TA0001–TA0005 emulation with consent)

## Best Practices

1. **Never commit secrets**: Use `.env` files (excluded from Git)
2. **Configure API keys**: Set `HANCOCK_API_KEYS` for production deployments
3. **Enable diagnostics auth**: Set `HANCOCK_ENABLE_INTERNAL_DIAGNOSTICS=true` and configure `HANCOCK_API_KEY`
4. **Use Docker security options**: Deploy with `security_opt: no-new-privileges`, `cap_drop: ALL`
5. **Network segmentation**: Use `--network none` for sandboxed tools unless network access is required

## Responsible Disclosure

Hancock is designed for **authorized security testing only**. Users must:
- Obtain written permission before testing any systems
- Operate within defined scope of engagement
- Follow responsible disclosure practices
- Comply with local laws and regulations

Unauthorized use for malicious purposes violates our license and applicable laws.
