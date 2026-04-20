# Zero-Day Detection & Multi-Model Routing

## Overview

Hancock v0.6.0+ includes advanced zero-day detection capabilities powered by machine learning, hybrid RAG (Retrieval-Augmented Generation), and intelligent multi-model routing. These features enhance Hancock's ability to identify, analyze, and respond to potential security vulnerabilities.

## Architecture

### Components

1. **Zero-Day Guard** (`hancock_zeroday_guard.py`)
   - ML-based prompt injection detection
   - Anomaly detection using Isolation Forest and Local Outlier Factor
   - OWASP LLM01/LLM04/LLM06 compliance enforcement
   - Real-time threat scoring

2. **Hybrid RAG** (`hancock_rag.py`)
   - FAISS semantic search with sentence transformers
   - BM25 keyword retrieval
   - Live threat intelligence ingestion from MITRE, NVD, CISA
   - LLM04 guard for filtering low-confidence results

3. **Multi-Model Router** (`hancock_router.py`)
   - Local-first inference (Ollama/NVIDIA NIM)
   - Cloud fallback (Anthropic Claude, OpenAI GPT)
   - Task-based routing (code, pentest, SOC)
   - LLM06 authorization gates

4. **Zero-Day Finder** (`hancock_zeroday_finder.py`)
   - Source code scanning with Semgrep and Bandit
   - Plugin vulnerability analysis (WordPress, VS Code extensions)
   - Sandboxed PoC generation with Docker
   - Auto-remediation suggestions
   - Responsible disclosure templates

5. **LangGraph Orchestration** (`hancock_langgraph.py`)
   - Multi-agent workflow coordination
   - Security gate integration
   - Sponsor mode for priority features

## Dependencies

The zero-day detection features require additional Python packages:

```bash
pip install langgraph>=0.2.0
pip install sentence-transformers>=2.2.0
pip install faiss-cpu>=1.7.0
pip install scikit-learn>=1.3.0
pip install numpy>=1.24.0
```

### Optional External Tools

- **Ollama** (for local model inference): https://ollama.ai
- **Semgrep** (for code scanning): `pip install semgrep`
- **Docker** (for sandboxed PoC execution)

## Usage

### Zero-Day Guard

The Zero-Day Guard automatically screens all prompts for potential malicious content:

```python
from hancock_zeroday_guard import guard

# Check if a prompt is potentially malicious
score = guard.score("Your prompt here")
is_malicious = guard.is_malicious("Your prompt here")

print(f"Threat score: {score:.4f}")
print(f"Malicious: {is_malicious}")
```

**Features:**
- Entropy analysis to detect obfuscated payloads
- N-gram detection for common injection patterns
- Character ratio analysis for special characters
- Ensemble ML model (Isolation Forest + LOF)

### Hybrid RAG

Ingest threat intelligence and retrieve relevant context:

```python
from hancock_rag import HancockRAG

rag = HancockRAG()

# Ingest documents
texts = ["CVE-2024-1234 affects Apache Struts...", "MITRE ATT&CK T1059..."]
metadata = [{"source": "NVD", "cve": "CVE-2024-1234"}, {"source": "MITRE", "tactic": "T1059"}]
rag.ingest(texts, metadata)

# Retrieve relevant context
query = "Apache Struts vulnerabilities"
results = rag.retrieve(query, k=5)
for result in results:
    print(f"Source: {result['source']}")
    print(f"Text: {result['text']}")
    print(f"Confidence: {result['confidence']:.2f}")
```

**Features:**
- Semantic search with FAISS
- Keyword boosting with BM25
- Confidence-based filtering
- Persistent vector storage

### Multi-Model Router

Route queries to the most appropriate model:

```python
from hancock_router import HancockRouter

router = HancockRouter()
state = {
    "messages": ["Explain SQL injection in PHP"],
    "mode": "pentest"
}

# Router selects best model based on task type and complexity
model_choice = router.route(state)
print(f"Selected model: {model_choice}")
```

**Routing Logic:**
- Code tasks → `qwen2.5-coder:32b`
- Pentest tasks → `mistral:7b-instruct`
- SOC tasks → `mistral:7b-instruct`
- High guard confidence → Blocked
- Low confidence + API key → Cloud fallback

### Zero-Day Finder

Scan source code for potential vulnerabilities:

```python
from hancock_zeroday_finder import scan_source_code, generate_sandboxed_poc, mediate_finding

# Scan a target directory
results = scan_source_code("/path/to/source", plugin_type="generic")

for finding in results["findings"]:
    if finding["zero_day_score"] > 70:
        print(f"High-risk finding: {finding['check_id']}")
        print(f"Score: {finding['zero_day_score']:.1f}")

        # Generate sandboxed PoC
        poc = generate_sandboxed_poc(finding)
        print(f"PoC: {poc}")

        # Get remediation advice
        remediation = mediate_finding(finding)
        print(f"Patch: {remediation['patch']}")
        print(f"Disclosure: {remediation['disclosure_template']}")
```

**Features:**
- Semgrep rule integration
- Plugin-specific scanning (WordPress, VS Code)
- ML-based zero-day scoring
- Docker-isolated PoC execution
- CVE-style disclosure templates

### CLI Usage

```bash
# Run zero-day finder from command line
python3 hancock_zeroday_finder.py --target /path/to/scan --mode wordpress

# Test LangGraph workflow
python3 hancock_langgraph.py
```

## LangGraph Workflow

The orchestration flow integrates all components:

```
Entry Point
    ↓
Zero-Day Guard (LLM01 check)
    ↓
Planner
    ↓
Sponsor Mode Check
    ↓
Multi-Model Router (LLM06 authorization)
    ↓
Hybrid RAG (context retrieval)
    ↓
Recon Agent
    ↓
Executor Agent (tool execution)
    ↓
Critic Agent (review)
    ↓
Zero-Day Finder (vulnerability scanning)
    ↓
Reporter Agent (final report)
    ↓
END
```

## Security Features

### OWASP LLM Top 10 Compliance

- **LLM01 (Prompt Injection)**: Zero-Day Guard screens all inputs
- **LLM04 (Model Denial of Service)**: RAG confidence filtering prevents low-quality results
- **LLM06 (Sensitive Information Disclosure)**: Router authorization gates prevent unauthorized access

### Sandboxing

- All tool executions via `OrchestrationController`
- Allowlist-based access control
- Docker-isolated PoC generation
- Read-only Google Cloud integrations

### Responsible Disclosure

- 90-day coordinated disclosure templates
- CVSS scoring
- Remediation suggestions
- No live exploit code in production

## Configuration

### Environment Variables

```bash
# Model backends
NVIDIA_API_KEY=your_nvidia_nim_key
ANTHROPIC_API_KEY=your_anthropic_key  # Optional cloud fallback
OPENAI_API_KEY=your_openai_key        # Optional cloud fallback

# Hancock API
HANCOCK_API_KEY=your_api_key
```

### Sponsor Mode

Activate priority features with sponsor mode:

```python
state = {
    "messages": ["bronze mode enabled"],
    "sponsor": True,
    "mode": "pentest"
}
# Enables: priority RAG, early-access features, private datasets
```

## Troubleshooting

### Missing Dependencies

If you see `ModuleNotFoundError` for `langgraph`, `faiss`, `sklearn`, or `sentence_transformers`:

```bash
pip install -r requirements.txt
```

### Ollama Not Available

The router will gracefully fall back if Ollama is not installed:

```
LOCAL: mistral:7b-instruct unavailable (ollama not installed) — using fallback response
```

To install Ollama:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull mistral:7b-instruct
```

### Semgrep Not Available

The zero-day finder will skip scanning if Semgrep is not installed:

```
semgrep not available - install with: pip install semgrep
```

### Docker Not Available

PoC generation will be skipped if Docker is not available:

```
PoC generation skipped (Docker not available)
```

## Performance Considerations

- **FAISS Index**: First-time embedding model download (~100MB)
- **Sentence Transformers**: Initial model load (~2-3 seconds)
- **Semgrep Scans**: Can take 30-300 seconds depending on codebase size
- **Local Models**: Ollama requires ~4GB RAM for Mistral 7B

## Roadmap

- [ ] Integration with GitHub Security Advisory
- [ ] Real-time CVE feed ingestion
- [ ] Advanced plugin scanners (Drupal, Joomla)
- [ ] Multi-language support (Java, Go, Rust)
- [ ] Custom Semgrep rule repository
- [ ] Automated patch generation with LLM

## References

- [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [MITRE ATT&CK](https://attack.mitre.org/)
- [NVD/CVE](https://nvd.nist.gov/)
- [Semgrep Rules](https://semgrep.dev/r)
- [LangGraph](https://github.com/langchain-ai/langgraph)
