---
name: launch
description: >
  Execution launcher: takes a Jira ticket or bead, enriches context, converges on
  a plan, then dispatches an agent team to BUILD it - producing real commits and a
  draft PR. The key distinction from /converge: launch writes code, converge writes
  a plan. Use when the ticket is well-scoped and you want hands-off implementation.
  Multiple invocations run in parallel via worktrees.
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

## Phase 1: Context Enrichment

See [context-enrichment.md](context-enrichment.md) for the full protocol.

**Summary**: Fetch the Jira ticket, discover related beads, read relevant source
files, then dispatch `prompt-refiner` in headless mode. Output is a 200-400 word
**implementation brief** that becomes the seed for Phase 2.

All tool calls in this phase run in parallel where possible. Do not show
intermediate output to the user.

## Phases 2-3: Plan Pipeline (Internal)

Run the converge-style plan pipeline against the implementation brief: refine
plus decompose plus pipeline-reuse gate (Phase 2), then challenge plus consult
in parallel (Phase 3a/3b), then synthesize plus parallelization strategy
(Phase 3c). Output is an internal converged plan + parallelization-strategy
YAML; not shown to the user yet.

**Load-bearing invariants:**
- Challenge and consult MUST run as parallel subagents in a single Agent-tool
  message. Serializing defeats the purpose.
- Phase 3c output is the **parallelization strategy** (agent roster, phasing,
  checkpoint gates, agent inputs), not just a converged plan. Phase 4 consumes
  this directly.
- Every checkpoint gate must be programmatically verifiable (e.g., "pants check
  passes" not "implementation complete").

For the full subagent prompt templates, the parallelization-strategy YAML
schema, and example phase diagrams, see [plan-pipeline.md](plan-pipeline.md).

## Phase 4: Approval Gate

**First output the user sees.** Present the converged plan:

```markdown
## Launch Plan: [topic, 3-8 words]

### Summary
[2-5 sentences: what this builds, design decisions, key constraints]

### Convergence Delta
> [What changed during stress-testing. 2-4 bullets showing modifications
> from challenge/consult. Honest - say "no significant changes" if clean.]

### Work Items
[For each item in dependency order:]

#### [N]. [Title]
**Type**: [task/feature/bug]
**Agent**: [implementer | tester | flex-{role}]
**Phase**: [A | B | C | ...]
**Depends on**: [item numbers or "none"]

[Description: 2-4 sentences.]

**Acceptance criteria:**
- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

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
[FRAGILE/UNVERIFIABLE assumptions the user should confirm. Omit if none.]

---

**Approve?** Reply "yes" to start execution, or provide feedback to revise.
```

**This is a hard stop.** Do not proceed to Phase 5 without explicit human approval.
If the user provides feedback, revise and re-present. Max 2 revision rounds - if
more changes are needed, suggest the user provide consolidated feedback.

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
**Graphite**: https://app.graphite.dev/github/pr/lawfirm/main/[number]
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

- **No intermediate output during phases 1-3.** Phase 4 is the first thing the user sees.
- **Hard stop at phase 4.** No execution without explicit human approval.
- **You are the orchestrator.** Don't spawn an orchestrator agent. Stay active, steer, unblock.
- **Shared worktree.** One worktree for all agents. No per-agent isolation.
- **Standup protocol is mandatory.** Every agent checks in after every logical unit.
- **Specialists are ephemeral.** Spawn them for review at checkpoints, don't persist them.
- **Draft PR always.** Never create a ready-for-review PR.

## Additional Resources

- [context-enrichment.md](context-enrichment.md) - Phase 1 protocol
- [plan-pipeline.md](plan-pipeline.md) - Phases 2-3 protocol
- Agent templates: `~/.claude/agents/launch-implementer.md`, `launch-tester.md`, `launch-flex.md`
- PR creation: `/pr` command in `.claude/commands/pr.md`
- Jira tickets: `/jira` command in `.claude/commands/jira.md`
