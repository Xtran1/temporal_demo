# Temporal Knowledge Share Plan

This knowledge share is broad and experimental: the presenter gives a practical overview of Temporal, then participants choose one or two learning paths to continue with. Nobody is expected to complete all three paths during the session.

Audience: medior-to-senior software engineers who can evaluate a new infrastructure pattern and relate it to systems they already work on.

## Session Paths

1. **Documentation path**
   - Presenter-owned.
   - The presenter will curate useful Temporal documentation pages separately.
   - This repo does not need to prescribe the docs list yet.

2. **Experiment with examples**
   - Use Python for all examples.
   - Keep the Python simple enough that engineers who do not write Python daily can still read and modify it.
   - Build three structurally comparable examples with different domain shapes.
   - Each example should have:
     - simple local setup
     - a walkthrough document
     - commands to start, watch/query, signal or unblock, inject failure, and inspect Temporal UI
     - a visible worker crash/restart moment
     - explicit expansion ideas using more of Temporal or a more involved workflow

3. **BYOC: Bring Your Own Code**
   - Small-group breakout format.
   - Participants map one real workplace process onto Temporal capabilities.
   - The output is both a fit assessment and a lightweight architecture sketch.
   - "Not a fit" is a valid and useful outcome.

## Path 2: Example Direction

The examples should be similar enough that participants can compare Temporal concepts across domains, but different enough that each one teaches a distinct process shape.

### Orders / Logistics

Use the current order fulfillment demo as the first example.

Focus:
- durable business process
- retries
- signals for external approval
- timers
- compensation
- long-running activities with heartbeats
- worker crash/restart resilience

Core idea: a business process survives unreliable systems without bespoke checkpointing.

Expansion ideas:
- add richer compensation for partial failures
- split fulfillment into child workflows
- add idempotency keys around side-effecting activities
- add search attributes for order status and customer/account dimensions
- add a delayed cancellation or customer change window

### Menu Versioning / Publishing

Add a menu publishing example inspired by versioned menu rollout use cases.

Focus:
- approval gates
- scheduled publishing
- fan-out to stores, regions, or delivery channels
- rollout status queries
- rollback or supersede ideas

Core idea: a rollout process has durable state and time-based coordination.

Expansion ideas:
- add staged rollout by region
- add rollback workflow
- add validation activities before publish
- model store/channel updates as child workflows
- add a signal to pause, resume, or cancel a rollout

### Agentic AI Loop

Add an agent-loop example that abstracts model decisions and tool calls.

Focus:
- repeated tool calls
- transient tool failures
- waits between actions
- loop completion
- cancellation or budget limits
- inspectable state while the loop runs

Core idea: an uncertain iterative process becomes resumable, observable, and controllable.

Important Temporal rule:
- Do not use randomness, time, network, or I/O directly inside workflow code.
- Simulated model choices, random step counts, random wait durations, and flaky tool behavior must happen in activities or be passed into the workflow as input.
- The workflow should deterministically orchestrate the loop based on recorded activity results.

Suggested loop:
1. Execute a `decide_next_action` activity.
2. If the decision is complete, return the final result.
3. Otherwise, optionally sleep with a durable timer.
4. Execute the selected tool activity with retries.
5. Record/query current state.
6. Repeat until complete, canceled, or budget exhausted.

Expansion ideas:
- add human approval before a risky tool call
- add separate child workflows for long-running tools
- add per-tool retry policies
- add a maximum cost, step, or time budget
- add a query for current plan, last tool result, and remaining budget

## Path 3: BYOC Direction

Run BYOC as a 25-35 minute small-group breakout. Groups choose one real workplace process from their own systems, then use `docs/BYOC_WORKSHEET.md` to produce both:

- a fit assessment: `yes`, `maybe`, or `probably not`
- a lightweight Temporal-shaped architecture sketch

Recommended flow:

1. **Case selection: 3 minutes**
   - Pick a process with waiting, retries, external side effects, human approval, scheduling, async jobs, or recovery pain.
   - Avoid pure synchronous CRUD or request-response paths.

2. **Current-state mapping: 7 minutes**
   - Identify trigger, completion condition, current state storage, external systems, retry/recovery logic, manual operations, and failure modes.

3. **Temporal projection: 10-12 minutes**
   - Sketch the main workflow, activities, signals, queries, timers, retry policies, compensation, and child workflows where useful.
   - Keep this conceptual; no SDK details or deployment design required.

4. **Fit assessment: 5-7 minutes**
   - Decide whether Temporal looks like a good fit.
   - List the clearest benefits, risks, and unanswered questions.

5. **Share-out: 5-8 minutes**
   - Each group summarizes the process, current pain, Temporal shape, fit verdict, and biggest question.

Acceptance criteria:
- Participants can complete the worksheet without needing Temporal expertise.
- Discussion stays grounded in real systems rather than abstract architecture.
- Each group leaves with both a reasoned fit assessment and a rough architecture sketch.
- The exercise does not require a polished design.
