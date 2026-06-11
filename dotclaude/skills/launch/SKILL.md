---
name: launch
description: >
  Execution launcher: takes a Jira ticket, bead, Slack thread, Confluence
  rough-draft, or free text and dispatches an agent team to BUILD it,
  producing real commits and a draft PR. Pipeline: enrich context, classify
  INPUT_MODE (problem-framed vs mechanism-prescribed), converge on a plan
  with challenge + consult stress-test, mandatory skeptic pass, and
  decision-maker proceed/iterate gate before user approval. Detects when
  the ticket prescribes a mechanism that should have been a feature of an
  existing noun (Fulfillment-vs-Coverage protection). The key distinction
  from /converge: launch writes code, converge writes a plan. Use when the
  ticket is well-scoped and you want hands-off implementation. Multiple
  invocations run in parallel via worktrees. For divergent approach
  generation before a plan exists, use /ideate. For planning only with no
  code, use /converge. For root cause investigation, use /investigate.
argument-hint: "[MX2-XXXXX | docr-XXXX | description] [--skip-checks]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "Write", "Edit", "WebFetch", "Skill", "AskUserQuestion"]
---

# Launch

Take a Jira ticket (or bead, or description) from zero to draft PR. Enrich context,
converge on a plan, get human approval, then dispatch an agent team to implement it
in an isolated worktree while you orchestrate.

## Input

Parse the raw invocation (`/launch $ARGUMENTS`) to extract:
1. **Identifier**: first token matching `MX2-\d+` (Jira), `docr-\w+` (bead), or a
   GitHub PR URL. Everything else is treated as free-text description.
2. **Flags**: `--skip-checks` skips pants tlc in finalization.

If the invocation contains neither an identifier nor any free-text description
(empty arguments), stop and ask for one. Otherwise treat the non-identifier text
as the free-text description; context-enrichment.md routes it through
prompt-refiner. Do NOT demand a ticket number when a description was given.

## Pipeline Overview

```
ticket / bead / Slack / Confluence / transcript / free text
   |
   v
[Phase 1: Context Enrichment] <-------+
   |                                  |  (loop-back on ESCALATE-QUESTIONS,
   v                                  |   after user answers narrowing Qs)
[Phase 2: Decompose] <----------+     |
   |                            |     |  (loop-back on ITERATE,
   +--------+--------+          |     |   scoped to the named
   |                 |          |     |   WEAK_DIMENSION)
   v                 v          |     |
[Phase 3a:        [Phase 3b:    |     |
 Challenge]        Consult]     |     |
   |                 |          |     |
   +--------+--------+          |     |
            |                   |     |
            v                   |     |
[Phase 3c: Synthesize] ---------+     |
            |                         |
            v                         |
[Phase 3.5: Skeptic Lens]           |
            |                         |
            v                         |
[Phase 3.6: Convergence Gate] --------+
            |
            | (PROCEED or LOW-CONFIDENCE only)
            v
[Phase 4: Approval Gate]      First synthesis-level user-facing output.
            |
       [user approval]
            |
            v
[Phase 5: Execution]          Worktree + agent team + retry loop.
            |
            v
[Phase 6: Finalization]       /review fan-out (incl bot-review) + PR creation.

Phase 3.6 verdicts:
  PROCEED            -> Phase 4
  LOW-CONFIDENCE     -> Phase 4 with (low-confidence) annotation
  ITERATE            -> Phase 2 (cap: 2 rounds)
  ESCALATE-QUESTIONS -> ask user, then Phase 1 (cap: 1 round)
  ESCALATE-ROUTE     -> Phase 4 with no agent team; suggest a different
                        skill (/converge, /ideate, /investigate)
```

Phases 1-3.6 are INTERNAL. The only user-facing output before Phase 4 is
the narrowing questions in ESCALATE-QUESTIONS (when fired). Phase 4 is the
first synthesis-level visible output; Phase 5 is execution (commits) and
Phase 6 is finalization (PR creation).

## Distinctions

- **vs `/converge`**: `/converge` writes a plan and creates beads;
  `/launch` writes code and creates a draft PR. `/launch` internally
  runs the same Phase 2-3.6 pipeline as `/converge` (challenge +
  consult + skeptic + decision-maker gate), then continues into
  Phase 5 execution. Use `/converge` when you want a plan without
  burning a worktree.
- **vs `/ideate`**: `/ideate` is upstream of both `/converge` and
  `/launch`. It generates 3-5 candidate approaches and ranks them.
  `/launch` takes ONE approach (the ticket's prescription) and builds
  it. When `/launch`'s gate detects multiple plausible mechanisms with
  no clear winner, it fires ESCALATE-ROUTE with
  SUGGESTED_NEXT_SKILL=/ideate.
- **vs `/investigate`**: `/investigate` finds root cause for a
  production error. `/launch` builds a fix AFTER root cause is known.
  When the gate detects an unknown root cause (the ticket is actually
  a bug investigation), it fires ESCALATE-ROUTE with
  SUGGESTED_NEXT_SKILL=/investigate.
- **vs `/challenge`**: `/challenge` extracts assumptions from an
  EXISTING plan. `/launch` invokes `/challenge`-style assumption
  extraction internally in Phase 3a.
- **vs `/consult`**: `/consult` runs parallel specialists with
  DIFFERENT lenses on the SAME code. `/launch` invokes
  `/consult`-style specialist orchestration internally in Phase 3b.
- **vs `/autopilot`**: `/autopilot` runs the full plan+build pipeline
  without human approval gates (uses `mx2-decision-maker` at every
  checkpoint). `/launch` keeps the human in the loop at Phase 4 and
  uses `mx2-decision-maker` only at the pre-approval Phase 3.6 gate.
  Use `/autopilot` when you want hands-off; use `/launch` when you
  want a draft PR you can review before publishing.

## Phase 1: Context Enrichment

See [context-enrichment.md](context-enrichment.md) for the full protocol.

**Summary**: Fetch the Jira ticket, discover related beads, read relevant source
files, then dispatch `prompt-refiner` in headless mode. Output is a 200-400 word
**implementation brief** that becomes the seed for Phase 2.

All tool calls in this phase run in parallel where possible. Do not show
intermediate output to the user.

## Phases 2-3.6: Plan Pipeline (Internal)

Run the converge-style plan pipeline against the implementation brief: refine
plus decompose plus pipeline-reuse gate (Phase 2), then challenge plus consult
in parallel (Phase 3a/3b), then synthesize (Phase 3c), then skeptic lens
(Phase 3.5), then decision-maker gate (Phase 3.6). Output is an internal
converged plan + parallelization-strategy YAML + iteration log; not shown to
the user yet.

### Bypass: pre-converged input

Skip Phases 2-3.6 entirely and go straight to Phase 4 (approval gate) when
either of the following is true:

1. The user's prompt explicitly states "do NOT re-converge" or "skip
   convergence" or "convergence already done", AND the input bead's
   description contains all four elements of a converged plan: (a) work-item
   scope with file targets, (b) acceptance criteria, (c) verification path,
   (d) consequence-of-wrong or risk note. Read `bd show <bead-id>` first to
   confirm.
2. The input bead carries a `decision:` or `memory:` label AND the description
   was produced by a prior `/converge` or `/launch` session (the description
   structure mirrors the Phase 4 template: Summary, Iteration Log, Convergence
   Delta, Work Items, Dependency Graph). This is a structural check, not a
   text match; if the bead looks like a converged plan, treat it as one.

When the bypass fires, the iteration log entry for Phase 4 reads
"Round 0 (initial): N work items from pre-converged input (bead docr-XXXX);
Phases 2-3.6 skipped per <reason>." The Convergence Delta category is set to
the prior session's category (preserved on the bead) or CONFIRMED if not
recorded. Phase 4 approval still gates execution; Phase 5+ proceeds normally.

The bypass exists because re-running challenge + consult + skeptic +
decision-maker on a plan that was already through that pipeline in a prior
session produces redundant token cost without new signal. The recurring case
is a `/launch` invocation that immediately follows a `/converge` whose plan
was forged into beads. Recurrence context: 2026-05-28 MX2-XXXXX / docr-xii5,
where the prompt told /launch the convergence was complete and the protocol
forced a re-run anyway; the orchestrator had to manually skip 1-3.6.

**Load-bearing invariants:**
- The Challenge subagent and all selected consult specialists MUST run as
  parallel dispatches in a single Agent-tool message (no consult-coordinator
  subagent; the orchestrator synthesizes consult findings). Serializing
  defeats the purpose.
- Phase 3c output includes the DELTA_CATEGORY label (CONFIRMED /
  MINOR_ADJUSTMENTS / MAJOR_REVISIONS / SCRAPPED_AND_REBUILT). CONFIRMED on
  a non-trivial `mechanism-prescribed` input is suspicious; Phase 3.6 gate
  fires ITERATE with WEAK_DIMENSION=mechanism when it sees that pattern
  (canonical Fulfillment-vs-Coverage protection).
- Phase 3.5 Skeptic Lens is mandatory. Runs `mx2-skeptic` on the
  converged plan with the DELTA_CATEGORY and INPUT_MODE as input. Output
  folds into Phase 4 as a `Skeptic Lens` block. If dispatch fails, note
  "Skeptic Lens unavailable" and proceed; do not silently drop.
- Phase 3.6 Decision-Maker Gate is mandatory. Runs `mx2-decision-maker` with
  `MODE: LAUNCH GATE` preamble. Returns PROCEED / ITERATE / ESCALATE-QUESTIONS
  / ESCALATE-ROUTE. ITERATE cap: 2 rounds; ESCALATE-QUESTIONS cap: 1 round.
- Phase 3.6 output is the **parallelization strategy** (agent roster, phasing,
  checkpoint gates, agent inputs) only when verdict is PROCEED. ESCALATE-ROUTE
  means no agent team gets dispatched; Phase 4 shows the gate's reason
  + suggested next skill.
- Every checkpoint gate must be programmatically verifiable (e.g., "pants check
  passes" not "implementation complete").
- Every work item must include a Verification path. Consequence=high items
  must have either a matching Verification path or an explicit risk-reduction
  note. Phase 3.6 gate enforces this.

For the orchestration shape (Phase 2 decompose, Phase 3c synthesize +
DELTA_CATEGORY, parallelization-strategy YAML), see
[plan-pipeline.md](plan-pipeline.md). For the Phase 3a Challenge
subagent and Phase 3b per-specialist prompt templates (orchestrator-
dispatched, INPUT_MODE-aware), see
[stress-test-prompts.md](stress-test-prompts.md). For the Phase 3.5
Skeptic Lens dispatch + the Phase 3.6 Decision-Maker Gate dispatch +
branch logic + caps + iteration log format, see
[gate-prompts.md](gate-prompts.md).

## Phase 4: Approval Gate

**First synthesis-level output the user sees** (the only earlier user-facing
output is the narrowing questions from a Phase 3.6 ESCALATE-QUESTIONS, when
fired).

Present the converged plan using the Phase 4 plan template in
[output-template.md](output-template.md). The template is the structural
contract for this output: an H2 `## Launch Plan` (with `(low-confidence)`
suffix when the gate forced a low-confidence PROCEED), then Summary, Iteration
Log (always present so the user sees the gate ran), Convergence Delta (with
CATEGORY tag), Prior Thinking Comparison (mechanism-prescribed inputs only),
the mandatory Skeptic Lens block, Work Items (each with Acceptance criteria +
Verification path + Consequence-of-wrong), Agent Roster, Phasing, Commit
Strategy, Open Assumptions, and the ESCALATE-ROUTE-only "No Agent Team
Dispatched" variant. Populate every applicable section in order; do not
free-form narrate the plan.

**This is a hard stop.** Do not proceed to Phase 5 without explicit human approval.
If the user provides feedback, revise and re-present. Max 2 revision rounds - if
more changes are needed, suggest the user provide consolidated feedback.

When the gate fired ESCALATE-ROUTE, "approval" is not the operative action;
the user is being told /launch is the wrong skill for this ticket. The
[output-template.md](output-template.md) template conditionalizes the final
prompt accordingly.

## Phase 5: Execution

**You (the primary Claude session) are the orchestrator.** You have the full plan
context, you spawned the agents, you steer the work. Do not be idle.

The first substeps establish durability and the worktree, then spawn the agent
team. The bash, exact bead-event writes, and recurrence calibration live in
[execution.md](execution.md):

- **5.0 Durable State Initialization**: acquire/create the tracking bead, claim
  it, write `SESSION_STARTED`; if a prior `LAUNCH_EVENT` exists on the bead, run
  the Cold-Start Protocol (`durable-state.md`) instead of proceeding to 5.1.
- **5.1 Create Shared Worktree**: one worktree under `.launch-worktrees/`
  (outside `.git/`, which Claude Code blocks writes to); all agents share it.
  Do NOT use `isolation: "worktree"` on agent spawns.
- **5.2 Spawn Agents (Phase A)**: scope each agent to ONE file or
  tightly-coupled concern (narrow mandate prevents pre-standup truncation);
  decompose into non-overlapping lanes for parallelism, serialize true
  conflicts, and assign one integration agent to the seam. Write the
  `AGENT_SPAWNED` bead event BEFORE the Agent tool call (Temporal pattern).
  Pass the bead ID prominently so the agent's bead-comment course-correction
  channel engages. Launch all Phase A agents in a single message on iteration 1.

### 5.3: Standup Protocol

Every agent template includes this check-in contract:

```
After every logical unit of work (function implemented, test file written,
config file created), emit a STANDUP block in your output (the orchestrator
reads your output stream; subagents have no messaging tool):

STANDUP:
  DONE: [what you just completed - be specific: file, function, test name]
  NEXT: [what you're about to work on]
  BLOCKED: [anything preventing progress, or "none"]
  RISK: [anything that might block you soon, or "none"]
```

### 5.3b: Terminal RESULT Contract + Authority Fence

Two canonical blocks every launch-phase agent template carries verbatim (the
agent defs mirror them via `summary-from` marked pairs; `lint-skill-summary-sync.sh`
keeps the copies in sync). Added 2026-06-09, bd docr-pnx9.

<!-- summary key: result-contract -->
End your FINAL message with a terminal RESULT block (a SubagentStop hook treats a missing block as truncation, and the orchestrator resumes you to produce it):

RESULT:
  STATUS: done | partial | blocked
  DONE: [completed work items / acceptance criteria, one line each]
  REMAINING: [unfinished work and why, or "none"]
  DISCOVERED: [unforeseen work found en route, one line each, classified as either "blocking-AC: <what> | proposed-fix: <one line> | files: <paths>" or "non-blocking: <what>" (non-blocking goes to a linked ticket; do NOT fix it inline)]
  NEEDS-DECISION: [questions only the orchestrator or user can answer, or "none"]
  VERIFICATION: [commands run + outcomes, e.g. "pants tlc <target>: green", or "not run: <why>"]

To ASK the orchestrator something mid-task, end your turn with STATUS: blocked and the question in NEEDS-DECISION; the orchestrator answers by resuming you with your context intact. Ending the turn beats idle-polling whenever a decision gates your next step.
<!-- /summary -->

<!-- summary key: authority-fence -->
AUTHORITY (every launch/autopilot agent):
- Allowed without asking: edits inside the shared worktree on files within your WORK ITEMS scope; running build/test/lint; local commits; `bd comment` / `bd create` for discovered work.
- Forbidden unless your startup prompt grants it for this phase: push, PR creation/publish. Forbidden without an explicit per-round user verb relayed by the orchestrator: force-push, rebase, branch deletion, history rewrites.
- Never: writes outside the worktree; expanding scope beyond WORK ITEMS (route via DISCOVERED instead); fixing a non-blocking discovery inline.
- End the turn as STATUS: blocked when: 3 fix attempts fail on one cause; an acceptance criterion is ambiguous; predicted or actual diff crosses the scope budget; a blocking-AC discovery requires touching files outside the plan surface.
<!-- /summary -->

### 5.3c: Continuation Channel

Agent dispatches return an agent ID; SendMessage to that ID resumes the agent
with its context intact. Prefer continuation over the legacy alternatives:

- **Adjudication** (SCOPE-CHECK, NEEDS-DECISION turn-ends): answer by resuming
  the agent. No bead-comment polling round-trip on the agent side.
- **Course correction between turns**: resume with the correction instead of
  re-dispatching.
- **Truncation recovery** (missing RESULT block, mid-thought ending): resume the
  SAME agent with (a) what is missing and (b) the definition of done. Cold
  re-dispatch of a new agent with a self-contained handoff prompt is the
  FALLBACK for when the agent is no longer resumable, not the default.

`bd comment` remains (a) the durable audit trail (mirror adjudications there)
and (b) the USER's channel into running agents; agents still poll it at the
named checkpoints because the user cannot SendMessage.

After the agents are running, you orchestrate to completion (full detail in
[execution.md](execution.md)):

- **5.4 Orchestration Loop**: stay active: read output, process standups,
  proactively unblock via specialist sub-agents, gate phase transitions on the
  plan's `gate_cmd`, prune standup accumulation after each gate, route
  RESULT.DISCOVERED items per the Escalation Protocol (non-blocking to a linked
  ticket; blocking-AC to one bounded detour agent), escalate on
  external-verification needs or the 3-attempt circuit breaker.
- **5.5 Agent Completion**: re-run gate verification once all `PHASE_GATE_PASSED`
  events are written; escalate any unmet criterion.
- **5.6 Retry Loop**: per-`(agent, phase)` slot, max 3 iterations (circuit
  breaker escalates to user), iteration count derived from `AGENT_FAILED` bead
  events (survives cold-start), `RETRY_CONTEXT` on iteration 2+. Full algorithm
  in [durable-state.md §Retry Loop Protocol](durable-state.md).

## Phase 6: Finalization

Finalization verifies, commits, runs the broad review gate, creates the draft
PR, self-reviews, and reports. The bash (commit strategy, PR paths A/B, the
em-dash guard, the report template) lives in [finalization.md](finalization.md):

- **6.1 Verification**: `pants tlc` on changed targets (skip if `--skip-checks`);
  route failures to the responsible agent; iterate until clean or circuit breaker.
- **6.2 Commits**: apply the approved commit strategy; messages carry the Jira
  ID `[MX2-XXXXX]`.
- **6.2.4 /review Fan-Out**: invoke `/review` against the worktree diff (it
  resolves to the more comprehensive personal/project skill; roster is
  conditional and evolves, do not hardcode a count). Findings are advisory; PR
  creation proceeds regardless. Post the report to the tracking bead; surface
  CRITICAL findings in the 6.5 report.
- **6.2.5 bot-review**: folded into `/review` as a conditional fan-out agent
  (public-surface changes only, hard-capped at COMMENT/NOTE/SUGGESTION); no
  separate dispatch.
- **6.3 PR Creation**: always from the worktree (never check out the launch
  branch in main). Independent launch (base = main) uses raw `gh pr create
  --draft`; stacked launch (base != main) uses `gt track` + `gt submit --stack
  --draft` so Graphite registers the stack. Build the PR body from the repo
  template FIRST, then layer `memory/pr-template.md`. Draft PR always.
- **6.3.5 Self-Review Gate**: run `/pr-intel --mine` on the just-created draft
  (CLAUDE.md heuristic 1b; the orchestrator's job, not a suggestion). It adds
  AC-compliance trace, CI status, static-analyzer pre-check, and the cross-phase
  integration-bug check that the 6.2.4 `/review` cannot; review-cache reuse keeps
  the cost to the AC/CI/static-analyzer delta. Resolve BLOCKING findings and
  amend before reporting. May be delegated when the user explicitly assigns the
  review to another session or reviewer; record the delegation on the tracking
  bead and skip the local run (running both duplicates the roster).
- **6.4 Cleanup**: `git worktree remove --force` (fallback `rm -rf` +
  `git worktree prune`).
- **6.5 Report**: present the Launch Complete report (PR URL, Graphite link,
  branch, Jira, what was built, agents dispatched, scope-creep tickets, next
  steps).

## Escalation Protocol

| Trigger | Action |
|---------|--------|
| Agent BLOCKED, specialist can help | Spawn specialist, route findings back |
| Agent BLOCKED, needs external verification | Ask user (Superset, Datadog, logs) |
| 3 failures on same issue | Stop, report what was tried, ask user |
| Plan was wrong | Stop, explain what the tests/code revealed, suggest revised approach |
| Non-blocking discovery (RESULT.DISCOVERED) | Linked ticket (/jira or bd create), continue with current plan; never fixed inline |
| Blocking-AC discovery (RESULT.DISCOVERED) | ONE bounded detour agent per work item: minimum scope to unblock the AC, diff counts against the same scope budget, 3-attempt breaker applies. A second detour on the same work item, or a fix touching files outside the plan surface, escalates instead (to the user here; through the decision-maker gate first in autopilot) |

## Rules

- **No intermediate output during phases 1-3.6.** Phase 4 is the first
  synthesis-level user-facing output. Exception: the narrowing questions
  in a Phase 3.6 ESCALATE-QUESTIONS verdict are explicitly user-facing.
- **Hard stop at phase 4.** No execution without explicit human approval.
- **You are the orchestrator.** Don't spawn an orchestrator agent. Stay active, steer, unblock.
- **Shared worktree.** One worktree for all agents. No per-agent isolation.
- **Standup protocol is mandatory.** Every agent checks in after every logical unit.
- **Specialists are ephemeral.** Spawn them for review at checkpoints, don't persist them.
- **Draft PR always.** Never create a ready-for-review PR.
- **Detect INPUT_MODE up front.** Phase 1 classifies the input as
  `problem-framed` or `mechanism-prescribed`. Jira tickets routinely
  prescribe mechanisms; the implementation pipeline must NOT
  rubber-stamp them. Mechanism-prescribed inputs trigger ENHANCED
  scrutiny in Phase 3 (both challenge and consult) and a Prior Thinking
  Comparison section in Phase 4. The Fulfillment-vs-Coverage failure
  mode (refining and BUILDING the wrong noun because the ticket
  prescribed it without challenge) is the canonical risk this rule
  guards against.
- **Skeptic is mandatory.** Phase 3.5 runs always. If the dispatch
  fails, note "Skeptic Lens unavailable" and proceed; do not silently
  drop the pass.
- **Decision-maker gate is mandatory.** Phase 3.6 runs always. PROCEED
  is not the default; the gate must affirmatively reach it. ITERATE
  cap is 2 rounds; ESCALATE-QUESTIONS cap is 1 round per invocation.
  ESCALATE-ROUTE means no agent team is dispatched; Phase 4 shows the
  user the gate's reason and the suggested next skill.
- **Verification path is mandatory per work item.** Items without it
  trigger ITERATE with WEAK_DIMENSION=verification.
- **Consequence-of-wrong is mandatory per work item.** Consequence=high
  AND no concrete Verification path is a workstream-killer; synthesis
  must either add the path or downgrade scope.
- **Convergence Delta gets a category, not just prose.** One of
  CONFIRMED / MINOR_ADJUSTMENTS / MAJOR_REVISIONS /
  SCRAPPED_AND_REBUILT. CONFIRMED on a complex mechanism-prescribed
  input is suspicious; the Phase 3.6 gate will fire ITERATE with
  WEAK_DIMENSION=mechanism on that pattern.
- **Iteration log is always visible.** Phase 4 shows it even when
  Round 0 was final, so the user knows the gate ran.
- **Ask the user when launch space is too ambiguous.** Phase 3.6 can
  fire ESCALATE-QUESTIONS with 1-3 narrowing questions. Max 3
  questions, each with a WHY clause. User can reply "you decide" to
  opt out (forces low-confidence PROCEED).
- **/launch is downstream of /converge and /ideate.** When the input is
  rough and no clear mechanism exists, the gate fires ESCALATE-ROUTE
  with SUGGESTED_NEXT_SKILL=/converge or /ideate.
- **Mixed-input precedence is fixed.** Inline text > Slack/transcript >
  Confluence > Jira/PR > bead notes. Surface disagreements in the
  Phase 4 "Open Assumptions" section. More recent/conversational inputs
  better reflect current user intent.
- **Calibration soak is expected.** The decision-maker invoked at Phase
  3.6 was originally calibrated for autopilot and convergence gates,
  not for launch (which has higher stakes: real commits, real PR
  review burden). First 3-5 `/launch` invocations are calibration soak.
  Record drift via
  `bd remember --key='calibration:mx2-decision-maker:launch:<topic>' '...'`
  so `/calibrate` reviews can keep launch-specific calibration
  separate from autopilot/converge/ideation.
- **Two independent revision caps.** Phase 3.6 has a 2-ITERATE cap
  (auto, pre-user). Phase 4 has a 2-revision-round cap (post-user,
  user feedback drives the revision). Theoretically a single `/launch`
  can go through 4 plan-revision cycles (2 auto + 2 user) before
  bailing. This is intentional: the auto caps catch structural
  issues, the user caps catch ones only the user can adjudicate. Do
  not collapse them; they catch different failure modes.
- **Pre-execution durability via `[LAUNCH_STAGE ...]` bead notes.**
  Phases 1-3.6 write stage events at each phase boundary; heavy
  payloads (challenge findings, consult findings, converged plan)
  go to `~/.claude/scratch/launch-<bead-id>/<stage>-<round>.md`
  with a `path=` pointer in the entry. Cold-start parses the stage
  entries, sorts by round + stage order, resumes at the next
  uncompleted stage. Scratch files are machine-local (codespace);
  if recycled, missing scratch payloads trigger re-running the
  relevant stage. See [durable-state.md](durable-state.md) for the
  full Pre-Execution Cold-Start protocol and Schema Manifest.
- **Bead acquisition timing.** Bead is acquired at the END of Phase 1
  (after prompt-refiner produces the brief), not at Phase 5. This
  makes the Phase 1-3.6 subagent dispatches durable while avoiding
  bead creation for inputs that fail early validation. See
  [durable-state.md](durable-state.md) §Bead Acquisition.
- **Schema version stamp.** Bead metadata carries
  `launch_skill_version=v1` set at acquisition. Cold-start refuses
  to resume across schema-version mismatches; the user starts the
  launch from scratch. Schema changes that break resume are rare
  and must bump the version + update the Stage Manifest in the same
  PR.

## Additional Resources

- [context-enrichment.md](context-enrichment.md) - Phase 1 protocol: input loading (Jira, bead, Slack, Confluence, PR, transcript), INPUT_MODE classification, prompt-refiner dispatch
- [plan-pipeline.md](plan-pipeline.md) - Phase 2 decompose (with Verification path + Consequence + Context fields), Phase 3c synthesize + DELTA_CATEGORY, parallelization-strategy YAML
- [stress-test-prompts.md](stress-test-prompts.md) - Phase 3a Challenge subagent + Phase 3b per-specialist prompts (orchestrator-dispatched, INPUT_MODE-aware)
- [gate-prompts.md](gate-prompts.md) - Phase 3.5 Skeptic Lens + Phase 3.6 Decision-Maker Gate dispatch prompts, branch logic, iteration caps, iteration log format
- [durable-state.md](durable-state.md) - Phase 5 event log, cold-start protocol, retry loop
- Agent templates: `~/.claude/agents/launch-implementer.md`, `launch-tester.md`, `launch-flex.md`
- PR creation: `/pr` command in `.claude/commands/pr.md`
- Jira tickets: `/jira` command in `.claude/commands/jira.md`
