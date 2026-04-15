"""
Fuzz target for GraphQL security tester input parsing paths.

Exercises argument parsing and user-provided identifier handling in
collectors/graphql_security_tester.py.
"""
import argparse
import atheris
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.graphql_security_tester import GraphQLSecurityTester  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--url", required=True)
    parser.add_argument("--token")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--report")
    return parser


def TestOneInput(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)

    # Fuzz argparse paths first; parsing errors should not crash the target.
    parser = _build_parser()
    arg_count = fdp.ConsumeIntInRange(0, 8)
    raw_args = [fdp.ConsumeUnicodeNoSurrogates(64) for _ in range(arg_count)]
    try:
        parser.parse_known_args(raw_args)
    except SystemExit:
        pass

    url = fdp.ConsumeUnicodeNoSurrogates(256) or "https://example/graphql"
    token = fdp.ConsumeUnicodeNoSurrogates(256)
    verbose = fdp.ConsumeBool()

    tester = GraphQLSecurityTester(url=url, token=token, verbose=verbose)

    tester.test_idor(fdp.ConsumeUnicodeNoSurrogates(128))

    ids = [fdp.ConsumeUnicodeNoSurrogates(64) for _ in range(fdp.ConsumeIntInRange(0, 32))]
    tester.test_idor_batch(ids)

    tester.test_mutation_authorization(fdp.ConsumeUnicodeNoSurrogates(128))
    tester.test_jwt_algorithm_confusion()
    tester.test_field_level_authorization()
    tester.test_rate_limiting()
    tester.generate_report()


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
