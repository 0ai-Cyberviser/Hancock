# 🔍 Hancock — Fuzz Testing

This directory contains [OSS-Fuzz](https://github.com/google/oss-fuzz) integration and
[atheris](https://github.com/google/atheris)-based fuzz targets for the Hancock project.

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
inputs. The fuzzer uses these as starting points to generate new interesting inputs.

## CI Integration

- **CIFuzz**: The `.github/workflows/cifuzz.yml` workflow runs fuzz targets on every PR
  that modifies relevant source files, catching regressions before merge.
- **Continuous Fuzzing**: The `.github/workflows/continuous-fuzz.yml` workflow runs all
  fuzz targets daily with extended duration (10 minutes each) to catch deeper bugs.
- **OSS-Fuzz**: Configuration in `oss-fuzz/` for continuous fuzzing via Google's
  OSS-Fuzz infrastructure.

## OSS-Fuzz Project Config

```
fuzz/oss-fuzz/
├── project.yaml   # OSS-Fuzz project metadata
├── Dockerfile     # Build environment for OSS-Fuzz
└── build.sh       # Compilation script for fuzz targets
```

### Submitting to Google OSS-Fuzz

To integrate Hancock into [Google OSS-Fuzz](https://github.com/google/oss-fuzz)
for continuous fuzzing, follow these steps:

1. **Sign the Google CLA** — Visit <https://cla.developers.google.com/> and sign
   the Individual (or Corporate) CLA. The email on the CLA **must match** the
   email in your git commits. Without this the `cla/google` check will fail.

2. **Fork `google/oss-fuzz`** fresh from upstream `master` — do **not** reuse a
   stale fork that has diverged from upstream, as extra files will pollute the PR.

3. **Add only three files** in a single commit:
   ```bash
   mkdir -p projects/hancock
   cp fuzz/oss-fuzz/project.yaml  projects/hancock/project.yaml
   cp fuzz/oss-fuzz/Dockerfile    projects/hancock/Dockerfile
   cp fuzz/oss-fuzz/build.sh      projects/hancock/build.sh
   ```

4. **Open a PR** titled `[New Project] Add hancock` with a description that links
   to this repo and the upstream fuzz targets (`fuzz/` directory).

5. **Wait for maintainer approval** — first-time contributors must have their
   workflow runs approved by a Google maintainer before CI checks will execute.

> **Important:** The PR must touch *only* files under `projects/hancock/`.
> Modifying anything else (infra, workflows, docs, etc.) will cause CI failures
> and delay review.

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
3. Add the target to `.github/workflows/cifuzz.yml` matrix
4. Test locally: `python fuzz/fuzz_<name>.py -atheris_runs=10000 fuzz/corpus/<name>`
