---
name: hancock-enhance
description: "Enhance Hancock with new security capabilities, modes, collectors, or integrations following HancockForge development process. Use when: adding pentest features, implementing new security modes, creating threat intel collectors, building SOAR/SIEM integrations, expanding RAG knowledge base, adding sandboxed tool wrappers, creating new agentic workflows."
argument-hint: "Feature/capability to add (e.g., 'Add cloud pentesting mode', 'Implement Splunk webhook', 'Create IoT recon collector')"
agent: "0ai"
tools: [read_file, replace_string_in_file, multi_replace_string_in_file, create_file, run_in_terminal, execution_subagent, semantic_search, grep_search]
---

You are enhancing Hancock with a new security capability following the **HancockForge Iterative Development Process**.

## Core Requirements

**SAFETY & ETHICS FIRST**: Every enhancement MUST preserve the "authorized-scope-only + responsible disclosure" ethos. Implement OWASP Top 10 for LLM Agents mitigations (prompt guards, intent verification, output sandboxing, least-privilege tool wrappers, human-in-the-loop for high-risk actions).

**NEVER** generate code that enables unauthorized real-world attacks.

## Iterative Development Process

Follow these steps exactly:

### 1. Acknowledge Current State
- Read [ROADMAP.md](../../ROADMAP.md) to identify current version (v0.X.X)
- Check [CHANGELOG.md](../../CHANGELOG.md) for last commit context
- Review relevant existing code in:
  - Core: `hancock_agent.py`, `hancock_langgraph.py`, `hancock_pipeline.py`
  - Collectors: `collectors/` directory
  - Security: `sandbox/`, `input_validator.py`, `0ai_zero_day_guard.py`
  - Deploy: `deploy/`, `Dockerfile`, `docker-compose.yml`
  - Tests: `tests/`, `fuzz/`

### 2. Analyze Impact
Assess impact on:
- Existing modes (pentest, soc, sigma, yara, ioc, osint, graphql, code, ciso, auto)
- System prompts (maintain guardrails from [CLAUDE.md](../../.claude/CLAUDE.md))
- Collectors and data pipelines
- Deployment configs (Docker, K8s, Helm)
- API endpoints and SDKs (Python/Node.js clients)
- Security posture (SECURITY.md compliance)

### 3. Propose Detailed Plan
Create plan with:
- **Feature Overview**: What capability is being added
- **Architecture**: Mermaid diagram showing integration points
- **Pros**: Benefits and capabilities gained
- **Cons**: Risks, complexity, or trade-offs
- **Risk Score Change**: Current (4-6/10) → New (X/10) with justification
- **NIST/MITRE Mapping**: Map to NIST 800-53 controls and MITRE ATT&CK techniques
- **Files to Modify**: List with change summary
- **Files to Create**: New modules, tests, docs
- **Dependencies**: New packages (add to requirements.txt)

### 4. Output Concrete Code
Provide:
- **Full new files** OR **precise diffs** for modifications
- Python 3.10+ style, 4-space indent, snake_case, 120-char lines
- Type hints, docstrings, error handling
- Input validation (use `input_validator.py` patterns)
- Audit logging for security-sensitive operations
- Configuration via environment variables (`.env.example` update)

### 5. Provide Test Commands
Include:
- **Unit tests**: `pytest tests/test_new_feature.py -v`
- **Integration tests**: Full workflow validation
- **Fuzz tests** (if applicable): `make fuzz-target TARGET=fuzz_new_feature`
- **Local validation**: Commands to test manually
- **Kali one-liners**: Quick pentester validation commands

### 6. Update Documentation
Update these files:
- `ROADMAP.md`: Add to appropriate version milestone
- `CHANGELOG.md`: Document changes under current version
- `README.md`: Update feature list, usage examples (if user-facing)
- `docs/`: Add detailed documentation if needed
- Mermaid diagrams: Architecture or workflow visualizations
- `SECURITY.md`: Security implications or new threat model considerations

### 7. Suggest GitHub PR
Provide:
- **PR Title**: `feat: <clear feature description>`
- **PR Description**: 
  ```markdown
  ## Summary
  [What was added]
  
  ## Changes
  - [Bulleted list of changes]
  
  ## Testing
  - [x] `make test` passes
  - [x] `make lint` passes  
  - [x] Manual validation: [steps taken]
  
  ## Security Review
  - [x] Input validation added
  - [x] Auth/scope checks implemented
  - [x] No credentials in code
  - [x] Follows principle of least privilege
  
  ## NIST Mapping
  [Controls addressed]
  
  Closes #[issue-number]
  ```

## Output Format

Structure your response as:

```markdown
## HancockForge Enhancement: [Feature Name]

**Version**: v0.X.X → v0.X+1.X  
**Risk Score**: 4-6/10 → X/10  
**NIST Controls**: AC-6, SI-4, [others]  
**MITRE ATT&CK**: [relevant techniques]

### 1. Current State Analysis
[Brief assessment]

### 2. Impact Analysis
[What changes, what's preserved]

### 3. Implementation Plan
[Detailed plan with Mermaid diagram]

### 4. Code Changes
#### New Files
[Full file content in code blocks]

#### Modified Files
[Precise diffs or multi_replace operations]

### 5. Testing & Validation
[Test commands and expected results]

### 6. Documentation Updates
[Roadmap, changelog, readme changes]

### 7. GitHub PR Ready
[PR title and description]

---
**Next Steps**: [What to tackle after this feature]
```

## Example Enhancements

- **Agentic**: LangGraph multi-agent (Planner → Recon → Executor → Critic → Reporter)
- **Execution**: Safe sandboxed tools (nmap, sqlmap, Metasploit in Docker-in-Docker)
- **Intelligence**: Dynamic RAG over live threat intel (vector DB + collectors)
- **Modes**: AI Red Teaming, Purple Teaming, Exploit PoC Generator
- **Integrations**: SOAR/SIEM webhooks, CI/CD pipelines, OTEL observability
- **Specializations**: Cloud pentest, mobile/IoT recon, supply-chain scanning

## Safety Guardrails

Every enhancement must:
1. ✅ Confirm authorization before suggesting active techniques
2. ✅ Recommend responsible disclosure and remediation
3. ✅ Reference real tools, commands, and CVEs with accuracy
4. ✅ Provide actionable, technically precise answers
5. ✅ Operate STRICTLY within authorized scope

---

**Begin enhancement now following the 7-step process above.**
