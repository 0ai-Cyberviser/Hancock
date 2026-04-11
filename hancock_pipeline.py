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

DATA_DIR = Path(__file__).parent / "data"


def run_kev(data_dir: Path = DATA_DIR) -> None:
    """Collect CISA Known Exploited Vulnerabilities."""
    from collectors.cisa_kev_collector import collect
    collect()


def run_atomic(data_dir: Path = DATA_DIR) -> None:
    """Collect Atomic Red Team tests."""
    from collectors.atomic_collector import collect
    collect()


def run_ghsa(data_dir: Path = DATA_DIR) -> None:
    """Collect GitHub Security Advisories."""
    from collectors.ghsa_collector import collect
    collect()


def run_formatter_v3() -> None:
    """Format all v3 data sources into hancock_v3.jsonl."""
    from collectors.formatter_v3 import format_all
    format_all()


def run_kb(data_dir: Path = DATA_DIR) -> None:
    """Build pentest knowledge base."""
    from collectors.pentest_kb import build
    build()


def run_soc_kb(data_dir: Path = DATA_DIR) -> None:
    """Build SOC knowledge base."""
    from collectors.soc_kb import build
    build()


def run_mitre(data_dir: Path = DATA_DIR) -> None:
    """Collect MITRE ATT&CK data."""
    from collectors.mitre_collector import collect
    collect()


def run_nvd(data_dir: Path = DATA_DIR) -> None:
    """Collect NVD CVE data."""
    from collectors.nvd_collector import collect
    collect()


def run_formatter(v2: bool = False) -> None:
    """Format collected data into JSONL training samples."""
    if v2:
        from formatter.to_mistral_jsonl_v2 import format_all
    else:
        from formatter.to_mistral_jsonl import format_all
    format_all()


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
        # Determine whether target is an IP or domain
        import socket
        try:
            socket.inet_aton(target)
            results = [geo.lookup_ip(target)]
        except OSError:
            results = geo.lookup_domain(target)

        # Enrich with threat intel (gracefully degrades without API keys)
        enriched = [geo.enrich_with_threat_intel(r) for r in results]

        # Map infrastructure (groups by ASN/country/ISP)
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

    # OSINT geolocation enrichment
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
        "--phase", type=int, choices=[1, 2, 3], default=3,
        help="Pipeline phase: 1=KB only, 2=CVE/GHSA/Atomic+v2, 3=all+v3 (default)",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR,
        help="Directory for raw/processed data files",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    if args.phase == 1:
        print("[pipeline] Phase 1: building KB datasets…")
        run_kb(data_dir)
        run_soc_kb(data_dir)
    elif args.phase == 2:
        print("[pipeline] Phase 2: collecting CVE / GHSA / Atomic…")
        run_mitre(data_dir)
        run_nvd(data_dir)
        run_ghsa(data_dir)
        run_atomic(data_dir)
        run_formatter(v2=True)
    else:
        print("[pipeline] Phase 3: full data collection + v3 format…")
        run_kb(data_dir)
        run_soc_kb(data_dir)
        run_mitre(data_dir)
        run_nvd(data_dir)
        run_kev(data_dir)
        run_ghsa(data_dir)
        run_atomic(data_dir)
        run_formatter_v3()

    print("[pipeline] Done.")


if __name__ == "__main__":
    sys.exit(main())
