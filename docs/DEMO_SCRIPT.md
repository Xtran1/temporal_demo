# Demo Script: Three Temporal Process Shapes

This script is the top-level runbook for the knowledge-share demo. It shows the same Temporal primitives through three different process shapes:

1. **Order fulfillment:** a durable business transaction with approval, retries, compensation ideas, and worker restart resilience.
2. **Menu rollout:** a versioned publishing process with approval, scheduled release, fan-out, and rollback.
3. **Agentic loop:** an uncertain iterative process with tool calls, automatic transient failures, retries, timers, and cancellation.

Use this script for the live overview. Use the specific walkthrough docs when participants choose an example to explore:

- `docs/ORDER_FULFILLMENT_WALKTHROUGH.md`
- `docs/MENU_ROLLOUT_WALKTHROUGH.md`
- `docs/AGENT_LOOP_WALKTHROUGH.md`

## Shared Setup

Use three terminals:

- **Terminal A:** Temporal Server + UI
- **Terminal B:** worker
- **Terminal C:** client commands / watcher

Start local Temporal:

```bash
docker compose up -d
```

Open Temporal UI:

```text
http://localhost:8233
```

Install or sync dependencies:

```bash
uv sync
```

Start the worker:

```bash
uv run python -m apps.worker
```

The same worker registers all three workflows.

## 1. Order Fulfillment

Represents: **a durable business transaction**.

This is the most direct "why Temporal" demo: a workflow keeps business state while Activities do side effects. The order waits for a fraud approval signal, retries transient failures, uses timers, and can survive worker restart without custom checkpointing.

Start an order:

```bash
uv run python -m apps.client start-order --pace-seconds 2
```

Copy the printed `workflow_id`, then watch it:

```bash
uv run python -m apps.client watch --workflow-id <workflow_id>
```

Approve the fraud check:

```bash
uv run python -m apps.client signal-fraud <workflow_id> --approved true
```

Optional failure demo:

```bash
uv run python -m apps.client inject-failure <workflow_id> --activity charge_card --mode transient
```

What to show in Temporal UI:

- the workflow waits for `fraud_check_result`
- Activity retry events are visible after failure injection
- durable timers appear in history
- killing and restarting the worker does not lose the workflow state

Crash/restart moment:

1. Start an order with a longer pace, or watch one waiting for approval.
2. Stop the worker in Terminal B with Ctrl-C.
3. Observe that the workflow still exists in Temporal UI.
4. Restart the worker:

```bash
uv run python -m apps.worker
```

## 2. Menu Rollout

Represents: **a versioned rollout / publishing process**.

This demo is less transaction-like and more coordination-like. A menu version is validated, waits for approval, optionally waits for a scheduled publish timer, then publishes to multiple channels.

Start a rollout:

```bash
uv run python -m apps.client start-menu --version v42 --channel stores --channel web --channel delivery --publish-delay-seconds 10
```

Copy the printed `workflow_id`, then watch it:

```bash
uv run python -m apps.client watch --workflow-id <workflow_id>
```

Approve the rollout:

```bash
uv run python -m apps.client signal-menu-approval <workflow_id> --approved true
```

Optional transient failure demo:

```bash
uv run python -m apps.client inject-menu-failure <workflow_id> --activity publish_menu_channel --mode transient --channel web
```

Optional compensation demo:

```bash
uv run python -m apps.client inject-menu-failure <workflow_id> --activity publish_menu_channel --mode business --channel delivery
```

What to show in Temporal UI:

- approval is modeled as a Signal
- scheduled publishing is a durable timer
- each channel publish is an Activity
- transient publish failure retries are visible
- non-retryable publish failure rolls back channels already published by this workflow

## 3. Agentic Loop

Represents: **an uncertain iterative process**.

This demo shows why Temporal can be useful for agent-like systems: the loop can run for a while, wait between steps, call tools, retry transient tool failures, expose query state, and stop when the agent is satisfied or a budget is exhausted.

Start an agent loop:

```bash
uv run python -m apps.client start-agent "Investigate a failed menu rollout" --min-steps 5 --max-steps 8 --max-tool-calls 10 --transient-failure-rate 0.35
```

Copy the printed `workflow_id`, then watch it:

```bash
uv run python -m apps.client watch --workflow-id <workflow_id>
```

Make automatic failures more obvious:

```bash
uv run python -m apps.client start-agent "Investigate flaky tools" --min-steps 5 --max-steps 8 --transient-failure-rate 0.75
```

Optional cancellation demo:

```bash
uv run python -m apps.client cancel-agent <workflow_id> --reason "demo cancellation"
```

What to show in Temporal UI:

- agent decisions and tool calls are Activities
- random-looking decisions are replay-safe because they happen in Activities
- waits between tool calls are durable timers
- simulated transient tool failures retry without manual signaling
- query state shows current tool, step count, and last result

## Closing Frame

The three examples are intentionally similar in structure but different in meaning:

- **Order fulfillment:** complete a business process despite failure.
- **Menu rollout:** coordinate a rollout over time.
- **Agentic loop:** control and observe an uncertain iterative process.

For hands-on exploration, send participants to the specific walkthrough for the demo they want to modify.
