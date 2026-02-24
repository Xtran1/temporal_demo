# Temporal Durable Execution Demo (Python) — TODO

Audience: engineers who want a concrete “why Temporal” proof: crash/restart resilience, retries, timers, signals, and strong visibility via event history.

## 0) Milestones (definition of done)
- Can run Temporal + UI locally via `docker compose up`.
- Can start a Workflow from a CLI, then:
  - kill the worker mid-run and restart it → Workflow continues correctly
  - inject transient failures → Activities retry and succeed without manual state handling
  - wait on a Signal (external input) → Workflow resumes on signal
  - demonstrate timer-based waiting without sleeping a process
- Docs contain a repeatable demo script with “expected observations” in Temporal UI.

## 1) Infra: Temporal Server + UI
- Add `docker-compose.yml` for Temporal + UI (local dev defaults).
- Add `docs/LOCAL_DEV.md` with:
  - required ports
  - how to reset state (docker volumes) when needed
  - how to open the UI and what to look at

## 2) Python project structure (uv + venv)
- Create package layout:
  - `src/temporal_demo/workflows/`
  - `src/temporal_demo/activities/`
  - `apps/worker/` (module entrypoint)
  - `apps/client/` (CLI entrypoint)
- Update `pyproject.toml`:
  - add `temporalio`
  - add a small CLI lib (prefer `typer`) and logging
  - add test deps (`pytest`)
- Ensure all run paths work via `uv run ...` and `.venv`.

## 3) Core demo workflow: “Order Fulfillment Saga”
- Workflow: `OrderFulfillmentWorkflow`
  - input: order id + items + amount
  - steps (Activities): reserve inventory → charge card → create shipment → send email
  - include compensation logic (Saga-style) for business failures
  - wait for a `FraudCheckResult` signal (or `CustomerApproval`) before charging
  - use a timer to enforce an approval timeout
- Activities:
  - implement idempotency-friendly behavior (log-only or file-based stubs initially)
  - add retryable vs non-retryable failure types
  - optional: long-running Activity with heartbeats

## 4) “Why Temporal” proofs (make these visible)
- Failure injection:
  - env var (e.g. `DEMO_FAIL_CHARGE=transient|business|off`)
  - deterministic trigger points so the demo is repeatable
- Worker crash demo:
  - document where to kill the worker and what you should see in UI
  - show that no custom checkpointing code exists in the workflow
- Replay/determinism demo:
  - add a short doc explaining what’s allowed in workflow code vs activity code
  - include a “don’t do this” snippet (kept out of the main workflow path)

## 5) CLI commands (developer experience)
- `apps.client` commands:
  - `start-order` (starts workflow)
  - `signal-approval` (sends approval/fraud result)
  - `cancel-order`
  - `describe` (fetches and prints workflow status; optional query)
- Provide copy/paste commands in `docs/DEMO_SCRIPT.md`.

## 6) Tests (time-skipping + determinism)
- Add unit/integration tests using Temporal’s Python testing utilities:
  - time-skipping for timers
  - assertion that retries occur as configured
  - workflow completes correctly across injected failures

## 7) Documentation polish
- `README.md` becomes the front door:
  - what this demo proves
  - 3-minute quickstart
  - links to deeper demo script(s)
- `docs/DEMO_SCRIPT.md`:
  - exact commands
  - “expected UI observations” section (history event types to notice)

