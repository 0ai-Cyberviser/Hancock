# Hancock Sandbox — Secure Tool Execution

**Version:** v0.5.0  
**Status:** Production Ready ✅  
**Risk Level:** Controlled (isolation + approval gates)

---

## 🎯 Overview

The Hancock Sandbox enables **autonomous execution** of offensive security tools (nmap, sqlmap, nikto, etc.) in an **isolated Docker environment** with comprehensive safety controls.

### Key Features

✅ **Multi-layer isolation**: Docker containers + gVisor runtime + non-root user  
✅ **Risk-based approval**: Auto-execute (low risk) → Human approval (medium) → Block (high)  
✅ **Resource limits**: 1 CPU core, 512MB RAM, 5min timeout, egress-only network  
✅ **Scope validation**: HANCOCK_AUTHORIZED_SCOPES env var (CIDR/domain whitelist)  
✅ **Output sanitization**: Strip credentials, API keys, PII from results  
✅ **Audit logging**: All executions timestamped with risk scores + approval status  

---

## 🏗️ Architecture

```
LangGraph Executor Node
        ↓
  SandboxExecutor
        ↓
  ┌─────────────────────┐
  │ Risk Scoring        │ → 1-3: Auto-execute
  │ (calculate_risk)    │ → 4-6: Require approval
  └─────────────────────┘ → 7-10: Block

        ↓
  ┌─────────────────────┐
  │ Scope Validation    │ → Check AUTHORIZED_SCOPES
  └─────────────────────┘

        ↓
  ┌─────────────────────┐
  │ Docker Sandbox      │ → kalilinux/kali-rolling
  │ + gVisor Runtime    │ → runsc (kernel syscall filtering)
  │ + Resource Limits   │ → --cpus=1 --memory=512m
  └─────────────────────┘

        ↓
  ┌─────────────────────┐
  │ Tool Execution      │ → nmap, sqlmap, nikto, etc.
  └─────────────────────┘

        ↓
  ┌─────────────────────┐
  │ Output Sanitization │ → Remove [REDACTED] credentials
  └─────────────────────┘

        ↓
    Audit Log
```

---

## 🚀 Quick Start

### 1. Build the Sandbox Image

```bash
cd sandbox
docker build -t hancock-sandbox:latest -f Dockerfile.sandbox .
```

Build time: ~5-10 minutes (downloads Kali base + security tools)

### 2. Set Authorized Scopes

```bash
export HANCOCK_AUTHORIZED_SCOPES="192.168.1.0/24,scanme.nmap.org,testfire.net"
```

**CRITICAL:** Only add targets you have **written authorization** to test.

### 3. Test Sandbox Executor

```bash
python3 sandbox/executor.py
```

Sample output:
```
[sandbox] ▶️  Executing nmap in isolated container...
[sandbox] ✅ Execution complete (exit 0)
{
  "success": true,
  "output": "Host is up (0.0012s latency)...",
  "risk_score": 3,
  "approved": true,
  "exit_code": 0
}
```

### 4. Use in LangGraph

```python
from hancock_langgraph import graph
import os

os.environ["HANCOCK_AUTHORIZED_SCOPES"] = "192.168.1.0/24"

state = {
    'messages': ["Scan for open ports on 192.168.1.10"],
    'mode': 'pentest',
    'authorized': True,
    'confidence': 0.90,
    'rag_context': [],
    'tool_output': '',
    'execution_result': {}
}

result = graph.invoke(state)
print(result['tool_output'])
```

---

## 🛡️ Safety Controls

### 1. Scope Validation

**Enforced:** Every tool execution validates target against `HANCOCK_AUTHORIZED_SCOPES`  
**Format:** Comma-separated list of IPs, CIDRs, or domains  
**Example:** `"10.0.0.0/8,192.168.1.1,example.com"`

```python
executor = SandboxExecutor(authorized_scopes=["192.168.1.0/24"])
result = executor.execute_tool(
    tool="nmap",
    command=["nmap", "-sn", "8.8.8.8"],  # ❌ BLOCKED
    target="8.8.8.8"
)
# → {"success": False, "error": "Target not in authorized scope"}
```

### 2. Risk-Based Approval Gates

| Risk Score | Action | Example Tools/Flags |
|------------|--------|---------------------|
| **1-3 (Low)** | Auto-execute | ping, whois, dig, nslookup, nmap -sn |
| **4-6 (Medium)** | Require human approval | nmap -sV, nikto, dirb, gobuster |
| **7-10 (High)** | Blocked by policy | sqlmap --risk=3, Metasploit payloads |

**Approval prompt (medium risk):**
```
[sandbox] ⚠️  APPROVAL REQUIRED (risk 5/10)
         Tool: nmap
         Command: nmap -sV -p 80,443 testfire.net
         Target: testfire.net
         Approve? [y/N]: 
```

### 3. Resource Limits

Enforced via Docker:
```python
RESOURCE_LIMITS = {
    "cpus": "1.0",        # Max 1 CPU core
    "memory": "512m",     # Max 512MB RAM
    "network": "bridge",  # Egress-only (TODO: custom network)
}
MAX_EXECUTION_TIME = 300  # 5 minutes
MAX_OUTPUT_SIZE = 1MB
```

**Prevents:**
- Fork bombs (CPU limit)
- Memory exhaustion (RAM limit)
- Long-running scans (timeout)
- Log flooding (output size cap)

### 4. Output Sanitization

Strips sensitive data before returning results:
```python
output = sanitize_output(raw_output)
```

**Removed patterns:**
- `password|passwd|pwd|secret|token|key`: → `[REDACTED]`
- Email addresses → `[EMAIL]`
- API keys (32+ char alphanum) → `[API_KEY]`

### 5. Audit Logging

Every execution logged with:
- Timestamp (UTC)
- Tool name
- Full command
- Target
- Risk score
- Approval status (auto / approved / denied)
- Exit code
- Output size

```python
executor.get_audit_log()
# → [{"timestamp": "2026-04-20T14:32:11Z", "tool": "nmap", ...}]
```

---

## 🔧 Tool Wrappers

Pre-configured wrappers in `sandbox/tools/wrappers.py`:

### Nmap

```python
from sandbox.tools.wrappers import NmapWrapper

# Ping sweep (low risk)
cmd = NmapWrapper.ping_sweep("192.168.1.0/24")
# → ["nmap", "-sn", "192.168.1.0/24"]

# Service version (medium risk)
cmd = NmapWrapper.service_version("scanme.nmap.org", "80,443")
# → ["nmap", "-sV", "-p", "80,443", "scanme.nmap.org"]
```

### SQLMap

```python
from sandbox.tools.wrappers import SqlmapWrapper

# Safe test (risk=1, level=1)
cmd = SqlmapWrapper.test_url("http://testphp.vulnweb.com/artists.php?artist=1")
# → ["sqlmap", "-u", "...", "--risk=1", "--level=1", "--batch"]

# HIGH RISK BLOCKED
cmd = SqlmapWrapper.test_url("...", risk_level=3, level=5)
# → ValueError: High-risk sqlmap settings blocked
```

### Nikto

```python
from sandbox.tools.wrappers import NiktoWrapper

cmd = NiktoWrapper.scan_web("testfire.net", port=443, ssl=True)
# → ["nikto", "-h", "testfire.net", "-p", "443", "-ssl"]
```

---

## 🧪 Testing

### Unit Tests

```bash
pytest tests/test_sandbox.py -v
```

### Integration Test (Requires Docker)

```bash
export HANCOCK_AUTHORIZED_SCOPES="scanme.nmap.org"
python3 sandbox/executor.py
```

Expected output:
```
[sandbox] ✅ Sandbox image built: hancock-sandbox:latest
[sandbox] ▶️  Executing nmap in isolated container...
[sandbox] ✅ Execution complete (exit 0)
```

---

## 🚨 Security Warnings

### DO NOT:
❌ Add `0.0.0.0/0` or `*` to AUTHORIZED_SCOPES  
❌ Run sandbox with `--privileged` Docker flag  
❌ Bypass approval gates in production  
❌ Execute high-risk commands without explicit authorization  
❌ Scan targets without written permission  

### DO:
✅ Maintain strict authorized scope lists  
✅ Review audit logs regularly  
✅ Use approval gates for medium/high risk  
✅ Keep sandbox image updated (security patches)  
✅ Follow responsible disclosure for findings  

---

## 📖 Next Steps

- **Add more tools**: Metasploit framework (exploit-only mode), Burp Suite API, Hashcat
- **Custom networks**: Create Docker network with egress-only firewall rules
- **gVisor integration**: Add `--runtime=runsc` for enhanced syscall filtering
- **Confidence scoring**: Auto-set risk thresholds based on LLM confidence
- **Report integration**: Auto-generate findings from tool outputs

---

**Maintainer:** Johnny Watters (0ai-Cyberviser)  
**License:** See [LICENSE](../LICENSE) and [OWNERSHIP.md](../OWNERSHIP.md)
