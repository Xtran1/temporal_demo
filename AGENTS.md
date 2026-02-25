# Temporal Demo (Python) — Agent & Repo Conventions

This repo is a proof-oriented demo of **Temporal durable execution** for experienced engineers: workflows as code with persistence, retries, timers, and crash/restart resilience.

## Ground Rules (Temporal)
- **Workflow code must be deterministic**: no network calls, random, time, or I/O directly in workflows.
- Put side effects in **Activities** (or through Child Workflows) and call them from workflows.
- Assume **replay** can happen at any time; workflow code should be written to be replay-safe.

## Python Environment (required)
- Python version is pinned in `.python-version` (3.12).
- Use the existing venv at `.venv/`.
- Use **uv** for dependency management and running commands.
  - Prefer `uv run ...` for executing Python so it always uses the project environment.
  - Avoid calling `pip` directly.

Common commands:
- Create/sync venv: `uv venv && uv sync`
- Add deps: `uv add temporalio`
- Run python: `uv run python main.py`
- Run tests: `uv run python -m unittest discover -s tests -p "test*.py" -v`

If you see cache permission errors from `uv` (e.g. writing to `~/.cache/uv`), set:
- `UV_CACHE_DIR=/tmp/uv-cache`

## Local Temporal (docker-compose)
- We will run Temporal Server + UI via `docker-compose`.
- Standard dev loop:
  - `docker compose up -d`
  - `uv run python -m apps.worker`
  - `uv run python -m apps.client ...`

## Repo Layout (target)
- `apps/worker/`: Temporal workers (workflows + activities registration)
- `apps/client/`: CLI utilities to start/signal/query workflows
- `src/temporal_demo/workflows/`: workflow implementations (deterministic only)
- `src/temporal_demo/activities/`: activity implementations (side effects)
- `docker-compose.yml`: Temporal Server + UI
- `docs/`: demo scripts (crash/restart, retries, signals, timers)

## Git Workflow (required)
- Make a **git commit after finishing each discrete task**, e.g. writing `AGENTS.md` or `TODO.md`.
- Keep commits small and message them as `docs: ...`, `chore: ...`, `feat: ...`.
