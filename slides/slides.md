---
theme: seriph
background: https://cover.sli.dev
title: Temporal Durable Execution
info: |
  A short knowledge-share introduction to workflows and Temporal.
class: text-center
drawings:
  persist: false
transition: slide-left
comark: true
duration: 20min
---

# Temporal

Durable execution for workflows as code

<!--
Frame the talk around engineering pain, not Temporal terminology. The first question should be familiar even to people who have never used a workflow engine.
-->

---
layout: center
class: text-center
---

# A Workflow

One process with state

<div class="mt-10 inline-grid text-left text-2xl leading-10" style="grid-template-areas: 'stack'">

<div v-click.hide="1" style="grid-area: stack">

- starts with an event
- moves through steps
- waits for things
- eventually finishes

</div>

<div v-click="[1, 2]" style="grid-area: stack">

- starts with a customer placing an order
- moves from payment processing to packing
- waits for automated payment confirmation and manual shipping confirmation
- finishes when the package is picked up

</div>

<div v-click="[2, 3]" style="grid-area: stack">

- starts with a release being promoted to staging
- moves from canary to a phased rollout
- waits for automated health checks and a manual go/no-go approval
- finishes when every region is on the new version

</div>

<div v-click="[3, 4]" style="grid-area: stack">

- starts with a user raising a support ticket
- moves from triage to assignment to resolution
- waits for an automated diagnostic and a manual engineer sign-off
- finishes when the ticket is closed and confirmed

</div>

<div v-click="4" style="grid-area: stack">

- starts with an agentic graph runnner
- moves through agent nodes with tool calls and deterministic decision points
- waits for model provider API calls and manual human-in-the-loop approvals
- finishes when the goal is met

</div>

</div>

<!--
Keep this generic, then make it concrete on the first click. An order, rollout, onboarding, ticket escalation, long-running agent task, or migration can all be workflows.
-->

---
layout: center
---

# Without a Workflow System

<div class="grid grid-cols-2 gap-10 mt-10 text-2xl">
<div>

**Logic**

- HTTP handlers
- queues
- cron
- workers

</div>
<div>

**State**

- DB flags
- retry tables
- logs
- runbooks

</div>
</div>

<div v-click="1" class="mt-12 text-2xl opacity-80">

This is not wrong, but it is <span class="inline-grid" style="grid-template-areas: 'stack'"><em v-click.hide="2" style="grid-area: stack">coupled, distributed logic</em><em v-click="[2, 3]" style="grid-area: stack">globally redundant</em><em v-click="3" style="grid-area: stack">fragile</em></span>

</div>

<!--
1: The problem is that orchestration semantics are spread across many places.
2: The solutions have been built many times over, but you end up making custom ones again
3: Crashes and restarts still lose progress

Comparisons: IaC vs clickops - similar declarative and trackable nature. Java/C memory switch - similar overhead payment for not having to put in the work
-->

---
layout: center
class: text-center
---

# The Workflow Class

<div class="text-2xl leading-10">

The process as code

<div v-click="1" class="mt-6">

Each step's I/O is recorded, so the code can be **replayed** to rebuild state after any crash.

</div>

<div v-click="2" class="mt-6">

Between steps the Workflow can **wait** — seconds or months — with no process held open.

</div>

<div v-click="3" class="mt-8 opacity-90">

For the messy parts — APIs, databases, randomness — it calls an **Activity**.

<div class="opacity-70 text-xl mt-2">Temporal runs those once, records the result, and retries on failure.</div>

</div>

</div>

<!--
This is the core mental model in one slide. The workflow is durable code; replay rebuilds it from recorded history; it can wait indefinitely because nothing is held open; and anything non-deterministic or side-effecting is pushed into an activity, which Temporal runs once, records, and retries. Activities are not peers of the workflow — they are the calls it makes out to the world.
-->

---
layout: center
class: text-center
---

# What Temporal Records


Temporal records one thing: a log of events.

<div class="mt-8 text-left inline-block text-2xl leading-12">

- a workflow started — `WorkflowExecutionStarted`
- a timer fired — `TimerFired`
- a signal arrived — `WorkflowExecutionSignaled`
- an activity ran — `ActivityTaskScheduled` → `Completed` / `Failed`

</div>

<div v-click="1" class="absolute inset-0 flex items-center justify-center bg-white/95">
  <img src="/images/temporal-database-img.svg" class="max-h-[80%] max-w-[85%]" />
</div>

<!--
History is nothing but a stream of events. An activity is work you write; running it appends several events (scheduled, started, completed/failed). Timers, signals, and retries are all just other kinds of events. This is why worker restart is not fatal — the worker replays history and continues from the next needed command.

On click, bring up the persistence layer: that event log is durably stored in Temporal's database (the persistence store, e.g. Cassandra/MySQL/PostgreSQL). The history is the source of truth — workers are stateless and replay from it. This is what makes it survive crashes.
-->

---
layout: center
---

# Useful Terms

<div class="text-2xl leading-12">

- **Worker** runs workflow and activity code
- **Task Queue** routes work to workers
- **Signal** changes a running workflow
- **Query** reads workflow state
- **Timer** waits durably

</div>

<!--
Keep terms operational. Avoid deep internals unless asked. These are enough for the demos.
-->


---
layout: center
---

# Still On You

<div class="mt-6 text-left inline-block text-2xl leading-12">

- **Idempotency** — activities can run more than once; your side effects must be safe
- **Workflow versioning** — replay means you can't freely edit in-flight workflow code

</div>

<!--
Temporal makes orchestration durable, not every side effect safe. Two gotchas survive it, both consequences of how it works:

Idempotency: activities are at-least-once, not exactly-once. A retry, or a completed activity whose result never got recorded, re-runs the code. If it charges a card, you double-charge unless the activity is idempotent. Temporal's internal state is consistent; your real-world effects are your responsibility.

Versioning: because workflows replay from history, changing workflow code can break determinism for running executions. Temporal gives you primitives (patched/GetVersion, worker versioning), but reasoning about in-flight workflows on old code stays yours.
-->

---
layout: center
class: text-center
---

# Three Options

<div class="grid grid-cols-3 gap-6 mt-12 text-xl">
<div>

**Docs**

Build understanding & many examples

</div>
<div>

**Examples**

Run the code in this repo. Try it, break it, build it out

</div>
<div>

**BYOC**

Small questionnaire to help map your system in a Temporal axis

</div>
</div>

<!--
This is the handoff into the workshop format: people choose their path. Mention that the examples cover orders, menu rollout, and agentic loops.
-->

---
layout: full
---

# Suggested Docs

1.  <a href="https://docs.temporal.io/temporal-service/temporal-server">Temporal server introduction</a>
2.  <a href="https://docs.temporal.io/temporal-service/persistence">Persistence Layer</a>
3.  <a href="https://docs.temporal.io/activities">Activities</a>
4.  <a href="https://docs.temporal.io/quickstarts">Quickstarts</a>
5.  <a href="https://learn.temporal.io/examples/">Huge list of example applications and SDK samples for Go, Java, .NET, Python, Ruby, Typescript</a>
6.  <a href="https://docs.temporal.io/develop/">Top level page for all SDK docs</a>
7.  <a href="https://docs.temporal.io/develop/activity-retry-simulator">Activity Retry Simulator</a>
8.  <a href="https://docs.temporal.io/develop/worker-performance">Worker Performance</a>
9.  <a href="https://docs.temporal.io/self-hosted-guide">Self-host to production guide</a>
10. <a href="https://github.com/temporalio">The repo</a>
