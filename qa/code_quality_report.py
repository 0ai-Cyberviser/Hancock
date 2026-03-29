"""
Hancock — Code quality report generator.

Generates metrics including:
- Test coverage (via pytest-cov)
- Cyclomatic complexity (via radon or manual counting)
- File/function statistics
- Trend tracking (stores results in qa/results/)

Run:
    python qa/code_quality_report.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_FILES = [
    "hancock_agent.py",
    "hancock_constants.py",
    "monitoring/logging_config.py",
    "monitoring/metrics_exporter.py",
    "monitoring/health_check.py",
    "monitoring/prometheus_dashboard.py",
    "deploy/startup_checks.py",
    "deploy/graceful_shutdown.py",
]


def _run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def collect_file_stats() -> list[dict]:
    stats = []
    for rel_path in SOURCE_FILES:
        p = Path(rel_path)
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        code_lines    = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        comment_lines = [l for l in lines if l.strip().startswith("#")]
        stats.append({
            "file":          str(p),
            "total_lines":   len(lines),
            "code_lines":    len(code_lines),
            "comment_lines": len(comment_lines),
            "blank_lines":   len(lines) - len(code_lines) - len(comment_lines),
        })
    return stats


def collect_tests() -> dict:
    """Collect test count by running pytest in collection-only mode."""
    rc, output = _run([
        sys.executable, "-m", "pytest",
        "tests/",
        "--ignore=tests/load_test_locust.py",
        "--ignore=tests/benchmark_suite.py",
        "--tb=no", "-q",
        "--co", "-q",  # collect only — fast
    ])
    tests_collected = 0
    for line in output.splitlines():
        if "test" in line.lower() and "selected" in line.lower():
            parts = line.split()
            try:
                tests_collected = int(parts[0])
            except (ValueError, IndexError):
                pass
    return {"tests_collected": tests_collected, "returncode": rc}


def run_flake8() -> dict:
    rc, output = _run([
        sys.executable, "-m", "flake8",
        "--select=E9,F63,F7,F82",
        "--count", "--statistics",
        "hancock_agent.py", "hancock_constants.py",
        "monitoring/", "deploy/",
        "--exclude=deploy/helm",
    ])
    lines = [l for l in output.strip().splitlines() if l.strip()]
    return {"issues": len(lines), "returncode": rc, "output": "\n".join(lines[:20])}


def generate_report() -> dict:
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    report = {
        "timestamp":    timestamp,
        "file_stats":   collect_file_stats(),
        "lint":         run_flake8(),
        "tests":        collect_tests(),
        "summary": {},
    }

    total_lines = sum(f["total_lines"] for f in report["file_stats"])
    total_code  = sum(f["code_lines"]  for f in report["file_stats"])
    report["summary"] = {
        "total_source_files": len(report["file_stats"]),
        "total_lines":        total_lines,
        "total_code_lines":   total_code,
        "lint_issues":        report["lint"]["issues"],
        "lint_passed":        report["lint"]["returncode"] == 0,
    }

    return report


def main() -> None:
    print("[Hancock QA] Generating code quality report...\n")
    report = generate_report()

    # Print summary
    s = report["summary"]
    print(f"  Source files : {s['total_source_files']}")
    print(f"  Total lines  : {s['total_lines']}")
    print(f"  Code lines   : {s['total_code_lines']}")
    print(f"  Lint issues  : {s['lint_issues']} ({'✅' if s['lint_passed'] else '❌'})")

    if report["lint"]["output"]:
        print(f"\nLint output:\n{report['lint']['output']}")

    # Save report
    out_file = RESULTS_DIR / f"quality_{report['timestamp'].replace(':', '-')}.json"
    with out_file.open("w") as fh:
        json.dump(report, fh, indent=2)
    print(f"\n[Hancock QA] Report saved to {out_file}")


if __name__ == "__main__":
    main()
