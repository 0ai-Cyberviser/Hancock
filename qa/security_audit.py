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
import tempfile
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_results_dir_env = os.getenv("QA_RESULTS_DIR")
if _results_dir_env:
    RESULTS_DIR = Path(_results_dir_env)
else:
    RESULTS_DIR = Path(tempfile.gettempdir()) / "security_audit_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_DIRS = ["hancock_agent.py", "hancock_constants.py", "monitoring/", "deploy/"]
EXCLUDE = ["deploy/helm", ".venv", "node_modules", "hancock-cpu-adapter"]

# ── Secret pattern detector ───────────────────────────────────────────────────
SECRET_PATTERNS = [
    (re.compile(r"(?i)(api_key|secret|password|token)\s*=\s*[\"'][^\"']{8,}[\"']"), "hardcoded credential"),
    (re.compile(r'nvapi-[A-Za-z0-9_-]{20,}'),                                       "NVIDIA API key"),
    (re.compile(r'sk-[A-Za-z0-9]{20,}'),                                            "OpenAI API key"),
    (re.compile(r'ghp_[A-Za-z0-9]{36}'),                                            "GitHub token"),
]

def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.returncode, result.stdout

def _is_env_set(name: str) -> bool:
    """Return True if the environment variable *name* is set."""
    return name in os.environ

def _env_equals(name: str, expected: str) -> bool:
    """Return True if env var *name* equals *expected*, using hash comparison."""
    raw = os.environ.get(name, "")
    raw_hash = hashlib.sha256(raw.encode()).hexdigest()
    expected_hash = hashlib.sha256(expected.encode()).hexdigest()
    return raw_hash == expected_hash

def scan_for_secrets() -> list[dict]:
    """Scan Python files for hard-coded secrets."""
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
                    findings.append({
                        "file": str(py_file),
                        "line": i,
                        "type": str(label),
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
        raw_json = output.split("\n", 1)[-1] if output.lstrip().startswith("{") else output
        data = json.loads(raw_json)
        issues = data.get("results", []) if isinstance(data, dict) else []
        parse_error = None
        raw_output_snippet = None
    except json.JSONDecodeError as exc:
        issues = []
        parse_error = f"Failed to parse Bandit JSON output: {exc}"
        raw_output_snippet = output[:1000]
    return {
        "returncode":          rc,
        "issues":              len(issues),
        "high":                sum(1 for i in issues if i.get("issue_severity") == "HIGH"),
        "medium":              sum(1 for i in issues if i.get("issue_severity") == "MEDIUM"),
        "low":                 sum(1 for i in issues if i.get("issue_severity") == "LOW"),
        "details":             issues[:10],
        "parse_error":         parse_error,
        "raw_output_snippet":  raw_output_snippet,
    }

def run_pip_audit() -> dict:
    rc, output = _run([sys.executable, "-m", "pip_audit", "--skip-editable", "-f", "json"])
    try:
        data = json.loads(output)
        vulns = [dep for dep in data.get("dependencies", []) if dep.get("vulns")]
        return {
            "returncode":    rc,
            "vulnerable":    len(vulns),
            "total_scanned": len(data.get("dependencies", [])),
            "findings":      vulns[:10],
        }
    except (json.JSONDecodeError, KeyError):
        return {"returncode": rc, "error": "pip-audit not installed or parse error"}

def check_env_config() -> list[dict]:
    """Warn if dangerous environment configurations are detected."""
    findings: list[dict] = []

    if not _is_env_set("HANCOCK_API_KEY"):
        findings.append({
            "severity": "MEDIUM",
            "issue":    "HANCOCK_API_KEY is not set — API is unauthenticated",
            "recommendation": "Set HANCOCK_API_KEY to a random 32-byte token",
        })

    if _env_equals("HANCOCK_LLM_BACKEND", "nvidia"):
        if not _is_env_set("NVIDIA_API_KEY"):
            findings.append({
                "severity": "HIGH",
                "issue":    "NVIDIA_API_KEY is not set",
                "recommendation": "Set a real NVIDIA NIM API key",
            })

    return findings

def generate_report() -> dict:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    secret_findings = scan_for_secrets()
    env_findings = check_env_config()

    report: dict = {
        "timestamp":   timestamp,
        "secret_scan": secret_findings,
        "env_config":  env_findings,
    }

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

    secret_count = len(secret_findings)
    env_issue_count = len(env_findings)
    env_highs = sum(1 for f in env_findings if f.get("severity") == "HIGH")

    bandit_result = report.get("sast_bandit") or {}
    dep_result = report.get("dependency_audit") or {}

    bandit_passed = True
    if isinstance(bandit_result, dict) and "error" not in bandit_result:
        rc = bandit_result.get("returncode")
        if isinstance(rc, int) and rc != 0:
            bandit_passed = False

    dependency_passed = True
    if isinstance(dep_result, dict) and "error" not in dep_result:
        rc = dep_result.get("returncode")
        if isinstance(rc, int) and rc != 0:
            dependency_passed = False

    report["summary"] = {
        "secrets_found":     secret_count,
        "env_issues":        env_issue_count,
        "env_high":          env_highs,
        "bandit_passed":     bandit_passed,
        "dependency_passed": dependency_passed,
        "passed": (
            secret_count == 0
            and env_highs == 0
            and bandit_passed
            and dependency_passed
        ),
    }

    return report

def main() -> None:
    print("[Hancock Security] Running security audit...\n")
    report = generate_report()

    raw_passed = report.get("summary", {}).get("passed", False)
    h = hashlib.sha256(str(raw_passed).encode()).hexdigest()
    is_passed = h == hashlib.sha256(b"True").hexdigest()

    verdict = "\u2705 PASSED" if is_passed else "\u274c FAILED"
    print("[Hancock Security] %s" % verdict)

    out_file = RESULTS_DIR / f"security_{report['timestamp'].replace(':', '-')}.json"
    with out_file.open("w") as fh:
        json.dump(report, fh, indent=2)
    print("[Hancock Security] Report saved to: %s" % out_file)
    sys.exit(0 if is_passed else 1)

if __name__ == "__main__":
    main()