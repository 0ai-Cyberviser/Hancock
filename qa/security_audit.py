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

_REDACTED = "***REDACTED***"


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def _redact_line(line: str, pattern: re.Pattern) -> str:
    """Replace all secret matches in *line* with a redaction marker."""
    return pattern.sub(_REDACTED, line)


def scan_for_secrets() -> list[dict]:
    findings = []
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
                    redacted = _redact_line(line.strip(), pattern)[:80]
                    findings.append({
                        "file":    str(py_file),
                        "line":    i,
                        "type":    label,
                        "snippet": redacted,
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
    """Warn if dangerous environment configurations are detected."""
    findings = []
    api_key_set = bool(os.getenv("HANCOCK_API_KEY", ""))
    backend = os.getenv("HANCOCK_LLM_BACKEND", "ollama")

    if not api_key_set:
        findings.append({
            "severity": "MEDIUM",
            "issue":    "HANCOCK_API_KEY is not set — API is unauthenticated",
            "recommendation": "Set HANCOCK_API_KEY to a random 32-byte token",
        })

    if backend == "nvidia":
        nim_key = os.getenv("NVIDIA_API_KEY", "")
        nim_key_invalid = not nim_key or "your" in nim_key.lower()
        # Clear reference to actual key value immediately
        del nim_key
        if nim_key_invalid:
            findings.append({
                "severity": "HIGH",
                "issue":    "NVIDIA_API_KEY appears to be a placeholder",
                "recommendation": "Set a real NVIDIA NIM API key",
            })

    return findings


def generate_report() -> dict:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    secret_findings = scan_for_secrets()
    env_findings = check_env_config()

    report = {
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

    # Summary — use plain integer counts, not references to tainted data
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


def main() -> None:
    print("[Hancock Security] Running security audit...\n")
    report = generate_report()

    secrets_found = int(report["summary"]["secrets_found"])
    env_issues = int(report["summary"]["env_issues"])
    env_high = int(report["summary"]["env_high"])
    passed = bool(report["summary"]["passed"])

    print(
        f"  Secrets found : {secrets_found} "
        f"({'✅' if secrets_found == 0 else '❌'})"
    )
    print(f"  Env issues    : {env_issues} ({env_high} HIGH)")

    if report["secret_scan"]:
        print("\n⚠️  Secret findings (values redacted):")
        for finding in report["secret_scan"]:
            # snippet is already redacted by scan_for_secrets()
            print(
                f"  [{finding['type']}] "
                f"{finding['file']}:{finding['line']}"
            )

    if report["env_config"]:
        print("\n⚠️  Configuration issues:")
        for finding in report["env_config"]:
            severity = finding["severity"]
            issue = finding["issue"]
            recommendation = finding["recommendation"]
            print(f"  [{severity}] {issue}")
            print(f"    → {recommendation}")

    # Save
    out_file = RESULTS_DIR / f"security_{report['timestamp'].replace(':', '-')}.json"
    with out_file.open("w") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[Hancock Security] Report saved to {out_file}")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
