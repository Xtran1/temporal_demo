# Example 2: Menu Rollout

This example shows a versioned rollout process: validate a menu, wait for approval, optionally wait for a scheduled publish time, publish to multiple channels, and notify.

Temporal concepts:
- Workflow: `MenuRolloutWorkflow`
- Activities: validate menu, publish channel, notify rollout
- Signal: menu approval
- Query: current rollout state
- Timers: approval timeout and scheduled publishing
- Retries: transient channel publish failures

## Run It

Start Temporal and a worker:

```bash
docker compose up -d
uv run python -m apps.worker
```

Start a rollout:

```bash
uv run python -m apps.client start-menu --version v42 --channel stores --channel web --channel delivery --publish-delay-seconds 10
```

Approve it:

```bash
uv run python -m apps.client signal-menu-approval <workflow_id> --approved true
```

Watch or inspect state:

```bash
uv run python -m apps.client watch --workflow-id <workflow_id>
uv run python -m apps.client describe <workflow_id>
```

Inject a transient publish failure:

```bash
uv run python -m apps.client inject-menu-failure <workflow_id> --activity publish_menu_channel --mode transient --channel web
```

Inject a non-retryable publish failure to see compensation:

```bash
uv run python -m apps.client inject-menu-failure <workflow_id> --activity publish_menu_channel --mode business --channel delivery
```

## What To Look For

In Temporal UI:
- the workflow blocks while waiting for approval
- the scheduled publish delay is a durable timer
- each channel publish is recorded as an Activity
- a transient failure retries without losing rollout state
- a non-retryable publish failure rolls back channels already published by this workflow
- worker restart leaves the rollout waiting or running in Temporal

## Expansion Ideas

- Add staged rollout by store, region, or brand.
- Move rollback into a dedicated child workflow for already-published channels.
- Add validation activities for pricing, availability, compliance, and images.
- Model store or channel updates as child workflows.
- Add pause, resume, supersede, or cancel signals.
- Add rollout progress search attributes.
