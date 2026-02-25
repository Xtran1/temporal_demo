from __future__ import annotations

import os
from datetime import timedelta

from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from temporal_demo.activities.order_activities import (
    charge_card,
    create_shipment,
    release_inventory,
    reserve_inventory,
    send_email,
)
from temporal_demo.workflows.order_fulfillment import (
    FraudCheckResult,
    InjectFailure,
    OrderFulfillmentWorkflow,
    OrderInput,
    OrderStatus,
)


TASK_QUEUE = "test-temporal-demo"


async def _run_with_worker(fn) -> None:
    async with WorkflowEnvironment.start_time_skipping() as env:
        assert isinstance(env.client, Client)
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[OrderFulfillmentWorkflow],
            activities=[reserve_inventory, release_inventory, charge_card, create_shipment, send_email],
        ):
            await fn(env.client)


def test_happy_path_completes() -> None:
    async def _test(client: Client) -> None:
        handle = await client.start_workflow(
            "OrderFulfillmentWorkflow",
            OrderInput(
                order_id="order-1",
                items=["widget"],
                amount_cents=500,
                pace_seconds=0.0,
                approval_timeout_seconds=60,
            ),
            id="order-1",
            task_queue=TASK_QUEUE,
            execution_timeout=timedelta(minutes=5),
        )
        await handle.signal("fraud_check_result", FraudCheckResult(approved=True))
        result = await handle.result()
        assert result.status == OrderStatus.COMPLETED
        assert result.reservation_id
        assert result.charge_id
        assert result.shipment_id

    import asyncio

    asyncio.run(_run_with_worker(_test))


def test_charge_transient_failure_retries_and_completes() -> None:
    async def _test(client: Client) -> None:
        handle = await client.start_workflow(
            "OrderFulfillmentWorkflow",
            OrderInput(
                order_id="order-2",
                items=["widget"],
                amount_cents=500,
                pace_seconds=0.0,
                approval_timeout_seconds=60,
            ),
            id="order-2",
            task_queue=TASK_QUEUE,
            execution_timeout=timedelta(minutes=5),
        )
        await handle.signal("inject_failure", InjectFailure(activity="charge_card", mode="transient"))
        await handle.signal("fraud_check_result", FraudCheckResult(approved=True))
        result = await handle.result()
        assert result.status == OrderStatus.COMPLETED

    import asyncio

    asyncio.run(_run_with_worker(_test))


def test_approval_timeout_rejects() -> None:
    async def _test(client: Client) -> None:
        handle = await client.start_workflow(
            "OrderFulfillmentWorkflow",
            OrderInput(
                order_id="order-3",
                items=["widget"],
                amount_cents=500,
                pace_seconds=0.0,
                approval_timeout_seconds=1,
            ),
            id="order-3",
            task_queue=TASK_QUEUE,
            execution_timeout=timedelta(minutes=5),
        )
        result = await handle.result()
        assert result.status == OrderStatus.REJECTED
        assert "timed out" in result.rejection_reason.lower()

    import asyncio

    asyncio.run(_run_with_worker(_test))


def test_env_failpoint_transient_first_attempt_succeeds() -> None:
    async def _test(client: Client) -> None:
        os.environ["DEMO_FAIL_CHARGE"] = "transient_first_attempt"
        try:
            handle = await client.start_workflow(
                "OrderFulfillmentWorkflow",
                OrderInput(
                    order_id="order-4",
                    items=["widget"],
                    amount_cents=500,
                    pace_seconds=0.0,
                    approval_timeout_seconds=60,
                ),
                id="order-4",
                task_queue=TASK_QUEUE,
                execution_timeout=timedelta(minutes=5),
            )
            await handle.signal("fraud_check_result", FraudCheckResult(approved=True))
            result = await handle.result()
            assert result.status == OrderStatus.COMPLETED
        finally:
            os.environ.pop("DEMO_FAIL_CHARGE", None)

    import asyncio

    asyncio.run(_run_with_worker(_test))

