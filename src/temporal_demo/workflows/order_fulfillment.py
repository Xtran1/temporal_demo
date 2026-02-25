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
    pace_seconds: float = 1.5
    approval_timeout_seconds: int = 300


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
    RUNNING = "RUNNING"


class OrderStep(str, Enum):
    START = "START"
    RESERVE = "RESERVE"
    WAIT_APPROVAL = "WAIT_APPROVAL"
    CHARGE = "CHARGE"
    SHIP = "SHIP"
    EMAIL = "EMAIL"
    DONE = "DONE"


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    status: OrderStatus
    reservation_id: Optional[str] = None
    charge_id: Optional[str] = None
    shipment_id: Optional[str] = None
    rejection_reason: str = ""


@dataclass(frozen=True)
class WorkflowState:
    order_id: str
    status: OrderStatus
    step: OrderStep
    message: str = ""
    reservation_id: str = ""
    charge_id: str = ""
    shipment_id: str = ""


@dataclass(frozen=True)
class InjectFailure:
    activity: str
    mode: str


@workflow.defn(name="OrderFulfillmentWorkflow")
class OrderFulfillmentWorkflow:
    def __init__(self) -> None:
        self._fraud_result: Optional[FraudCheckResult] = None
        self._inject_failure: Optional[InjectFailure] = None
        self._status: OrderStatus = OrderStatus.RUNNING
        self._step: OrderStep = OrderStep.START
        self._message: str = ""
        self._reservation_id: str = ""
        self._charge_id: str = ""
        self._shipment_id: str = ""

    @workflow.signal(name="fraud_check_result")
    async def fraud_check_result(self, result: FraudCheckResult) -> None:
        self._fraud_result = result

    @workflow.signal(name="inject_failure")
    async def inject_failure(self, inject: InjectFailure) -> None:
        self._inject_failure = inject
        self._message = f"Will inject {inject.mode} failure into {inject.activity}"

    @workflow.query(name="state")
    def state(self) -> WorkflowState:
        return WorkflowState(
            order_id=workflow.info().workflow_id,
            status=self._status,
            step=self._step,
            message=self._message,
            reservation_id=self._reservation_id,
            charge_id=self._charge_id,
            shipment_id=self._shipment_id,
        )

    def _take_injection(self, activity_name: str) -> str:
        if self._inject_failure is None:
            return "off"
        if self._inject_failure.activity.strip().lower() != activity_name.strip().lower():
            return "off"
        mode = self._inject_failure.mode
        self._inject_failure = None
        self._message = f"Injecting {mode} failure into {activity_name}"
        return mode

    @workflow.run
    async def run(self, input_: OrderInput) -> OrderResult:
        workflow.logger.info("Workflow started", extra={"order_id": input_.order_id})

        await workflow.sleep(timedelta(seconds=input_.pace_seconds))
        self._step = OrderStep.RESERVE
        reservation = await workflow.execute_activity(
            reserve_inventory,
            args=[
                input_.order_id,
                input_.items,
                self._take_injection("reserve_inventory"),
            ],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )
        self._reservation_id = reservation.reservation_id
        await workflow.sleep(timedelta(seconds=input_.pace_seconds))

        self._step = OrderStep.WAIT_APPROVAL
        self._status = OrderStatus.PENDING_APPROVAL
        try:
            await workflow.wait_condition(
                lambda: self._fraud_result is not None,
                timeout=timedelta(seconds=input_.approval_timeout_seconds),
            )
        except (TimeoutError, asyncio.TimeoutError):
            await workflow.execute_activity(
                release_inventory,
                reservation,
                start_to_close_timeout=timedelta(seconds=10),
            )
            self._status = OrderStatus.REJECTED
            self._step = OrderStep.DONE
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
            self._status = OrderStatus.REJECTED
            self._step = OrderStep.DONE
            return OrderResult(
                order_id=input_.order_id,
                status=OrderStatus.REJECTED,
                reservation_id=reservation.reservation_id,
                rejection_reason=self._fraud_result.reason,
            )

        self._status = OrderStatus.APPROVED
        await workflow.sleep(timedelta(seconds=input_.pace_seconds))

        self._step = OrderStep.CHARGE
        charge = await workflow.execute_activity(
            charge_card,
            args=[
                input_.order_id,
                input_.amount_cents,
                self._take_injection("charge_card"),
            ],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(initial_interval=timedelta(seconds=1), maximum_attempts=10),
        )
        self._charge_id = charge.charge_id
        await workflow.sleep(timedelta(seconds=input_.pace_seconds))

        self._step = OrderStep.SHIP
        shipment = await workflow.execute_activity(
            create_shipment,
            args=[
                input_.order_id,
                input_.items,
                self._take_injection("create_shipment"),
            ],
            start_to_close_timeout=timedelta(minutes=5),
            heartbeat_timeout=timedelta(seconds=5),
            retry_policy=RetryPolicy(maximum_attempts=5),
        )
        self._shipment_id = shipment.shipment_id
        await workflow.sleep(timedelta(seconds=input_.pace_seconds))

        self._step = OrderStep.EMAIL
        await workflow.execute_activity(
            send_email,
            args=[input_.order_id, "order_completed"],
            start_to_close_timeout=timedelta(seconds=10),
        )

        self._status = OrderStatus.COMPLETED
        self._step = OrderStep.DONE
        return OrderResult(
            order_id=input_.order_id,
            status=OrderStatus.COMPLETED,
            reservation_id=reservation.reservation_id,
            charge_id=charge.charge_id if isinstance(charge, Charge) else None,
            shipment_id=shipment.shipment_id if isinstance(shipment, Shipment) else None,
        )
