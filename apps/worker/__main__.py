from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from temporal_demo.activities.order_activities import (
    charge_card,
    create_shipment,
    release_inventory,
    reserve_inventory,
    send_email,
)
from temporal_demo.config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, TEMPORAL_TASK_QUEUE
from temporal_demo.workflows.order_fulfillment import OrderFulfillmentWorkflow


async def main() -> None:
    client = await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)

    worker = Worker(
        client,
        task_queue=TEMPORAL_TASK_QUEUE,
        workflows=[OrderFulfillmentWorkflow],
        activities=[reserve_inventory, release_inventory, charge_card, create_shipment, send_email],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

