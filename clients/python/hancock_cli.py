"""Command-line interface for the Hancock Python SDK."""

from __future__ import annotations
import os
import sys
import argparse
from hancock_client import CHAT_MODE_TO_SYSTEM, HancockClient, MODELS


SUPPORTED_MODES = tuple(CHAT_MODE_TO_SYSTEM.keys())


def _normalize_mode(mode: str) -> str:
    normalized = (mode or "auto").strip().lower()
    return "auto" if normalized == "security" else normalized


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hancock",
        description="Hancock AI Security Agent — Python CLI",
    )
    parser.add_argument(
        "--mode",
        default="auto",
        choices=["security", *SUPPORTED_MODES],
        help="Interaction mode (default: auto; security is an alias for auto)",
    )
    parser.add_argument("--task",  help="One-shot: task or question to answer")
    parser.add_argument("--model", default="mistral-7b",
                        help=f"Model alias. Options: {', '.join(MODELS)}")
    args = parser.parse_args()
    mode = _normalize_mode(args.mode)

    try:
        client = HancockClient(model=args.model)
    except ValueError as e:
        print(f"❌  {e}")
        sys.exit(1)

    if args.task:
        result = client.code(args.task) if mode == "code" else client.chat(args.task, mode=mode)
        print(result)
        return

    # Interactive
    print(f"""
╔══════════════════════════════════════════════════════════╗
║   HANCOCK  —  AI Cybersecurity Agent  (Python client)   ║
║   Powered by NVIDIA NIM + CyberViser                    ║
╚══════════════════════════════════════════════════════════╝
Mode: {mode} | Model: {args.model}
Commands: /mode auto | /mode pentest | /mode soc | /mode code | /mode ciso | /mode sigma | /mode yara | /mode ioc | /mode osint | /mode security | /model <alias> | /exit
Aliases:  {' | '.join(MODELS)}
""")

    history = []

    while True:
        try:
            user_input = input(f"[{mode}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input in ("/exit", "/quit"):
            print("Goodbye.")
            break
        if user_input.startswith("/mode "):
            requested_mode = user_input[6:].strip()
            mode = _normalize_mode(requested_mode)
            if mode not in SUPPORTED_MODES:
                print(f"Unsupported mode: {requested_mode}\n")
                continue
            print(f"Switched to {mode} mode\n")
            history = []
            continue
        if user_input.startswith("/model "):
            alias = user_input[7:].strip()
            client.model = MODELS.get(alias, alias)
            print(f"Model set to {client.model}\n")
            continue

        try:
            if mode == "code":
                answer = client.code(user_input)
            else:
                answer = client.chat(user_input, history=history, mode=mode)
                history.append({"role": "user",      "content": user_input})
                history.append({"role": "assistant",  "content": answer})
                if len(history) > 20:
                    history = history[-20:]
            print(f"\nHancock > {answer}\n")
        except Exception as e:
            print(f"\n⚠️  Error: {e}\n")


if __name__ == "__main__":
    main()
