from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Optional
from uuid import uuid4

import typer
from rich import print
from temporalio.client import Client, WorkflowHandle

from temporal_demo.config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, TEMPORAL_TASK_QUEUE
from temporal_demo.workflows.order_fulfillment import FraudCheckResult, OrderInput, OrderStatus


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
) -> None:
    """Start the Order Fulfillment workflow."""

    async def _run() -> None:
        client = await _client()
        resolved_order_id = order_id or f"order-{uuid4()}"
        workflow_id = resolved_order_id

        input_ = OrderInput(order_id=resolved_order_id, items=item, amount_cents=amount_cents)
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
            result = await handle.result()
            print("result:")
            print(result)
        except Exception as e:
            print(f"result not available: {type(e).__name__}: {e}")

    import asyncio

    asyncio.run(_run())


if __name__ == "__main__":
    app()

