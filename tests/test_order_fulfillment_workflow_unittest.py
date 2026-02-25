from __future__ import annotations

import os
import unittest
from datetime import timedelta
from uuid import uuid4

from temporalio.client import Client
from temporalio.worker import Worker

from temporal_demo.activities.order_activities import (
    charge_card,
    create_shipment,
    release_inventory,
    reserve_inventory,
    send_email,
)
from temporal_demo.config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE
from temporal_demo.workflows.order_fulfillment import (
    FraudCheckResult,
    InjectFailure,
    OrderFulfillmentWorkflow,
    OrderInput,
    OrderStatus,
)


TASK_QUEUE = "test-temporal-demo"


async def _run_with_worker(fn) -> None:
    client = await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)
    async with Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[OrderFulfillmentWorkflow],
        activities=[reserve_inventory, release_inventory, charge_card, create_shipment, send_email],
    ):
        await fn(client)


class OrderFulfillmentWorkflowTests(unittest.IsolatedAsyncioTestCase):
    def _status(self, result: object) -> str:
        if isinstance(result, dict) and "status" in result:
            return str(result["status"])
        raise AssertionError(f"Unexpected result type: {type(result).__name__}: {result!r}")

    async def test_happy_path_completes(self) -> None:
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
                id=f"test-order-1-{uuid4()}",
                task_queue=TASK_QUEUE,
                execution_timeout=timedelta(minutes=5),
            )
            await handle.signal("fraud_check_result", FraudCheckResult(approved=True))
            result = await handle.result()
            self.assertEqual(self._status(result), OrderStatus.COMPLETED)
            self.assertTrue(result.get("reservation_id"))
            self.assertTrue(result.get("charge_id"))
            self.assertTrue(result.get("shipment_id"))

        await _run_with_worker(_test)

    async def test_charge_transient_failure_retries_and_completes(self) -> None:
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
                id=f"test-order-2-{uuid4()}",
                task_queue=TASK_QUEUE,
                execution_timeout=timedelta(minutes=5),
            )
            await handle.signal("inject_failure", InjectFailure(activity="charge_card", mode="transient"))
            await handle.signal("fraud_check_result", FraudCheckResult(approved=True))
            result = await handle.result()
            self.assertEqual(self._status(result), OrderStatus.COMPLETED)

        await _run_with_worker(_test)

    async def test_approval_timeout_rejects(self) -> None:
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
                id=f"test-order-3-{uuid4()}",
                task_queue=TASK_QUEUE,
                execution_timeout=timedelta(minutes=5),
            )
            result = await handle.result()
            self.assertEqual(self._status(result), OrderStatus.REJECTED)
            self.assertIn("timed out", str(result.get("rejection_reason", "")).lower())

        await _run_with_worker(_test)

    async def test_env_failpoint_transient_first_attempt_succeeds(self) -> None:
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
                    id=f"test-order-4-{uuid4()}",
                    task_queue=TASK_QUEUE,
                    execution_timeout=timedelta(minutes=5),
                )
                await handle.signal("fraud_check_result", FraudCheckResult(approved=True))
                result = await handle.result()
                self.assertEqual(self._status(result), OrderStatus.COMPLETED)
            finally:
                os.environ.pop("DEMO_FAIL_CHARGE", None)

        await _run_with_worker(_test)


if __name__ == "__main__":
    unittest.main()
