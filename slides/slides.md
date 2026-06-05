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

<div class="mt-10 text-xl opacity-70">
What breaks when a process outlives one request?
</div>

<!--
Frame the talk around engineering pain, not Temporal terminology. The first question should be familiar even to people who have never used a workflow engine.
-->

---
layout: center
class: text-center
---

# A Workflow

One process with memory

<div class="mt-10 text-left inline-block text-2xl leading-10">

- starts from an event
- moves through steps
- waits for things
- eventually finishes

</div>

<!--
Keep this generic. An order, rollout, onboarding, ticket escalation, long-running agent task, or migration can all be workflows.
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

<!--
This is not wrong architecture. It is often where teams naturally end up. The problem is that orchestration semantics are spread across many places.
-->

---
layout: center
class: text-center
---

# Temporal's Bet

Write the process once.

Keep its progress durably.

Run side effects safely.

<!--
The core proposition: durable execution, not just another queue. Emphasize that the workflow code describes orchestration, while Temporal records enough history to recover and replay.
-->

---
layout: center
---

# The Split

<div class="grid grid-cols-2 gap-10 mt-8 text-2xl">
<div>

**Workflow**

- deterministic
- orchestration
- decisions
- waits

</div>
<div>

**Activity**

- side effects
- APIs
- databases
- randomness

</div>
</div>

<!--
This is the most important implementation concept. Workflows decide what should happen. Activities do things that touch the outside world.
-->

---
layout: center
class: text-center
---

# What Temporal Records

<div class="mt-10 text-3xl leading-14">

events · timers · signals · retries · results

</div>

<div class="mt-10 text-xl opacity-70">
Replay rebuilds workflow state from history.
</div>

<!--
This is why worker restart is not fatal. The worker can replay history and continue from the next needed command.
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
class: text-center
---

# What It Buys You

<div class="mt-10 text-3xl leading-14">

less checkpointing<br>
visible retries<br>
long waits without sleeping processes<br>
crash/restart continuity

</div>

<!--
Tie back to the demo: order waits for approval, menu waits for publish time, agent waits between tool calls.
-->

---
layout: center
---

# What It Does Not Remove

<div class="text-2xl leading-12">

- idempotency
- versioning workflow code
- operational ownership
- choosing workflow boundaries
- understanding failure semantics

</div>

<!--
Temporal solves orchestration durability. It does not make every side effect safe or every process design obvious.
-->

---
layout: center
class: text-center
---

# Three Ways To Continue

<div class="grid grid-cols-3 gap-6 mt-12 text-xl">
<div>

**Docs**

mental model

</div>
<div>

**Examples**

run and break it

</div>
<div>

**BYOC**

map real systems

</div>
</div>

<!--
This is the handoff into the workshop format: people choose their path. Mention that the examples cover orders, menu rollout, and agentic loops.
-->
