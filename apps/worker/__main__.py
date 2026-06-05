from __future__ import annotations

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from temporal_demo.activities.agent_activities import decide_next_action, run_agent_tool
from temporal_demo.activities.menu_activities import (
    notify_menu_rollout,
    publish_menu_channel,
    rollback_menu_channel,
    validate_menu,
)
from temporal_demo.activities.order_activities import (
    charge_card,
    create_shipment,
    release_inventory,
    reserve_inventory,
    send_email,
)
from temporal_demo.config import TEMPORAL_ADDRESS, TEMPORAL_NAMESPACE, TEMPORAL_TASK_QUEUE
from temporal_demo.workflows.agent_loop import AgentLoopWorkflow
from temporal_demo.workflows.menu_rollout import MenuRolloutWorkflow
from temporal_demo.workflows.order_fulfillment import OrderFulfillmentWorkflow


async def main() -> None:
    client = await Client.connect(TEMPORAL_ADDRESS, namespace=TEMPORAL_NAMESPACE)

    worker = Worker(
        client,
        task_queue=TEMPORAL_TASK_QUEUE,
        workflows=[OrderFulfillmentWorkflow, MenuRolloutWorkflow, AgentLoopWorkflow],
        activities=[
            reserve_inventory,
            release_inventory,
            charge_card,
            create_shipment,
            send_email,
            validate_menu,
            publish_menu_channel,
            rollback_menu_channel,
            notify_menu_rollout,
            decide_next_action,
            run_agent_tool,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
