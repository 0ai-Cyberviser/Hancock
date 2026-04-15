# 🔍 Hancock — Fuzz Testing

This directory contains [OSS-Fuzz](https://github.com/google/oss-fuzz) integration and
[atheris](https://github.com/google/atheris)-based fuzz targets for the Hancock project.

Hancock participates in **continuous fuzzing** via Google's
[OSS-Fuzz](https://google.github.io/oss-fuzz/) programme, which is within scope
for the [Google Bug Hunters](https://bughunters.google.com/) open-source rewards
programme. Vulnerabilities found through fuzzing can be reported through Google
Bug Hunters.

## Fuzz Targets

| Target | Module Under Test | What It Fuzzes |
|--------|-------------------|---------------|
| `fuzz_nvd_parser.py` | `collectors/nvd_collector.py` | NVD CVE JSON parsing (`parse_cve()`) |
| `fuzz_mitre_parser.py` | `collectors/mitre_collector.py` | MITRE ATT&CK technique extraction |
| `fuzz_formatter.py` | `formatter/to_mistral_jsonl*.py` | JSONL formatter functions (KB, MITRE, CVE, SOC) |
| `fuzz_formatter_v3.py` | `collectors/formatter_v3.py` | v3 dataset formatter (NVD, KEV, GHSA, Atomic) |
| `fuzz_api_inputs.py` | `hancock_agent.py` | REST API endpoint JSON input parsing |
| `fuzz_webhook_signature.py` | `hancock_agent.py` | HMAC-SHA256 webhook signature verification |
| `fuzz_ghsa_parser.py` | `collectors/ghsa_collector.py` | GitHub Security Advisory parsing |
| `fuzz_xml_parsing.py` | `collectors/nmap_recon.py` | XML parsing via defusedxml |
| `fuzz_input_validator.py` | `input_validator.py` | IOC type detection, payload validation, regex matching |
| `fuzz_atomic_parser.py` | `collectors/atomic_collector.py` | Atomic Red Team YAML test parsing (regex-heavy) |
| `fuzz_graphql_security_tester.py` | `collectors/graphql_security_tester.py` | GraphQL CLI/identifier input parsing and report generation paths |
| `fuzz_osint_geolocation.py` | `collectors/osint_geolocation.py` | Multi-provider geolocation response parsing fallback chain |
| `fuzz_webhook_request_parsing.py` | `hancock_agent.py` | `/v1/webhook` signature + body parsing with malformed/oversized input |

## Quick Start

```bash
# Install fuzzing dependencies
pip install atheris

# Run all fuzz targets (60 seconds each)
make fuzz

# Run a specific target (5 minutes)
make fuzz-target TARGET=fuzz_nvd_parser

# Run manually with custom options
python fuzz/fuzz_nvd_parser.py -atheris_runs=100000 -max_total_time=600 fuzz/corpus/nvd_parser
```

## Seed Corpus

Each target has a seed corpus in `corpus/<target_name>/` containing valid and edge-case
inputs. New corpora now include malformed JSON, oversized payloads, invalid encodings, and
edge Unicode samples to quickly reach parser edge conditions. The fuzzer uses these as
starting points to generate new interesting inputs.

## CI Integration

- **CIFuzz (ClusterFuzzLite)**: The `.github/workflows/cifuzz.yml` workflow uses
  [ClusterFuzzLite](https://google.github.io/clusterfuzzlite/) to build and run fuzz
  targets on every PR that modifies relevant source files, catching regressions before
  merge. Configuration lives in `.clusterfuzzlite/`. Once hancock is accepted into
  OSS-Fuzz, the workflow can be switched to the CIFuzz actions.
- **Continuous Fuzzing**: The `.github/workflows/continuous-fuzz.yml` workflow runs all
  fuzz targets daily with extended duration (10 minutes each) to catch deeper bugs.
- **OSS-Fuzz**: Configuration in `fuzz/oss-fuzz/` for continuous fuzzing via Google's
  OSS-Fuzz infrastructure (pending project registration).

## Google Bug Hunters

This project is eligible for [Google Bug Hunters](https://bughunters.google.com/)
open-source rewards. If you discover a vulnerability through fuzzing:

1. **OSS-Fuzz bugs** — Issues found by OSS-Fuzz are automatically filed and tracked.
   Reporters can claim rewards through the Bug Hunters platform once the bug is
   confirmed and fixed.
2. **Manual fuzzing** — If you find a crash or vulnerability by running fuzz targets
   locally, report it through [Google Bug Hunters](https://bughunters.google.com/)
   for open-source projects.
3. **Responsible disclosure** — Please allow 90 days for fixes before public
   disclosure, per [Google's disclosure policy](https://g.co/vulnz).

See also: [SECURITY.md](../SECURITY.md) for the project's vulnerability disclosure
policy.

## OSS-Fuzz Project Config

```
fuzz/oss-fuzz/
├── project.yaml   # OSS-Fuzz project metadata
├── Dockerfile     # Build environment for OSS-Fuzz
└── build.sh       # Compilation script for fuzz targets
```

## ClusterFuzzLite Config

```
.clusterfuzzlite/
├── project.yaml   # ClusterFuzzLite project metadata
├── Dockerfile     # Build environment for ClusterFuzzLite
└── build.sh       # Compilation script for fuzz targets
```

## Local Crash Repro Workflow

```bash
# 1) Reproduce quickly with existing corpus
python fuzz/fuzz_webhook_request_parsing.py \
  -atheris_runs=100000 \
  -max_total_time=300 \
  fuzz/corpus/webhook_request_parsing

# 2) Re-run a specific crashing input from CI/ClusterFuzzLite artifacts
python fuzz/fuzz_webhook_request_parsing.py \
  out/artifacts/fuzz_webhook_request_parsing/crash-*

# 3) Minimize a crashing input (optional)
python fuzz/fuzz_webhook_request_parsing.py \
  -atheris_runs=0 \
  -reduce_inputs=1 \
  out/artifacts/fuzz_webhook_request_parsing/crash-*
```

For corpus growth tracking in CI, inspect uploaded `cifuzz-corpus-*` artifacts (`out/corpus` and
`out/new_corpus`) alongside `cifuzz-crashes-*` artifacts (`out/artifacts`).

## Adding a New Fuzz Target

1. Create `fuzz/fuzz_<name>.py` following the atheris pattern:
   ```python
   import atheris
   import sys

   def TestOneInput(data: bytes) -> None:
       # Your fuzzing logic here
       pass

   def main() -> None:
       atheris.Setup(sys.argv, TestOneInput)
       atheris.Fuzz()

   if __name__ == "__main__":
       main()
   ```
2. Add seed inputs to `fuzz/corpus/<name>/`
3. The CIFuzz and continuous fuzzing workflows automatically pick up new `fuzz_*.py`
   targets — no workflow changes needed.
4. Test locally: `python fuzz/fuzz_<name>.py -atheris_runs=10000 fuzz/corpus/<name>`
