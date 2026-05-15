# Context Loading Protocol

## The pattern

Before starting any substantive work, load context from the persistent task tracker (beads, in this author's setup; equivalent in other tools). This is not optional.

## At session start

1. List in-progress work items.
2. List ready-to-start work items.
3. For the task at hand, run `show` on relevant work items to load design decisions, acceptance criteria, and prior analysis.

## Before dispatching to analysis skills

When dispatching to skills that produce judgment (PR review, challenge passes, multi-specialist consults, plan convergence, work decomposition, specialist agents):

- Include relevant work-item context in the prompt you build for the skill or agent. Run `show` on related items and pass the output as context.
- Skills running without context will produce analysis that ignores prior decisions.

**Exception**: PR reviews of others' code rarely have associated work items in the author's tracker; the PR diff, ticket, and design doc provide the context. Skip context-loading when no relevant items exist for the work being reviewed.

## Epic-first check for domain-familiar work

If the request touches a domain with an active epic (a known long-running workstream), run `show` on the epic and list its children before converging, decomposing, OR reviewing PRs in that domain. Convergence without this produces plans that duplicate existing items from parallel sessions; PR review without this produces concerns that misread the migration's current state. The cost of one `show` is near-zero; the cost of re-planning or re-framing a posted review is high.

## Include checkpoint handoff instruction in subagent prompts

When dispatching a subagent, include this instruction:

> "If your analysis produces findings, decisions, or conclusions that would be lost to conversation compaction, include a Checkpoint Recommendation block in your response."

When a subagent returns a Checkpoint Recommendation, invoke the work-decomposition skill in checkpoint mode with it. This is not optional.

## Before starting implementation

After a plan is approved, after decomposition, after discussion converges:

- Verify the work is captured in the tracker. If there are open design decisions, acceptance criteria, or dependency relationships from the conversation that are not in a work item yet, persist them first.
- Do not start coding until the item for the current task has `in_progress` status AND contains enough context for a cold-start agent to continue the work.
- Claim the item before starting (optimistic locking: signals intent to parallel sessions but does not hard-block). Check the current state first to see if another session already has it.

## Verify infrastructure assumptions

Before writing code that depends on external resources (database tables, queues, buckets, API endpoints), confirm the resource exists using available tools (cloud provider CLI, infrastructure-as-code search). Do not infer existence from naming conventions, other code's imports, or logical expectation. If you cannot verify, say so explicitly before proceeding.

Building on unverified infrastructure assumptions is the implementation equivalent of proposing a fix without root cause investigation.

## After deep analysis or discussion

If the conversation has 3+ exchanges on design, rejected alternatives, or scope changes:

- If the conversation holds decisions or findings not yet in the tracker, invoke the work-decomposition skill in checkpoint mode before moving on. Compaction will erase this context otherwise.
- This is a hard trigger, not a judgment call. If you discussed it and it's not in an item, checkpoint it.

## Why this exists

Conversation context is ephemeral. Persistent task-tracker items are durable. The boundary between the two determines what survives compaction or session end.

The protocol is asymmetric: loading context is cheap (one `show` query); not loading is expensive (re-derivation, duplicate work, plans that conflict with parallel sessions). The default of "load before substantive work" eliminates the failure mode at the cost of routine overhead.

Checkpointing is the complementary discipline: durable artifacts only stay durable if the things worth preserving make it INTO the durable layer before compaction. The trigger conditions ("3+ exchanges of design", "decisions not yet in items") catch the cases that matter.

## How this compounds

A session that consistently loads context at start, includes context in subagent prompts, and checkpoints accumulated decisions produces a task-tracker state that is always current. Cold-start sessions pick up cleanly from where the last session left off. The compounding effect is that the tracker becomes a reliable persistent memory across sessions, machines, and team members.

A session that skips the protocol produces a tracker that drifts: items reflect what was true days ago, subagents produce analysis that ignores recent decisions, cold-start sessions re-litigate closed questions. The drift is gradual and hard to reverse.

## Where it has limits

- The protocol assumes a useful task tracker exists. In environments without one, the closest substitute is a structured scratch directory or a memory store with disciplined key namespacing.
- Routine work (single-file edits with no decisions to preserve) does not warrant the full protocol. The "after deep analysis" trigger is what catches the cases that matter; routine sessions can skip everything except the start-of-session orientation.
