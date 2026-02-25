# Temporal durable execution demo (Python)

This repo demonstrates **Temporal’s durable execution**: workflows that keep progressing across worker crashes/restarts, with built-in retries, timers, and external signals—without bespoke checkpointing.

What’s happening in this demo:
- `OrderFulfillmentWorkflow` is a **Workflow** (durable, replayed, deterministic) that orchestrates steps.
- Side effects happen in **Activities** (charge, ship, email).
- The workflow waits for an external **Signal** (`fraud_check_result`) before charging.
- The workflow uses **durable timers** between steps (`pace_seconds`) so you can watch progress without sleeping a worker.
- You can inject a one-time transient failure into the next Activity call via a **Signal** (`inject_failure`) or via env failpoints in Activities.

## Quickstart
1. Start Temporal + UI:
   - `docker compose up -d`
   - UI: http://localhost:8233
2. Install dependencies:
   - `uv sync`
3. Run the worker:
   - `uv run python -m apps.worker`
4. Start a workflow:
   - `uv run python -m apps.client start-order`
5. Approve it (signal):
   - `uv run python -m apps.client signal-fraud <workflow_id> --approved true`

Docs:
- `docs/LOCAL_DEV.md`
- `docs/DEMO_SCRIPT.md`
