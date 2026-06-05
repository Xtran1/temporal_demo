# Example 1: Order Fulfillment

This example shows a durable business process: reserve inventory, wait for approval, charge, ship, and notify.

Temporal concepts:
- Workflow: `OrderFulfillmentWorkflow`
- Activities: reserve inventory, charge card, create shipment, send email
- Signal: fraud approval
- Query: current workflow state
- Timers: pacing delays and approval timeout
- Retries: transient Activity failures
- Heartbeats: slow shipment resume after worker restart

## Run It

Start Temporal and a worker:

```bash
docker compose up -d
uv run python -m apps.worker
```

Start and watch an order:

```bash
uv run python -m apps.client watch --start
```

In another terminal, start a separate order and approve it:

```bash
uv run python -m apps.client start-order
uv run python -m apps.client signal-fraud <workflow_id> --approved true
```

Inject a transient failure before approval or charging:

```bash
uv run python -m apps.client inject-failure <workflow_id> --activity charge_card --mode transient
```

## What To Look For

In Temporal UI:
- the workflow waits at the approval signal
- Activity retries appear in event history
- durable timers appear without keeping worker code asleep
- killing and restarting the worker does not lose workflow state

## Expansion Ideas

- Add richer compensation for partial failures.
- Split fulfillment into child workflows for payment, warehouse, and shipping.
- Add idempotency keys around side-effecting activities.
- Add search attributes for order status and customer/account dimensions.
- Add a delayed cancellation or customer change window.
