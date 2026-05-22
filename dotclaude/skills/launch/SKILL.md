---
name: launch
description: >
  Execution launcher: takes a Jira ticket, bead, Slack thread, Confluence
  rough-draft, or free text and dispatches an agent team to BUILD it,
  producing real commits and a draft PR. Pipeline: enrich context, classify
  INPUT_MODE (problem-framed vs mechanism-prescribed), converge on a plan
  with challenge + consult stress-test, mandatory tenth-man pass, and
  decision-maker proceed/iterate gate before user approval. Detects when
  the ticket prescribes a mechanism that should have been a feature of an
  existing noun (Fulfillment-vs-Coverage protection). The key distinction
  from /converge: launch writes code, converge writes a plan. Use when the
  ticket is well-scoped and you want hands-off implementation. Multiple
  invocations run in parallel via worktrees. For divergent approach
  generation before a plan exists, use /ideate. For planning only with no
  code, use /converge. For root cause investigation, use /investigate.
argument-hint: "[MX2-XXXXX | docr-XXXX | description] [--skip-checks]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "Write", "Edit", "WebFetch"]
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

If no identifier is found, stop and ask the user for a Jira ticket number.

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
[Phase 3.5: Tenth-Man Lens]           |
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
[Phase 6: Finalization]       /review fan-out + bot-review + PR creation.

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
  consult + tenth-man + decision-maker gate), then continues into
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
in parallel (Phase 3a/3b), then synthesize (Phase 3c), then tenth-man lens
(Phase 3.5), then decision-maker gate (Phase 3.6). Output is an internal
converged plan + parallelization-strategy YAML + iteration log; not shown to
the user yet.

**Load-bearing invariants:**
- Challenge and consult MUST run as parallel subagents in a single Agent-tool
  message. Serializing defeats the purpose.
- Phase 3c output includes the DELTA_CATEGORY label (CONFIRMED /
  MINOR_ADJUSTMENTS / MAJOR_REVISIONS / SCRAPPED_AND_REBUILT). CONFIRMED on
  a non-trivial `mechanism-prescribed` input is suspicious; Phase 3.6 gate
  fires ITERATE with WEAK_DIMENSION=mechanism when it sees that pattern
  (canonical Fulfillment-vs-Coverage protection).
- Phase 3.5 Tenth-Man Lens is mandatory. Runs `mx2-tenth-man` on the
  converged plan with the DELTA_CATEGORY and INPUT_MODE as input. Output
  folds into Phase 4 as a `Tenth-Man Lens` block. If dispatch fails, note
  "Tenth-Man Lens unavailable" and proceed; do not silently drop.
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
[plan-pipeline.md](plan-pipeline.md). For the Phase 3a + 3b Challenge
and Consult subagent prompt templates (with INPUT_MODE-aware framing),
see [stress-test-prompts.md](stress-test-prompts.md). For the Phase 3.5
Tenth-Man Lens dispatch + the Phase 3.6 Decision-Maker Gate dispatch +
branch logic + caps + iteration log format, see
[gate-prompts.md](gate-prompts.md).

## Phase 4: Approval Gate

**First synthesis-level output the user sees** (the only earlier user-facing
output is the narrowing questions from a Phase 3.6 ESCALATE-QUESTIONS, when
fired). Present the converged plan:

```markdown
## Launch Plan: [topic, 3-8 words]  (low-confidence)?

[Suffix `(low-confidence)` on the H2 IF the Phase 3.6 gate forced a
low-confidence PROCEED (2 ITERATE rounds hit the cap, or user opted out
of ESCALATE-QUESTIONS with "you decide"). Add a "Low-confidence reason:"
line at the end of Summary stating which path triggered it.]

### Summary
[2-5 sentences: what this builds, design decisions, key constraints]

### Iteration Log
[Always present even when Round 0 was final, so the user sees the gate
ran. List each round with verdict + action taken:]
- Round 0 (initial): N work items drafted; DELTA_CATEGORY=<X>.
- Round 1 (if any): VERDICT (REASON). Action: <what changed>.
- Round 2 (if any): VERDICT (REASON). Action: <what changed>.
- Final verdict: PROCEED | LOW-CONFIDENCE | ESCALATE-ROUTE.

### Convergence Delta  [CATEGORY: CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT]
> [What changed during stress-testing. 2-4 bullets showing modifications
> from challenge/consult. The CATEGORY tag is load-bearing: CONFIRMED
> means specialists agreed with concrete evidence (not punted);
> MAJOR_REVISIONS or SCRAPPED_AND_REBUILT means the original framing
> did not survive.]

### Prior Thinking Comparison  [only when INPUT_MODE = mechanism-prescribed]
[Surface how the converged plan compares to the ticket's prescribed
mechanism. One of:
- "Specialists agreed the prescribed mechanism is right. <Brief evidence.>"
- "Specialists refined the prescribed mechanism: <what changed>"
- "Specialists recommended a different mechanism: <X>. <Why.>"
- "Specialists recommended scrapping the prescribed mechanism: it
  should be folded into <Y> as a feature of <Y>, not a new noun."
  (canonical Fulfillment-vs-Coverage outcome)
This section makes mechanism-vs-feature decisions visible BEFORE the
agent team starts writing code. Omit when INPUT_MODE = problem-framed.]

### Tenth-Man Lens
[Verbatim 🔻 block from Phase 3.5. Always present (the pass is
mandatory). If returned "🔻 No concerns from this lens", include that
line verbatim so the user sees the pass ran.]

### Work Items
[For each item in dependency order:]

#### [N]. [Title]
**Type**: [task/feature/bug]
**Agent**: [implementer | tester | flex-{role}]
**Phase**: [A | B | C | ...]
**Context**: [greenfield | legacy | hybrid]
**Depends on**: [item numbers or "none"]

[Description: 2-4 sentences.]

**Acceptance criteria:**
- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

**Verification path:** [How the implementer (and orchestrator at
checkpoint gating) will know this is correct BEFORE committing. Cite
specific test, command, or pattern. 1-2 sentences.]

**Consequence of wrong:** [low | med | high. If high, must have a
matching Verification path OR explicit risk-reduction note.]

---

### Agent Roster
| Agent | Role | Phase | Specialist access |
|-------|------|-------|-------------------|
| implementer | [scope] | [phase] | mx2-code-reviewer, mx2-silent-failure-hunter |
| tester | [scope] | [phase] | test-quality-reviewer, /test-forge |
| flex-infra | [scope] | [phase] | mx2-devops-build-deploy |

### Phasing
[Phase diagram with gates:]
Phase A: [agents] → Gate: [criteria] → Phase B: [agents] → ...

### Commit Strategy
[One commit | N commits at behavior boundaries. Explain the gates.]

### Open Assumptions
[FRAGILE/UNVERIFIABLE assumptions the user should confirm. Include any
mixed-input disagreements from Phase 1. Omit only if none.]

---

### OR: Escalation: No Agent Team Dispatched  [only when final verdict was ESCALATE-ROUTE]
[Replaces the Work Items / Agent Roster / Phasing / Commit Strategy
sections when the Phase 3.6 gate fired ESCALATE-ROUTE. 2-3 sentences
naming the SUGGESTED_NEXT_SKILL and the reason no agent team is being
dispatched. Format:

"The launch gate fired ESCALATE-ROUTE: <reason from gate>. No agent
team is being dispatched; the suggested next step is
<SUGGESTED_NEXT_SKILL: /converge, /ideate, or /investigate>. The draft
work items are preserved above for reference, but /launch is not the
right tool for this ticket yet."

The Iteration Log + Convergence Delta + Prior Thinking Comparison +
Tenth-Man Lens are still shown so the user understands WHY the gate
refused to launch.]

---

[When final verdict is PROCEED or LOW-CONFIDENCE:]
**Approve?** Reply "yes" to start execution, or provide feedback to revise.

[When final verdict is ESCALATE-ROUTE (replaces "Approve?" line):]
**No agent team will be dispatched.** Run the suggested next skill
(`<SUGGESTED_NEXT_SKILL>`) instead, or provide feedback if you believe
`/launch` is still the right tool here.
```

**This is a hard stop.** Do not proceed to Phase 5 without explicit human approval.
If the user provides feedback, revise and re-present. Max 2 revision rounds - if
more changes are needed, suggest the user provide consolidated feedback.

When the gate fired ESCALATE-ROUTE, "approval" is not the operative action;
the user is being told /launch is the wrong skill for this ticket. The
template above conditionalizes the final prompt accordingly.

## Phase 5: Execution

**You (the primary Claude session) are the orchestrator.** You have the full plan
context, you spawned the agents, you steer the work. Do not be idle.

### 5.0: Durable State Initialization

Before creating the worktree, establish the bead-based event log target.

**Contract** (full bash and conflict-handling logic in
[durable-state.md §Bead Acquisition](durable-state.md)):
- For Jira-ticket launches: find existing bead by ticket ID, or create one.
- For bead-ID launches: `$LAUNCH_BEAD_ID` is the input argument directly.
- Surface conflicts when the bead is already claimed by another session
  (optimistic locking; not a hard block, but the human safety gate).
- Claim the bead for this session via `bd update --claim`.

After acquisition, store `$LAUNCH_BEAD_ID` and check for a prior session:
```bash
PRIOR=$(bd show "$LAUNCH_BEAD_ID" --json | jq -r '.[] | .notes // ""' | grep 'LAUNCH_EVENT')
```
- If `PRIOR` is non-empty: run the Cold-Start Protocol in `durable-state.md`. Do not
  proceed to 5.1 - cold-start handles worktree recovery and phase resumption.
- If empty: write session start and proceed to 5.1.

```bash
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_EVENT type=SESSION_STARTED session=$CLAUDE_SESSION_ID ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

### 5.1: Create Shared Worktree

```bash
WORKTREE_BASE="/workspaces/main/.launch-worktrees"
mkdir -p "$WORKTREE_BASE"
WORKTREE_DIR="$WORKTREE_BASE/launch-$(date +%s)"
BRANCH="launch-$(date +%s)"
git worktree add "$WORKTREE_DIR" -b "$BRANCH" origin/HEAD 2>&1
```

**Path constraint**: WORKTREE_BASE must be outside `.git/`. Claude Code treats
`.git/` as a protected directory - Edit/Write tools are blocked there regardless
of permission mode. Agents can Read but never write. This is not overridable via
`mode: "bypassPermissions"` (that controls approval prompts, not tool availability).

Verify: `git -C "$WORKTREE_DIR" log -1 --oneline`

After successful creation, write durability events and store metadata:
```bash
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_EVENT type=WORKTREE_CREATED branch=$BRANCH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
bd update "$LAUNCH_BEAD_ID" --set-metadata launch_branch="$BRANCH"
bd update "$LAUNCH_BEAD_ID" --set-metadata launch_worktree="$WORKTREE_DIR"
```

All agents work in this single worktree. Do NOT use `isolation: "worktree"` on
agent spawns - that creates per-agent worktrees with no coordination.

### 5.2: Spawn Agents (Phase A)

For each agent in Phase A, use the Retry Loop protocol from
[durable-state.md](durable-state.md) rather than spawning directly. The retry
loop handles the `AGENT_SPAWNED` event write, the Agent tool call, verification,
and retry logic in one coherent block.

Key rules for agent spawn prompts:
- `name`: addressable name (e.g., "implementer", "tester", "flex-infra")
- `run_in_background: true`
- `prompt`: includes worktree path, work items, acceptance criteria, standup
  protocol, RETRY_CONTEXT block if `iteration >= 2`, **and the bead ID** (so
  the agent's bead-comment polling channel engages; see "Mid-flight Updates
  from User" in `~/.claude/agents/launch-*.md`). Mention the bead ID
  prominently (e.g., "BEAD: docr-XXXX" or "Working on bead `docr-XXXX`").

**User-facing channel**: while agents are running, the user can leave comments
on the bead via `bd comment <bead-id> "..."` to send course corrections, scope
changes, or stop instructions. Spawned launch-* agents poll their bead at
verification/commit/push checkpoints. This is the canonical real-time
communication channel during long-running parallel work.

**Write `AGENT_SPAWNED` to bead BEFORE the Agent tool call** (Temporal pattern).
If the orchestrator dies after the write but before the agent completes, cold-start
treats it as in-flight and increments the iteration count on resume.

Launch all Phase A agents in a **single message** (parallel dispatch) on iteration 1.
On retries, agents are spawned sequentially per slot (the retry loop serializes).

### 5.3: Standup Protocol

Every agent template includes this check-in contract:

```
After every logical unit of work (function implemented, test file written,
config file created), send a standup to the orchestrator via SendMessage:

STANDUP:
  DONE: [what you just completed - be specific: file, function, test name]
  NEXT: [what you're about to work on]
  BLOCKED: [anything preventing progress, or "none"]
  RISK: [anything that might block you soon, or "none"]
```

### 5.4: Orchestration Loop

While agents are running, you are actively:

1. **Reading output files** - tail agent output for detailed progress beyond standups
2. **Processing standups** - parse DONE/NEXT/BLOCKED/RISK from each agent
3. **Proactive unblocking** - when a standup reports BLOCKED or RISK:
   - Spawn the relevant specialist sub-agent with the blocking context
   - Wait for specialist result
   - Route findings back via SendMessage: "Guidance from [specialist]: [findings]"
4. **Checkpoint gating** - when all Phase N agents complete (or checkpoint):
   - Run the gate verification command from the plan's `gate_cmd` field
   - If met: write `PHASE_GATE_PASSED` event to bead, then spawn Phase N+1 agents
     with Phase N outputs as context (use the Retry Loop in 5.6 for each slot)
   - If not met: invoke the Retry Loop (5.6) for the specific agent slot that
     owns the failed criteria - do not re-run agents that passed
   - **After each phase gate**: prune standup accumulation from your context by
     retaining only the final DONE summary per agent. Drop intermediate standups.
     This limits context growth across multi-phase executions.
5. **Scope creep handling** - when an agent reports out-of-scope work:
   - Gather details from the agent's standup/output
   - Create a linked Jira ticket via `/jira` with enough context for a
     future cold-start `/launch` invocation
   - Tell the agent: "Out of scope. Created MX2-XXXXX for follow-up. Continue
     with the current plan."
6. **Escalation** - stop and ask the user when:
   - An agent needs external verification (Superset query, Datadog dashboard,
     log check) that tools can't provide
   - 3 failed attempts on the same issue (circuit breaker)
   - The plan was wrong (tests reveal the approach doesn't work)

### 5.5: Agent Completion

When all phases complete (all `PHASE_GATE_PASSED` events written for every phase
in the plan), verify final worktree state:
1. Confirm all acceptance criteria are met by re-running gate verification commands
2. If any criterion is unmet at this stage, it means the retry loop exhausted or
   was bypassed - escalate to the user with the specific failure

### 5.6: Retry Loop

Per-agent retry loop with circuit breaker. Applied for every agent slot in every
phase. Full algorithm in [durable-state.md §Retry Loop Protocol](durable-state.md).

Key properties:
- Max 3 iterations per `(agent, phase)` slot - circuit breaker escalates to user
- Iteration count derived from `AGENT_FAILED` events in bead (survives cold-start)
- `AGENT_SPAWNED` written BEFORE the Agent tool call (Temporal pre-execution journal)
- On iteration 2+, agent receives `RETRY_CONTEXT` block with: prior commit list,
  exact failure output (500 char truncated), files to not touch, and an
  orchestrator-synthesized specific directive naming the exact fix needed
- Phase gate event written only after ALL agents in the phase pass verification

## Phase 6: Finalization

### 6.1: Verification

Run `pants tlc` against all changed targets in the worktree (skip if
`--skip-checks` was passed). Route failures to the responsible agent:
- Lint/style failures -> implementer or flex agent that wrote the code
- Test failures -> tester (if test is wrong) or implementer (if code is wrong)
- Type errors -> whoever introduced the untyped code

Iterate until clean or circuit breaker (3 attempts).

### 6.2: Commits

Apply the commit strategy from the approved plan:
- **Small tasks**: one commit with a clear message
- **Larger tasks**: separate commits at behavior boundaries, each with a message
  documenting the behavior contract of that commit state

Commit messages include the Jira ticket ID: `[MX2-XXXXX] <description>`

### 6.2.4: /review Fan-Out (broad pre-PR gate)

After commits land on the worktree branch and BEFORE the bot-review pass,
invoke the `/review` skill against the worktree diff. `/review` dispatches
four project review agents in parallel (`code-reviewer` for structural design,
`test-quality-reviewer` for behavioral test quality, `observability-reviewer`
for instrumentation gaps, `silent-failure-hunter` for error propagation),
deduplicates overlapping findings, and produces a severity-grouped report.

Distinct from 6.2.5: `/review` is the broad gate (4-agent fan-out, runs on
every diff, can emit CRITICAL/WARNING). `bot-review` is the cross-file
blast-radius specialist (runs only when public surface changes, hard-capped
at COMMENT/NOTE/SUGGESTION). Both are advisory; PR creation proceeds
regardless of findings. The operator reads both before flipping the PR
from draft to ready and resolves CRITICAL/WARNING items before publishing.

Invocation: from the worktree directory so `git diff origin/main..HEAD` is
the natural scope, then:

```
Skill(skill="review")
```

Post the report to the tracking bead:

```bash
bd comment <tracking-bead-id> "[/review report: PR-pending]

<skill output>"
```

If `/review` returns CRITICAL findings, surface them to the operator in the
Phase 6.5 report under a `### /review CRITICAL findings` header so they are
not missed in the bot-review noise.

### 6.2.5: bot-review Advisory Pass

After 6.2.4 completes and BEFORE PR creation, dispatch `bot-review` on the
worktree diff. Output is posted to the tracking bead as advisory commentary;
PR creation proceeds regardless of findings.

Skip when the diff has no public-symbol changes. Compute the
`changes_public_surface` signal per `~/.claude/skills/pr-intel/SKILL.md` Dispatch
Signals; if false, post `bd comment <tracking-bead-id> "[bot-review advisory:
PR-pending] skipped (no public surface change)"` and proceed to 6.3.

When dispatched:

```
Agent(
  subagent_type="bot-review",
  prompt="""
  REPO STATE: Worktree at $WORKTREE_DIR. Use as <code_root>.

  SCOPE: full diff in the worktree (origin/main..HEAD).

  Apply the verbatim three-citation gate from your agent definition. Severity
  vocabulary is COMMENT/NOTE/SUGGESTION only. Output FINDING blocks or no-findings
  line.

  Diff:
  [git -C "$WORKTREE_DIR" diff origin/main..HEAD]

  Changed file paths:
  [file path list]
  """
)
```

Post the agent's output to the tracking bead:

```bash
bd comment <tracking-bead-id> "[bot-review advisory: PR-pending]

<agent output>"
```

Strict advisory: `bot-review`'s severity hard-bar (COMMENT/NOTE/SUGGESTION only)
guarantees the output cannot block PR creation. The user reads the advisory
before flipping the PR from draft to ready.

### 6.3: PR Creation

Always run from the worktree. Never check out the launch branch in the main
workspace. Two sub-paths depending on whether the launch is **independent**
(worktree off `origin/HEAD` / main; default) or **dependent** (worktree off a
non-main parent branch; stacked launch on top of an unmerged parent PR).

> **Em-dash guard**: `~/.claude/hooks/block-em-dash.sh` scans `gh pr create`,
> `gh api -X POST/PUT/PATCH`, `gh pr comment`, `gh pr review`, and `gh issue
> comment` for U+2014 and blocks on match. `gt submit` shells out to `gh`, so
> the same constraint applies. Sanitize the PR body file before invoking
> either path.

**Step 1: Determine the base branch.** Read the worktree's branch parent:
```bash
BASE_BRANCH=$(git -C "$WORKTREE_DIR" rev-parse --abbrev-ref --symbolic-full-name @{upstream} 2>/dev/null | sed 's|^origin/||' \
  || git -C "$WORKTREE_DIR" log --pretty=%D origin/HEAD..HEAD --decorate=full 2>/dev/null | grep -oE 'origin/[^,)]+' | head -1 | sed 's|^origin/||' \
  || echo "main")
```
For a standard non-stacked launch (worktree created from `origin/HEAD` in Phase 5.1)
this resolves to `main`. For stacked launches (worktree created from another branch)
it resolves to that parent. Defaults to `main` if detection fails.

**Step 2: Build the PR body file.** Build `/tmp/pr-body-<branch>.md` BEFORE
invoking either submit path. Read the repo's PR template FIRST
(`<repo>/pull_request_template.md` or `<repo>/.github/PULL_REQUEST_TEMPLATE.md`)
and use its structural skeleton (H1 sections, `Jira issue link:` line,
`# Checklist` items filled out, `Require-reviewers: all` line). Layer the personal
style rules from `memory/pr-template.md` on top (H2 subsections within Summary,
Jira link at the bottom, no hard line-wrapping, clickable markdown links).
Skipping the repo template breaks Mergify's checklist-fill protection and produces
a PR description that does not match the team's structural standard. See the
recurrence note in `~/.claude/CLAUDE.md` PR descriptions rule for the 2026-04-29
instance.

**Step 3: Submit the PR (path depends on Step 1).**

**Path A: Independent launch (`BASE_BRANCH == "main"`).** Raw `gh` is fine. The
PR has no parent relationship to register, and Graphite tracking adds no value.
```bash
cd "$WORKTREE_DIR"
git push -u origin HEAD
gh pr create --draft \
  --title "[MX2-XXXXX] <description>" \
  --body-file /tmp/pr-body-<branch>.md
```

**Path B: Dependent launch (`BASE_BRANCH != "main"`).** Use `gt` so the stack
relationship is registered with Graphite. Without this, the GitHub-level base
branch is set correctly (so reviewers see only the new delta), but Graphite is
unaware: `gt log short` won't show the stack, and `gt restack` / `gt sync` won't
operate on it. Recurrence context: 2026-05-08 PR #8971 silent-failure-hunter
launch shipped via Path A and required retroactive `gt track` cleanup.
```bash
cd "$WORKTREE_DIR"
gt track --parent "$BASE_BRANCH"
gt submit --stack --no-interactive --draft \
  --body-file /tmp/pr-body-<branch>.md
```
- `gt track` is forbidden in the main checkout (CLAUDE.md), allowed in worktrees
  under the worktree exception.
- `gt submit --stack` submits this branch and any tracked ancestors that haven't
  been submitted yet, sets the PR base to the tracked parent automatically, and
  pushes with `-u`. On already-submitted parent PRs it re-pushes commits but does
  not clobber existing PR description bodies (verified 2026-05-09 launch-sfh).
- `--draft` matches the "draft PR always" rule below.

**Step 4: Capture the PR URL** for the report in 6.5:
```bash
PR_URL=$(gh pr view --json url --jq .url)
```

### 6.4: Cleanup

```bash
git worktree remove "$WORKTREE_DIR" --force 2>&1 || \
  (rm -rf "$WORKTREE_DIR" && git worktree prune)
```

### 6.5: Report

Present to the user:
```markdown
## Launch Complete: [topic]

**PR**: [URL] (draft)
**Graphite**: https://app.graphite.dev/github/pr/<org>/<repo>/[number]
**Branch**: [branch-name]
**Jira**: [MX2-XXXXX]

### What was built
[2-4 sentences summarizing what the agents implemented]

### Agents dispatched
[Agent roster with what each did]

### Scope creep tickets
[MX2-YYYYY, MX2-ZZZZZ, or "none"]

### Suggested next steps
- [ ] Review the PR on Graphite
- [ ] Run `/pr-intel [number] --mine` for self-review
- [ ] Publish when ready
```

## Escalation Protocol

| Trigger | Action |
|---------|--------|
| Agent BLOCKED, specialist can help | Spawn specialist, route findings back |
| Agent BLOCKED, needs external verification | Ask user (Superset, Datadog, logs) |
| 3 failures on same issue | Stop, report what was tried, ask user |
| Plan was wrong | Stop, explain what the tests/code revealed, suggest revised approach |
| Scope creep discovered | /jira to create linked ticket, continue with current plan |

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
- **Tenth-man is mandatory.** Phase 3.5 runs always. If the dispatch
  fails, note "Tenth-Man Lens unavailable" and proceed; do not silently
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
- [stress-test-prompts.md](stress-test-prompts.md) - Phase 3a Challenge + Phase 3b Consult subagent prompts (INPUT_MODE-aware)
- [gate-prompts.md](gate-prompts.md) - Phase 3.5 Tenth-Man Lens + Phase 3.6 Decision-Maker Gate dispatch prompts, branch logic, iteration caps, iteration log format
- [durable-state.md](durable-state.md) - Phase 5 event log, cold-start protocol, retry loop
- Agent templates: `~/.claude/agents/launch-implementer.md`, `launch-tester.md`, `launch-flex.md`
- PR creation: `/pr` command in `.claude/commands/pr.md`
- Jira tickets: `/jira` command in `.claude/commands/jira.md`
