# BYOC Worksheet: Bring Your Own Code

Use this worksheet to map a real workplace process onto Temporal. The goal is not to prove Temporal is the answer. The goal is to decide whether durable execution could simplify the process, make it more reliable, or make it easier to operate.

## 1. Pick a Process

Process name:

Owner/team/context:

Choose a process that has at least one of these:
- waiting for time or external input
- retries or manual recovery
- async jobs, queues, cron, or scheduled work
- external side effects
- human approval
- long-running state
- partial failure or compensation

Avoid pure synchronous CRUD or request-response flows.

## 2. Current State

Trigger:

Done condition:

Where does process state live today?

Examples: database rows, status flags, queue messages, cron jobs, logs, spreadsheets, manual tracking.

External systems or side effects:

Examples: payment, email, internal services, third-party APIs, data pipelines, generated files.

Retry and recovery behavior:

Examples: automatic retries, manual reruns, dead-letter queues, support scripts, dashboard buttons.

Known pain points:

Examples: lost state, duplicate work, hard-to-debug failures, unclear ownership, manual cleanup, poor visibility.

## 3. Temporal Projection

Main Workflow:

What durable process would the workflow represent?

Activities:

What side effects or external calls would move out of workflow code and into activities?

Signals:

What external events might arrive while the process is running?

Examples: approval, cancellation, new input, retry request, pause/resume.

Queries:

What state would operators, users, or other services want to inspect?

Timers:

Where would durable waiting help?

Examples: SLA timeout, delayed publish, reminder, retry window, cooling-off period.

Retries:

Which failures are retryable, and which should stop or branch the process?

Compensation:

What needs to be undone or reconciled if a later step fails?

Child Workflows:

Would any repeated, parallel, or independently tracked subprocesses be clearer as child workflows?

## 4. Fit Assessment

Verdict:

Choose one: `yes`, `maybe`, `probably not`

Best reasons Temporal might help:

Risks or costs:

Open questions:

What would you test in a spike?

## 5. Share-Out

Use this short summary if your group presents:

- Process:
- Current pain:
- Temporal shape:
- Fit verdict:
- Biggest question:
