from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ByocAnswers:
    process_name: str
    summary: str
    current_mechanism: str
    pain_points: str
    external_systems: str
    has_waits: bool
    has_external_events: bool
    has_retries: bool
    has_manual_recovery: bool
    needs_visibility: bool
    has_parallel_work: bool
    needs_compensation: bool
    can_run_long: bool
    adoption_concerns: str


@dataclass(frozen=True)
class Finding:
    concept: str
    why_it_may_help: str
    sketch_hint: str
    score: int


@dataclass(frozen=True)
class ByocAnalysis:
    fit_label: str
    fit_reason: str
    findings: list[Finding]
    sketch: list[str]
    follow_up_questions: list[str]


def _has_text(value: str) -> bool:
    return bool(value.strip())


def _split_examples(value: str) -> list[str]:
    parts = []
    for raw in value.replace(";", ",").split(","):
        item = raw.strip()
        if item:
            parts.append(item)
    return parts


def analyze_answers(answers: ByocAnswers) -> ByocAnalysis:
    findings: list[Finding] = []

    if answers.can_run_long or answers.has_manual_recovery or _has_text(answers.current_mechanism):
        findings.append(
            Finding(
                concept="Workflow",
                why_it_may_help=(
                    "The process has state over time. A Temporal Workflow can make that state durable "
                    "instead of spreading it across jobs, queues, status flags, or manual notes."
                ),
                sketch_hint="Model the end-to-end process as one durable workflow execution.",
                score=2 if answers.can_run_long or answers.has_manual_recovery else 1,
            )
        )

    if _has_text(answers.external_systems):
        findings.append(
            Finding(
                concept="Activities",
                why_it_may_help=(
                    "The process calls systems outside the workflow. Temporal Activities are the boundary "
                    "for side effects such as service calls, emails, payments, file writes, or API requests."
                ),
                sketch_hint="Put each external call or side effect behind an activity.",
                score=2,
            )
        )

    if answers.has_retries or answers.has_manual_recovery:
        findings.append(
            Finding(
                concept="Activity retries",
                why_it_may_help=(
                    "The process already needs retry or recovery behavior. Temporal can retry Activities "
                    "with recorded attempts and visible failure history."
                ),
                sketch_hint="Give retryable activities explicit retry policies and separate non-retryable failures.",
                score=2,
            )
        )

    if answers.has_waits:
        findings.append(
            Finding(
                concept="Timers",
                why_it_may_help=(
                    "The process waits for time to pass. Temporal timers are durable, so no worker process "
                    "has to stay alive while waiting."
                ),
                sketch_hint="Use workflow timers for deadlines, reminders, delayed starts, or timeout branches.",
                score=2,
            )
        )

    if answers.has_external_events:
        findings.append(
            Finding(
                concept="Signals",
                why_it_may_help=(
                    "The process changes when an outside event arrives. Signals let a running workflow "
                    "receive approvals, cancellations, updates, or callbacks."
                ),
                sketch_hint="Use signals for external events that should alter an in-flight process.",
                score=2,
            )
        )

    if answers.needs_visibility:
        findings.append(
            Finding(
                concept="Queries",
                why_it_may_help=(
                    "People or systems need to know what is happening while the process runs. Queries can "
                    "expose workflow state without changing it."
                ),
                sketch_hint="Add queries for current step, waiting reason, last error, and business status.",
                score=1,
            )
        )

    if answers.has_parallel_work:
        findings.append(
            Finding(
                concept="Child Workflows or fan-out Activities",
                why_it_may_help=(
                    "The process has repeated or parallel sub-work. Temporal can track those branches "
                    "explicitly instead of hiding them inside a batch job."
                ),
                sketch_hint="Use child workflows for independently tracked branches; use activities for simple fan-out.",
                score=1,
            )
        )

    if answers.needs_compensation:
        findings.append(
            Finding(
                concept="Compensation",
                why_it_may_help=(
                    "Some completed steps may need to be undone or reconciled after later failures. "
                    "A workflow can make those compensation paths explicit."
                ),
                sketch_hint="Record completed side effects and call compensating activities when needed.",
                score=1,
            )
        )

    score = sum(finding.score for finding in findings)
    if score >= 7:
        fit_label = "strong candidate"
        fit_reason = "This process has several Temporal-shaped signals: durable state, side effects, waiting, retries, or recovery pain."
    elif score >= 4:
        fit_label = "possible candidate"
        fit_reason = "Temporal may help, but the group should identify the smallest painful slice before designing a full migration."
    else:
        fit_label = "weak or unclear candidate"
        fit_reason = "The answers do not show much long-running orchestration pain yet. A simpler job, queue, or CRUD flow may be enough."

    process = answers.process_name.strip() or "This process"
    external_items = _split_examples(answers.external_systems)
    activity_hint = ", ".join(external_items[:4]) if external_items else "side-effecting steps"

    sketch = [
        f"Workflow: `{_workflow_name(process)}` represents the process from trigger to done condition.",
        f"Activities: wrap {activity_hint}.",
    ]
    if answers.has_external_events:
        sketch.append("Signals: receive approvals, cancellations, callbacks, or changed input while the workflow is running.")
    if answers.has_waits:
        sketch.append("Timers: model deadlines, reminders, scheduled work, or timeout branches.")
    if answers.needs_visibility:
        sketch.append("Queries: expose current step, waiting reason, last error, and business status.")
    if answers.needs_compensation:
        sketch.append("Compensation: call undo or reconciliation activities when later steps fail.")
    if answers.has_parallel_work:
        sketch.append("Child workflows: consider them for branches that need their own status, retries, or ownership.")

    follow_up_questions = [
        "Which external actions must be idempotent if Temporal retries them?",
        "Which failures should retry automatically, and which should stop or branch the workflow?",
        "What state would operators need to query during an incident?",
    ]
    if answers.has_external_events:
        follow_up_questions.append("Who is allowed to send signals, and what should happen if a signal arrives late?")
    if answers.has_waits:
        follow_up_questions.append("What deadlines or timers are business rules rather than implementation details?")
    if answers.needs_compensation:
        follow_up_questions.append("Which completed side effects can be undone, and which require reconciliation instead?")
    if _has_text(answers.adoption_concerns):
        follow_up_questions.append(f"Resolve this adoption concern: {answers.adoption_concerns.strip()}")

    return ByocAnalysis(
        fit_label=fit_label,
        fit_reason=fit_reason,
        findings=sorted(findings, key=lambda finding: finding.score, reverse=True),
        sketch=sketch,
        follow_up_questions=follow_up_questions,
    )


def _workflow_name(process_name: str) -> str:
    words = []
    current = []
    for char in process_name:
        if char.isalnum():
            current.append(char)
        elif current:
            words.append("".join(current))
            current = []
    if current:
        words.append("".join(current))
    if not words:
        return "CandidateWorkflow"
    return "".join(word[:1].upper() + word[1:] for word in words) + "Workflow"
