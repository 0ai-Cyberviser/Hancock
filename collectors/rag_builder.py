"""
Hybrid RAG Builder — Hancock v0.4.3
Aggregates live threat intel from all collectors into a FAISS vector index.
Enables semantic search over MITRE ATT&CK, NVD CVEs, CISA KEV, Atomic Red Team, and GitHub Security Advisories.

Usage:
    python collectors/rag_builder.py                 # Build full index
    python collectors/rag_builder.py --quick         # Skip collector runs, use existing data/*.json
    python collectors/rag_builder.py --test          # Load and test the index
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

# Conditional imports for RAG dependencies
try:
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain.schema import Document
except ImportError:
    print("[rag] WARNING: langchain dependencies not found.")
    print("[rag] Install with: pip install langchain langchain-community faiss-cpu sentence-transformers")
    sys.exit(1)

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
INDEX_DIR = Path(__file__).parent.parent / "chroma_db" / "hancock_rag"
COLLECTORS = [
    ("mitre", "collectors/mitre_collector.py", "data/raw_mitre.json"),
    ("nvd", "collectors/nvd_collector.py", "data/raw_cve.json"),
    ("kev", "collectors/cisa_kev_collector.py", "data/raw_kev.json"),
    ("atomic", "collectors/atomic_collector.py", "data/raw_atomic.json"),
    ("ghsa", "collectors/ghsa_collector.py", "data/raw_ghsa.json"),
]

# Embedding model (384-dim, fast, runs on CPU)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def run_collectors(verbose: bool = True):
    """Execute all threat intel collectors to refresh data/*.json outputs."""
    print("[rag] 🔄 Running collectors to fetch latest threat intel...")
    for name, script, output_path in COLLECTORS:
        full_path = Path(__file__).parent.parent / script
        if not full_path.exists():
            print(f"[rag]   ⚠️  {name}: script not found at {full_path}, skipping")
            continue
        if verbose:
            print(f"[rag]   ▶️  {name}: {script}")
        try:
            result = subprocess.run(
                [sys.executable, str(full_path)],
                capture_output=not verbose,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                print(f"[rag]   ❌ {name}: collector failed (exit {result.returncode})")
                if not verbose and result.stderr:
                    print(f"       {result.stderr[:200]}")
            elif verbose:
                print(f"[rag]   ✅ {name}: complete")
        except subprocess.TimeoutExpired:
            print(f"[rag]   ⏱️  {name}: timeout (5 min), skipping")
        except Exception as e:
            print(f"[rag]   ❌ {name}: error ({e})")


def load_mitre_data(path: Path) -> List[Document]:
    """Parse MITRE ATT&CK techniques into documents."""
    if not path.exists():
        print(f"[rag] ⚠️  MITRE data not found at {path}, skipping")
        return []

    data = json.loads(path.read_text())
    docs = []

    # Techniques
    for tech in data.get("techniques", [])[:500]:  # Limit to top 500
        text = f"{tech.get('id', 'T????')}: {tech.get('name', 'Unknown')} — {tech.get('description', '')}"
        metadata = {"source": "mitre_attack", "type": "technique", "id": tech.get("id", "")}
        docs.append(Document(page_content=text, metadata=metadata))

    print(f"[rag]   ✅ MITRE: {len(docs)} techniques")
    return docs


def load_nvd_data(path: Path) -> List[Document]:
    """Parse NVD CVEs into documents."""
    if not path.exists():
        print(f"[rag] ⚠️  NVD data not found at {path}, skipping")
        return []

    data = json.loads(path.read_text())
    docs = []

    for cve in data[:1000]:  # Top 1000 recent CVEs
        cve_id = cve.get("id", "CVE-UNKNOWN")
        desc = cve.get("description", "")
        cvss = cve.get("cvss", 0.0)
        vector = cve.get("attack_vector", "")

        text = f"{cve_id} (CVSS {cvss}): {desc}"
        if vector:
            text += f" [Attack Vector: {vector}]"

        metadata = {"source": "nvd", "type": "cve", "id": cve_id, "cvss": cvss}
        docs.append(Document(page_content=text, metadata=metadata))

    print(f"[rag]   ✅ NVD: {len(docs)} CVEs")
    return docs


def load_kev_data(path: Path) -> List[Document]:
    """Parse CISA KEV (Known Exploited Vulnerabilities) into documents."""
    if not path.exists():
        print(f"[rag] ⚠️  KEV data not found at {path}, skipping")
        return []

    data = json.loads(path.read_text())
    docs = []

    for vuln in data[:500]:  # Top 500 KEVs
        cve_id = vuln.get("cve_id", "")
        name = vuln.get("name", "")
        vendor = vuln.get("vendor", "")
        product = vuln.get("product", "")
        action = vuln.get("action", "")
        cvss = vuln.get("cvss_score", 0.0)

        text = f"⚠️ EXPLOITED: {cve_id} — {vendor} {product}: {name}"
        if action:
            text += f" | Required Action: {action}"
        if cvss:
            text += f" (CVSS {cvss})"

        metadata = {"source": "cisa_kev", "type": "exploited_vuln", "id": cve_id, "cvss": cvss}
        docs.append(Document(page_content=text, metadata=metadata))

    print(f"[rag]   ✅ CISA KEV: {len(docs)} exploited vulnerabilities")
    return docs


def load_atomic_data(path: Path) -> List[Document]:
    """Parse Atomic Red Team test cases into documents."""
    if not path.exists():
        print(f"[rag] ⚠️  Atomic data not found at {path}, skipping")
        return []

    data = json.loads(path.read_text())
    docs = []

    for test in data[:300]:  # Top 300 tests
        technique_id = test.get("technique_id", "")
        name = test.get("name", "")
        description = test.get("description", "")
        platform = test.get("platform", "")

        text = f"🔬 Atomic Red Team {technique_id}: {name} — {description}"
        if platform:
            text += f" [Platform: {platform}]"

        metadata = {"source": "atomic_red_team", "type": "test", "id": technique_id}
        docs.append(Document(page_content=text, metadata=metadata))

    print(f"[rag]   ✅ Atomic Red Team: {len(docs)} tests")
    return docs


def load_ghsa_data(path: Path) -> List[Document]:
    """Parse GitHub Security Advisories into documents."""
    if not path.exists():
        print(f"[rag] ⚠️  GHSA data not found at {path}, skipping")
        return []

    data = json.loads(path.read_text())
    docs = []

    for advisory in data[:500]:  # Top 500 advisories
        ghsa_id = advisory.get("id", "")
        summary = advisory.get("summary", "")
        severity = advisory.get("severity", "")
        cves = advisory.get("cves", [])

        text = f"📦 {ghsa_id} ({severity}): {summary}"
        if cves:
            text += f" | CVEs: {', '.join(cves[:3])}"

        metadata = {"source": "github_advisory", "type": "advisory", "id": ghsa_id, "severity": severity}
        docs.append(Document(page_content=text, metadata=metadata))

    print(f"[rag]   ✅ GitHub Advisories: {len(docs)} advisories")
    return docs


def build_index(quick: bool = False, verbose: bool = True) -> Tuple[FAISS, int]:
    """Build FAISS vector index from all threat intel sources."""
    if not quick:
        run_collectors(verbose=verbose)

    print("[rag] 📚 Loading threat intel data...")
    all_docs = []

    # Load all data sources
    all_docs.extend(load_mitre_data(DATA_DIR / "raw_mitre.json"))
    all_docs.extend(load_nvd_data(DATA_DIR / "raw_cve.json"))
    all_docs.extend(load_kev_data(DATA_DIR / "raw_kev.json"))
    all_docs.extend(load_atomic_data(DATA_DIR / "raw_atomic.json"))
    all_docs.extend(load_ghsa_data(DATA_DIR / "raw_ghsa.json"))

    if not all_docs:
        print("[rag] ❌ No documents loaded — check that collectors have run successfully")
        sys.exit(1)

    print(f"[rag] 🧮 Embedding {len(all_docs)} documents with {EMBEDDING_MODEL}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    # Build FAISS index
    vectorstore = FAISS.from_documents(all_docs, embeddings)

    # Save to disk
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR))

    print(f"[rag] 💾 Saved FAISS index to {INDEX_DIR}")
    print(f"[rag] ✅ Hybrid RAG index built: {len(all_docs)} documents")

    return vectorstore, len(all_docs)


def test_index():
    """Load and test the RAG index with sample queries."""
    if not INDEX_DIR.exists():
        print(f"[rag] ❌ Index not found at {INDEX_DIR} — run build first")
        sys.exit(1)

    print(f"[rag] 🔍 Loading index from {INDEX_DIR}...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    vectorstore = FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True
    )

    # Test queries
    test_queries = [
        "credential dumping lsass mimikatz",
        "SQL injection vulnerability CVE",
        "lateral movement techniques",
        "log4shell remote code execution",
        "privilege escalation windows",
    ]

    print("[rag] 🧪 Running test queries...\n")
    for query in test_queries:
        print(f"🔎 Query: '{query}'")
        results = vectorstore.similarity_search(query, k=3)
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "unknown")
            content = doc.page_content[:150]
            print(f"   {i}. [{source}] {content}...")
        print()

    print("[rag] ✅ Index test complete")


def main():
    parser = argparse.ArgumentParser(description="Hancock Hybrid RAG Index Builder")
    parser.add_argument("--quick", action="store_true", help="Skip collector runs, use existing data")
    parser.add_argument("--test", action="store_true", help="Test the existing index")
    parser.add_argument("--quiet", action="store_true", help="Suppress collector output")
    args = parser.parse_args()

    if args.test:
        test_index()
    else:
        build_index(quick=args.quick, verbose=not args.quiet)


if __name__ == "__main__":
    main()
