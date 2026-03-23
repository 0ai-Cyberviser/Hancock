"""
Hancock pre-flight startup checks.

Validates required environment variables, model backend connectivity,
and disk space before the agent accepts requests.

Usage::

    python deploy/startup_checks.py           # exit 1 on any failure
    python deploy/startup_checks.py --warn    # exit 0 even on failures
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys

logger = logging.getLogger(__name__)

# Minimum free disk space required (bytes)
_MIN_DISK_FREE_BYTES = 500 * 1024 * 1024  # 500 MiB


def check_env_vars() -> list[str]:
    """
    Return a list of error messages for missing/invalid env vars.

    An empty list means all checks passed.
    """
    errors: list[str] = []
    backend = os.getenv("HANCOCK_LLM_BACKEND", "openai").lower()

    if backend == "openai":
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("NVIDIA_API_KEY"):
            errors.append(
                "Neither OPENAI_API_KEY nor NVIDIA_API_KEY is set "
                "(required when HANCOCK_LLM_BACKEND=openai)"
            )
    elif backend == "ollama":
        if not os.getenv("OLLAMA_BASE_URL"):
            logger.info("OLLAMA_BASE_URL not set; defaulting to http://localhost:11434")
    else:
        errors.append(
            f"Unknown HANCOCK_LLM_BACKEND={backend!r}. "
            "Expected 'openai' or 'ollama'."
        )

    return errors


def check_backend_connectivity() -> list[str]:
    """
    Attempt a lightweight HTTP GET to the configured LLM backend.

    Returns a list of error strings (empty = OK).
    """
    import urllib.request
    import urllib.error

    errors: list[str] = []
    backend = os.getenv("HANCOCK_LLM_BACKEND", "openai").lower()

    if backend == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        url = f"{base_url}/api/tags"
        try:
            urllib.request.urlopen(url, timeout=5)
            logger.info("Ollama backend reachable at %s", base_url)
        except Exception as exc:
            errors.append(f"Ollama backend unreachable at {base_url}: {exc}")
    else:
        # OpenAI / NVIDIA NIM — just check DNS resolution
        try:
            urllib.request.urlopen("https://api.openai.com", timeout=5)
            logger.info("OpenAI API endpoint reachable")
        except urllib.error.HTTPError:
            # Any HTTP response (including 4xx) means we reached the server
            logger.info("OpenAI API endpoint reachable (HTTP response received)")
        except Exception as exc:
            errors.append(f"OpenAI endpoint unreachable: {exc}")

    return errors


def check_disk_space(path: str = "/") -> list[str]:
    """
    Ensure sufficient free disk space is available.

    Returns error strings if disk is too full.
    """
    errors: list[str] = []
    try:
        usage = shutil.disk_usage(path)
        if usage.free < _MIN_DISK_FREE_BYTES:
            free_mb = usage.free // (1024 * 1024)
            errors.append(
                f"Low disk space on {path}: only {free_mb} MiB free "
                f"(minimum {_MIN_DISK_FREE_BYTES // (1024 * 1024)} MiB required)"
            )
        else:
            logger.info(
                "Disk space OK: %.1f GiB free on %s",
                usage.free / 1e9, path,
            )
    except Exception as exc:
        errors.append(f"Could not check disk space on {path}: {exc}")

    return errors


def run_all_checks(warn_only: bool = False) -> bool:
    """
    Run all startup checks.

    Parameters
    ----------
    warn_only:
        If True, log failures as warnings instead of raising SystemExit.

    Returns
    -------
    bool
        True if all checks passed, False otherwise.
    """
    all_errors: list[str] = []

    logger.info("=== Hancock startup checks ===")

    all_errors.extend(check_env_vars())
    all_errors.extend(check_backend_connectivity())
    all_errors.extend(check_disk_space())

    if all_errors:
        for err in all_errors:
            logger.error("STARTUP CHECK FAILED: %s", err)
        if not warn_only:
            logger.critical("Startup checks failed — aborting")
            return False
        logger.warning("Startup checks failed (warn-only mode — continuing)")
        return False

    logger.info("All startup checks passed.")
    return True


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Hancock pre-flight startup checks")
    parser.add_argument(
        "--warn",
        action="store_true",
        help="Log failures as warnings but exit 0 regardless",
    )
    args = parser.parse_args()

    ok = run_all_checks(warn_only=args.warn)
    return 0 if (ok or args.warn) else 1


if __name__ == "__main__":
    sys.exit(main())
