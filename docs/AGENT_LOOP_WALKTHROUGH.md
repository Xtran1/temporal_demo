# Example 3: Agentic Loop

This example shows an abstract agent loop: ask for the next action, wait, call a tool, record the result, and repeat until the simulated agent is satisfied or a budget is exhausted.

Temporal concepts:
- Workflow: `AgentLoopWorkflow`
- Activities: decide next action, run tool
- Signal: inject a tool failure or request cancellation
- Query: current agent state
- Timers: waits between tool calls
- Retries: transient tool failures
- Budget: maximum tool calls

The workflow does not use randomness directly. Simulated model decisions, target step count, tool choice, wait duration, and flaky tool behavior live in Activities, so the Workflow remains replay-safe.

## Run It

Start Temporal and a worker:

```bash
docker compose up -d
uv run python -m apps.worker
```

Start an agent loop:

```bash
uv run python -m apps.client start-agent "Investigate a failed menu rollout" --min-steps 3 --max-steps 8 --max-tool-calls 10
```

Watch or inspect state:

```bash
uv run python -m apps.client watch --workflow-id <workflow_id>
uv run python -m apps.client describe <workflow_id>
```

Inject a transient failure into the next tool call:

```bash
uv run python -m apps.client inject-agent-failure <workflow_id> --tool-name '*' --mode transient
```

Request cooperative cancellation:

```bash
uv run python -m apps.client cancel-agent <workflow_id> --reason "demo cancellation"
```

## What To Look For

In Temporal UI:
- every agent decision is an Activity result recorded in history
- random-looking behavior is replay-safe because it happens in Activities
- waits between tool calls are durable timers
- transient tool failures retry visibly
- query state shows the current tool, completed step count, and last result

## Expansion Ideas

- Add human approval before risky tools.
- Add separate child workflows for long-running tools.
- Add per-tool retry policies and non-retryable tool errors.
- Add maximum cost, step, or wall-clock budgets.
- Add queries for current plan, last tool result, remaining budget, and waiting reason.
- Replace the simulated decision Activity with a real model call while keeping it outside workflow code.
