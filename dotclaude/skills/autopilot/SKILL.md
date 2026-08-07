---
name: autopilot
description: >
  Autonomous pipeline: converge on a plan or build a feature without human
  approval gates. Uses mx2-decision-maker as the quality gate at each checkpoint.
  Modes: plan (converge only, output = beads) or build (converge + launch,
  output = draft PR). Use when you want to kick off work and walk away.
argument-hint: "<task | MX2-XXXXX | docr-XXXX> [--mode plan|build] [--max-iterations N]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "Write", "Edit", "WebFetch", "ScheduleWakeup", "CronCreate", "Skill", "SendMessage"]
---

# Autopilot

Run the converge/launch pipeline autonomously. The mx2-decision-maker agent
replaces human approval at every gate. You (the main session) orchestrate.

> **Retirement trigger (armed 2026-07-20, docr-go00s; decision lineage
> docr-9bp1b/docr-1vqfg).** `build` mode is slated for retirement to a stub
> pointing at `/campaign` + `/launch --gate=agent`. The trigger is falsifiable:
> it fires when the FIRST real (non-throwaway) epic completes a `/campaign` run
> to cursor `state=COMPLETE` with 2+ nodes and a run report on the epic bead.
> When that happens: record the firing on docr-9bp1b, then replace this skill's
> build path with the stub (plan mode's fate is decided at the same review).
> Do NOT stub before the trigger fires; drill runs (campaign-drill label) do
> not count.

## Input

Parse `/autopilot $ARGUMENTS`:

1. **Task**: everything that is not a flag. Can be:
   - Free-text description
   - Jira ticket (`MX2-\d+`)
   - Bead ID (`docr-\w+`)
   - A mix of the above
2. **Flags**:
   - `--mode plan|build` (default: `plan`)
   - `--max-iterations N` (default: 5 for plan, 10 for build)

## Modes

| Mode | Pipeline | Output | Use when |
|------|----------|--------|----------|
| `plan` | Phases 1-6 | Converged plan in beads | You want a stress-tested plan to review async |
| `build` | Phases 1-10 | Draft PR + beads | You want code written, tested, and PR'd |

## Pipeline

The entire pipeline runs synchronously in a single skill invocation. No
ScheduleWakeup between phases (except Phase 10: bot remediation).

### Phase 1: Initialize

1. Create a tracking bead:
   ```
   bd create --title="AUTOPILOT: [short task summary]" --type=task --priority=1
   bd update <id> --claim
   ```
2. Log the mode, max-iterations, and input to the bead description.

### Phase 2-3: Refine + Decompose

Run converge Phases 1 and 2 internally: refine the raw input into a
well-specified scope (extract intent, gather context, enrich on Jira / bead
identifiers, expand specificity), then decompose into a draft plan with
work items, acceptance criteria, dependencies, infrastructure pull-up, and
the pipeline-reuse gate. For the full protocol see
[converge/SKILL.md Phase 1-2](../converge/SKILL.md). Autopilot-specific
delta: do NOT present intermediate output to the user; the entire pipeline
is autonomous.

Output: internal refined scope plus draft plan with dependency graph.

### Phase 4: Stress Test

Run the stress test in parallel (per converge Phase 3a/3b): dispatch the
Challenge subagent AND all selected consult specialists (roster:
`~/.claude/skills/consult/specialists.md`) YOURSELF, in one message. There
is NO consult-coordinator subagent: subagents cannot spawn subagents
(verified 2026-06-09), so a coordinator would silently roleplay its
specialists in one context. Challenge searches `bd memories` for
domain-specific gotchas and produces a modifications table; each
specialist reviews the plan items in its domain.

**Launch the Challenge subagent and every selected specialist in a single
message. Do not serialize.**

**Why autopilot embeds these protocols by reading their files at runtime
rather than invoking `/converge` as a sub-skill**: skill invocation has no
return-channel for structured Evidence blocks the decision-maker consumes
in Phase 6, and autopilot needs the outputs in a specific shape under its
control. See the rule at the bottom of this file ("Existing skills are not
modified"). When updating challenge/consult protocol details, update them
in their canonical files (`../challenge/embed-protocol.md`,
`../consult/specialists.md`) and confirm the changes flow through here.

**Autopilot-specific instruction to each subagent**: emit a structured
evidence block at the end of the response (the decision-maker consumes the
combined evidence in Phase 6 via Phase 5 synthesis).

Challenge subagent emits:

```
## Challenge Evidence
- Assumptions extracted: N (FRAGILE: N, SOFT: N, SOLID: N)
- FRAGILE assumptions examined:
  - [assumption]: searched [what], found [result], adjudication: [state]
- Modifications required: [list of changes to the plan]
```

The Consult Evidence block is composed by YOU (the orchestrator) from the
real specialist results, after each specialist ran with the Author Mode
preamble ("CI has not run yet. Flag everything."). "Specialists dispatched"
is the truthful list of Agent calls you actually made:

```
## Consult Evidence
- Specialists dispatched: [list with rationale]
- Fix Now: [items]
- Fix Next: [items]
- Defer: [items]
- Themes: [cross-specialist patterns]
- Gaps: [what no specialist covered]
```

### Phase 5: Synthesize

Apply converge Phase 4 synthesis (gather, connect, deduplicate, apply to
plan). Autopilot-specific addition: **build the evidence trail** by
combining the two Phase 4 evidence blocks into a single structured document
for the decision-maker (Phase 6 consumes this directly; the block headers
above are autopilot-internal scaffolding, not load-bearing for the
decision-maker, which references "Evidence trail" generically).

Output: converged plan + evidence trail.

**Boundary: the embedded converge protocol ends here, at Phase 4 synthesis.**
Do NOT run converge Phases 4.5 (skeptic) or 4.6 (convergence gate) inside
autopilot: Gate 1 (Phase 6 below) replaces the convergence gate, and skeptic
expansion to autopilot is calibration-gated (CLAUDE.md Agent Dispatch routing
rule 3). Their "mandatory" language in converge/SKILL.md applies to /converge
runs, not to this embedding; likewise the /converge present-template
enforcement (stop-validate-plan-present.sh) does not arm for /autopilot.

### Phase 6: Decision Gate 1 (Plan Approval)

Invoke `mx2-decision-maker` as a subagent via the Agent tool:

```
Agent(
  subagent_type="mx2-decision-maker",
  prompt="""
  ## Gate: plan-approval

  ## Artifact
  [The converged plan from Phase 5]

  ## Evidence Trail
  [The combined evidence trail from Phase 5]

  ## Iteration History
  [Prior decisions in this run, or "First evaluation" if none]
  """
)
```

**Handle the decision:**

- **PROCEED**: log to bead comment, continue to Phase 7 (plan mode) or Phase 8
  (build mode).
- **ITERATE**: log to bead comment, loop back to the phase specified in the
  REVISIT field. Decrement remaining iterations. If iterations exhausted (0
  remaining), ESCALATE automatically with "Max iterations reached after N
  ITERATE decisions."
- **ESCALATE**: execute the escalation protocol (see Escalation section below).

### Phase 7: Create Beads

Persist the approved plan as beads:

1. `bd create` for each work item with `--title`, `--description`, `--type`,
   `--priority`. Include acceptance criteria and design notes in description.
2. Wire dependencies via `bd dep add`.
3. Log bead IDs to the tracking bead as a comment.

**Plan mode ends here.** Report to user:

```
## Autopilot Complete (plan mode)

Converged plan created as beads:
- [bead-id]: [title]
- [bead-id]: [title]
...

Decision trail: [N] gate evaluations, [M] iterations.
Review: `bd show <tracking-bead-id>` for full history.
```

### Phase 8: Execute (build mode only)

Follow the launch execution protocol:

1. **Create shared worktree**: `git worktree add .launch-worktrees/autopilot-<bead-id> -b autopilot/<bead-id>`
2. **Determine agent roster**: based on plan items (implementer, tester,
   flex roles as needed). Follow launch Phase 3.6 parallelization strategy.
3. **Spawn agents in parallel**: all Phase A agents in a single message.
   Each agent receives:
   - Their assigned work items with acceptance criteria
   - The worktree path
   - The standup protocol (report DONE/NEXT/BLOCKED/RISK after each logical unit)
   - **The bead ID prominently** (e.g., "BEAD: docr-XXXX") so the agent's
     bead-comment polling channel engages. Spawned launch-* agents poll their
     bead at verification/commit/push checkpoints; the user can leave a
     comment via `bd comment <bead-id> "..."` to send real-time course
     corrections or stop instructions. See "Mid-flight Updates from User" in
     the launch-* agent definitions.
4. **Orchestrate**: read agent outputs, process standups, gate phase transitions,
   route RESULT.DISCOVERED items: non-blocking discoveries go to a linked
   bead/ticket (never fixed inline); a blocking-AC discovery authorizes ONE
   bounded detour agent per work item (minimum scope to unblock the AC, diff
   counted against the same scope budget, 3-attempt breaker), gated through
   `mx2-decision-maker` first whenever the fix touches files outside the plan
   surface; a second detour on the same work item is an ESCALATE. Prefer
   SendMessage continuation (agent ID, context intact) over cold re-dispatch
   for adjudicating STATUS: blocked turn-ends, course corrections, and
   truncation recovery (missing RESULT block per the SubagentStop hook).
5. **Checkpoint gates**: verify acceptance criteria at each phase boundary.
6. **Agent completion**: verify all acceptance criteria met across all agents.

### Phase 8.4: /review Fan-Out (broad evidence gate)

Invoke the `/review` skill against the worktree diff. `/review` resolves to the
more comprehensive of the personal and project review skills (personal wins via
name-overlap precedence and is the broader fan-out); it dispatches its full
parallel review-agent roster (conditionally triggered), deduplicates overlapping
findings, and produces a severity-grouped report. The roster evolves with the
skill, so do not hardcode a count here.

`/review` findings DO carry weight in `mx2-decision-maker`'s evaluation (it can
return ITERATE on a `/review` CRITICAL). `bot-review` is one of `/review`'s
conditional fan-out agents (runs when public surface changes, hard-capped at
COMMENT/NOTE/SUGGESTION), so its cross-file blast-radius findings arrive within
the `## /review Evidence` as advisory-only (never forcing ITERATE); there is no
separate bot-review dispatch.

Invocation: from the worktree directory so `git diff origin/main..HEAD` is
the natural scope, then:

```
Skill(skill="review")
```

Append the report to the Evidence Trail under a `## /review Evidence` header
(see Phase 9 format below).

### Phase 9: Decision Gate 2 (Implementation Approval)

Run `pants tlc` on all changed files in the worktree. Then invoke
`mx2-decision-maker`:

```
Agent(
  subagent_type="mx2-decision-maker",
  prompt="""
  ## Gate: implementation-approval

  ## Artifact
  [git diff of all changes in the worktree]

  ## Evidence Trail
  - pants tlc result: [PASS/FAIL with output summary]
  - Tests written: [list]
  - Tests passing: [yes/no]
  - Files changed: [list]
  - Agent standup history: [summary of DONE/BLOCKED/RISK reports]

  ## /review Evidence
  - Findings: N (CRITICAL: P, WARNING: Q, SUGGESTION: R)
  - CRITICAL findings (if any):
    - [agent_name] [file:line] [one-line articulation]
    - ...
  - WARNING findings summary: <one-line per WARNING, or "none">
  - Agents that ran: enumerate the agents `/review` actually dispatched (its roster is conditional and evolves with the skill; do not hardcode it)
    (note which conditional agents were skipped and why)

  ## Iteration History
  [All prior decisions including Gate 1]
  """
)
```

The decision-maker treats `## /review Evidence` as weight-bearing: a CRITICAL
finding can force ITERATE on its own, and clustered WARNINGs in the same
domain (e.g., multiple test-quality issues) are a signal to consider ITERATE.
Because `bot-review` cannot emit BLOCKING/CRITICAL, its findings arrive inside
`## /review Evidence` as advisory-only and never force ITERATE on their own.

**Handle the decision:**

- **PROCEED**: continue to Phase 10.
- **ITERATE**: fix the issues identified. Re-run `pants tlc`. Re-invoke the
  decision-maker. Max 3 iterations at this gate.
- **ESCALATE**: execute the escalation protocol.

### Phase 10: Create PR + Bot Remediation

1. **Create draft PR** from the worktree branch. Read the repo's PR template FIRST
   (`<repo>/pull_request_template.md` or `<repo>/.github/PULL_REQUEST_TEMPLATE.md`)
   and use its structural skeleton: H1 sections, `Jira issue link:` line, `# Checklist`
   items (filled out, not unchecked default), `Require-reviewers: all` line. Then layer
   the personal style rules from `memory/pr-template.md` on top: H2 subsections within
   the H1 Summary, Jira link at the bottom, no hard line-wrapping in bullets, clickable
   markdown links. If no repo template exists, `memory/pr-template.md` alone applies.
   See the recurrence note in `~/.claude/CLAUDE.md` PR descriptions rule for the
   2026-04-29 instance where this was missed across an autopilot batch.

2. **Bot remediation loop** (ScheduleWakeup-driven):

   ```
   ScheduleWakeup(
     delaySeconds=600,
     reason="waiting for CI checks to complete on PR #N",
     prompt="/autopilot remediate PR=#N bead=<tracking-bead-id> iteration=1 max=4"
   )
   ```

   **Cadence selection:**
   - 270s if you expect imminent CI completion and the user is actively
     watching (cache stays warm).
   - 600s default for hands-off polling once the user steps away
     (one cache miss per iteration, ~30 min coverage at 4 iterations).
   - 1200-1800s if the wait is genuinely idle.

   **ScheduleWakeup gotcha:** wakeups queue, they don't replace. If you
   reissue with a different cadence before the first fires, both will fire.
   Defensive iteration prompts should check `bd show <tracking-bead>` for
   prior logged work in the same iteration before duplicating effort. See
   `bd memories gotcha:schedulewakeup-queues`.

   **Harness fallback:** ScheduleWakeup is a main-loop tool documented as
   /loop pacing machinery; direct calls work today (verified 2026-06-09) but
   are not guaranteed across harness versions. If the call is rejected or the
   tool is absent, schedule the wakeup with a CronCreate one-shot instead:
   `CronCreate(cron="<minute> <hour> <dom> <month> *", recurring=false,
   prompt="<same re-entry prompt>")` pinned to the chosen cadence rounded up
   to the next minute. Do not silently drop a wakeup; if neither tool is
   available, log the state to the tracking bead and stop cleanly.

   On each wakeup:
   a. Poll `gh pr checks <PR-number>` for completion status.
   b. If checks still running: ScheduleWakeup again at the same cadence
      (max 3 waits total for check completion, then proceed with whatever
      has posted).
   c. Once checks complete (or after the third wait): fetch ALL THREE
      comment streams in parallel. Bots split across them; missing one
      means missing comments. See `memory/github-api.md`:
      - Inline review comments: `gh api repos/{owner}/{repo}/pulls/{N}/comments`
      - Issue-level comments: `gh pr view {N} --json comments,reviewDecision,statusCheckRollup`
      - Review summaries: `gh api repos/{owner}/{repo}/pulls/{N}/reviews`
   d. **Triage comments**:
      - **Actionable inline**: file path + line number + specific code concern
        (Copilot, Sentry, human reviewers on inline). Fix these.
      - **Actionable issue-level**: rare; usually a human reviewer asking a
        substantive question. Address if real.
      - **Informational**: metrics summaries (PR Metrics), status echoes
        (Mergify, Vercel deploy tables), generic "looks good", trend
        warnings without specific code refs, quality-gate-passed badges
        (SonarCloud). Log to bead, do not fix, do not reply.
   e. If actionable comments exist:
      1. Fix in worktree, run `pants check` / `pants test` on changed paths.
      2. Commit (HEREDOC + Co-Authored-By trailer; mention which bot/reviewer
         flagged the issue in the message).
      3. Push.
      4. **Reply to the comment thread inline** confirming the fix and the
         commit SHA: `gh api repos/{owner}/{repo}/pulls/{N}/comments/{comment_id}/replies`.
         This keeps the resolution visible inline rather than buried in
         the diff. Do NOT send "thanks" replies to status-only bots
         (Mergify, Vercel deploy tables, PR Metrics, SonarCloud) - those
         are noise.
      5. Log fix and reply IDs to bead.
      6. ScheduleWakeup for the next iteration to verify CI re-runs cleanly.
   f. If no actionable comments remain: report final status and end.

   Max 4 fix iterations. After that, report remaining items for human review.

3. **Final report**:

   ```
   ## Autopilot Complete (build mode)

   PR: [URL]
   Branch: [branch name]
   Beads: [list of bead IDs]

   Decision trail: [N] gate evaluations, [M] iterations, [K] bot fixes.
   Bot comments resolved: [list]
   Bot comments for human review: [list, or "none"]

   Review: `bd show <tracking-bead-id>` for full history.
   ```

## Escalation Protocol

When any decision gate returns ESCALATE:

1. **Persist state**: update the tracking bead description with:
   - Current phase and what was completed
   - The decision-maker's ESCALATE output (trigger, evaluate, state)
   - The converged plan (if past Gate 1)
   - The evidence trail
2. **Log**: `bd comment <tracking-bead-id> "ESCALATED at [gate]: [trigger]"`
3. **Report to user**:

   ```
   ## Autopilot Escalated

   **Gate**: [which gate]
   **Trigger**: [why escalation was needed]
   **What to evaluate**: [from decision-maker output]

   Current state saved to bead: <tracking-bead-id>
   Run `bd show <tracking-bead-id>` for full context.

   To resume after review: re-run /autopilot with the bead ID and any
   guidance as additional context.
   ```

4. **Stop**. Do not continue the pipeline. Do not attempt to resolve the
   escalation autonomously.

## Self-Reflection Trigger

After any of these events, pass feedback to the decision-maker for its
self-reflection protocol:

- A phase fails after a PROCEED decision (pants tlc failure, agent BLOCKED, etc.)
- Two consecutive ITERATE decisions target the same issue
- Bot comments flag something that should have been caught at Gate 2

Include the failure context in the decision-maker invocation:

```
Agent(
  subagent_type="mx2-decision-maker",
  prompt="""
  ## Self-Reflection Trigger

  Previous decision: PROCEED at [gate]
  Failure: [what happened]
  Context: [relevant details]

  Run your self-reflection protocol. If a new rule or example would
  have prevented this miss, emit calibration drift via bd remember per
  your Self-Reflection Protocol. Never attempt to edit the calibration
  file directly; calibration changes pass through the /calibrate human
  review gate by design, so the bd-remember channel is the only merge path.
  """
)
```

## Resumption

If a previous autopilot run was ESCALATED or interrupted:

1. Parse the bead ID from the input
2. `bd show <bead-id>` to load the saved state
3. Determine which phase to resume from based on the saved state
4. Continue the pipeline from that phase

This is a cold-start; treat the bead description as the authoritative state.

## Rules

- **No intermediate output to user.** Phases 1-5 are internal. The user sees
  the final report (Phase 7 or Phase 10) or an escalation notice.
- **Parallel is mandatory.** The Phase 4 Challenge subagent and all selected
  consult specialists MUST run in parallel via separate Agent tool calls in
  the same message (no coordinator subagent).
- **Beads are the audit trail.** Every decision, iteration, and escalation is
  logged as a bead comment. The tracking bead is the single source of truth.
- **Decision-maker is a subagent.** Always invoke via Agent tool with
  `subagent_type="mx2-decision-maker"`. Fresh context for unbiased judgment.
- **Each decision is independent.** If the artifact + evidence trail for a single
  decision is too large to evaluate without summarization, ESCALATE. Do not
  summarize to fit. If this happens frequently (>1% of decisions), the
  decomposition phase is producing items that are too large; fix decomposition.
- **ScheduleWakeup only for bot remediation.** The main pipeline runs
  synchronously. ScheduleWakeup is used in Phase 10 only, for waiting on
  CI checks and bot comments.
- **Existing skills are not modified.** This skill embeds challenge and consult
  protocols by reading their files at runtime, not by invoking /challenge or
  /consult as skills.
- **Max iterations are hard limits.** When reached, ESCALATE automatically.
  Do not extend limits. Do not "try one more time."
