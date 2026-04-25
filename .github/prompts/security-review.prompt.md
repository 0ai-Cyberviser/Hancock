---
name: security-review
description: "Perform comprehensive security code review for OWASP Top 10, CWE, and common vulnerabilities. Use when: auditing code, reviewing pull requests, analyzing application security, finding injection flaws, checking authentication/authorization, validating input handling."
argument-hint: "Language/framework (or leave blank to auto-detect from selection)"
agent: "0ai"
tools: [read_file, grep_search, semantic_search, vscode_listCodeUsages]
---

Perform a comprehensive security code review on the selected code or specified file(s).

## Security Analysis Framework

### 1. Scope Identification

**Code Context**:
- Language: [Python, JavaScript, Java, C#, PHP, Go, etc.]
- Framework: [Django, Flask, Express, Spring, .NET, etc.]
- Application Type: [Web API, Frontend, Backend, Microservice, etc.]
- Authentication Method: [JWT, OAuth, Session, API Key, etc.]

**Review Scope**:
- Files/Functions: [list what's being reviewed]
- Lines of Code: [approximate count]
- Entry Points: [user inputs, API endpoints, file uploads, etc.]

### 2. OWASP Top 10 Analysis

Check for each vulnerability class:

#### A01:2021 – Broken Access Control
- [ ] Missing authorization checks on sensitive functions
- [ ] Insecure Direct Object References (IDOR)
- [ ] Path traversal vulnerabilities
- [ ] Elevation of privilege (horizontal/vertical)
- [ ] Force browsing to authenticated pages
- [ ] CORS misconfiguration

**Findings**: [list issues or "✓ None found"]

#### A02:2021 – Cryptographic Failures
- [ ] Hardcoded secrets (API keys, passwords, tokens)
- [ ] Weak encryption algorithms (MD5, SHA1, DES)
- [ ] Insufficient key lengths (< 2048-bit RSA)
- [ ] Plaintext storage of sensitive data
- [ ] Missing TLS/SSL enforcement
- [ ] Weak random number generation

**Findings**: [list issues or "✓ None found"]

#### A03:2021 – Injection
- [ ] SQL Injection (dynamic queries, string concatenation)
- [ ] NoSQL Injection (MongoDB, etc.)
- [ ] Command Injection (os.system, subprocess, exec)
- [ ] LDAP Injection
- [ ] XPath Injection
- [ ] Template Injection (SSTI)
- [ ] XML Injection / XXE

**Findings**: [list issues or "✓ None found"]

#### A04:2021 – Insecure Design
- [ ] Missing rate limiting / throttling
- [ ] No abuse prevention (account enumeration, brute force)
- [ ] Insufficient business logic validation
- [ ] Missing security headers
- [ ] Overly permissive defaults
- [ ] No threat modeling evidence

**Findings**: [list issues or "✓ None found"]

#### A05:2021 – Security Misconfiguration
- [ ] Debug mode enabled in production
- [ ] Default credentials not changed
- [ ] Directory listing enabled
- [ ] Verbose error messages (stack traces)
- [ ] Unnecessary features enabled
- [ ] Missing security patches / outdated dependencies

**Findings**: [list issues or "✓ None found"]

#### A06:2021 – Vulnerable Components
- [ ] Outdated dependencies with known CVEs
- [ ] Unused libraries (attack surface expansion)
- [ ] Missing integrity checks (SRI)
- [ ] Unsigned packages / compromised supply chain risk

**Findings**: [list issues or "✓ None found"]

Run dependency check:
```bash
# Python
pip-audit
safety check

# Node.js
npm audit
yarn audit

# Java
dependency-check

# Go
nancy
```

#### A07:2021 – Authentication Failures
- [ ] Weak password requirements
- [ ] Credential stuffing vulnerabilities
- [ ] Missing account lockout
- [ ] Insecure session management
- [ ] Predictable session IDs
- [ ] Missing MFA support
- [ ] Insecure password recovery

**Findings**: [list issues or "✓ None found"]

#### A08:2021 – Software/Data Integrity Failures
- [ ] Unsigned updates / auto-updates without verification
- [ ] Insecure deserialization (pickle, yaml.load)
- [ ] Missing CI/CD pipeline security
- [ ] No integrity verification on artifacts

**Findings**: [list issues or "✓ None found"]

#### A09:2021 – Logging & Monitoring Failures
- [ ] Insufficient logging (no audit trail)
- [ ] Sensitive data in logs (passwords, tokens)
- [ ] No alerting on security events
- [ ] Missing log integrity protection
- [ ] Logs not centralized

**Findings**: [list issues or "✓ None found"]

#### A10:2021 – Server-Side Request Forgery (SSRF)
- [ ] User-controlled URLs in HTTP requests
- [ ] Missing URL validation (scheme, host whitelist)
- [ ] Internal service exposure
- [ ] Cloud metadata API access (169.254.169.254)

**Findings**: [list issues or "✓ None found"]

### 3. Input Validation Analysis

For each user input:

**Input Sources**:
- [ ] HTTP parameters (GET, POST, headers, cookies)
- [ ] File uploads
- [ ] Database queries
- [ ] External APIs
- [ ] Configuration files

**Validation Checks**:
- [ ] Type checking (int, string, email, URL)
- [ ] Length limits (min/max)
- [ ] Format validation (regex)
- [ ] Whitelist vs blacklist approach
- [ ] Encoding/escaping (HTML, SQL, XML, JSON)
- [ ] Canonicalization (path normalization)

**Findings**: [specific input validation issues]

### 4. Authentication & Authorization Review

**Authentication Mechanisms**:
```
[Describe how users authenticate]
```

**Issues Found**:
- [ ] Password storage (bcrypt, Argon2, PBKDF2 vs plain/MD5)
- [ ] Token handling (secure storage, expiration, rotation)
- [ ] Session management (secure flags, httpOnly, SameSite)

**Authorization Logic**:
```
[Describe how permissions are checked]
```

**Issues Found**:
- [ ] Missing permission checks
- [ ] Inconsistent enforcement
- [ ] Client-side only validation
- [ ] Role confusion / privilege escalation

### 5. CWE Mapping

Map findings to Common Weakness Enumerations:

| Finding | CWE | Severity |
|---------|-----|----------|
| SQL Injection in login | CWE-89 | Critical |
| Hardcoded API key | CWE-798 | High |
| ... | ... | ... |

**Top CWEs to Check**:
- CWE-79: Cross-Site Scripting (XSS)
- CWE-89: SQL Injection
- CWE-78: OS Command Injection
- CWE-22: Path Traversal
- CWE-352: CSRF
- CWE-502: Deserialization
- CWE-798: Hardcoded Credentials
- CWE-326: Weak Encryption
- CWE-601: Open Redirect
- CWE-918: SSRF

### 6. Secure Coding Patterns

**Good Practices Found** ✓:
- [List positive security patterns observed]

**Missing Patterns**:
- [ ] Parameterized queries / ORMs
- [ ] Input validation library usage
- [ ] Security headers (CSP, HSTS, X-Frame-Options)
- [ ] Output encoding functions
- [ ] Least privilege principle
- [ ] Defense in depth

### 7. Specific Language/Framework Checks

#### Python/Django/Flask
- [ ] `yaml.load()` → use `yaml.safe_load()`
- [ ] `pickle.loads()` → insecure deserialization
- [ ] `eval()`, `exec()` → code injection
- [ ] Debug mode in production (`DEBUG=True`)
- [ ] SQL queries with string formatting
- [ ] Missing CSRF tokens
- [ ] Template auto-escaping disabled

#### JavaScript/Node.js/Express
- [ ] `eval()`, `Function()` constructor
- [ ] `innerHTML` usage (XSS)
- [ ] Prototype pollution
- [ ] ReDoS (Regular Expression DoS)
- [ ] Missing helmet.js security headers
- [ ] NoSQL injection (`$where`, `$regex`)
- [ ] Path traversal in `fs` operations

#### Java/Spring
- [ ] XXE vulnerabilities (XML parsers)
- [ ] JNDI injection (Log4Shell pattern)
- [ ] Spring Expression Language (SpEL) injection
- [ ] Insecure deserialization (readObject)
- [ ] Missing CSRF protection
- [ ] SQL injection in JPA native queries

#### PHP
- [ ] `eval()`, `assert()`, `create_function()`
- [ ] `include()`, `require()` with user input
- [ ] `system()`, `exec()`, `passthru()`
- [ ] `unserialize()` vulnerabilities
- [ ] Missing prepared statements
- [ ] `extract()` variable overwrite
- [ ] Disabled `magic_quotes` (legacy)

### 8. Security Testing Recommendations

**Static Analysis Tools**:
- Python: Bandit, Semgrep, Pylint
- JavaScript: ESLint (security plugin), Snyk
- Java: FindBugs, SpotBugs, SonarQube
- PHP: Psalm, PHPStan
- Multi-language: Semgrep, CodeQL

**Dynamic Testing**:
- DAST: OWASP ZAP, Burp Suite
- Fuzzing: AFL, Atheris (Python), jazzer (Java)
- Container scanning: Trivy, Grype
- SAST + SCA: Snyk, Checkmarx

**Manual Testing Focus Areas**:
1. [Business logic flaws that scanners miss]
2. [Complex authorization chains]
3. [Multi-step attack scenarios]

## Output Format

```markdown
# Security Code Review: [Project/Module Name]

## Executive Summary
**Risk Rating**: Critical/High/Medium/Low  
**Critical Issues**: [count]  
**High Issues**: [count]  
**Medium Issues**: [count]  
**Low Issues**: [count]

[2-3 sentence summary of top risks]

## Detailed Findings

### Critical Severity

#### Finding 1: [Title]
**CWE**: CWE-XXX  
**OWASP**: A0X:2021  
**Location**: [file.py:line]

**Vulnerable Code**:
```python
[code snippet]
```

**Explanation**:
[Why this is vulnerable]

**Exploit Scenario**:
[How an attacker could exploit this]

**Remediation**:
```python
[secure code example]
```

**References**:
- [OWASP guidance]
- [CWE description]

---

[Repeat for each finding, organized by severity]

## Positive Findings
[Security controls that are correctly implemented]

## Recommendations

**Immediate (0-7 days)**:
- [ ] Fix critical SQL injection in auth module
- [ ] Remove hardcoded API keys
- [ ] ...

**Short-term (7-30 days)**:
- [ ] Implement rate limiting
- [ ] Add security headers
- [ ] ...

**Long-term (30+ days)**:
- [ ] Security training for developers
- [ ] SAST integration in CI/CD
- [ ] Threat modeling workshop
- [ ] ...

## Testing & Validation

Run these commands to verify findings:

```bash
# Static analysis
bandit -r . -ll

# Dependency check
pip-audit

# Manual testing
[specific commands to reproduce findings]
```

## Compliance Impact

- **OWASP Top 10**: [Compliant / Issues in A01, A03, A06]
- **SANS 25**: [Relevant CWEs present]
- **PCI DSS**: [Requirements 6.5.x violated if applicable]
- **NIST 800-53**: [Controls SI-10, SC-8, AC-3 affected]

---
**Reviewer**: [Your name]  
**Date**: [Review date]  
**Methodology**: Manual + Automated (Bandit, Semgrep)
```

## Safety & Ethics

1. ✅ Focus on DEFENSE (help fix vulnerabilities, not exploit them)
2. ✅ Provide secure code examples, not weaponized exploits
3. ✅ Recommend coordinated disclosure for critical findings
4. ✅ Respect code confidentiality (no sharing external to authorized team)
5. ✅ Prioritize fixes by business impact and exploitability

---

**Begin security code review now.**

If code is selected in the editor, analyze that selection.  
If no selection, analyze the currently open file.  
If a file path is provided, analyze that file.
