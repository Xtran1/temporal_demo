# BYOC Terminal Assistant

Path 3 should not assume participants already know where Temporal fits. After a short presentation, most people will not be ready to design Workflows, Activities, Signals, Queries, and Timers from a blank page.

Instead, use the BYOC terminal assistant. It asks plain-language questions about a real workplace process, then prints:

- where Temporal might help
- a rough Temporal-shaped sketch
- questions the group should discuss next

Run it with:

```bash
uv run python -m apps.byoc
```

## How To Use It In The Session

Recommended timebox: 25-35 minutes.

1. **Pick a case**
   - Choose one real process from the group's work.
   - Good candidates involve waiting, retries, scheduled work, external systems, manual recovery, long-running state, approvals, fan-out, or compensation.
   - Avoid pure synchronous CRUD or request-response flows.

2. **Answer the prompts**
   - Do not try to sound like a Temporal expert.
   - Describe the current system in normal engineering language: queues, cron, DB flags, runbooks, dashboards, scripts, support tickets, manual fixes.

3. **Read the generated analysis**
   - Treat the fit signal as a discussion starter, not a verdict.
   - The important output is the mapping from today's pain to possible Temporal concepts.

4. **Discuss the follow-up questions**
   - Focus on whether Temporal would remove real operational pain.
   - "Not a fit" is a valid outcome.

5. **Share out**
   - Process:
   - Current pain:
   - Where Temporal might help:
   - Biggest unanswered question:

## What The Prompts Are Looking For

The assistant does not ask "where would you use Signals?" or "what is the Workflow?" because those questions require Temporal knowledge. It asks about symptoms instead:

- Does the process run for a long time?
- Does it wait for time, approvals, callbacks, or outside events?
- Does it call external systems?
- Does it need retries?
- Do people manually inspect, rerun, or repair failed cases?
- Would better visibility into the current step help?
- Does one case fan out into repeated or parallel work?
- Can later failure require undo, rollback, refund, release, or reconciliation?

The script then maps those symptoms to likely Temporal concepts:

- long-running state -> Workflow
- external systems or side effects -> Activities
- flaky calls or manual reruns -> Activity retries
- waiting for time -> Timers
- approvals, callbacks, cancellations, changed input -> Signals
- operator visibility -> Queries
- repeated or parallel branches -> Child Workflows or fan-out Activities
- undo or rollback needs -> Compensation

## Facilitator Notes

The goal is not to sell Temporal. The goal is to help engineers ask sharper questions about a real process:

- Which parts are orchestration rather than business computation?
- Which side effects must be idempotent?
- Which failures should retry, stop, branch, or compensate?
- Which state would be useful during an incident?
- What is the smallest painful slice worth prototyping?

If the generated analysis says the case is weak or unclear, that is useful. It means the group can avoid forcing Temporal onto a problem that may be better handled by a normal request, job, queue, or database transaction.
