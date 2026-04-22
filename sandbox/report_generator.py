"""
Hancock Professional Pentest Report Generator — v0.7.0

Transforms workflow execution results into actionable PTES-compliant penetration
testing reports with executive summaries, technical findings, and remediation guidance.

Supported formats:
- Markdown (.md) - Human-readable, version-controllable
- JSON (.json) - Machine-readable, API-friendly
- HTML (.html) - Web-viewable with styling
- PDF (.pdf) - Professional deliverable (requires wkhtmltopdf)

Report structure follows PTES (Penetration Testing Execution Standard):
1. Executive Summary - Business impact, risk ratings, critical findings
2. Methodology - Scope, tools used, testing approach, limitations
3. Findings - Vulnerabilities categorized by severity with CVSS scores
4. Technical Details - Reproduction steps, evidence, tool outputs
5. Remediation Roadmap - Prioritized fixes with timelines
6. Appendix - Raw data, references, tools versions

Author: Johnny Watters (0ai-Cyberviser)
License: See LICENSE and OWNERSHIP.md
"""

import json
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Finding severity levels aligned with CVSS qualitative ratings."""
    CRITICAL = "Critical"  # CVSS 9.0-10.0
    HIGH = "High"          # CVSS 7.0-8.9
    MEDIUM = "Medium"      # CVSS 4.0-6.9
    LOW = "Low"            # CVSS 0.1-3.9
    INFO = "Informational" # CVSS 0.0


class FindingCategory(Enum):
    """OWASP Top 10 / SANS Top 25 aligned categories."""
    INJECTION = "Injection"
    BROKEN_AUTH = "Broken Authentication"
    SENSITIVE_DATA = "Sensitive Data Exposure"
    XXE = "XML External Entities"
    BROKEN_ACCESS = "Broken Access Control"
    SECURITY_MISCONFIG = "Security Misconfiguration"
    XSS = "Cross-Site Scripting"
    INSECURE_DESERIAL = "Insecure Deserialization"
    VULN_COMPONENTS = "Using Components with Known Vulnerabilities"
    INSUFFICIENT_LOGGING = "Insufficient Logging & Monitoring"
    NETWORK = "Network Vulnerabilities"
    OTHER = "Other"


@dataclass
class Finding:
    """Represents a single security finding/vulnerability."""
    title: str
    severity: Severity
    category: FindingCategory
    cvss_score: Optional[float] = None
    cvss_vector: Optional[str] = None
    description: str = ""
    impact: str = ""
    affected_hosts: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)  # Tool outputs, screenshots
    reproduction_steps: List[str] = field(default_factory=list)
    remediation: str = ""
    references: List[str] = field(default_factory=list)  # CVEs, CWEs, OWASP refs

    def to_dict(self) -> Dict:
        """Convert to serializable dict."""
        return {
            "title": self.title,
            "severity": self.severity.value,
            "category": self.category.value,
            "cvss_score": self.cvss_score,
            "cvss_vector": self.cvss_vector,
            "description": self.description,
            "impact": self.impact,
            "affected_hosts": self.affected_hosts,
            "evidence": self.evidence,
            "reproduction_steps": self.reproduction_steps,
            "remediation": self.remediation,
            "references": self.references,
        }


@dataclass
class ReportMetadata:
    """Report metadata and scope information."""
    report_id: str
    title: str
    client_name: str
    test_date: str
    tester_name: str
    scope: List[str]  # Target IPs/domains
    methodology: str = "PTES (Penetration Testing Execution Standard)"
    tools_used: List[str] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to serializable dict."""
        return {
            "report_id": self.report_id,
            "title": self.title,
            "client_name": self.client_name,
            "test_date": self.test_date,
            "tester_name": self.tester_name,
            "scope": self.scope,
            "methodology": self.methodology,
            "tools_used": self.tools_used,
            "limitations": self.limitations,
        }


class ReportGenerator:
    """
    Generates professional penetration testing reports from workflow results.

    Workflow integration:
    1. Orchestrator executes workflow (nmap → nikto → sqlmap)
    2. ReportGenerator parses workflow summary
    3. Extract findings from tool outputs
    4. Generate report in requested format(s)
    """

    def __init__(self, output_dir: Path = Path("sandbox/reports")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_workflow(
        self,
        workflow_summary: Dict,
        metadata: ReportMetadata,
        output_formats: List[str] = ["markdown", "json"]
    ) -> Dict[str, Path]:
        """
        Generate report from workflow execution summary.

        Args:
            workflow_summary: Output from WorkflowOrchestrator.execute_workflow()
            metadata: Report metadata (client, scope, etc.)
            output_formats: List of formats to generate (markdown, json, html, pdf)

        Returns:
            Dict mapping format to output file path
        """
        print(f"\n{'='*80}")
        print(f"GENERATING PENTEST REPORT")
        print(f"{'='*80}")
        print(f"Report ID: {metadata.report_id}")
        print(f"Client: {metadata.client_name}")
        print(f"Target: {', '.join(metadata.scope)}")
        print(f"Formats: {', '.join(output_formats)}")
        print(f"{'='*80}\n")

        # Extract findings from workflow
        findings = self._extract_findings(workflow_summary)
        print(f"Extracted {len(findings)} findings")

        # Build report structure
        report = {
            "metadata": metadata.to_dict(),
            "executive_summary": self._generate_executive_summary(findings),
            "findings": [f.to_dict() for f in findings],
            "workflow_summary": workflow_summary,
        }

        # Generate reports in requested formats
        output_files = {}

        if "json" in output_formats:
            json_path = self._generate_json(report, metadata.report_id)
            output_files["json"] = json_path
            print(f"✅ JSON report: {json_path}")

        if "markdown" in output_formats:
            md_path = self._generate_markdown(report, metadata.report_id)
            output_files["markdown"] = md_path
            print(f"✅ Markdown report: {md_path}")

        if "html" in output_formats:
            html_path = self._generate_html(report, metadata.report_id)
            output_files["html"] = html_path
            print(f"✅ HTML report: {html_path}")

        if "pdf" in output_formats:
            pdf_path = self._generate_pdf(report, metadata.report_id)
            if pdf_path:
                output_files["pdf"] = pdf_path
                print(f"✅ PDF report: {pdf_path}")
            else:
                print(f"⚠️  PDF generation skipped (wkhtmltopdf not available)")

        print(f"\n{'='*80}")
        print(f"REPORT GENERATION COMPLETE")
        print(f"{'='*80}\n")

        return output_files

    def _extract_findings(self, workflow_summary: Dict) -> List[Finding]:
        """Extract security findings from workflow step outputs."""
        findings = []

        for step in workflow_summary.get("steps", []):
            tool = step.get("tool", "")
            output = step.get("result", {}).get("output", "") if step.get("result") else ""

            if not output or output == "(simulated output)":
                continue

            # Parse tool-specific findings
            if tool == "nmap":
                findings.extend(self._parse_nmap_findings(output, workflow_summary["target"]))
            elif tool == "nikto":
                findings.extend(self._parse_nikto_findings(output, workflow_summary["target"]))
            elif tool == "sqlmap":
                findings.extend(self._parse_sqlmap_findings(output, workflow_summary["target"]))
            elif tool == "enum4linux":
                findings.extend(self._parse_enum4linux_findings(output, workflow_summary["target"]))

        return findings

    def _parse_nmap_findings(self, output: str, target: str) -> List[Finding]:
        """Parse nmap output for security findings."""
        findings = []

        # Simplified parser — production would use nmap XML output
        output_lower = output.lower()

        # Check for open ports
        if "open" in output_lower:
            # Count open ports (simplified)
            open_count = output_lower.count("open")

            if open_count > 10:
                severity = Severity.MEDIUM
                cvss = 5.0
            elif open_count > 5:
                severity = Severity.LOW
                cvss = 3.0
            else:
                severity = Severity.INFO
                cvss = 0.0

            findings.append(Finding(
                title=f"Open Ports Detected ({open_count} ports)",
                severity=severity,
                category=FindingCategory.NETWORK,
                cvss_score=cvss,
                description=f"Host {target} has {open_count} open ports exposed to the network.",
                impact="Open ports increase attack surface and may expose vulnerable services.",
                affected_hosts=[target],
                evidence=[output[:500]],
                reproduction_steps=[
                    f"Run: nmap -sV {target}",
                    "Observe open ports in output"
                ],
                remediation="Close unnecessary ports. Implement firewall rules to restrict access.",
                references=["CWE-693: Protection Mechanism Failure"]
            ))

        # Check for outdated software versions
        if "version" in output_lower and any(year in output for year in ["2018", "2019", "2020"]):
            findings.append(Finding(
                title="Outdated Software Detected",
                severity=Severity.MEDIUM,
                category=FindingCategory.VULN_COMPONENTS,
                cvss_score=6.0,
                description="Services running outdated software versions detected.",
                impact="Outdated software may contain known vulnerabilities.",
                affected_hosts=[target],
                evidence=[output[:500]],
                remediation="Update all services to latest stable versions.",
                references=["CWE-1104: Use of Unmaintained Third Party Components"]
            ))

        return findings

    def _parse_nikto_findings(self, output: str, target: str) -> List[Finding]:
        """Parse nikto output for web vulnerabilities."""
        findings = []

        output_lower = output.lower()

        # SQL injection indicators
        if "sql" in output_lower or "injection" in output_lower:
            findings.append(Finding(
                title="Potential SQL Injection Vulnerability",
                severity=Severity.CRITICAL,
                category=FindingCategory.INJECTION,
                cvss_score=9.8,
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
                description="Web application may be vulnerable to SQL injection attacks.",
                impact="Attacker could extract sensitive data, modify database, or gain unauthorized access.",
                affected_hosts=[target],
                evidence=[output[:500]],
                reproduction_steps=[
                    f"Run: nikto -h http://{target}",
                    "Check for SQL injection vectors in output"
                ],
                remediation="Use parameterized queries. Implement input validation and WAF.",
                references=["CWE-89: SQL Injection", "OWASP A03:2021 Injection"]
            ))

        # XSS indicators
        if "xss" in output_lower or "cross-site" in output_lower:
            findings.append(Finding(
                title="Cross-Site Scripting (XSS) Vulnerability",
                severity=Severity.HIGH,
                category=FindingCategory.XSS,
                cvss_score=7.3,
                description="Web application vulnerable to XSS attacks.",
                impact="Attacker could execute malicious scripts in victim browsers.",
                affected_hosts=[target],
                evidence=[output[:500]],
                remediation="Implement output encoding and Content Security Policy.",
                references=["CWE-79: Cross-site Scripting", "OWASP A07:2021 XSS"]
            ))

        return findings

    def _parse_sqlmap_findings(self, output: str, target: str) -> List[Finding]:
        """Parse sqlmap output for confirmed SQL injection."""
        findings = []

        if "vulnerable" in output.lower() or "injectable" in output.lower():
            findings.append(Finding(
                title="Confirmed SQL Injection Vulnerability",
                severity=Severity.CRITICAL,
                category=FindingCategory.INJECTION,
                cvss_score=10.0,
                cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
                description="SQL injection confirmed via automated exploitation.",
                impact="Complete database compromise possible. RCE potential.",
                affected_hosts=[target],
                evidence=[output[:500]],
                reproduction_steps=[
                    f"Run: sqlmap -u http://{target}/vulnerable-page?id=1",
                    "Confirm injection point",
                    "Extract database schema"
                ],
                remediation="IMMEDIATE: Use prepared statements. Audit all SQL queries. Deploy WAF.",
                references=[
                    "CWE-89: SQL Injection",
                    "OWASP A03:2021 Injection",
                    "NIST SP 800-53 SI-10"
                ]
            ))

        return findings

    def _parse_enum4linux_findings(self, output: str, target: str) -> List[Finding]:
        """Parse enum4linux output for SMB enumeration findings."""
        findings = []

        if "users" in output.lower() or "shares" in output.lower():
            findings.append(Finding(
                title="SMB Information Disclosure",
                severity=Severity.MEDIUM,
                category=FindingCategory.SENSITIVE_DATA,
                cvss_score=5.3,
                description="SMB service discloses user and share information anonymously.",
                impact="Attackers can enumerate valid usernames for password attacks.",
                affected_hosts=[target],
                evidence=[output[:500]],
                remediation="Disable null sessions. Restrict SMB access to authorized networks only.",
                references=["CWE-200: Information Exposure"]
            ))

        return findings

    def _generate_executive_summary(self, findings: List[Finding]) -> Dict:
        """Generate executive summary with risk ratings."""
        severity_counts = {
            "critical": sum(1 for f in findings if f.severity == Severity.CRITICAL),
            "high": sum(1 for f in findings if f.severity == Severity.HIGH),
            "medium": sum(1 for f in findings if f.severity == Severity.MEDIUM),
            "low": sum(1 for f in findings if f.severity == Severity.LOW),
            "info": sum(1 for f in findings if f.severity == Severity.INFO),
        }

        # Calculate overall risk rating
        if severity_counts["critical"] > 0:
            overall_risk = "Critical"
            risk_color = "red"
        elif severity_counts["high"] > 0:
            overall_risk = "High"
            risk_color = "orange"
        elif severity_counts["medium"] > 0:
            overall_risk = "Medium"
            risk_color = "yellow"
        elif severity_counts["low"] > 0:
            overall_risk = "Low"
            risk_color = "green"
        else:
            overall_risk = "Informational"
            risk_color = "blue"

        # Top 3 critical findings
        critical_findings = [f for f in findings if f.severity in [Severity.CRITICAL, Severity.HIGH]]
        critical_findings.sort(key=lambda f: f.cvss_score or 0, reverse=True)
        top_findings = critical_findings[:3]

        return {
            "overall_risk": overall_risk,
            "risk_color": risk_color,
            "total_findings": len(findings),
            "severity_breakdown": severity_counts,
            "top_critical_findings": [f.title for f in top_findings],
            "summary_text": self._generate_summary_text(overall_risk, severity_counts),
        }

    def _generate_summary_text(self, overall_risk: str, severity_counts: Dict) -> str:
        """Generate human-readable executive summary text."""
        total = sum(severity_counts.values())

        text = f"Overall Risk Rating: {overall_risk}\n\n"
        text += f"The security assessment identified {total} findings:\n"

        if severity_counts["critical"] > 0:
            text += f"- {severity_counts['critical']} Critical vulnerabilities requiring immediate remediation\n"
        if severity_counts["high"] > 0:
            text += f"- {severity_counts['high']} High-severity issues requiring urgent attention\n"
        if severity_counts["medium"] > 0:
            text += f"- {severity_counts['medium']} Medium-severity issues for planned remediation\n"
        if severity_counts["low"] > 0:
            text += f"- {severity_counts['low']} Low-severity observations\n"
        if severity_counts["info"] > 0:
            text += f"- {severity_counts['info']} Informational findings\n"

        if severity_counts["critical"] > 0 or severity_counts["high"] > 0:
            text += "\n⚠️  Critical/High findings pose immediate risk to confidentiality, integrity, or availability."
            text += " Immediate action required."

        return text

    def _generate_json(self, report: Dict, report_id: str) -> Path:
        """Generate JSON report."""
        output_path = self.output_dir / f"{report_id}.json"

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        return output_path

    def _generate_markdown(self, report: Dict, report_id: str) -> Path:
        """Generate Markdown report."""
        output_path = self.output_dir / f"{report_id}.md"

        md = self._build_markdown_content(report)

        with open(output_path, 'w') as f:
            f.write(md)

        return output_path

    def _build_markdown_content(self, report: Dict) -> str:
        """Build Markdown report content."""
        metadata = report["metadata"]
        exec_summary = report["executive_summary"]
        findings = report["findings"]

        md = f"""# {metadata['title']}

**Report ID:** {metadata['report_id']}
**Client:** {metadata['client_name']}
**Test Date:** {metadata['test_date']}
**Tester:** {metadata['tester_name']}
**Methodology:** {metadata['methodology']}

---

## Executive Summary

**Overall Risk Rating:** {exec_summary['overall_risk']}
**Total Findings:** {exec_summary['total_findings']}

### Severity Breakdown

| Severity | Count |
|----------|-------|
| 🔴 Critical | {exec_summary['severity_breakdown']['critical']} |
| 🟠 High | {exec_summary['severity_breakdown']['high']} |
| 🟡 Medium | {exec_summary['severity_breakdown']['medium']} |
| 🟢 Low | {exec_summary['severity_breakdown']['low']} |
| ℹ️ Info | {exec_summary['severity_breakdown']['info']} |

### Summary

{exec_summary['summary_text']}

---

## Scope & Methodology

**Target Scope:**
"""
        for scope_item in metadata['scope']:
            md += f"- {scope_item}\n"

        md += f"\n**Tools Used:**\n"
        for tool in metadata.get('tools_used', []):
            md += f"- {tool}\n"

        md += "\n---\n\n## Findings\n\n"

        # Sort findings by severity
        severity_order = {
            "Critical": 0,
            "High": 1,
            "Medium": 2,
            "Low": 3,
            "Informational": 4
        }
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f['severity'], 5))

        for idx, finding in enumerate(sorted_findings, 1):
            severity_icon = {
                "Critical": "🔴",
                "High": "🟠",
                "Medium": "🟡",
                "Low": "🟢",
                "Informational": "ℹ️"
            }.get(finding['severity'], "")

            md += f"### {idx}. {severity_icon} {finding['title']}\n\n"
            md += f"**Severity:** {finding['severity']}  \n"
            if finding.get('cvss_score'):
                md += f"**CVSS Score:** {finding['cvss_score']}  \n"
            md += f"**Category:** {finding['category']}  \n"
            md += f"**Affected Hosts:** {', '.join(finding['affected_hosts'])}  \n\n"

            md += f"**Description:**  \n{finding['description']}\n\n"
            md += f"**Impact:**  \n{finding['impact']}\n\n"

            if finding.get('reproduction_steps'):
                md += "**Reproduction Steps:**\n"
                for step in finding['reproduction_steps']:
                    md += f"1. {step}\n"
                md += "\n"

            md += f"**Remediation:**  \n{finding['remediation']}\n\n"

            if finding.get('references'):
                md += "**References:**  \n"
                for ref in finding['references']:
                    md += f"- {ref}\n"
                md += "\n"

            md += "---\n\n"

        md += f"""
## Appendix

### Tools Used
"""
        for tool in metadata.get('tools_used', []):
            md += f"- {tool}\n"

        md += f"""
### Testing Limitations

"""
        for limitation in metadata.get('limitations', []):
            md += f"- {limitation}\n"

        md += f"""
---

*This report was generated by Hancock v0.7.0*
*Report generation timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*
"""

        return md

    def _generate_html(self, report: Dict, report_id: str) -> Path:
        """Generate HTML report from Markdown."""
        # First generate markdown
        md_path = self._generate_markdown(report, f"{report_id}_temp")

        output_path = self.output_dir / f"{report_id}.html"

        # Simple HTML wrapper (production would use proper markdown → HTML converter)
        with open(md_path, 'r') as f:
            md_content = f.read()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{report["metadata"]["title"]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; border-bottom: 2px solid #95a5a6; padding-bottom: 8px; margin-top: 30px; }}
        h3 {{ color: #7f8c8d; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        .critical {{ color: #e74c3c; font-weight: bold; }}
        .high {{ color: #e67e22; font-weight: bold; }}
        .medium {{ color: #f39c12; font-weight: bold; }}
        .low {{ color: #27ae60; font-weight: bold; }}
        code {{ background-color: #ecf0f1; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background-color: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
<pre>{md_content}</pre>
</body>
</html>"""

        with open(output_path, 'w') as f:
            f.write(html)

        # Clean up temp markdown
        md_path.unlink()

        return output_path

    def _generate_pdf(self, report: Dict, report_id: str) -> Optional[Path]:
        """Generate PDF report (requires wkhtmltopdf)."""
        try:
            # Check if wkhtmltopdf is available
            subprocess.run(
                ["wkhtmltopdf", "--version"],
                capture_output=True,
                check=True
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

        # Generate HTML first
        html_path = self._generate_html(report, report_id)
        output_path = self.output_dir / f"{report_id}.pdf"

        try:
            subprocess.run(
                ["wkhtmltopdf", str(html_path), str(output_path)],
                capture_output=True,
                check=True
            )
            return output_path
        except subprocess.CalledProcessError:
            return None


# Example usage
if __name__ == "__main__":
    print("Hancock Professional Report Generator v0.7.0")
    print("=" * 80)

    # Example workflow summary (from orchestrator)
    workflow_summary = {
        "workflow_id": "web-assessment-demo",
        "status": "completed",
        "target": "example.com",
        "total_steps": 3,
        "completed": 3,
        "failed": 0,
        "skipped": 0,
        "total_time": 45.2,
        "steps": [
            {
                "tool": "nmap",
                "description": "Port scan",
                "status": "completed",
                "result": {
                    "output": "PORT     STATE SERVICE VERSION\n80/tcp   open  http    Apache 2.4.41\n443/tcp  open  ssl/http Apache 2.4.41"
                }
            },
            {
                "tool": "nikto",
                "description": "Web vulnerability scan",
                "status": "completed",
                "result": {
                    "output": "+ OSVDB-3092: /admin/: This might be interesting...\n+ OSVDB-877: HTTP TRACE method is active, suggesting potential XSS\n+ Potential SQL injection in /login.php"
                }
            }
        ]
    }

    # Report metadata
    metadata = ReportMetadata(
        report_id="PENTEST-2026-001",
        title="Penetration Test Report - Example Corp",
        client_name="Example Corporation",
        test_date="2026-04-22",
        tester_name="Hancock AI (0ai-Cyberviser)",
        scope=["example.com", "192.168.1.0/24"],
        tools_used=["nmap 7.99", "nikto 2.5.0", "sqlmap 1.10.4"],
        limitations=[
            "Testing performed from external network only",
            "No social engineering or physical security testing",
            "Credentials not provided for authenticated testing"
        ]
    )

    # Generate reports
    generator = ReportGenerator()
    output_files = generator.generate_from_workflow(
        workflow_summary=workflow_summary,
        metadata=metadata,
        output_formats=["markdown", "json", "html"]
    )

    print("\nGenerated reports:")
    for fmt, path in output_files.items():
        print(f"  {fmt}: {path}")
