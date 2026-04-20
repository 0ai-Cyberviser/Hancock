# Hancock Hybrid RAG — Quick Start Guide

**Version:** v0.4.3  
**Status:** Production Ready ✅

---

## 🎯 What is Hybrid RAG?

Hancock's Hybrid RAG (Retrieval-Augmented Generation) combines **live threat intelligence** from multiple authoritative sources with **semantic vector search** to provide accurate, up-to-date security recommendations.

### Data Sources (Auto-Updated Daily)
- **MITRE ATT&CK** — Tactics, techniques, procedures (TTPs)
- **NVD** — Critical/High severity CVEs with CVSS scores
- **CISA KEV** — Known Exploited Vulnerabilities (highest priority)
- **Atomic Red Team** — Detection engineering test cases
- **GitHub Security Advisories** — Supply chain vulnerabilities

### Architecture
```
User Query → LangGraph Planner → RAG Node → FAISS Vector Search
                                       ↓
                            [2000+ Threat Intel Docs]
                                       ↓
                            Semantic Top-5 Results → Context
                                       ↓
                            Recon → Executor → Critic → Reporter
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `langchain` + `langchain-community` (RAG framework)
- `faiss-cpu` (vector similarity search)
- `sentence-transformers` (embedding model: all-MiniLM-L6-v2)

### 2. Build the RAG Index

**Option A: Full build (recommended first run)**
```bash
python collectors/rag_builder.py
```
- Fetches latest threat intel from all collectors (~5-10 min)
- Embeds 2000+ documents
- Saves to `chroma_db/hancock_rag/`

**Option B: Quick build (use existing data)**
```bash
python collectors/rag_builder.py --quick
```
- Skips collector runs
- Uses existing `data/raw_*.json` files
- Faster (~2-3 min)

### 3. Test the Index

```bash
python collectors/rag_builder.py --test
```

Sample output:
```
🔎 Query: 'credential dumping lsass mimikatz'
   1. [mitre_attack] T1003.001: OS Credential Dumping: LSASS Memory — Adversaries may attempt to access credential material stored in the process memory of the Local Security Authority Subsystem Service (LSASS)...
   2. [cisa_kev] ⚠️ EXPLOITED: CVE-2021-36934 — Microsoft Windows: HiveNightmare/SeriousSAM Privilege Escalation (CVSS 7.8)...
   3. [atomic_red_team] 🔬 Atomic Red Team T1003.001: Dump LSASS.exe Memory — Mimikatz credential harvesting test [Platform: Windows]...
```

### 4. Use in LangGraph

```python
from hancock_langgraph import graph

state = {
    'messages': ["How do I detect T1003 credential dumping?"],
    'mode': 'pentest',
    'authorized': True,
    'confidence': 0.95,
    'rag_context': [],
    'rag_sources': [],
    'rag_ids': [],
    'tool_output': ''
}

result = graph.invoke(state)

# Access RAG results
print("RAG Context:", result['rag_context'])
print("Sources:", result['rag_sources'])  # ['mitre_attack', 'cisa_kev', ...]
print("IDs:", result['rag_ids'])          # ['T1003.001', 'CVE-2021-36934', ...]
```

---

## 🔄 Automated Daily Refresh

The RAG index auto-updates daily via GitHub Actions (`.github/workflows/rag-refresh.yml`):

- **Schedule:** Daily at 02:00 UTC
- **Trigger:** `workflow_dispatch` (manual), or push to `collectors/**`
- **Output:** Versioned artifact `hancock-rag-index-<run_number>.tar.gz`

### Download Latest Index

```bash
# From GitHub Actions artifacts (requires gh CLI)
gh run download --name hancock-rag-index-<run_number>
tar -xzf hancock-rag-index.tar.gz
```

Or build locally anytime:
```bash
python collectors/rag_builder.py
```

---

## 📊 Index Statistics

| Metric | Value |
|--------|-------|
| **Total Documents** | ~2000+ |
| **MITRE Techniques** | 500 (top techniques) |
| **NVD CVEs** | 1000 (Critical/High) |
| **CISA KEV** | 500 (actively exploited) |
| **Atomic Tests** | 300 (red team scenarios) |
| **GitHub Advisories** | 500 (supply chain) |
| **Embedding Dimension** | 384 (all-MiniLM-L6-v2) |
| **Index Size** | ~50-100 MB (compressed) |

---

## 🛠️ Troubleshooting

### "No RAG index found" Warning

**Cause:** `chroma_db/hancock_rag/` doesn't exist  
**Fix:**
```bash
python collectors/rag_builder.py
```

### Collector Timeout

**Cause:** NVD API rate limiting or network issues  
**Fix:** Run in quick mode, or wait and retry:
```bash
python collectors/rag_builder.py --quick
```

### Memory Error (OOM) During Embedding

**Cause:** Large dataset + limited RAM  
**Fix:** Reduce doc limits in `rag_builder.py`:
```python
for tech in data.get("techniques", [])[:500]:  # Reduce to 250
```

---

## 🎓 Advanced Usage

### Custom Embedding Model

Edit `collectors/rag_builder.py`:
```python
EMBEDDING_MODEL = "multi-qa-mpnet-base-cos-v1"  # 768-dim, more accurate but slower
```

### Filter by Source

```python
# In rag_node, filter results:
docs = vectorstore.similarity_search(query, k=10)
mitre_only = [d for d in docs if d.metadata['source'] == 'mitre_attack']
```

### Add Custom Data Source

1. Create `collectors/my_custom_collector.py` → outputs `data/raw_custom.json`
2. Add to `COLLECTORS` list in `rag_builder.py`
3. Create loader function `load_custom_data()`
4. Add to `build_index()`: `all_docs.extend(load_custom_data(...))`

---

## 📖 Next Steps

- **Integrate with Hancock Agent API** — add RAG context to `/v1/ask`, `/v1/triage` endpoints
- **LangGraph Multi-Agent** — use RAG in planner node for dynamic technique selection
- **Confidence Scoring** — weight RAG results by source priority (KEV > MITRE > NVD)
- **Hybrid Search** — combine vector similarity + keyword filters (e.g., "CVSS > 8.0")

---

**Questions?** See `ROADMAP.md` for v0.4.3 details or open an issue.  
**Maintainer:** Johnny Watters (0ai-Cyberviser)
