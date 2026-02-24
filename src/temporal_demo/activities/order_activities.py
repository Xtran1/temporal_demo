from __future__ import annotations

import os
from dataclasses import dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError


@dataclass(frozen=True)
class Reservation:
    reservation_id: str


@dataclass(frozen=True)
class Charge:
    charge_id: str


@dataclass(frozen=True)
class Shipment:
    shipment_id: str


def _env(name: str) -> str:
    return os.getenv(name, "").strip().lower()


def _should_fail_transient(env_name: str) -> bool:
    mode = _env(env_name)
    if mode in {"", "off", "0", "false"}:
        return False
    if mode in {"transient", "transient_first_attempt", "first_attempt"}:
        return activity.info().attempt == 1
    return False


def _should_fail_business(env_name: str) -> bool:
    mode = _env(env_name)
    return mode in {"business", "non_retryable"}


def _maybe_fail(fail_mode: str, *, env_name: str, operation: str) -> None:
    if fail_mode == "off":
        if _should_fail_transient(env_name):
            raise RuntimeError(f"{operation} transient failure (env={env_name})")
        if _should_fail_business(env_name):
            raise ApplicationError(f"{operation} business failure (env={env_name})", non_retryable=True)
        return

    mode = fail_mode.strip().lower()
    if mode in {"transient", "retryable"}:
        raise RuntimeError(f"{operation} transient failure (signal)")
    if mode in {"business", "non_retryable"}:
        raise ApplicationError(f"{operation} business failure (signal)", non_retryable=True)


@activity.defn
async def reserve_inventory(order_id: str, items: list[str], fail_mode: str = "off") -> Reservation:
    _maybe_fail(fail_mode, env_name="DEMO_FAIL_RESERVE", operation="reserve_inventory")
    activity.logger.info("Reserving inventory", extra={"order_id": order_id, "items": items})
    return Reservation(reservation_id=f"resv-{order_id}")


@activity.defn
async def release_inventory(reservation: Reservation) -> None:
    activity.logger.info("Releasing inventory", extra={"reservation_id": reservation.reservation_id})


@activity.defn
async def charge_card(order_id: str, amount_cents: int, fail_mode: str = "off") -> Charge:
    _maybe_fail(fail_mode, env_name="DEMO_FAIL_CHARGE", operation="charge_card")
    activity.logger.info("Charging card", extra={"order_id": order_id, "amount_cents": amount_cents})
    return Charge(charge_id=f"ch_{order_id}")


@activity.defn
async def create_shipment(order_id: str, items: list[str], fail_mode: str = "off") -> Shipment:
    _maybe_fail(fail_mode, env_name="DEMO_FAIL_SHIPMENT", operation="create_shipment")
    activity.logger.info("Creating shipment", extra={"order_id": order_id, "items": items})
    return Shipment(shipment_id=f"ship_{order_id}")


@activity.defn
async def send_email(order_id: str, template: str) -> None:
    activity.logger.info("Sending email", extra={"order_id": order_id, "template": template})
