from __future__ import annotations

import random
from dataclasses import dataclass

from temporalio import activity


@dataclass(frozen=True)
class AgentDecision:
    done: bool
    tool_name: str = ""
    tool_input: str = ""
    wait_seconds: float = 0.0
    target_steps: int = 0
    final_answer: str = ""


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    output: str


def should_fail_transient_tool(
    *,
    attempt: int,
    fail_mode: str = "off",
    transient_failure_rate: float = 0.25,
    random_value: float,
) -> bool:
    mode = fail_mode.strip().lower()
    if mode in {"transient", "retryable"}:
        return attempt == 1
    return mode in {"", "off", "0", "false"} and attempt == 1 and random_value < transient_failure_rate


@activity.defn
async def decide_next_action(
    goal: str,
    completed_steps: int,
    previous_results: list[str],
    target_steps: int,
    min_steps: int,
    max_steps: int,
) -> AgentDecision:
    if target_steps <= 0:
        target_steps = random.randint(min_steps, max_steps)

    if completed_steps >= target_steps:
        summary = "; ".join(previous_results[-3:]) if previous_results else "no tool output"
        return AgentDecision(
            done=True,
            target_steps=target_steps,
            final_answer=f"Satisfied after {completed_steps} tool calls for '{goal}'. Last evidence: {summary}",
        )

    tool_name = random.choice(["search_docs", "inspect_ticket", "summarize_findings"])
    wait_seconds = round(random.uniform(0.1, 0.6), 2)
    return AgentDecision(
        done=False,
        tool_name=tool_name,
        tool_input=f"{goal} / step {completed_steps + 1}",
        wait_seconds=wait_seconds,
        target_steps=target_steps,
    )


@activity.defn
async def run_agent_tool(
    tool_name: str,
    tool_input: str,
    fail_mode: str = "off",
    transient_failure_rate: float = 0.25,
) -> ToolResult:
    if should_fail_transient_tool(
        attempt=activity.info().attempt,
        fail_mode=fail_mode,
        transient_failure_rate=transient_failure_rate,
        random_value=random.random(),
    ):
        raise RuntimeError(f"{tool_name} simulated flaky tool failure")

    activity.logger.info(
        "Running agent tool",
        extra={
            "tool_name": tool_name,
            "tool_input": tool_input,
            "attempt": activity.info().attempt,
            "transient_failure_rate": transient_failure_rate,
        },
    )
    return ToolResult(tool_name=tool_name, output=f"{tool_name} result for {tool_input}")
