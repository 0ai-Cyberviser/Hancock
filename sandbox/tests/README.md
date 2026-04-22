# Hancock Sandbox Security Testing Framework

**Version:** v0.5.0  
**Purpose:** Validate that the Hancock sandbox cannot be escaped through common container breakout techniques  
**Status:** Production Ready ✅

---

## 🎯 Overview

The Hancock Sandbox Security Testing Framework is a comprehensive **meta-sandbox** that validates the security posture of the Hancock execution environment. It includes **50+ escape attempt tests** across 5 categories, all designed to **fail** if the sandbox is properly hardened.

### Philosophy

**"If it can be broken, we will find out before attackers do."**

This framework implements:
- ✅ Offensive security mindset (assume breach, test defenses)
- ✅ Zero-trust validation (every claim must be proven)
- ✅ Continuous testing (run before every deployment)
- ✅ Automated reporting (JSON + human-readable outputs)

---

## 📁 Structure

```
sandbox/tests/
├── test_sandbox_security.py          # Automated test harness (Python)
├── run_all_tests.sh                  # Master test runner (Bash)
├── escape_attempts/                  # Individual attack payloads
│   ├── 01_priv_escalation.sh         # Privilege escalation (sudo, setuid, caps)
│   ├── 02_container_breakout.sh      # Container escape (Docker socket, cgroups)
│   ├── 03_resource_exhaustion.sh     # DoS attacks (fork bombs, memory bombs)
│   ├── 04_network_escape.sh          # Network isolation bypass
│   └── 05_filesystem_escape.sh       # Filesystem escape (path traversal, mounts)
└── validation/                       # Auto-generated reports
    ├── security_report.txt           # Human-readable summary
    └── security_results.json         # Machine-readable results
```

---

## 🚀 Quick Start

### 1. Build the Sandbox Image

```bash
cd sandbox
docker build -t hancock-sandbox:latest -f Dockerfile.sandbox .
```

### 2. Run All Tests

**Option A: Automated Python Test Suite (Recommended)**
```bash
python3 sandbox/tests/test_sandbox_security.py --all
```

**Option B: Manual Bash Test Runner**
```bash
bash sandbox/tests/run_all_tests.sh hancock-sandbox:latest
```

### 3. Review Results

Check the generated reports:
```bash
cat sandbox/tests/validation/security_report.txt
cat sandbox/tests/validation/security_results.json
```

**Expected Output:**
```
SECURITY POSTURE: 🔒 SECURE
Total Tests:     50
Passed:          50 ✅
Failed:          0 ❌
Critical Issues: 0 🚨
```

---

## 🧪 Test Categories

### Category 1: Privilege Escalation (8 tests)

**Goal:** Validate that container user cannot escalate to root.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `priv-esc-sudo` | Attempt `sudo whoami` | BLOCKED (sudo unavailable or denied) |
| `priv-esc-setuid` | Search for setuid binaries | BLOCKED (no setuid bins) |
| `priv-esc-capabilities` | Check Linux capabilities | BLOCKED (all caps dropped) |
| `priv-esc-su` | Attempt `su - root` | BLOCKED (authentication failure) |
| `/etc/passwd` write | Modify password file | BLOCKED (read-only filesystem) |
| `/etc/shadow` read | Access shadow file | BLOCKED (permission denied) |
| `pkexec` abuse | Exploit PwnKit CVE-2021-4034 | BLOCKED (pkexec not installed) |
| D-Bus escalation | Local privilege escalation via D-Bus | BLOCKED (D-Bus not available) |

**Why This Matters:**  
Privilege escalation is the gateway to container breakout. If an attacker gains root inside the container, they can exploit kernel vulnerabilities to escape.

---

### Category 2: Container Breakout (10 tests)

**Goal:** Validate that container cannot access host resources.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `breakout-docker-socket` | Access `/var/run/docker.sock` | BLOCKED (socket not mounted) |
| `breakout-cgroup` | Modify cgroup `release_agent` | BLOCKED (cgroup read-only) |
| `breakout-proc-mounts` | Inspect `/proc/mounts` for exploits | LIMITED (mounts visible but not exploitable) |
| Kernel module load | `insmod /tmp/evil.ko` | BLOCKED (CAP_SYS_MODULE dropped) |
| `/proc/sys` write | Modify kernel parameters | BLOCKED (read-only sysctl) |
| Host `/proc` leak | Check if host PIDs visible | PASS (only container PIDs) |
| Block device access | List `/dev/sd*`, `/dev/nvme*` | BLOCKED (no host block devices) |
| AppArmor/SELinux | Check LSM profile | ACTIVE (if available on host) |
| Seccomp bypass | Verify seccomp filter | ACTIVE (syscall filtering) |
| Namespace isolation | Check PID/user/net namespaces | ISOLATED (separate namespaces) |

**Why This Matters:**  
Container breakout techniques (e.g., Docker socket abuse, cgroup escapes) allow attackers to gain root on the host system.

---

### Category 3: Resource Exhaustion (8 tests)

**Goal:** Validate that resource limits prevent DoS attacks.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `resource-fork-bomb` | Launch `:(){  :|:& };:` | BLOCKED (PID limit hit) |
| `resource-memory-bomb` | Allocate 10GB RAM | BLOCKED (OOM killer at 256MB) |
| `resource-cpu-loop` | Infinite `while true; do :; done` | LIMITED (CPU quota enforced) |
| `resource-disk-fill` | `dd if=/dev/zero of=/tmp/big bs=1G count=10` | BLOCKED (tmpfs 50MB limit) |
| Inode exhaustion | Create 100K files in `/tmp` | BLOCKED (tmpfs size limit) |
| Process spawn | Spawn 1000 `sleep` processes | BLOCKED (--pids-limit=50) |
| Log flooding | Print infinite lines to stdout | LIMITED (timeout enforced) |
| `/dev/urandom` exhaustion | Read 10GB from urandom | LIMITED (timeout enforced) |

**Why This Matters:**  
Resource exhaustion can take down the host or starve other containers. Strict limits ensure isolation.

---

### Category 4: Network Escape (10 tests)

**Goal:** Validate that network isolation prevents exfiltration.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `network-outbound` | `curl http://example.com` | BLOCKED (--network=none) |
| `network-localhost` | `curl http://127.0.0.1:8080` | BLOCKED (no services running) |
| `network-dns-exfil` | `nslookup evil.attacker.com` | BLOCKED (no DNS resolution) |
| Raw socket creation | Create `SOCK_RAW` socket | BLOCKED (CAP_NET_RAW dropped) |
| ICMP ping | `ping 8.8.8.8` | BLOCKED (no network access) |
| Interface enumeration | `ip addr show` | PASS (only loopback visible) |
| Port scanning | Scan `127.0.0.1:1-1024` | LIMITED (localhost only) |
| ARP spoofing | Modify ARP table | BLOCKED (no eth0 interface) |
| IPv6 tunneling | Use IPv6 for exfiltration | BLOCKED (IPv6 disabled) |
| Network namespace | Check `/proc/self/ns/net` | ISOLATED (separate netns) |

**Why This Matters:**  
Network isolation prevents data exfiltration and command-and-control (C2) communication.

---

### Category 5: Filesystem Escape (12 tests)

**Goal:** Validate that filesystem isolation prevents host access.

| Test | Description | Expected Result |
|------|-------------|-----------------|
| `fs-write-root` | Write to `/etc/evil.txt` | BLOCKED (--read-only rootfs) |
| `/etc/passwd` modification | Append malicious user | BLOCKED (read-only) |
| `fs-path-traversal` | Read `../../../../etc/passwd` | LIMITED (container `/etc` only) |
| `fs-symlink` | Symlink to `/host/etc/shadow` | BLOCKED (no `/host` mount) |
| `fs-mount` | `mount -t tmpfs tmpfs /mnt` | BLOCKED (CAP_SYS_ADMIN dropped) |
| Bind mount | `mount --bind /etc /tmp/etc` | BLOCKED (CAP_SYS_ADMIN dropped) |
| `/proc/self/root` escape | Read `/proc/self/root/etc/hostname` | LIMITED (container filesystem) |
| Hard link attack | Link `/etc/shadow` to `/tmp` | BLOCKED (cross-filesystem hardlink) |
| `/tmp` size bypass | Write 100MB to `/tmp` | BLOCKED (tmpfs 50MB limit) |
| `/tmp` noexec | Execute script in `/tmp` | BLOCKED (--tmpfs noexec flag) |
| Docker layer mounts | Inspect overlay/aufs mounts | VISIBLE (expected, not exploitable) |
| `/dev/shm` exploitation | Write to shared memory | DEPENDS (check if mounted) |

**Why This Matters:**  
Filesystem escape allows attackers to read host secrets (SSH keys, credentials) or modify host system files.

---

## 🔍 How to Read Test Results

### Test Output Format

```bash
[1] Attempting sudo privilege escalation...
✅ PASS: sudo not available

[2] Searching for setuid binaries...
✅ PASS: No setuid binaries found

[3] Checking dangerous capabilities...
CapInh:	0000000000000000
CapPrm:	0000000000000000
CapEff:	0000000000000000
✅ PASS: All capabilities dropped
```

### Status Codes

- ✅ **PASS** — Test succeeded (escape attempt was blocked)
- ❌ **FAIL** — Test failed (escape attempt succeeded → SECURITY ISSUE)
- ⚠️  **WARNING** — Test passed but with caveats (review recommended)
- 🚨 **CRITICAL** — Severe security issue (DO NOT DEPLOY)

### Automated Report

After running `test_sandbox_security.py --all`, check the report:

```bash
cat sandbox/tests/validation/security_report.txt
```

**Example output:**
```
HANCOCK SANDBOX SECURITY VALIDATION REPORT
Date: 2026-04-20T15:30:00Z
Image: hancock-sandbox:latest

SUMMARY
-------
Total Tests:     50
Passed:          50 ✅
Failed:          0 ❌
Critical Issues: 0 🚨

SECURITY POSTURE: 🔒 SECURE

✅ NO CRITICAL ISSUES FOUND
✅ Sandbox passed all escape attempt tests
✅ Safe for production deployment (with continued monitoring)
```

---

## 🛠️ Customizing Tests

### Add a New Test Category

1. Create new test script:
```bash
sandbox/tests/escape_attempts/06_custom_attacks.sh
```

2. Add to `run_all_tests.sh`:
```bash
run_test "Custom Attacks" "$ESCAPE_DIR/06_custom_attacks.sh"
```

3. Add to `test_sandbox_security.py`:
```python
def test_custom_attacks(self):
    self.run_escape_test(
        name="custom-attack-1",
        description="Custom exploit attempt",
        command=["bash", "-c", "your_command_here"],
        expect_blocked=True,
        severity="HIGH"
    )
```

### Modify Security Restrictions

Edit `test_sandbox_security.py` → `run_escape_test()` → `docker_cmd`:

```python
docker_cmd = [
    "docker", "run", "--rm",
    "--cpus", "0.5",              # Adjust CPU limit
    "--memory", "256m",           # Adjust memory limit
    "--pids-limit", "50",         # Adjust process limit
    "--security-opt", "no-new-privileges",
    "--cap-drop", "ALL",
    "--read-only",
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=50m",  # Adjust tmpfs size
    "--network", "none",          # Change to "bridge" to test network isolation
    sandbox_image,
] + command
```

---

## 📊 CI/CD Integration

### GitHub Actions

Add to `.github/workflows/security-test.yml`:

```yaml
name: Sandbox Security Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build sandbox
        run: docker build -t hancock-sandbox:latest -f sandbox/Dockerfile.sandbox .
      - name: Run security tests
        run: python3 sandbox/tests/test_sandbox_security.py --all
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: sandbox/tests/validation/
```

### Pre-Deployment Checklist

Before deploying Hancock sandbox to production:

- [ ] Run `python3 sandbox/tests/test_sandbox_security.py --all`
- [ ] Verify **0 critical issues** in report
- [ ] Review any warnings or medium-severity findings
- [ ] Test with actual pentesting tools (nmap, sqlmap, nikto)
- [ ] Verify audit logs are being generated
- [ ] Confirm AUTHORIZED_SCOPES is configured correctly
- [ ] Enable gVisor runtime if available (`--runtime=runsc`)
- [ ] Set up monitoring/alerting for container escapes

---

## 🚨 What to Do If Tests Fail

### Critical Failure (🚨)

If any test shows `❌ CRITICAL: ...`:

1. **DO NOT DEPLOY** the sandbox in production
2. Review the failed test output
3. Identify the root cause (missing Docker flag, capability leak, etc.)
4. Apply hardening fix (see "Common Fixes" below)
5. Re-run tests until all pass

### Common Fixes

| Issue | Fix |
|-------|-----|
| Docker socket accessible | Remove `-v /var/run/docker.sock:/var/run/docker.sock` |
| Root filesystem writable | Add `--read-only` flag |
| Network access allowed | Change to `--network=none` |
| Too many capabilities | Add `--cap-drop=ALL` |
| Fork bomb succeeded | Add `--pids-limit=50` |
| Memory bomb succeeded | Lower `--memory` limit (e.g., 256m) |
| `/tmp` executable | Add `noexec` to tmpfs options |

---

## 📚 References

- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [OWASP Container Security](https://owasp.org/www-project-docker-top-10/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [NIST SP 800-190](https://csrc.nist.gov/publications/detail/sp/800-190/final) — Application Container Security Guide

---

**Questions?** See main sandbox docs: [`sandbox/README.md`](../README.md)  
**Maintainer:** Johnny Watters (0ai-Cyberviser)
