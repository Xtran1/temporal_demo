from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    import asyncio

    from temporal_demo.activities.order_activities import (
        Charge,
        Reservation,
        Shipment,
        charge_card,
        create_shipment,
        release_inventory,
        reserve_inventory,
        send_email,
    )


@dataclass(frozen=True)
class OrderInput:
    order_id: str
    items: list[str]
    amount_cents: int


@dataclass(frozen=True)
class FraudCheckResult:
    approved: bool
    reason: str = ""


class OrderStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    status: OrderStatus
    reservation_id: Optional[str] = None
    charge_id: Optional[str] = None
    shipment_id: Optional[str] = None
    rejection_reason: str = ""


@workflow.defn(name="OrderFulfillmentWorkflow")
class OrderFulfillmentWorkflow:
    def __init__(self) -> None:
        self._fraud_result: Optional[FraudCheckResult] = None

    @workflow.signal(name="fraud_check_result")
    async def fraud_check_result(self, result: FraudCheckResult) -> None:
        self._fraud_result = result

    @workflow.run
    async def run(self, input_: OrderInput) -> OrderResult:
        workflow.logger.info("Workflow started", extra={"order_id": input_.order_id})

        reservation = await workflow.execute_activity(
            reserve_inventory,
            input_.order_id,
            input_.items,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )

        try:
            await workflow.wait_condition(
                lambda: self._fraud_result is not None,
                timeout=timedelta(minutes=5),
            )
        except (TimeoutError, asyncio.TimeoutError):
            await workflow.execute_activity(
                release_inventory,
                reservation,
                start_to_close_timeout=timedelta(seconds=10),
            )
            return OrderResult(
                order_id=input_.order_id,
                status=OrderStatus.REJECTED,
                reservation_id=reservation.reservation_id,
                rejection_reason="Fraud check timed out",
            )

        assert self._fraud_result is not None
        if not self._fraud_result.approved:
            await workflow.execute_activity(
                release_inventory,
                reservation,
                start_to_close_timeout=timedelta(seconds=10),
            )
            return OrderResult(
                order_id=input_.order_id,
                status=OrderStatus.REJECTED,
                reservation_id=reservation.reservation_id,
                rejection_reason=self._fraud_result.reason,
            )

        charge = await workflow.execute_activity(
            charge_card,
            input_.order_id,
            input_.amount_cents,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=10),
        )

        shipment = await workflow.execute_activity(
            create_shipment,
            input_.order_id,
            input_.items,
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )

        await workflow.execute_activity(
            send_email,
            input_.order_id,
            "order_completed",
            start_to_close_timeout=timedelta(seconds=10),
        )

        return OrderResult(
            order_id=input_.order_id,
            status=OrderStatus.COMPLETED,
            reservation_id=reservation.reservation_id,
            charge_id=charge.charge_id if isinstance(charge, Charge) else None,
            shipment_id=shipment.shipment_id if isinstance(shipment, Shipment) else None,
        )
