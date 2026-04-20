
## v0.4.3 — Hybrid RAG Production Integration (COMPLETE)
- [x] Full Hybrid RAG implementation (collectors → FAISS → LangGraph)
- [x] collectors/rag_builder.py — aggregates MITRE/NVD/KEV/Atomic/GHSA into vector DB
- [x] hancock_langgraph.py — loads persisted FAISS index with provenance tracking
- [x] Daily auto-refresh workflow (.github/workflows/rag-refresh.yml)
- [x] RAG dependencies added to requirements.txt
- [x] Semantic search over 2000+ threat intel documents (ATT&CK techniques, CVEs, KEVs, etc.)
NIST: AU-6, IR-4, SI-4

## v0.4.2 — Hybrid RAG + Sponsorship Integration (COMPLETE)
- [x] BuyMeACoffee Bronze tier LIVE → https://buymeacoffee.com/0aic
- [x] Official QR code added (`assets/bmc_qr.png`)
- [x] Full Funding section in README.md (BuyMeACoffee + Open Collective + GitHub Sponsors badges)
- [x] Sponsor Mode node added to LangGraph (priority RAG + early-access)
- [x] Hybrid RAG prototype (static FAISS) → UPGRADED in v0.4.3 to full production
NIST: AU-6, IR-4

## 2026-04-17 194919 — Continuous Improvement Run v0.4.8
- Fuzz suite completed
- v3 dataset built
- LangGraph + RAG verified
- Sandbox rebuilt
- Security lint passed (Hancock-only, no cuda noise)
- Deps + cppcheck auto-installed
- Script recreated after interrupted paste
- Unstaged changes auto-stashed
