#!/usr/bin/env python3
# Copyright (c) 2025 CyberViser. All Rights Reserved.
# Licensed under the CyberViser Proprietary License — see LICENSE for details.
"""
Hancock Pipeline — Dataset orchestration for fine-tuning

Usage:
    python hancock_pipeline.py                    # run full pipeline (all phases)
    python hancock_pipeline.py --phase 1          # pentest + SOC KB only
    python hancock_pipeline.py --phase 2          # CVE/GHSA/Atomic + format v2
    python hancock_pipeline.py --phase 3          # all sources + format v3
    python hancock_pipeline.py --assess 10.0.0.1  # automated security assessment
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from orchestration_controller import OrchestrationController, OrchestrationReport

DATA_DIR = Path(__file__).parent / "data"

# ── Security-tool allowlist used by automated assessments ────────────
ASSESSMENT_TOOLS = ["nmap", "sqlmap", "burp", "graphql", "osint"]

# ── Data-collection allowlist used by training-data pipelines ────────
DATA_COLLECTION_TOOLS = [
    "kb",
    "soc_kb",
    "soc_collector",
    "graphql_kb",
    "mitre",
    "nvd",
    "kev",
    "ghsa",
    "atomic",
    "formatter_v3",
]

# =====================================================================
# Individual collector wrappers
# =====================================================================


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


def run_soc_collector() -> None:
    """Collect SOC detection data (MITRE detections + Sigma rules)."""
    from collectors.soc_collector import collect
    collect()


def run_graphql_kb() -> int:
    """Build GraphQL security knowledge base.

    Returns the number of Q&A pairs generated.
    """
    from collectors.graphql_security_kb import collect
    return collect()


def run_graphql_security(url: str, token: str | None = None) -> dict[str, Any]:
    """Run automated GraphQL security tests against *url*.

    Returns the assessment report dictionary produced by the tester.
    """
    try:
        from collectors.graphql_security_tester import GraphQLSecurityTester
    except ImportError as exc:
        print(f"[pipeline] graphql_security_tester unavailable: {exc}")
        return {}

    tester = GraphQLSecurityTester(url=url, token=token, verbose=True)
    tester.run_all_tests()
    return tester.generate_report()


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


# =====================================================================
# Orchestrated assessment helpers
# =====================================================================


def _build_assessment_controller(
    target: str,
    tools: list[str] | None = None,
) -> OrchestrationController:
    """Create an :class:`OrchestrationController` wired for security assessment.

    Each tool is registered as a zero-arg callable that captures *target*
    in its closure so the controller can execute it generically.
    """
    tools = tools or ASSESSMENT_TOOLS
    controller = OrchestrationController(allowlist=tools)

    def _nmap() -> None:
        from collectors.nmap_recon import run_nmap
        run_nmap(target)

    def _sqlmap() -> dict[str, str]:
        from collectors.sqlmap_exploit import SQLMapAPI  # noqa: F401
        return {"status": "ready", "target": target}

    def _burp() -> dict[str, str]:
        from collectors.burp_post_exploit import BurpCollector  # noqa: F401
        return {"status": "ready", "target": target}

    def _graphql() -> dict[str, Any]:
        return run_graphql_security(url=target)

    def _osint() -> dict:
        return run_osint_geolocation(target)

    controller.register_tool("nmap", _nmap)
    controller.register_tool("sqlmap", _sqlmap)
    controller.register_tool("burp", _burp)
    controller.register_tool("graphql", _graphql)
    controller.register_tool("osint", _osint)

    return controller


def _build_data_collection_controller(
    data_dir: Path = DATA_DIR,
    tools: list[str] | None = None,
) -> OrchestrationController:
    """Create an :class:`OrchestrationController` wired for data collection.

    Each tool is registered as a zero-arg callable that captures *data_dir*.
    """
    tools = tools or DATA_COLLECTION_TOOLS
    controller = OrchestrationController(allowlist=tools)

    controller.register_tool("kb", lambda: run_kb(data_dir))
    controller.register_tool("soc_kb", lambda: run_soc_kb(data_dir))
    controller.register_tool("soc_collector", run_soc_collector)
    controller.register_tool("graphql_kb", run_graphql_kb)
    controller.register_tool("mitre", lambda: run_mitre(data_dir))
    controller.register_tool("nvd", lambda: run_nvd(data_dir))
    controller.register_tool("kev", lambda: run_kev(data_dir))
    controller.register_tool("ghsa", lambda: run_ghsa(data_dir))
    controller.register_tool("atomic", lambda: run_atomic(data_dir))
    controller.register_tool("formatter_v3", run_formatter_v3)

    return controller


# =====================================================================
# High-level orchestration functions
# =====================================================================


def run_automated_assessment(
    target: str,
    tools: list[str] | None = None,
) -> OrchestrationReport:
    """Run an automated security assessment against *target*.

    Coordinates every allowed security tool through the
    :class:`OrchestrationController`, collects structured results, and
    returns an :class:`OrchestrationReport`.
    """
    print(f"[pipeline] Starting automated assessment for {target}")
    controller = _build_assessment_controller(target, tools=tools)
    report = controller.run_all()
    print(f"[pipeline] Automated assessment finished: {report.summary()}")
    return report


def run_automated_data_collection(
    data_dir: Path = DATA_DIR,
    tools: list[str] | None = None,
) -> OrchestrationReport:
    """Run the full data-collection pipeline via the orchestration controller.

    Returns an :class:`OrchestrationReport` summarising each step.
    """
    print("[pipeline] Starting automated data collection…")
    controller = _build_data_collection_controller(data_dir, tools=tools)
    report = controller.run_all()
    print(f"[pipeline] Data collection finished: {report.summary()}")
    return report


def run_full_assessment(target: str) -> None:
    """Orchestrate a full security assessment pipeline for a given target.

    Delegates to the :class:`OrchestrationController` for structured tool
    coordination while preserving the original public API.
    """
    report = run_automated_assessment(target)
    if report.failed:
        print(f"[pipeline] {report.failed} tool(s) encountered errors")
    print("[pipeline] Full assessment completed successfully.")


# =====================================================================
# CLI entry-point
# =====================================================================


def main() -> None:
    parser = argparse.ArgumentParser(description="Hancock data pipeline")
    parser.add_argument(
        "--phase", type=int, choices=[1, 2, 3], default=None,
        help="Pipeline phase: 1=KB only, 2=CVE/GHSA/Atomic+v2, 3=all+v3",
    )
    parser.add_argument(
        "--data-dir", type=Path, default=DATA_DIR,
        help="Directory for raw/processed data files",
    )
    parser.add_argument(
        "--assess", metavar="TARGET",
        help="Run automated security assessment against TARGET (IP, URL, or domain)",
    )
    parser.add_argument(
        "--collect-all", action="store_true",
        help="Run full orchestrated data collection (all registered collectors)",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)

    # Automated assessment mode
    if args.assess:
        run_automated_assessment(args.assess)
        return

    # Orchestrated data-collection mode
    if args.collect_all:
        run_automated_data_collection(data_dir)
        return

    # Legacy phase-based data collection (default: phase 3)
    phase = args.phase if args.phase is not None else 3

    if phase == 1:
        print("[pipeline] Phase 1: building KB datasets…")
        run_kb(data_dir)
        run_soc_kb(data_dir)
    elif phase == 2:
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
