from __future__ import annotations

from textwrap import fill

from temporal_demo.byoc_assistant import ByocAnalysis, ByocAnswers, analyze_answers


def main() -> None:
    print("BYOC Temporal fit helper")
    print("========================")
    print(
        "Answer in plain language. The goal is to describe a real process; "
        "the script will map your answers to Temporal concepts.\n"
    )

    answers = ByocAnswers(
        process_name=_ask("Process name"),
        summary=_ask("What starts this process, and what means it is done?"),
        current_mechanism=_ask(
            "How is this coordinated today? Examples: DB flags, queues, cron, batch job, manual runbook"
        ),
        pain_points=_ask(
            "What is painful today? Examples: duplicate work, lost state, manual recovery, poor visibility"
        ),
        external_systems=_ask(
            "Which external systems or side effects are involved? Separate examples with commas"
        ),
        has_waits=_ask_bool("Does the process wait for time to pass, deadlines, schedules, or reminders?"),
        has_external_events=_ask_bool(
            "Can outside events change the process while it is running? Examples: approval, cancellation, callback"
        ),
        has_retries=_ask_bool("Does it need retries for flaky services, jobs, APIs, or infrastructure?"),
        has_manual_recovery=_ask_bool("Do people manually inspect, rerun, repair, or clean up failed cases?"),
        needs_visibility=_ask_bool("Would people benefit from seeing the current step and waiting reason?"),
        has_parallel_work=_ask_bool("Does one case fan out into repeated or parallel work?"),
        needs_compensation=_ask_bool("Can later failure require undo, refund, release, rollback, or reconciliation?"),
        can_run_long=_ask_bool("Can one case run for minutes, hours, days, or longer?"),
        adoption_concerns=_ask("What would worry you about using Temporal here? Leave blank if unknown", required=False),
    )

    analysis = analyze_answers(answers)
    _print_analysis(analysis)


def _ask(prompt: str, *, required: bool = True) -> str:
    while True:
        value = input(f"{prompt}\n> ").strip()
        if value or not required:
            print()
            return value
        print("Please enter a short answer.\n")


def _ask_bool(prompt: str) -> bool:
    while True:
        value = input(f"{prompt} [y/n]\n> ").strip().lower()
        if value in {"y", "yes"}:
            print()
            return True
        if value in {"n", "no"}:
            print()
            return False
        print("Please answer y or n.\n")


def _print_analysis(analysis: ByocAnalysis) -> None:
    print("\nAnalysis")
    print("========")
    print(f"Fit signal: {analysis.fit_label}")
    print(fill(analysis.fit_reason, width=88))

    print("\nWhere Temporal might help")
    print("-------------------------")
    if not analysis.findings:
        print("- No strong Temporal-shaped pain surfaced from these answers.")
    for finding in analysis.findings:
        print(f"- {finding.concept}: {fill(finding.why_it_may_help, width=84, subsequent_indent='  ')}")

    print("\nRough Temporal sketch")
    print("---------------------")
    for item in analysis.sketch:
        print(f"- {item}")

    print("\nQuestions to take back to the group")
    print("-----------------------------------")
    for question in analysis.follow_up_questions:
        print(f"- {question}")


if __name__ == "__main__":
    main()
