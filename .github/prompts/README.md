# Hancock Custom Prompts

This directory contains reusable prompt templates for common Hancock cybersecurity tasks. These prompts integrate with VS Code Copilot and can be invoked via slash commands in chat.

## Available Prompts

| Prompt | Command | Purpose | Best For |
|--------|---------|---------|----------|
| **Hancock Enhance** | `/hancock-enhance` | Add new security capabilities to Hancock | Building features, modes, collectors, integrations |
| **CVE Analyze** | `/cve-analyze` | Deep-dive CVE analysis with MITRE ATT&CK mapping | Vulnerability research, threat intel, patch prioritization |
| **Pentest Report** | `/pentest-report` | Generate professional PTES-compliant reports | Client deliverables, assessment documentation |
| **Threat Intel** | `/threat-intel` | Enrich IOCs with OSINT and multi-source intelligence | SOC investigations, malware analysis, incident response |
| **Security Review** | `/security-review` | Comprehensive OWASP/CWE code security audit | Code reviews, PR analysis, vulnerability hunting |
| **Create Dataset** | `/create-dataset` | Generate fine-tuning datasets in JSONL format | Model training, knowledge base expansion |

## Quick Start

### 1. Using Prompts in VS Code

**Via Chat Panel**:
1. Open Copilot Chat (`Ctrl+Shift+I` or `Cmd+Shift+I`)
2. Type `/` to see available prompts
3. Select prompt from the list
4. Provide required argument or context
5. Receive structured expert guidance

**Via Command Palette**:
1. `Ctrl+Shift+P` / `Cmd+Shift+P`
2. Type "Chat: Run Prompt..."
3. Select prompt
4. Enter arguments

### 2. Example Invocations

```markdown
# Enhance Hancock with new feature
/hancock-enhance Add Kubernetes security scanning mode

# Analyze a CVE
/cve-analyze CVE-2024-1234

# Generate pentest report from findings
/pentest-report Scope: 10.0.0.0/24 web application assessment

# Enrich threat intelligence
/threat-intel 192.168.1.100

# Security code review (select code first, then run)
/security-review Python/Flask

# Create fine-tuning dataset
/create-dataset pentest - web application testing scenarios
```

### 3. With Code Selection

Some prompts work best with code selected in the editor:

1. **Security Review**: Select vulnerable code → Run `/security-review`
2. **Create Dataset**: Select example conversations → Run `/create-dataset`

## Prompt Details

### 🔧 hancock-enhance

**Purpose**: Comprehensive feature development following HancockForge process

**Inputs**:
- New feature/capability description
- Examples: "Add AWS pentest mode", "Integrate Splunk webhook", "Create mobile app security scanner"

**Outputs**:
- Current state analysis
- Impact assessment with risk scoring
- Implementation plan with Mermaid diagrams
- Complete code (new files + diffs)
- Test commands (pytest, fuzz, manual)
- Documentation updates (ROADMAP.md, CHANGELOG.md, README.md)
- GitHub PR template

**Best Practices**:
- Be specific about the feature (not just "improve security")
- Mention target version if known (v0.X.X)
- Reference existing modes/collectors for context

---

### 🔍 cve-analyze

**Purpose**: Multi-source vulnerability intelligence and MITRE ATT&CK mapping

**Inputs**:
- CVE ID (CVE-YYYY-NNNNN)
- Vulnerability description (if CVE unknown)

**Outputs**:
- CVSS scoring and severity
- CISA KEV status check
- MITRE ATT&CK technique mapping
- Exploitation assessment (PoC availability, ITW activity)
- Detection rules (Sigma, YARA, IDS signatures)
- Remediation guidance (patches, workarounds, mitigations)
- Pentest validation steps (authorized scope only)

**Data Sources**:
- Hancock RAG knowledge base (NVD, MITRE, CISA KEV, Atomic Red Team)
- Public threat intel (VirusTotal, AlienVault OTX)
- Exploit databases (Exploit-DB, Metasploit)

---

### 📊 pentest-report

**Purpose**: Professional penetration testing reports following PTES methodology

**Inputs**:
- Findings data (JSON, text, or manual input)
- Scope details (IP ranges, domains, timeline)

**Outputs**:
- Executive summary (C-level audience)
- Technical summary (IT/security teams)
- PTES methodology documentation
- Detailed findings with CVSS/CWE/OWASP mapping
- Risk matrix and remediation roadmap
- Multiple formats (Markdown, HTML, PDF, JSON)

**Report Sections**:
1. Executive Summary (business impact, risk rating)
2. Technical Summary (methodology, tools, timeline)
3. PTES Phases (pre-engagement → reporting)
4. Detailed Findings (vulnerability details, reproduction, evidence)
5. Risk Matrix (prioritized by severity × likelihood)
6. Remediation Roadmap (immediate, short-term, long-term)
7. Appendices (raw outputs, tool configs, compliance mapping)

---

### 🕵️ threat-intel

**Purpose**: IOC enrichment and threat actor attribution

**Inputs**:
- IP address (IPv4/IPv6)
- Domain / FQDN / URL
- File hash (MD5, SHA1, SHA256)
- Email address
- Threat actor name / APT group

**Outputs**:
- IOC classification and reputation
- Multi-source enrichment (VirusTotal, AbuseIPDB, Shodan, etc.)
- Malware analysis (family, capabilities, TTPs)
- Threat actor attribution (APT profile, campaigns)
- Network intelligence (geolocation, ASN, services)
- Risk assessment and recommended actions
- Detection rules (Sigma, YARA, SIEM queries)
- Incident response guidance

**Safety**:
- Passive OSINT only (no active scanning)
- PII sanitization from WHOIS
- Confidence-scored attribution

---

### 🛡️ security-review

**Purpose**: OWASP Top 10 and CWE-based code security audit

**Inputs**:
- Language/framework (or auto-detected from selection)
- Selected code in editor (or current file)

**Outputs**:
- OWASP Top 10:2021 comprehensive analysis
- Input validation assessment
- Authentication/authorization review
- CWE mapping for findings
- Secure coding pattern recommendations
- Language-specific checks (Python, JS, Java, PHP)
- Remediation code examples
- Testing commands (SAST, dependency checks)

**Checks**:
- A01: Broken Access Control
- A02: Cryptographic Failures
- A03: Injection (SQL, Command, XSS, etc.)
- A04: Insecure Design
- A05: Security Misconfiguration
- A06: Vulnerable Components
- A07: Authentication Failures
- A08: Software/Data Integrity
- A09: Logging/Monitoring Failures
- A10: SSRF

---

### 📚 create-dataset

**Purpose**: Generate JSONL fine-tuning datasets for Hancock LLM training

**Inputs**:
- Security domain (pentest, SOC, threat-intel, sigma, yara)
- Specific topic (optional)

**Outputs**:
- `hancock_[domain]_v[X].jsonl` file
- 50+ diverse training examples
- System + user + assistant message format
- Metadata (example count, topics covered)
- Validation commands
- Fine-tuning integration commands

**Quality Standards**:
- ✅ Realistic scenarios (real tools, CVEs, commands)
- ✅ Technical depth (exact syntax, parameters)
- ✅ Safety guardrails (authorization, responsible disclosure)
- ✅ Methodology frameworks (PTES, MITRE ATT&CK)
- ✅ Diverse examples (multiple tools, techniques, contexts)

**Dataset Sources**:
- Hancock collectors (MITRE, NVD, CISA KEV, Atomic Red Team)
- Security knowledge bases (pentest_kb, soc_kb, graphql_security_kb)
- Real-world scenarios (pentest reports, IR cases)

## Advanced Usage

### Combining Prompts

Chain prompts for complex workflows:

```markdown
# 1. Research CVE
/cve-analyze CVE-2024-1234

# 2. Generate detection rule
/hancock-enhance Add Sigma rule for CVE-2024-1234 exploitation

# 3. Create training data
/create-dataset CVE-2024-1234 detection and exploitation scenarios
```

### Custom Arguments

Some prompts accept detailed arguments:

```markdown
/pentest-report {
  "scope": "10.0.0.0/24, example.com",
  "timeline": "2024-04-15 to 2024-04-19",
  "findings": [
    {
      "title": "SQL Injection in login.php",
      "severity": "Critical",
      "cvss": 9.8,
      "evidence": "sqlmap confirmed union-based injection"
    }
  ]
}
```

### Selection-Based Prompts

For security review, select code first:

1. Highlight vulnerable function
2. Run `/security-review`
3. Review OWASP findings
4. Apply suggested fixes

## Integration with Hancock

These prompts leverage Hancock's capabilities:

- **0ai Agent**: Uses the HancockForge custom agent for context
- **Collectors**: References `collectors/` for live threat intel
- **RAG**: Queries Hancock's vector database via `hancock_langgraph.py`
- **Modes**: Aligns with existing modes (pentest, soc, sigma, yara, etc.)
- **Safety**: Enforces "authorized scope only" guardrails

## Contributing New Prompts

To add a new prompt:

1. Create `[name].prompt.md` in this directory
2. Include YAML frontmatter:
   ```yaml
   ---
   name: prompt-name
   description: "Clear description with use-when keywords"
   argument-hint: "What input does this expect?"
   agent: "0ai"  # or "agent" for default
   tools: [relevant, tools]
   ---
   ```
3. Write prompt body with clear structure
4. Add to this README table
5. Test with `Ctrl+Shift+I` → `/prompt-name`

## Safety Guidelines

All prompts enforce Hancock's core principles:

1. ✅ **Authorization First**: Confirm scope before suggesting active techniques
2. ✅ **Responsible Disclosure**: Recommend coordinated disclosure for vulnerabilities
3. ✅ **Accuracy**: Reference real tools, CVEs, and commands
4. ✅ **Defense-Focused**: Prioritize detection and remediation
5. ✅ **No Weaponization**: Provide guidance, not ready-to-run exploits

## Troubleshooting

**Prompt not appearing in chat**:
- Ensure `.prompt.md` extension
- Check YAML frontmatter syntax (no tabs, proper quotes)
- Reload VS Code window

**Prompt gives unexpected results**:
- Provide more specific arguments
- Select relevant code/files before running
- Check that required tools are available

**Want to customize a prompt**:
- Copy to user prompts folder: `~/.config/Code/User/prompts/`
- Edit locally (workspace prompts take precedence)

## Resources

- [VS Code Prompt Files Documentation](https://code.visualstudio.com/docs/copilot/customization/prompt-files)
- [Hancock Project README](../../README.md)
- [Hancock Roadmap](../../ROADMAP.md)
- [Security Guidelines](../../SECURITY.md)

---

**HancockForge** | Cybersecurity AI Assistant  
GitHub: [cyberviser/Hancock](https://github.com/cyberviser/Hancock)  
Docs: [cyberviser.github.io/Hancock](https://cyberviser.github.io/Hancock)
