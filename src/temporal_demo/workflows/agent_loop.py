from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import Optional

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from temporal_demo.activities.agent_activities import AgentDecision, decide_next_action, run_agent_tool


@dataclass(frozen=True)
class AgentLoopInput:
    goal: str
    min_steps: int = 3
    max_steps: int = 10
    max_tool_calls: int = 12
    transient_failure_rate: float = 0.25
    pace_seconds: float = 0.0


@dataclass(frozen=True)
class AgentInjectFailure:
    tool_name: str
    mode: str


class AgentStatus(str, Enum):
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    TOOL_CALL = "TOOL_CALL"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"


@dataclass(frozen=True)
class AgentLoopState:
    goal: str
    status: AgentStatus
    completed_steps: int
    target_steps: int
    current_tool: str = ""
    message: str = ""
    last_result: str = ""


@dataclass(frozen=True)
class AgentLoopResult:
    goal: str
    status: AgentStatus
    completed_steps: int
    final_answer: str = ""
    tool_results: list[str] | None = None


@workflow.defn(name="AgentLoopWorkflow")
class AgentLoopWorkflow:
    def __init__(self) -> None:
        self._goal = ""
        self._status = AgentStatus.RUNNING
        self._completed_steps = 0
        self._target_steps = 0
        self._current_tool = ""
        self._message = ""
        self._tool_results: list[str] = []
        self._inject_failure: Optional[AgentInjectFailure] = None
        self._cancel_requested = False

    @workflow.signal(name="inject_agent_failure")
    async def inject_agent_failure(self, inject: AgentInjectFailure) -> None:
        self._inject_failure = inject
        self._message = f"Will inject {inject.mode} failure into {inject.tool_name}"

    @workflow.signal(name="cancel_agent")
    async def cancel_agent(self, reason: str = "canceled by signal") -> None:
        self._cancel_requested = True
        self._message = reason

    @workflow.query(name="state")
    def state(self) -> AgentLoopState:
        return AgentLoopState(
            goal=self._goal,
            status=self._status,
            completed_steps=self._completed_steps,
            target_steps=self._target_steps,
            current_tool=self._current_tool,
            message=self._message,
            last_result=self._tool_results[-1] if self._tool_results else "",
        )

    def _take_tool_failure(self, tool_name: str) -> str:
        if self._inject_failure is None:
            return "off"
        if self._inject_failure.tool_name not in {"*", tool_name}:
            return "off"
        mode = self._inject_failure.mode
        self._inject_failure = None
        self._message = f"Injecting {mode} failure into {tool_name}"
        return mode

    @workflow.run
    async def run(self, input_: AgentLoopInput) -> AgentLoopResult:
        self._goal = input_.goal

        while self._completed_steps < input_.max_tool_calls:
            if self._cancel_requested:
                self._status = AgentStatus.CANCELED
                return AgentLoopResult(
                    goal=input_.goal,
                    status=AgentStatus.CANCELED,
                    completed_steps=self._completed_steps,
                    final_answer=self._message,
                    tool_results=list(self._tool_results),
                )

            decision = await workflow.execute_activity(
                decide_next_action,
                args=[
                    input_.goal,
                    self._completed_steps,
                    list(self._tool_results),
                    self._target_steps,
                    input_.min_steps,
                    input_.max_steps,
                ],
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )
            if isinstance(decision, AgentDecision):
                self._target_steps = decision.target_steps
                if decision.done:
                    self._status = AgentStatus.COMPLETED
                    return AgentLoopResult(
                        goal=input_.goal,
                        status=AgentStatus.COMPLETED,
                        completed_steps=self._completed_steps,
                        final_answer=decision.final_answer,
                        tool_results=list(self._tool_results),
                    )
                self._current_tool = decision.tool_name
                if decision.wait_seconds > 0:
                    self._status = AgentStatus.WAITING
                    self._message = f"Waiting {decision.wait_seconds:g}s before {decision.tool_name}"
                    await workflow.sleep(timedelta(seconds=decision.wait_seconds + input_.pace_seconds))

                self._status = AgentStatus.TOOL_CALL
                tool_result = await workflow.execute_activity(
                    run_agent_tool,
                    args=[
                        decision.tool_name,
                        decision.tool_input,
                        self._take_tool_failure(decision.tool_name),
                        input_.transient_failure_rate,
                    ],
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=RetryPolicy(maximum_attempts=5),
                )
                self._completed_steps += 1
                self._tool_results.append(f"{tool_result.tool_name}: {tool_result.output}")

        self._status = AgentStatus.BUDGET_EXHAUSTED
        return AgentLoopResult(
            goal=input_.goal,
            status=AgentStatus.BUDGET_EXHAUSTED,
            completed_steps=self._completed_steps,
            final_answer="Stopped because the tool-call budget was exhausted",
            tool_results=list(self._tool_results),
        )
