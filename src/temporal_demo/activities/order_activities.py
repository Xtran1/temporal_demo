from __future__ import annotations

from dataclasses import dataclass

from temporalio import activity


@dataclass(frozen=True)
class Reservation:
    reservation_id: str


@dataclass(frozen=True)
class Charge:
    charge_id: str


@dataclass(frozen=True)
class Shipment:
    shipment_id: str


@activity.defn
async def reserve_inventory(order_id: str, items: list[str]) -> Reservation:
    activity.logger.info("Reserving inventory", extra={"order_id": order_id, "items": items})
    return Reservation(reservation_id=f"resv-{order_id}")


@activity.defn
async def release_inventory(reservation: Reservation) -> None:
    activity.logger.info("Releasing inventory", extra={"reservation_id": reservation.reservation_id})


@activity.defn
async def charge_card(order_id: str, amount_cents: int) -> Charge:
    activity.logger.info("Charging card", extra={"order_id": order_id, "amount_cents": amount_cents})
    return Charge(charge_id=f"ch_{order_id}")


@activity.defn
async def create_shipment(order_id: str, items: list[str]) -> Shipment:
    activity.logger.info("Creating shipment", extra={"order_id": order_id, "items": items})
    return Shipment(shipment_id=f"ship_{order_id}")


@activity.defn
async def send_email(order_id: str, template: str) -> None:
    activity.logger.info("Sending email", extra={"order_id": order_id, "template": template})

