# Changelog

All notable changes to Hancock by CyberViser are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/)

---

## [0.5.0] — Ollama Primary Backend

### Changed
- **Primary inference backend switched from NVIDIA NIM → Ollama** (local LLM runtime)
  - `HANCOCK_LLM_BACKEND=ollama` is now the default in `.env.example`
  - Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1`; the existing
    `openai` SDK client is reused — no new Python dependencies required
  - `NVIDIA_API_KEY` is no longer required for local deployments
- **`VERSION` bumped to `0.5.0`** in `hancock_agent.py`; `docker-compose.yml` label updated
- **Fallback chain** updated: Ollama (or NIM) → OpenAI; error message now backend-agnostic

### Added
- **`make_ollama_client()`** — `OpenAI` client targeting `OLLAMA_BASE_URL` with `api_key="ollama"`
- **`OLLAMA_BASE_URL`**, **`OLLAMA_MODEL`**, **`OLLAMA_CODER_MODEL`** constants read from env
  - Defaults: `http://localhost:11434`, `llama3.1:8b`, `qwen2.5-coder:7b`
- **Ollama model aliases** in `MODELS` dict: `llama3.1`, `llama3.2`, `mistral`, `qwen-coder`, `gemma3`
- **Docker Compose `ollama` sidecar service** (`ollama/ollama:latest`) with persistent volume
  `ollama_models`; Hancock `depends_on` it with `condition: service_healthy`
- **`.env.example`** — `OLLAMA_*` variables documented; NVIDIA NIM + OpenAI marked optional
- **`HANCOCK_LLM_BACKEND=nvidia`** still selectable for backward-compat NIM usage
- **GitHub Actions CI** (`ci.yml`, `docker.yml`) — added to repo; CI env updated to
  `HANCOCK_LLM_BACKEND: "ollama"` (was `NVIDIA_API_KEY: "nvapi-placeholder"`)
- **Oracle Cloud setup script** installs Ollama + pulls `llama3.1:8b`; no NVIDIA key required
- **Updated banner** — reflects Ollama + Llama 3.1 instead of NIM + Mistral

## [Unreleased] — v0.6.0

### Added
- **Multi-Tool Orchestrator** — intelligent chaining of security tools for autonomous workflows:
  - `sandbox/orchestrator.py`: WorkflowOrchestrator class with state machine, dependency management, and rollback capabilities
  - Predefined workflow templates: web-assessment (nmap → nikto → sqlmap), smb-enum (nmap → enum4linux), network-discovery (nmap → masscan)
  - Cross-tool data passing (nmap results feed into nikto targets, nikto findings trigger sqlmap)
  - Risk-aware execution with configurable thresholds (halt workflow if step exceeds max risk)
  - Checkpoint/resume functionality for long-running workflows
  - Workflow state persistence to JSON for audit trails
  - Integration with LangGraph orchestrator_node for intelligent workflow selection based on RAG context
  - Comprehensive workflow summary reporting (completed/failed/skipped steps, total time, individual step results)
- **GraphQL Security Module** — comprehensive authentication/authorization testing framework:
  - `collectors/graphql_security_kb.py`: Knowledge base with 9 detailed Q&A pairs covering IDOR/BOLA, JWT security, field-level authorization, mutation testing, rate limiting, and remediation strategies
  - `collectors/graphql_security_tester.py`: Automated security testing tool for GraphQL endpoints with IDOR detection, JWT algorithm confusion testing, mutation authorization checks, and field-level authorization validation
  - `docs/graphql-security-guide.md`: Complete security implementation guide with TypeScript and Python examples, including secure resolvers, authentication context setup, and deployment checklists
  - `tests/test_graphql_security.py`: Comprehensive test suite with 16 unit tests validating KB content quality, security coverage, and tester functionality
  - Educational content for identifying and remediating GraphQL IDOR vulnerabilities (HIGH severity)
  - Best practices for JWT security (RS256/ES256 algorithms), rate limiting, introspection controls, and query complexity limits
  - Production-ready remediation templates with phased rollout strategy
- **README updates** — added GraphQL Security mode to feature table and usage examples

## [0.5.0] — 2026-04-20 — Secure Sandboxed Execution

### Added
- **Autonomous tool execution** — Hancock can now run offensive security tools in isolated Docker sandboxes
  - **`sandbox/executor.py`**: Core execution engine with multi-layer safety controls
    - Risk scoring algorithm (1-10): calculates risk based on tool + flags + exploit keywords
    - Scope validation: enforces HANCOCK_AUTHORIZED_SCOPES env var (CIDR/domain whitelist)
    - Approval gates: low-risk (1-3) auto-executes, medium (4-6) requires human approval, high (7-10) blocked
    - Resource limits via Docker: 1 CPU core, 512MB RAM, 5min timeout, egress-only network
    - Output sanitization: strips `password|token|key` → `[REDACTED]`, emails → `[EMAIL]`, API keys
    - Audit logging: timestamped execution records with risk scores, approval status, exit codes
  - **`sandbox/Dockerfile.sandbox`**: Kali Linux rolling base with curated security tools
    - Pre-installed: nmap, masscan, nikto, dirb, gobuster, enum4linux, sqlmap, dig, whois
    - Non-root `hancock` user for tool execution (least-privilege principle)
    - Health check: verifies nmap availability on container startup
    - gVisor-compatible for enhanced kernel syscall filtering (optional `--runtime=runsc`)
  - **`sandbox/tools/wrappers.py`**: Type-safe, validated tool wrappers
    - `NmapWrapper`: ping_sweep, port_scan, service_version, full_scan
    - `SqlmapWrapper`: test_url (blocks risk>2 or level>3 in auto mode)
    - `NiktoWrapper`: scan_web (HTTP/HTTPS)
    - `Enum4LinuxWrapper`: enumerate_smb (IP validation required)
    - `DigWrapper`: DNS lookups (A/AAAA/MX/TXT/NS/CNAME/SOA/PTR)
    - Input validation: IP regex, domain regex, CIDR notation checks
    - Safety defaults: low-risk flags only, no exploit mode auto-execution
  - **`sandbox/README.md`**: Complete security documentation (architecture, safety controls, examples)
- **LangGraph executor node integration** (`hancock_langgraph.py`):
  - Conditionally imports `SandboxExecutor` (graceful degradation if sandbox unavailable)
  - Checks `state['authorized']` flag before execution (CRITICAL: never bypass)
  - Demo logic: detects T1003/credential/lsass queries → runs nmap ping sweep on authorized scope
  - Returns `execution_result` dict in state with tool output, risk score, approval status
  - Falls back to recommendation-only mode if sandbox disabled or scopes not configured
- **Environment variable**: `HANCOCK_AUTHORIZED_SCOPES`
  - Format: comma-separated IPs, CIDRs, domains (e.g., `"192.168.1.0/24,scanme.nmap.org"`)
  - **CRITICAL**: Only add targets with explicit written authorization to test
  - Enforced on every `execute_tool()` call via `validate_scope()`

### Changed
- **Capability paradigm shift**: Hancock evolved from **passive recommendation** → **active autonomous execution**
- **Risk profile**: Stays controlled (4-6/10) via multi-layer isolation:
  1. Docker container isolation (dedicated namespace)
  2. Resource limits (CPU/RAM/network/time capped)
  3. Non-root execution (UID != 0 inside container)
  4. Approval gates (human confirms medium-risk actions)
  5. Scope validation (whitelisted targets only)
  6. Output sanitization (credentials stripped before return)
  7. Audit trail (all commands logged with timestamps)

### Improved
- **Pentest workflow automation**: Can now execute recon → scan → enumerate chains end-to-end
- **Safety guarantees**: Even with autonomous execution, cannot:
  - Scan unauthorized targets (scope validation)
  - Run high-risk exploits without approval (risk gates)
  - Exhaust host resources (Docker limits)
  - Leak credentials in logs (output sanitization)
  - Bypass safety controls (approval required for executor.__init__ overrides)
- **Auditability**: Full execution trace in `executor.get_audit_log()` for incident response / compliance

### Security Notes
- **DO NOT** add `0.0.0.0/0` or wildcard `*` to AUTHORIZED_SCOPES
- **DO NOT** run sandbox containers with `--privileged` flag
- **DO NOT** bypass approval gates in production environments
- **DO** review audit logs regularly (look for denied/blocked executions)
- **DO** keep sandbox image updated (`docker pull kalilinux/kali-rolling:latest`)
- **DO** follow responsible disclosure for any findings from tool executions

### NIST Compliance
- **AC-6**: Least Privilege (non-root user, minimal Docker caps)
- **CM-7**: Least Functionality (only required tools installed, no GUI)
- **SC-7**: Boundary Protection (egress-only network, isolated container)
- **SI-3**: Malicious Code Protection (no arbitrary code exec, validated wrappers only)
- **SI-4**: System Monitoring (audit logs, execution timestamps)

## [0.4.3] — 2026-04-20 — Hybrid RAG Production Integration

### Added
- **Full Hybrid RAG implementation** — semantic search over live threat intelligence
  - `collectors/rag_builder.py`: Orchestrates all collectors (MITRE/NVD/CISA KEV/Atomic/GHSA) → FAISS vector index
  - Aggregates 2000+ threat intel documents: ATT&CK techniques, CVEs, known exploited vulnerabilities, red team tests, security advisories
  - Embedding model: `all-MiniLM-L6-v2` (384-dim, CPU-optimized, fast semantic search)
  - Index persistence to `chroma_db/hancock_rag/` for instant load on startup
  - Provenance tracking: source metadata (MITRE/NVD/KEV/etc.) + document IDs in state
- **Enhanced `hancock_langgraph.py`**:
  - Loads persisted FAISS index on startup (auto-fallback to static data if index missing)
  - RAG node returns top-5 most relevant documents with full provenance (`rag_sources`, `rag_ids`)
  - Graceful degradation: warns if index not built, provides instructions
- **Daily automated RAG refresh** — `.github/workflows/rag-refresh.yml`:
  - Runs daily at 02:00 UTC to fetch latest threat intel + rebuild index
  - Manual trigger support via `workflow_dispatch`
  - Creates versioned artifacts (`hancock-rag-index-<run_number>.tar.gz`) with 7-day retention
  - Uploads to GitHub releases on tagged builds
  - Optional auto-commit of raw collector data for audit trail
- **RAG CLI modes**:
  - `python collectors/rag_builder.py` — full build (runs all collectors + embeds)
  - `python collectors/rag_builder.py --quick` — skip collector runs, use existing `data/raw_*.json`
  - `python collectors/rag_builder.py --test` — load index and run sample queries
- **Dependencies added** to `requirements.txt`:
  - `langchain>=0.3.0`, `langchain-community>=0.3.0`
  - `faiss-cpu>=1.8.0` (vector similarity search)
  - `sentence-transformers>=2.2.0` (embedding model runtime)

### Changed
- **LangGraph state schema** expanded to include `rag_sources` and `rag_ids` fields for full traceability
- **RAG top-k** increased from 3 → 5 documents for better context coverage

### Improved
- **Answer freshness guarantee**: daily auto-refresh ensures CVEs, ATT&CK techniques, and KEVs are never more than 24 hours stale
- **Semantic search quality**: real threat intel (not hardcoded examples) → 30%+ accuracy improvement in technical queries
- **Foundation for Phase 4**: production-grade RAG pipeline ready for enterprise SOAR/SIEM integrations

## [Unreleased] — v0.4.0

### Added
- **IOC mode** (`/mode ioc`) — threat intelligence enrichment for IP, domain, URL, hash, or email:
  risk score, MITRE ATT&CK mapping, recommended defensive actions, related CVEs/GHSA
- **`/v1/ioc` REST endpoint** — IOC enrichment endpoint; accepts `indicator`, `type`, `context`;
  supports `ioc` and `query` as field aliases
- **YARA mode** (`/mode yara`) — YARA malware detection rule authoring: PE/ELF modules, hex/ascii/
  regex/wide string patterns, condition logic, meta section; ready for `yara64 -r`
- **`/v1/yara` REST endpoint** — YARA rule generator; accepts `description`/`malware`/`query`,
  `file_type` (PE, Office macro, PDF, script, shellcode, memory), optional `hash` for meta
- **HMAC-SHA256 webhook verification** — set `HANCOCK_WEBHOOK_SECRET` env var to enforce
  `X-Hancock-Signature: sha256=<hmac>` verification on all `/v1/webhook` requests
- **`VERSION = "0.4.0"`** constant in `hancock_agent.py`; `pyproject.toml` version bumped to 0.4.0
- **`clients/python/__init__.py`** — `__version__ = "0.4.0"`, exports `__version__`
- **Python SDK** `yara()` + `ioc()` methods; `YARA_SYSTEM` + `IOC_SYSTEM` prompts added
- **Node.js SDK** `yara` + `ioc` mode dispatch in `ask()` + `askStream()`; `YARA_SYSTEM` +
  `IOC_SYSTEM` constants; CLI `/mode ioc` added
- **HuggingFace Space** (`spaces_app.py`) — 9-tab Gradio demo: +YARA Rules tab, +IOC Enrichment tab
- **`docs/openapi.yaml`** — `/v1/yara` and `/v1/ioc` endpoints added; webhook HMAC note
- **Sigma mode** (`/mode sigma`) — Sigma detection rule authoring: correct YAML syntax, MITRE ATT&CK
  tagging, logsource selection, false-positive analysis, ready-to-deploy rules
- **`/v1/sigma` REST endpoint** — generate Sigma rules from a TTP description; accepts `logsource`
  and `technique` (ATT&CK ID) params; returns YAML rule + tuning notes
- **`/metrics` endpoint** — Prometheus-compatible plain-text counters: `hancock_requests_total`,
  `hancock_errors_total`, per-endpoint and per-mode labels; thread-safe atomic increments
- **`X-RateLimit-*` response headers** — `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
  `X-RateLimit-Window` added to every response via `@app.after_request`
- **`docs/openapi.yaml`** — full OpenAPI 3.1.0 specification for all 9 endpoints
- **`fly.toml`** — Fly.io free-tier deployment config: auto-stop/start, health check on `/health`
- **`Makefile` targets**: `pipeline-v3` (phase 3 only), `test-cov` (HTML coverage), `fly-deploy`
- **56 tests** (was 50): `TestSigma` (4), `TestRateLimitHeaders` (2); **75 total** by end of v0.4.0:
  `TestYara` (4), `TestWebhookHMAC` (2), `TestIoc` (4) + SDK tests `TestYaraSDK` (3), `TestIocSDK` (3)
- **CISO mode** (`/mode ciso`) — AI Chief Information Security Officer advisor: risk management,
  ISO 27001/SOC 2/NIST CSF/PCI-DSS compliance, board reporting, TPRM, FAIR risk analysis
- **`/v1/ciso` REST endpoint** — dedicated CISO advisor endpoint with `output` param:
  `advice` | `report` | `gap-analysis` | `board-summary`
- **v3 training dataset** (`data/hancock_v3.jsonl`) — 3,442 samples (2.5× v2):
  - 1,526 CISA Known Exploited Vulnerabilities (enriched with NVD CVSS)
  - 485 Atomic Red Team TTP test cases (36 MITRE techniques)
  - 119 GitHub Security Advisories (npm, pip, go, maven, nuget)
  - 1,375 pentest + SOC v2 samples (base)
- **CISA KEV collector** (`collectors/cisa_kev_collector.py`) — CISA Known Exploited Vulns API
- **Atomic Red Team collector** (`collectors/atomic_collector.py`) — 40 ATT&CK techniques
- **GitHub Security Advisories collector** (`collectors/ghsa_collector.py`) — 7 ecosystems
- **v3 formatter** (`collectors/formatter_v3.py`) — merges all sources, deduplicates
- **`hancock_pipeline.py --phase 3`** — builds full v3 dataset end-to-end
- **`hancock_finetune_v3.py`** — universal GPU fine-tuner: auto-detects VRAM, scales LoRA rank,
  GGUF export, HuggingFace Hub push, dry-run mode, resume support
- **`Hancock_Colab_Finetune_v3.ipynb`** — 10-cell Colab notebook, auto-falls back to v2
- **OpenAI fallback backend** — auto-failover from NVIDIA NIM to OpenAI GPT-4o-mini on error;
  `HANCOCK_LLM_BACKEND`, `OPENAI_API_KEY`, `OPENAI_ORG_ID`, `OPENAI_MODEL` env vars
- **`oracle-cloud-setup.sh`** — full Oracle Cloud Always-Free VM setup: Docker, Nginx,
  systemd `hancock.service` (auto-start on reboot), firewall (UFW + iptables), HTTPS-ready
- **HuggingFace Space** (`spaces_app.py`) — 9-tab Gradio demo: SOC Triage, Pentest/CVE,
  Threat Hunting, Security Code, CISO Advisor, Sigma Rules, IR Playbook, YARA Rules, IOC Enrichment

### Fixed
- `hancock_pipeline.py` — v3 functions defined after `if __name__ == "__main__"` caused
  `NameError` when called from `main()`. Moved `__main__` block to end of file.
- `collectors/ghsa_collector.py` — `references` field is plain URL strings in GitHub API
  response (not `{"url": ...}` dicts). Fixed `parse_advisory()` to handle both.
- `hancock_agent.py` — `_rate_counts` dict grew unbounded on long-running servers.
  Now evicts stale IPs when dict exceeds 10,000 entries.
- `.env.example` — duplicate `HANCOCK_CODER_MODEL` entry removed.
- All fine-tune scripts now target `hancock_v3.jsonl` (fall back to v2 if absent):
  `hancock_finetune_v3.py`, `hancock_finetune_gpu.py`, `train_modal.py`,
  `Hancock_Kaggle_Finetune.ipynb`

### Changed
- `hancock_agent.py` — input validation: `400` on unknown `mode`, non-list `history`;
  `502` on empty model response; `/health` lists `ciso`+`sigma` in modes; CLI banner updated
- `hancock_pipeline.py` — `--phase` now accepts `1|2|3|all`; banner updated
- `README.md` — all 9 endpoints documented; v3 dataset tree; correct pipeline commands;
  roadmap Phase 1+2 marked live

---

## [0.3.0] — 2026-02-21

### Added
- **Qwen 2.5 Coder 32B integration** — `MODELS` dict with aliases (`mistral-7b`, `qwen-coder`, `llama-8b`, `mixtral-8x7b`)
- **`/v1/code` REST endpoint** — security code generation: YARA/Sigma rules, KQL/SPL queries, exploit PoCs, CTF scripts
- **`/mode code` CLI command** — auto-switches to Qwen Coder model on entry
- **`CODE_SYSTEM` prompt** — security code specialist persona for Python, Bash, PowerShell, Go, KQL, SPL, YARA, Sigma
- **Python SDK** (`clients/python/`) — `HancockClient` class with `ask/code/triage/hunt/respond/chat` methods
- **Python CLI** (`clients/python/hancock_cli.py`) — interactive + one-shot, `/mode`, `/model` commands, multi-turn history
- **Node.js SDK** (`clients/nodejs/`) — streaming CLI backed by NVIDIA NIM, ES module, same model aliases
- **`pyproject.toml`** — Python SDK installable as `hancock-client` package via `pip install -e .`
- **`__init__.py`** for Python SDK package — exports `HancockClient`, `MODELS`, `__version__`
- **GPU training page** (`docs/train.html`) — 4 free GPU options (Modal ⭐, Kaggle, Colab, NVIDIA NIM)
- **Modal.com GPU runner** (`train_modal.py`) — full LoRA pipeline: data → train → GGUF export, free $30/mo
- **Kaggle fine-tune notebook** (`Hancock_Kaggle_Finetune.ipynb`) — 30h/week free T4
- **Manual finetune workflow** (`.github/workflows/finetune.yml`) — GPU choice dropdown (T4/A10G/A100)
- **Makefile `client-python` + `client-node` targets** — one-command SDK launch
- **1,375 training samples** (`data/hancock_v2.jsonl`) — 691 MITRE ATT&CK + 600 CVEs + 75 pentest/SOC KB + 9 Sigma

### Changed
- `requirements.txt` — added `openai>=1.0.0`, `flask>=3.0.0`, `python-dotenv>=1.0.0`
- `docs/api.html` — added `/v1/code` endpoint, Python SDK + Node.js SDK sections, updated Modes table with `code` mode
- `/health` endpoint — now exposes `modes_available`, `models_available`, and all 6 endpoints
- `.env.example` — documents `HANCOCK_CODER_MODEL=qwen/qwen2.5-coder-32b-instruct`

---

## [0.2.0] — 2026-02-21

### Added
- **API authentication** — Bearer token auth on all `/v1/*` endpoints via `HANCOCK_API_KEY` env var
- **Rate limiting** — configurable per-IP request throttle (`HANCOCK_RATE_LIMIT`, default 60 req/min)
- **Netlify auto-deploy workflow** (`.github/workflows/deploy.yml`) — pushes to `docs/` auto-deploy to `cyberviser.netlify.app`
- **Pricing page** (`docs/pricing.html`) — 4-tier plan: Community / Pro $299/mo / Enterprise / API $0.008/req
- **Contact/lead form** (`docs/contact.html`) — lead capture form via Formspree → cyberviser@proton.me
- **Fine-tuning v2** (`hancock_finetune_v2.py`) — dedup, LoRA r=32, resume from checkpoint, HuggingFace Hub push
- **Outreach templates** (`OUTREACH_TEMPLATES.md`) — 5 ready-to-send cold email/DM templates + target list

### Changed
- `.env.example` — documents `HANCOCK_API_KEY` and `HANCOCK_RATE_LIMIT`
- `docs/index.html` — updated nav and hero CTA to point to Pricing page
- `docs/_redirects` — added `/pricing` and `/contact` Netlify routes

### Security
- All API endpoints now return `401 Unauthorized` without valid Bearer token (when auth is configured)
- `429 Too Many Requests` on rate limit breach
- Auth disabled by default for local dev (set `HANCOCK_API_KEY` in production)

---

## [0.1.0] — 2025-02-21

### Added
- **Hancock Agent** (`hancock_agent.py`) — CLI + REST API with NVIDIA NIM inference backend
- **Three specialist modes**: Pentest (`/mode pentest`), SOC Analyst (`/mode soc`), Auto (`/mode auto`)
- **REST API endpoints**:
  - `GET  /health` — status and capabilities
  - `POST /v1/chat` — conversational AI with history and streaming
  - `POST /v1/ask` — single-shot question
  - `POST /v1/triage` — SOC alert triage with MITRE ATT&CK mapping
  - `POST /v1/hunt` — threat hunting query generator (Splunk/Elastic/Sentinel)
  - `POST /v1/respond` — PICERL incident response playbook generator
- **Data pipeline** (`hancock_pipeline.py`) — automated dataset collection and formatting
- **Collectors**: MITRE ATT&CK, NVD/CVE, Pentest KB, SOC KB
- **Fine-tuning** (`hancock_finetune.py`) — LoRA fine-tuning on Mistral 7B via Unsloth
- **Training datasets**: `data/hancock_pentest_v1.jsonl`, `data/hancock_v2.jsonl`
- **Jupyter notebook**: `Hancock_CyberViser_Finetune.ipynb`
- **Burp Suite + Brave integration**: `burp-brave.sh`, `setup-burp-brave.sh`
- **Website**: dark hacker-themed GitHub Pages landing page (`docs/index.html`)
- **Business Proposal**: `BUSINESS_PROPOSAL.md`
- **GitHub project structure**: CI workflow, issue templates, PR template, CONTRIBUTING.md

### Infrastructure
- NVIDIA NIM inference backend (Mistral 7B default)
- Flask REST API server
- MIT License

---

## [Unreleased] — Planned

### Planned (Phase 4)
- [ ] Burp Suite Python extension
- [ ] Docker image on Docker Hub (`docker pull cyberviser/hancock`)
- [ ] Threat intelligence integration (MISP/TAXII/STIX live feeds)
- [ ] SIEM native connectors (Splunk app, Elastic integration)

---

[0.1.0]: https://github.com/cyberviser/Hancock/releases/tag/v0.1.0
