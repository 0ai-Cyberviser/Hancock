"""
Hancock Pipeline — Orchestration for data collection and assessment phases.
CyberViser | hancock_pipeline.py

Usage:
    python hancock_pipeline.py --phase 1 --data-dir ./data
    python hancock_pipeline.py --phase 2
    python hancock_pipeline.py --phase 3
    python hancock_pipeline.py --full
"""
from __future__ import annotations

import argparse
import logging
import sys

logger = logging.getLogger(__name__)


def run_kev(data_dir: str = "./data") -> dict:
    """Run CISA KEV collector."""
    try:
        from collectors.cisa_kev_collector import collect
        result = collect()
        logger.info("[pipeline] KEV collection complete: %d entries", len(result or []))
        return {"status": "ok", "count": len(result or [])}
    except Exception as exc:
        logger.error("[pipeline] KEV collection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_atomic(data_dir: str = "./data") -> dict:
    """Run Atomic Red Team collector."""
    try:
        from collectors.atomic_collector import collect
        result = collect()
        logger.info("[pipeline] Atomic collection complete: %d entries", len(result or []))
        return {"status": "ok", "count": len(result or [])}
    except Exception as exc:
        logger.error("[pipeline] Atomic collection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_ghsa(data_dir: str = "./data") -> dict:
    """Run GitHub Security Advisory collector."""
    try:
        from collectors.ghsa_collector import collect
        result = collect()
        logger.info("[pipeline] GHSA collection complete: %d entries", len(result or []))
        return {"status": "ok", "count": len(result or [])}
    except Exception as exc:
        logger.error("[pipeline] GHSA collection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_formatter_v3(data_dir: str = "./data") -> dict:
    """Run formatter v3 to convert raw data to JSONL."""
    try:
        from collectors.formatter_v3 import format_all
        result = format_all()
        logger.info("[pipeline] Formatter v3 complete")
        return {"status": "ok", "result": str(result)}
    except Exception as exc:
        logger.error("[pipeline] Formatter v3 failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_kb(data_dir: str = "./data") -> dict:
    """Run pentest knowledge base collector."""
    try:
        from collectors.pentest_kb import collect
        result = collect()
        logger.info("[pipeline] KB collection complete: %d entries", len(result or []))
        return {"status": "ok", "count": len(result or [])}
    except Exception as exc:
        logger.error("[pipeline] KB collection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_soc_kb(data_dir: str = "./data") -> dict:
    """Run SOC knowledge base collector."""
    try:
        from collectors.soc_collector import collect
        result = collect()
        logger.info("[pipeline] SOC KB collection complete: %d entries", len(result or []))
        return {"status": "ok", "count": len(result or [])}
    except Exception as exc:
        logger.error("[pipeline] SOC KB collection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_mitre(data_dir: str = "./data") -> dict:
    """Run MITRE ATT&CK collector."""
    try:
        from collectors.mitre_collector import collect
        result = collect()
        logger.info("[pipeline] MITRE collection complete: %d entries", len(result or []))
        return {"status": "ok", "count": len(result or [])}
    except Exception as exc:
        logger.error("[pipeline] MITRE collection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_nvd(data_dir: str = "./data") -> dict:
    """Run NVD CVE collector."""
    try:
        from collectors.nvd_collector import collect
        result = collect()
        logger.info("[pipeline] NVD collection complete: %d entries", len(result or []))
        return {"status": "ok", "count": len(result or [])}
    except Exception as exc:
        logger.error("[pipeline] NVD collection failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_formatter(data_dir: str = "./data") -> dict:
    """Run base formatter to convert raw data."""
    try:
        from formatter.to_mistral_jsonl import format_all
        result = format_all()
        logger.info("[pipeline] Formatter complete")
        return {"status": "ok", "result": str(result)}
    except Exception as exc:
        logger.error("[pipeline] Formatter failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def run_full_assessment(target: str, data_dir: str = "./data") -> dict:
    """
    Orchestrate a full assessment pipeline.

    Runs all collection phases sequentially.  Only operates on systems for
    which the caller has explicit written authorisation.
    """
    results: dict = {}

    phase1_runners = [run_kev, run_atomic, run_ghsa, run_mitre, run_nvd]
    for runner in phase1_runners:
        key = runner.__name__
        results[key] = runner(data_dir)

    phase2_runners = [run_kb, run_soc_kb]
    for runner in phase2_runners:
        key = runner.__name__
        results[key] = runner(data_dir)

    results["run_formatter"] = run_formatter(data_dir)

    logger.info("[pipeline] Full assessment complete for target: %s", target)
    return results


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hancock data pipeline")
    parser.add_argument(
        "--phase", type=int, choices=[1, 2, 3],
        help="Run a specific pipeline phase (1=collect, 2=kb, 3=format)"
    )
    parser.add_argument(
        "--full", action="store_true",
        help="Run all phases end-to-end"
    )
    parser.add_argument(
        "--data-dir", default="./data",
        help="Directory for raw/processed data (default: ./data)"
    )
    parser.add_argument(
        "--target", default="localhost",
        help="Assessment target identifier (used for logging only)"
    )
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = _build_parser().parse_args()

    if args.full:
        results = run_full_assessment(args.target, args.data_dir)
        for k, v in results.items():
            status = v.get("status", "?")
            logger.info("  %s → %s", k, status)
        return 0

    if args.phase == 1:
        for runner in [run_kev, run_atomic, run_ghsa, run_mitre, run_nvd]:
            runner(args.data_dir)
    elif args.phase == 2:
        for runner in [run_kb, run_soc_kb]:
            runner(args.data_dir)
    elif args.phase == 3:
        run_formatter(args.data_dir)
        run_formatter_v3(args.data_dir)
    else:
        _build_parser().print_help()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
