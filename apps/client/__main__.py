from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import Optional
from uuid import uuid4

import typer
from rich import print
from temporalio.client import Client, WorkflowHandle

from temporal_demo.config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, TEMPORAL_TASK_QUEUE
from temporal_demo.workflows.agent_loop import AgentInjectFailure, AgentLoopInput, AgentLoopState
from temporal_demo.workflows.menu_rollout import (
    MenuApproval,
    MenuInjectFailure,
    MenuRolloutInput,
    MenuRolloutState,
)
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


def _print_state(state: object) -> None:
    if isinstance(state, WorkflowState):
        print(f"step={state.step} message={state.message}")
        return
    if isinstance(state, MenuRolloutState):
        channels = ", ".join(state.published_channels or [])
        print(f"status={state.status} step={state.step} published=[{channels}] message={state.message}")
        return
    if isinstance(state, AgentLoopState):
        print(
            f"status={state.status} steps={state.completed_steps}/{state.target_steps} "
            f"tool={state.current_tool} message={state.message} last={state.last_result}"
        )
        return
    print(state)


@app.command()
def start_order(
    order_id: Optional[str] = typer.Option(None, help="Order ID (defaults to a UUID)"),
    amount_cents: int = typer.Option(1299, help="Amount in cents"),
    item: list[str] = typer.Option(["widget"], help="Repeatable item name"),
    pace_seconds: float = typer.Option(1.5, help="Delay between steps (durable timer)"),
    approval_timeout_seconds: int = typer.Option(300, help="Seconds to wait for approval before rejecting"),
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
            approval_timeout_seconds=approval_timeout_seconds,
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
def start_menu(
    menu_id: Optional[str] = typer.Option(None, help="Menu ID (defaults to a UUID)"),
    version: str = typer.Option("v1", help="Menu version"),
    channel: list[str] = typer.Option(["stores", "web", "delivery"], help="Repeatable publish channel"),
    publish_delay_seconds: float = typer.Option(0.0, help="Durable delay before publishing after approval"),
    approval_timeout_seconds: int = typer.Option(300, help="Seconds to wait for approval before rejecting"),
    pace_seconds: float = typer.Option(1.0, help="Delay between workflow steps"),
) -> None:
    """Start the Menu Rollout workflow."""

    async def _run() -> None:
        client = await _client()
        resolved_menu_id = menu_id or f"menu-{uuid4()}"
        workflow_id = f"{resolved_menu_id}-{version}"
        input_ = MenuRolloutInput(
            menu_id=resolved_menu_id,
            version=version,
            channels=channel,
            publish_delay_seconds=publish_delay_seconds,
            approval_timeout_seconds=approval_timeout_seconds,
            pace_seconds=pace_seconds,
        )
        handle = await client.start_workflow(
            "MenuRolloutWorkflow",
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
def signal_menu_approval(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    approved: bool = typer.Option(..., help="Approve or reject"),
    reason: str = typer.Option("", help="Reason (optional)"),
) -> None:
    """Send menu approval result to the workflow."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        await handle.signal("menu_approval", MenuApproval(approved=approved, reason=reason))
        print(f"Signaled menu_approval to workflow_id={workflow_id}")

    import asyncio

    asyncio.run(_run())


@app.command()
def inject_menu_failure(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    activity: str = typer.Option("publish_menu_channel", help="Activity to fail"),
    mode: str = typer.Option("transient", help="Failure mode (transient|business)"),
    channel: str = typer.Option("", help="Optional channel filter"),
) -> None:
    """Inject a failure into the next matching menu Activity call."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        await handle.signal("inject_menu_failure", MenuInjectFailure(activity=activity, mode=mode, channel=channel))
        print(f"Injected {mode} failure for {activity} into workflow_id={workflow_id}")

    import asyncio

    asyncio.run(_run())


@app.command()
def start_agent(
    goal: str = typer.Argument("Investigate whether Temporal fits this process", help="Agent goal"),
    workflow_id: Optional[str] = typer.Option(None, help="Workflow ID (defaults to a UUID)"),
    min_steps: int = typer.Option(3, help="Minimum simulated tool calls before satisfaction"),
    max_steps: int = typer.Option(10, help="Maximum simulated tool calls before satisfaction"),
    max_tool_calls: int = typer.Option(12, help="Budget cap for tool calls"),
    pace_seconds: float = typer.Option(0.0, help="Extra durable delay between tool calls"),
) -> None:
    """Start the Agent Loop workflow."""

    async def _run() -> None:
        client = await _client()
        resolved_workflow_id = workflow_id or f"agent-{uuid4()}"
        input_ = AgentLoopInput(
            goal=goal,
            min_steps=min_steps,
            max_steps=max_steps,
            max_tool_calls=max_tool_calls,
            pace_seconds=pace_seconds,
        )
        handle = await client.start_workflow(
            "AgentLoopWorkflow",
            input_,
            id=resolved_workflow_id,
            task_queue=TEMPORAL_TASK_QUEUE,
            execution_timeout=timedelta(days=7),
        )
        print(f"Started workflow_id={handle.id}")
        print(asdict(input_))

    import asyncio

    asyncio.run(_run())


@app.command()
def inject_agent_failure(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    tool_name: str = typer.Option("*", help="Tool to fail, or * for the next tool"),
    mode: str = typer.Option("transient", help="Failure mode (transient)"),
) -> None:
    """Inject a transient failure into the next matching agent tool Activity."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        await handle.signal("inject_agent_failure", AgentInjectFailure(tool_name=tool_name, mode=mode))
        print(f"Injected {mode} failure for tool={tool_name} into workflow_id={workflow_id}")

    import asyncio

    asyncio.run(_run())


@app.command()
def cancel_agent(
    workflow_id: str = typer.Argument(..., help="Workflow ID"),
    reason: str = typer.Option("canceled by demo signal", help="Cancellation reason"),
) -> None:
    """Request cooperative cancellation of an Agent Loop workflow."""

    async def _run() -> None:
        client = await _client()
        handle = _handle(client, workflow_id)
        await handle.signal("cancel_agent", reason)
        print(f"Signaled cancel_agent to workflow_id={workflow_id}")

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
            if isinstance(state, (WorkflowState, MenuRolloutState, AgentLoopState)):
                _print_state(state)
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
    approval_timeout_seconds: int = typer.Option(300, help="Seconds to wait for approval if starting"),
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
            OrderInput(
                order_id=resolved_order_id,
                items=["widget"],
                amount_cents=1299,
                pace_seconds=pace_seconds,
                approval_timeout_seconds=approval_timeout_seconds,
            ),
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
                _print_state(state)
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
