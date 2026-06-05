from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal_demo.activities.menu_activities import (
        ChannelPublish,
        publish_menu_channel,
        rollback_menu_channel,
        notify_menu_rollout,
        validate_menu,
    )


@dataclass(frozen=True)
class MenuRolloutInput:
    menu_id: str
    version: str
    channels: list[str]
    publish_delay_seconds: float = 0.0
    approval_timeout_seconds: int = 300
    pace_seconds: float = 1.0


@dataclass(frozen=True)
class MenuApproval:
    approved: bool
    reason: str = ""


@dataclass(frozen=True)
class MenuInjectFailure:
    activity: str
    mode: str
    channel: str = ""


class MenuRolloutStatus(str, Enum):
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PUBLISHED = "PUBLISHED"
    ROLLED_BACK = "ROLLED_BACK"


class MenuRolloutStep(str, Enum):
    START = "START"
    VALIDATE = "VALIDATE"
    WAIT_APPROVAL = "WAIT_APPROVAL"
    WAIT_PUBLISH_TIME = "WAIT_PUBLISH_TIME"
    PUBLISH = "PUBLISH"
    NOTIFY = "NOTIFY"
    DONE = "DONE"


@dataclass(frozen=True)
class MenuRolloutState:
    menu_id: str
    version: str
    status: MenuRolloutStatus
    step: MenuRolloutStep
    message: str = ""
    published_channels: list[str] | None = None


@dataclass(frozen=True)
class MenuRolloutResult:
    menu_id: str
    version: str
    status: MenuRolloutStatus
    published_channels: list[str]
    reason: str = ""


@workflow.defn(name="MenuRolloutWorkflow")
class MenuRolloutWorkflow:
    def __init__(self) -> None:
        self._approval: Optional[MenuApproval] = None
        self._inject_failure: Optional[MenuInjectFailure] = None
        self._status = MenuRolloutStatus.RUNNING
        self._step = MenuRolloutStep.START
        self._message = ""
        self._menu_id = ""
        self._version = ""
        self._published_channels: list[str] = []

    @workflow.signal(name="menu_approval")
    async def menu_approval(self, approval: MenuApproval) -> None:
        self._approval = approval

    @workflow.signal(name="inject_menu_failure")
    async def inject_menu_failure(self, inject: MenuInjectFailure) -> None:
        self._inject_failure = inject
        self._message = f"Will inject {inject.mode} failure into {inject.activity}"

    @workflow.query(name="state")
    def state(self) -> MenuRolloutState:
        return MenuRolloutState(
            menu_id=self._menu_id,
            version=self._version,
            status=self._status,
            step=self._step,
            message=self._message,
            published_channels=list(self._published_channels),
        )

    def _take_injection(self, activity_name: str, channel: str = "") -> str:
        if self._inject_failure is None:
            return "off"
        if self._inject_failure.activity.strip().lower() != activity_name.strip().lower():
            return "off"
        if self._inject_failure.channel and self._inject_failure.channel != channel:
            return "off"
        mode = self._inject_failure.mode
        self._inject_failure = None
        self._message = f"Injecting {mode} failure into {activity_name}"
        return mode

    @workflow.run
    async def run(self, input_: MenuRolloutInput) -> MenuRolloutResult:
        self._menu_id = input_.menu_id
        self._version = input_.version

        await workflow.sleep(timedelta(seconds=input_.pace_seconds))
        self._step = MenuRolloutStep.VALIDATE
        validation = await workflow.execute_activity(
            validate_menu,
            args=[input_.menu_id, input_.version, self._take_injection("validate_menu")],
            start_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        if validation.warnings:
            self._message = "; ".join(validation.warnings)

        await workflow.sleep(timedelta(seconds=input_.pace_seconds))
        self._step = MenuRolloutStep.WAIT_APPROVAL
        self._status = MenuRolloutStatus.WAITING_APPROVAL
        try:
            await workflow.wait_condition(
                lambda: self._approval is not None,
                timeout=timedelta(seconds=input_.approval_timeout_seconds),
            )
        except TimeoutError:
            self._status = MenuRolloutStatus.REJECTED
            self._step = MenuRolloutStep.DONE
            await workflow.execute_activity(
                notify_menu_rollout,
                args=[input_.menu_id, input_.version, "approval_timeout"],
                start_to_close_timeout=timedelta(seconds=10),
            )
            return MenuRolloutResult(
                menu_id=input_.menu_id,
                version=input_.version,
                status=MenuRolloutStatus.REJECTED,
                published_channels=[],
                reason="Approval timed out",
            )

        assert self._approval is not None
        if not self._approval.approved:
            self._status = MenuRolloutStatus.REJECTED
            self._step = MenuRolloutStep.DONE
            await workflow.execute_activity(
                notify_menu_rollout,
                args=[input_.menu_id, input_.version, "rejected"],
                start_to_close_timeout=timedelta(seconds=10),
            )
            return MenuRolloutResult(
                menu_id=input_.menu_id,
                version=input_.version,
                status=MenuRolloutStatus.REJECTED,
                published_channels=[],
                reason=self._approval.reason,
            )

        self._status = MenuRolloutStatus.APPROVED
        if input_.publish_delay_seconds > 0:
            self._step = MenuRolloutStep.WAIT_PUBLISH_TIME
            self._message = f"Waiting {input_.publish_delay_seconds:g}s before publishing"
            await workflow.sleep(timedelta(seconds=input_.publish_delay_seconds))

        self._step = MenuRolloutStep.PUBLISH
        try:
            for channel in input_.channels:
                publish = await workflow.execute_activity(
                    publish_menu_channel,
                    args=[
                        input_.menu_id,
                        input_.version,
                        channel,
                        self._take_injection("publish_menu_channel", channel),
                    ],
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(maximum_attempts=5),
                )
                if isinstance(publish, ChannelPublish):
                    self._published_channels.append(publish.channel)
        except Exception:
            self._status = MenuRolloutStatus.ROLLED_BACK
            self._message = "Publish failed; rolling back channels already published by this workflow"
            await self._rollback_published_channels(input_)
            self._step = MenuRolloutStep.DONE
            await workflow.execute_activity(
                notify_menu_rollout,
                args=[input_.menu_id, input_.version, "rolled_back"],
                start_to_close_timeout=timedelta(seconds=10),
            )
            return MenuRolloutResult(
                menu_id=input_.menu_id,
                version=input_.version,
                status=MenuRolloutStatus.ROLLED_BACK,
                published_channels=list(self._published_channels),
                reason="Publish failed; rollback attempted",
            )

        self._step = MenuRolloutStep.NOTIFY
        await workflow.execute_activity(
            notify_menu_rollout,
            args=[input_.menu_id, input_.version, "published"],
            start_to_close_timeout=timedelta(seconds=10),
        )
        self._status = MenuRolloutStatus.PUBLISHED
        self._step = MenuRolloutStep.DONE
        return MenuRolloutResult(
            menu_id=input_.menu_id,
            version=input_.version,
            status=MenuRolloutStatus.PUBLISHED,
            published_channels=list(self._published_channels),
        )

    async def _rollback_published_channels(self, input_: MenuRolloutInput) -> None:
        for channel in reversed(self._published_channels):
            await workflow.execute_activity(
                rollback_menu_channel,
                args=[input_.menu_id, input_.version, channel],
                start_to_close_timeout=timedelta(seconds=10),
            )
