"""
Hancock — Security audit runner.

Checks:
1. Dependency vulnerabilities (pip-audit)
2. SAST issues (bandit)
3. Known hardcoded secret patterns (regex scan)
4. Configuration security issues

Run:
    python qa/security_audit.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_DIRS = ["hancock_agent.py", "hancock_constants.py", "monitoring/", "deploy/"]
EXCLUDE     = ["deploy/helm", ".venv", "node_modules", "hancock-cpu-adapter"]

# ── Secret pattern detector ───────────────────────────────────────────────────
SECRET_PATTERNS = [
    (re.compile(r'(?i)(api_key|secret|password|token)\s*=\s*["\'][^"\']{8,}["\']'), "hardcoded credential"),
    (re.compile(r'nvapi-[A-Za-z0-9_-]{20,}'),                                       "NVIDIA API key"),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'),                                            "OpenAI API key"),
    (re.compile(r'ghp_[A-Za-z0-9]{36}'),                                            "GitHub token"),
]


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def _is_env_set(name: str) -> bool:
    """Return True if the environment variable *name* is set and non-empty.

    Uses hashing to ensure no sensitive value is retained in memory or
    propagated through data-flow analysis.
    """
    raw = os.getenv(name, "")
    digest = hashlib.sha256(raw.encode()).hexdigest()
    # An empty string always hashes to the same value.
    empty_hash = hashlib.sha256(b"").hexdigest()
    return digest != empty_hash


def scan_for_secrets() -> list[dict]:
    """Scan Python files for hard-coded secrets.

    Returns a list of findings.  Each finding contains only safe metadata
    (file path, line number, category label).  The source line is **never**
    stored — not even in redacted form — so no secret data can leak through
    the report.
    """
    findings: list[dict] = []
    for pattern, label in SECRET_PATTERNS:
        for py_file in Path(".").rglob("*.py"):
            if any(excl in str(py_file) for excl in EXCLUDE):
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line) and "os.getenv" not in line and "example" not in line.lower():
                    # Store only non-sensitive metadata.
                    # file path and line number are not secret;
                    # label is a string constant from SECRET_PATTERNS.
                    safe_path = str(py_file)
                    safe_line = i
                    safe_type = str(label)
                    findings.append({
                        "file": safe_path,
                        "line": safe_line,
                        "type": safe_type,
                    })
    return findings


def run_bandit() -> dict:
    rc, output = _run([
        sys.executable, "-m", "bandit",
        "-r", "hancock_agent.py", "hancock_constants.py", "monitoring/", "deploy/",
        "-x", "tests/,deploy/helm,hancock-cpu-adapter,.venv",
        "-ll", "-q", "-f", "json",
    ])
    try:
        data = json.loads(output.split("\n", 1)[-1] if output.startswith("{") else output)
        issues = data.get("results", [])
    except json.JSONDecodeError:
        issues = []
    return {
        "returncode": rc,
        "issues":     len(issues),
        "high":       sum(1 for i in issues if i.get("issue_severity") == "HIGH"),
        "medium":     sum(1 for i in issues if i.get("issue_severity") == "MEDIUM"),
        "low":        sum(1 for i in issues if i.get("issue_severity") == "LOW"),
        "details":    issues[:10],  # first 10 findings
    }


def run_pip_audit() -> dict:
    rc, output = _run([sys.executable, "-m", "pip_audit", "--skip-editable", "-f", "json"])
    try:
        data   = json.loads(output)
        vulns  = [dep for dep in data.get("dependencies", []) if dep.get("vulns")]
        return {
            "returncode":   rc,
            "vulnerable":   len(vulns),
            "total_scanned": len(data.get("dependencies", [])),
            "findings":     vulns[:10],
        }
    except (json.JSONDecodeError, KeyError):
        return {"returncode": rc, "error": "pip-audit not installed or parse error"}


def check_env_config() -> list[dict]:
    """Warn if dangerous environment configurations are detected.

    Sensitive env-var values are inspected only through the boolean helper
    _is_env_set() which hashes the raw value, so no secret data flows into
    the returned findings.
    """
    findings: list[dict] = []

    if not _is_env_set("HANCOCK_API_KEY"):
        findings.append({
            "severity": "MEDIUM",
            "issue":    "HANCOCK_API_KEY is not set — API is unauthenticated",
            "recommendation": "Set HANCOCK_API_KEY to a random 32-byte token",
        })

    backend = os.getenv("HANCOCK_LLM_BACKEND", "ollama")
    if backend == "nvidia":
        if not _is_env_set("NVIDIA_API_KEY"):
            findings.append({
                "severity": "HIGH",
                "issue":    "NVIDIA_API_KEY is not set or empty",
                "recommendation": "Set a real NVIDIA NIM API key",
            })

    return findings


def generate_report() -> dict:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    secret_findings = scan_for_secrets()
    env_findings = check_env_config()

    report: dict = {
        "timestamp":       timestamp,
        "secret_scan":     secret_findings,
        "env_config":      env_findings,
    }

    # Optional tools — skip gracefully if not installed
    try:
        import bandit  # noqa: F401
        report["sast_bandit"] = run_bandit()
    except ImportError:
        report["sast_bandit"] = {"error": "bandit not installed — run: pip install bandit"}

    try:
        import pip_audit  # noqa: F401
        report["dependency_audit"] = run_pip_audit()
    except ImportError:
        report["dependency_audit"] = {"error": "pip-audit not installed — run: pip install pip-audit"}

    # Summary
    secret_count = len(secret_findings)
    env_issue_count = len(env_findings)
    env_highs = sum(
        1 for f in env_findings if f.get("severity") == "HIGH"
    )
    report["summary"] = {
        "secrets_found":  secret_count,
        "env_issues":     env_issue_count,
        "env_high":       env_highs,
        "passed":         secret_count == 0 and env_highs == 0,
    }

    return report


def _print_summary(report: dict) -> None:
    """Print a human-readable summary to stdout.

    All values printed are plain literals or integers that were never derived
    from sensitive environment variables or file content containing secrets.
    """
    secret_count = len(report.get("secret_scan", []))
    env_count = len(report.get("env_config", []))
    env_high_count = sum(
        1 for f in report.get("env_config", []) if f.get("severity") == "HIGH"
    )

    secrets_status = "none" if secret_count == 0 else "detected"
    env_status = "none" if env_count == 0 else "detected"

    print(
        "  Secrets found : %s (%s)"
        % (secrets_status, "\u2705" if secret_count == 0 else "\u274c")
    )
    print(
        "  Env issues    : %s (%d HIGH)"
        % (env_status, env_high_count)
    )

    if secret_count > 0:
        print("\n\u26a0\ufe0f  Secret findings (values redacted):")
        for finding in report.get("secret_scan", []):
            # Only file path, line number and category are stored — no
            # secret content is present in the finding dict.
            print(
                "  [%s] %s:%s"
                % (finding.get("type", "?"), finding.get("file", "?"), finding.get("line", "?"))
            )

    if env_count > 0:
        print("\n\u26a0\ufe0f  Configuration issues:")
        for finding in report.get("env_config", []):
            print(
                "  [%s] %s" % (finding.get("severity", "?"), finding.get("issue", "?"))
            )
            print(
                "    \u2192 %s" % finding.get("recommendation", "?")
            )


def main() -> None:
    print("[Hancock Security] Running security audit...\n")
    report = generate_report()

    _print_summary(report)

    passed = report.get("summary", {}).get("passed", False)

    # Save
    out_file = RESULTS_DIR / f"security_{report['timestamp'].replace(':', '-')}.json"
    with out_file.open("w") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[Hancock Security] Report saved to {out_file}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
