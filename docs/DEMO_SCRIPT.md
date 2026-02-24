# Demo script: durable execution “why Temporal”

This script is designed to be repeatable and visible in Temporal UI (http://localhost:8233).

## Terminals
- Terminal A: Temporal + UI
- Terminal B: Worker (kill/restart to prove durability)
- Terminal C: Client / watcher

## 1) Start infra
- Terminal A:
  - `docker compose up -d`

## 2) Install deps
- Terminal C:
  - `uv sync`

## 3) Start a worker
- Terminal B:
  - `uv run python -m apps.worker`

## 4) Start a workflow and watch it live
- Terminal C:
  - `uv run python -m apps.client watch --start`

Observations:
- The watcher prints `status`, `step`, and any `message`.
- In Temporal UI, open the workflow’s Event History and watch it grow.

## 5) Unblock approval (signal)
In another Terminal C tab/window:
- `uv run python -m apps.client start-order`
- Copy the `workflow_id=...`
- Approve:
  - `uv run python -m apps.client signal-fraud <workflow_id> --approved true`

## 6) Prove crash/restart resilience (durable execution)
While the workflow is running:
- Terminal B: press Ctrl-C to stop the worker process.

Observations:
- The workflow does not “lose state”; it will be stuck waiting for a worker.
- The watcher continues to show the last known step/state (query is served by Temporal).

Then:
- Terminal B: restart the worker:
  - `uv run python -m apps.worker`

Observation:
- The workflow resumes and completes without any manual checkpointing.

## 7) Dynamic failure injection (Ctrl-C without stopping the watcher)
While `watch` is running:
- Terminal C: press Ctrl-C

What happens:
- The watcher catches Ctrl-C and sends a Temporal Signal to inject a failure into the next `charge_card` Activity call.
- Temporal will retry the Activity per policy; the workflow continues.

Try again:
- Press Ctrl-C multiple times to inject multiple transient failures (one per signal).

## 8) Deterministic failure injection (pre-programmed failpoints)
These failpoints are read by **Activities** (safe) and are repeatable:
- `DEMO_FAIL_CHARGE=transient_first_attempt` (fails once, then succeeds on retry)
- `DEMO_FAIL_CHARGE=business` (non-retryable; workflow should fail/stop depending on handling)

Example:
- Terminal B:
  - `DEMO_FAIL_CHARGE=transient_first_attempt uv run python -m apps.worker`

Then start + approve a new workflow and observe retries in UI.

