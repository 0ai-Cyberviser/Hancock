"""
Hancock LLM04 Data & Model Poisoning Protection
SHA256 manifest + runtime verification for all datasets
"""
import hashlib
import json
from pathlib import Path
from typing import Dict

MANIFEST_PATH = Path("data/manifest.json")

def compute_sha256(file_path: str) -> str:
    """Compute SHA256 of a dataset file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            sha256.update(block)
    return sha256.hexdigest()

def generate_manifest() -> None:
    """Generate signed manifest for all datasets (run after hancock_pipeline.py)."""
    data_dir = Path("data")
    manifest = {}
    for jsonl in data_dir.glob("*.jsonl"):
        manifest[jsonl.name] = compute_sha256(str(jsonl))
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"✅ LLM04 manifest generated: {MANIFEST_PATH} ({len(manifest)} datasets)")

def verify_dataset(dataset_path: str) -> bool:
    """LLM04 runtime check — fail fast if poisoned."""
    if not MANIFEST_PATH.exists():
        raise RuntimeError("LLM04: No dataset manifest found — run generate_manifest() first")
    manifest = json.loads(MANIFEST_PATH.read_text())
    filename = Path(dataset_path).name
    if filename not in manifest:
        raise RuntimeError(f"LLM04: Dataset {filename} not in signed manifest")
    current_hash = compute_sha256(dataset_path)
    if current_hash != manifest[filename]:
        raise RuntimeError(f"LLM04 DATA POISONING DETECTED: {filename} hash mismatch")
    print(f"✅ LLM04 verification passed: {filename}")
    return True
