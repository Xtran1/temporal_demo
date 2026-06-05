from __future__ import annotations

from dataclasses import dataclass

from temporalio import activity
from temporalio.exceptions import ApplicationError


@dataclass(frozen=True)
class MenuValidation:
    validation_id: str
    warnings: list[str]


@dataclass(frozen=True)
class ChannelPublish:
    channel: str
    publish_id: str


def _maybe_fail(fail_mode: str, *, operation: str) -> None:
    mode = fail_mode.strip().lower()
    if mode in {"", "off", "0", "false"}:
        return
    if mode in {"transient", "retryable"}:
        if activity.info().attempt == 1:
            raise RuntimeError(f"{operation} transient failure")
        return
    if mode in {"business", "non_retryable"}:
        raise ApplicationError(f"{operation} business failure", non_retryable=True)


@activity.defn
async def validate_menu(menu_id: str, version: str, fail_mode: str = "off") -> MenuValidation:
    _maybe_fail(fail_mode, operation="validate_menu")
    activity.logger.info("Validating menu", extra={"menu_id": menu_id, "version": version})
    warnings = []
    if version.endswith("-draft"):
        warnings.append("Version still has draft suffix")
    return MenuValidation(validation_id=f"menu-val-{menu_id}-{version}", warnings=warnings)


@activity.defn
async def publish_menu_channel(
    menu_id: str,
    version: str,
    channel: str,
    fail_mode: str = "off",
) -> ChannelPublish:
    _maybe_fail(fail_mode, operation=f"publish_menu_channel[{channel}]")
    activity.logger.info(
        "Publishing menu channel",
        extra={"menu_id": menu_id, "version": version, "channel": channel},
    )
    return ChannelPublish(channel=channel, publish_id=f"pub-{menu_id}-{version}-{channel}")


@activity.defn
async def rollback_menu_channel(menu_id: str, version: str, channel: str) -> None:
    activity.logger.info(
        "Rolling back menu channel",
        extra={"menu_id": menu_id, "version": version, "channel": channel},
    )


@activity.defn
async def notify_menu_rollout(menu_id: str, version: str, status: str) -> None:
    activity.logger.info(
        "Notifying menu rollout",
        extra={"menu_id": menu_id, "version": version, "status": status},
    )
