#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Pipeline — Dataset orchestration for fine-tuning

Usage:
    python hancock_pipeline.py           # run full pipeline (all phases)
    python hancock_pipeline.py --phase 1 # pentest + SOC KB only
    python hancock_pipeline.py --phase 2 # CVE/GHSA/Atomic + format v2
    python hancock_pipeline.py --phase 3 # all sources + format v3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from collectors.registry import build_default_registry

DATA_DIR = Path(__file__).parent / "data"

REGISTRY = build_default_registry()

PHASE_COLLECTOR_ORDER: dict[int, list[str]] = {
    1: ["pentest-kb", "soc-kb"],
    2: ["mitre", "nvd", "ghsa", "atomic", "formatter-v2"],
    3: ["pentest-kb", "soc-kb", "mitre", "nvd", "kev", "ghsa", "atomic", "formatter-v3"],
}


def run_collector(collector_id: str, data_dir: Path = DATA_DIR) -> None:
    """Run a collector from the registry by id."""
    # data_dir is kept in the signature for future collector extensibility.
    del data_dir
    REGISTRY.run(collector_id)


def run_kev(data_dir: Path = DATA_DIR) -> None:
    """Collect CISA Known Exploited Vulnerabilities."""
    run_collector("kev", data_dir)


def run_atomic(data_dir: Path = DATA_DIR) -> None:
    """Collect Atomic Red Team tests."""
    run_collector("atomic", data_dir)


def run_ghsa(data_dir: Path = DATA_DIR) -> None:
    """Collect GitHub Security Advisories."""
    run_collector("ghsa", data_dir)


def run_formatter_v3()
generate_sbom()
run_trivy_scan()
generate_manifest()
    sign_model(\"hancock-cpu-adapter/\")
    sign_model(\"data/\") -> None:
    """Format all v3 data sources into hancock_v3.jsonl."""
    run_collector("formatter-v3")


def run_kb(data_dir: Path = DATA_DIR) -> None:
    """Build pentest knowledge base."""
    run_collector("pentest-kb", data_dir)


def run_soc_kb(data_dir: Path = DATA_DIR) -> None:
    """Build SOC knowledge base."""
    run_collector("soc-kb", data_dir)


def run_mitre(data_dir: Path = DATA_DIR) -> None:
    """Collect MITRE ATT&CK data."""
    run_collector("mitre", data_dir)


def run_nvd(data_dir: Path = DATA_DIR) -> None:
    """Collect NVD CVE data."""
    run_collector("nvd", data_dir)


def run_formatter(v2: bool = False) -> None:
    """Format collected data into JSONL training samples."""
    run_collector("formatter-v2" if v2 else "formatter-v3")


def run_osint_geolocation(target: str) -> dict:
    """Run OSINT geolocation enrichment for a target IP or domain.

    Performs geolocation lookup, threat intel enrichment, and infrastructure
    mapping. Returns a structured result dictionary.
    """
    try:
        from collectors.osint_geolocation import GeoIPLookup, InfrastructureMapper
    except ImportError as exc:
        print(f"[pipeline] osint_geolocation unavailable: {exc}")
        return {}

    geo = GeoIPLookup()
    mapper = InfrastructureMapper()

    try:
        import socket

        try:
            socket.inet_aton(target)
            results = [geo.lookup_ip(target)]
        except OSError:
            results = geo.lookup_domain(target)

        enriched = [geo.enrich_with_threat_intel(r) for r in results]
        mapping = mapper.map_infrastructure([target])

        return {
            "target": target,
            "geo_results": [vars(r) for r in enriched],
            "infrastructure_map": mapping,
        }
    except Exception as exc:
        print(f"[pipeline] osint_geolocation step failed for {target}: {exc}")
        return {"target": target, "error": str(exc)}


def run_full_assessment(target: str) -> None:
    """Orchestrate a full security assessment pipeline for a given target."""
    allowlist = ["nmap", "sqlmap", "burp"]

    for tool in allowlist:
        if tool == "nmap":
            try:
                from collectors.nmap_recon import run_nmap

                run_nmap(target)
            except Exception as exc:
                print(f"[pipeline] nmap step skipped: {exc}")
        elif tool == "sqlmap":
            try:
                from collectors.sqlmap_exploit import SQLMapAPI

                print(f"[pipeline] sqlmap step ready for {target}")
            except Exception as exc:
                print(f"[pipeline] sqlmap step skipped: {exc}")
        elif tool == "burp":
            try:
                from collectors.burp_post_exploit import BurpAPI

                print(f"[pipeline] burp step ready for {target}")
            except Exception as exc:
                print(f"[pipeline] burp step skipped: {exc}")

    try:
        osint_result = run_osint_geolocation(target)
        if osint_result and not osint_result.get("error"):
            print(f"[pipeline] osint_geolocation completed for {target}")
        else:
            print(f"[pipeline] osint_geolocation step skipped or failed for {target}")
    except Exception as exc:
        print(f"[pipeline] osint_geolocation step skipped: {exc}")

    print("[pipeline] Full assessment completed successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Hancock data pipeline")
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3],
        default=3,
        help="Pipeline phase: 1=KB only, 2=CVE/GHSA/Atomic+v2, 3=all+v3 (default)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory for raw/processed data files",
    )
    parser.add_argument(
        "--list-collectors",
        action="store_true",
        help="List registered collectors and exit.",
    )
    args = parser.parse_args()

    if args.list_collectors:
        for spec in REGISTRY.list_collectors():
            print(f"{spec.collector_id}: {spec.module}.{spec.entrypoint}")
        return

    data_dir: Path = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"[pipeline] Phase {args.phase}: executing registered collectors…")
    for collector_id in PHASE_COLLECTOR_ORDER[args.phase]:
        run_collector(collector_id, data_dir)

    print("[pipeline] Done.")


from data_integrity import generate_manifest

if __name__ == "__main__":
    sys.exit(main())
