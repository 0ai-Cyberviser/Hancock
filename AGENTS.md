# Repository Guidelines

## Project Structure & Module Organization
- `hancock_agent.py` is the main CLI and REST API entry point.
- `hancock_pipeline.py`, `hancock_finetune*.py`, and `train_modal.py` handle dataset generation and fine-tuning workflows.
- `collectors/` contains OSINT, GraphQL, Nmap, SQLMap, and Burp integrations.
- `clients/python/` and `clients/nodejs/` hold the SDK/client examples.
- `tests/` contains pytest suites; `docs/` holds API, deployment, monitoring, and security docs.
- `fuzz/`, `data/`, `build/`, and adapter folders support fuzzing, generated data, and packaging.

## Build, Test, and Development Commands
- `make setup` creates `.venv`, installs dependencies, and seeds `.env` from `.env.example`.
- `make run` starts the interactive CLI; `make server` starts the REST API on port 5000.
- `make test` runs `pytest tests/ -v --tb=short`.
- `make lint` runs flake8 for critical syntax/runtime issues only.
- `make test-cov` generates a coverage report in `htmlcov/index.html`.
- `make fuzz` runs all fuzz targets; `make fuzz-target TARGET=fuzz_nvd_parser` runs one target.

## Coding Style & Naming Conventions
- Use Python 3.10+ style with 4-space indentation, `snake_case` for functions/modules, and `PascalCase` for classes.
- Keep lines within 120 characters where practical.
- The repo’s flake8 config only enforces critical errors (`E9`, `F63`, `F7`, `F82`), so prefer clear, explicit code over cleverness.

## Testing Guidelines
- Write pytest tests in `tests/` with `test_*.py` files and `Test*` classes.
- Cover both success and validation/error paths for API handlers and collectors.
- For API changes, verify `/health`, `/metrics`, auth behavior, and rate-limit headers with the Flask test client.

## Commit & Pull Request Guidelines
- Commit messages are short, imperative, and descriptive, often with an optional scope such as `fix:`, `test:`, or `docs:`.
- PRs should include a clear summary, linked issue if applicable, and the commands you ran (`make test`, `make lint`).
- Include sample payloads or screenshots when changing docs, API responses, or operator-facing output.

## Security & Configuration Tips
- Never commit secrets. Configure `.env` locally with `NVIDIA_API_KEY`, optional `OPENAI_API_KEY`, and `HANCOCK_API_KEY`.
- Keep `/internal/diagnostics` operator-only and preserve auth/rate-limit checks when editing related code.
