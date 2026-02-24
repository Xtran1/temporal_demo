from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Optional
from uuid import uuid4

import typer
from rich import print
from temporalio.client import Client, WorkflowHandle

from temporal_demo.config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, TEMPORAL_TASK_QUEUE
from temporal_demo.workflows.order_fulfillment import (
    FraudCheckResult,
    InjectFailure,
    OrderInput,
    WorkflowState,
)


app = typer.Typer(no_args_is_help=True)


async def _client() -> Client:
    return await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)


def _handle(client: Client, workflow_id: str) -> WorkflowHandle:
    return client.get_workflow_handle(workflow_id)


@app.command()
def start_order(
    order_id: Optional[str] = typer.Option(None, help="Order ID (defaults to a UUID)"),
    amount_cents: int = typer.Option(1299, help="Amount in cents"),
    item: list[str] = typer.Option(["widget"], help="Repeatable item name"),
    pace_seconds: float = typer.Option(1.5, help="Delay between steps (durable timer)"),
) -> None:
    """Start the Order Fulfillment workflow."""

    async def _run() -> None:
        client = await _client()
        resolved_order_id = order_id or f"order-{uuid4()}"
        workflow_id = resolved_order_id

        input_ = OrderInput(
            order_id=resolved_order_id,
            items=item,
            amount_cents=amount_cents,
            pace_seconds=pace_seconds,
        )
        handle = await client.start_workflow(
            "OrderFulfillmentWorkflow",
            input_,
            id=workflow_id,
            task_queue=TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(days=7),
        )
        print(f"Started workflow_id={handle.id}")
        print(asdict(input_))

    import asyncio

    asyncio.run(_run())


@app.command()
def signal_fraud(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    approved: bool = typer.Option(..., help="Approve or reject"),
    reason: str = typer.Option("", help="Reason (optional)"),
) -> None:
    """Send fraud-check result to the workflow (signal)."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        await handle.signal("fraud_check_result", FraudCheckResult(approved=approved, reason=reason))
        print(f"Signaled fraud_check_result to workflow_id={workflow_id}")

    import asyncio

    asyncio.run(_run())


@app.command()
def inject_failure(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    activity: str = typer.Option(
        "charge_card",
        help="Activity to fail (reserve_inventory|charge_card|create_shipment)",
    ),
    mode: str = typer.Option("transient", help="Failure mode (transient|business)"),
) -> None:
    """Inject a failure into the *next* matching activity call (signal-driven)."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        await handle.signal("inject_failure", InjectFailure(activity=activity, mode=mode))
        print(f"Injected {mode} failure for {activity} into workflow_id={workflow_id}")

    import asyncio

    asyncio.run(_run())


@app.command()
def cancel(workflow_id: str = typer.Argument(..., help="Workflow ID")) -> None:
    """Cancel a workflow execution."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        await handle.cancel()
        print(f"Cancellation requested for workflow_id={workflow_id}")

    import asyncio

    asyncio.run(_run())


@app.command()
def describe(workflow_id: str = typer.Argument(..., help="Workflow ID")) -> None:
    """Describe current workflow status (and result if available)."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        desc = await handle.describe()
        print(f"workflow_id={workflow_id} status={desc.status.name}")
        try:
            state = await handle.query("state")
            if isinstance(state, WorkflowState):
                print(f"step={state.step} message={state.message}")
        except Exception:
            pass
        try:
            result = await handle.result()
            print("result:")
            print(result)
        except Exception as e:
            print(f"result not available: {type(e).__name__}: {e}")

    import asyncio

    asyncio.run(_run())


@app.command()
def watch(
    workflow_id: Optional[str] = typer.Option(None, help="Workflow ID to watch"),
    start: bool = typer.Option(False, help="Start a new workflow if no workflow_id is given"),
    pace_seconds: float = typer.Option(1.5, help="Delay between workflow steps if starting"),
    poll_seconds: float = typer.Option(0.75, help="Polling interval for state query"),
    inject_on_ctrl_c: bool = typer.Option(True, help="On Ctrl-C, inject a transient charge failure"),
) -> None:
    """Continuously print workflow state; Ctrl-C can inject a failure without stopping the watcher."""

    async def _start_if_needed(client: Client) -> str:
        if workflow_id:
            return workflow_id
        if not start:
            raise typer.BadParameter("--workflow-id is required unless --start is set")
        resolved_order_id = f"order-{uuid4()}"
        handle = await client.start_workflow(
            "OrderFulfillmentWorkflow",
            OrderInput(order_id=resolved_order_id, items=["widget"], amount_cents=1299, pace_seconds=pace_seconds),
            id=resolved_order_id,
            task_queue=TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(days=7),
        )
        return handle.id

    async def _run() -> None:
        client = await _client()
        wid = await _start_if_needed(client)
        handle = _handle(client, wid)

        print(f"Watching workflow_id={wid} (Ctrl-C to {'inject failure' if inject_on_ctrl_c else 'exit'})")
        while True:
            try:
                state = await handle.query("state")
                if isinstance(state, WorkflowState):
                    print(f"{state.status} {state.step} {state.message}".strip())
                else:
                    print(state)
                import asyncio

                await asyncio.sleep(poll_seconds)
            except KeyboardInterrupt:
                if not inject_on_ctrl_c:
                    raise
                await handle.signal("inject_failure", InjectFailure(activity="charge_card", mode="transient"))
                print("Injected: transient failure into charge_card (signal). Press Ctrl-C again to inject again.")

    import asyncio

    asyncio.run(_run())


if __name__ == "__main__":
    app()
