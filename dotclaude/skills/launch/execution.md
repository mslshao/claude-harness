# Phase 5: Execution

Detailed procedure for the execution phase: durable-state initialization,
shared-worktree creation, agent spawning (narrow-mandate + lane-based
parallelism), the orchestration loop, completion verification, and the retry
loop. The SKILL.md Phase 5 section points here and keeps the load-bearing
invariants inline.

> **5.3 Standup Protocol** stays inline in SKILL.md; each agent file carries a
> role-tuned copy (see `_shared/launch-protocol.md` §Role-tuned variations).
> It is omitted here to avoid a third copy.

## 5.0: Durable State Initialization

The bead was already acquired at the END of Phase 1 (context-enrichment), not
here; by 5.0 `$LAUNCH_BEAD_ID` exists and is claimed. This step only verifies
the durable-state preconditions before creating the worktree.

**Contract** (full bash and conflict-handling logic in
[durable-state.md §Bead Acquisition](durable-state.md), which also covers the
rare direct-resume case where acquisition has not happened yet):
- `$LAUNCH_BEAD_ID` is set and the bead is claimed by this session.
- Conflicts (bead claimed by another session) were surfaced at acquisition
  time (optimistic locking; not a hard block, but the human safety gate).

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

## 5.1: Create Shared Worktree

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

## 5.2: Spawn Agents (Phase A)

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
- **Scope each agent's mandate to one file or one tightly-coupled concern.**
  A subagent accumulates context with every file it reads, tool it runs, and
  self-review it invokes. A mandate spanning several files or concerns risks the
  agent hitting context/token pressure and truncating BEFORE it emits its final
  standup. The work often lands on disk, but the summary is lost and the
  orchestrator must recover from the diff. Prefer N agents each owning one
  file/concern over one agent owning N: for a tester, one test file (or one
  behavior cluster) per dispatch; for an implementer, one cohesive change per
  dispatch. Parallelize the narrow dispatches in a single message when
  independent; sequence them when dependent. This does NOT change the
  one-worktree rule (all narrow dispatches still share the Phase 5.1 worktree).

**Lane-based parallelization.** The narrow-mandate rule is not only about
truncation; it is the unit of parallelism. Decompose the build into atomic
pieces and give each agent a clearly-scoped lane (a file, a module, a layer).
Lanes that do not overlap run fully in parallel (single-message dispatch). When
two pieces DO overlap (shared file, shared interface), do not let two agents
write the same region: serialize the overlapping pieces, then assign ONE agent
the integration/middleware seam between them once the pieces land. Maximize
parallelism across non-overlapping lanes; serialize only the true conflicts.
All lanes share the one Phase 5.1 worktree, so an integration agent sees the
prior pieces already on disk.

**Mandate-scoping recurrence context.** 2026-05-29 MX2-NNNNN / docr-0wf0: a
single tester given a 4-file mandate (enum + settings + span + metric tests)
truncated at ~147K tokens / 55 tool-uses mid-write of the last file. The test
files landed but the final standup did not, and the orchestrator recovered by
inspecting the worktree (per the truncated-subagent-result rule) and finishing
the residual lint directly. Subagent `maxTurns` is unset on the launch agents
(no hard turn cap), so the limiter is context accumulation, not turns: narrower
mandates are the lever, not a `maxTurns` bump.

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

## 5.4: Orchestration Loop

While agents are running, you are actively:

1. **Reading output files** - tail agent output for detailed progress beyond standups
2. **Processing standups** - parse DONE/NEXT/BLOCKED/RISK from each agent
3. **Proactive unblocking** - when a standup reports BLOCKED, RISK, or
   `checkpoint-review-requested: <specialist> on <scope>`:
   - Spawn the requested/relevant specialist sub-agent with the blocking context
     (agents cannot dispatch specialists themselves; you own all dispatch)
   - Wait for specialist result
   - Route findings back via the bead-comment channel: `bd comment <bead-id>
     "[orchestrator guidance] From [specialist]: [findings]"`. Agents poll
     comments at checkpoints. (SendMessage only continues a COMPLETED agent;
     it cannot deliver mid-run guidance.)
4. **SCOPE-CHECK adjudication** - when an implementer emits a SCOPE-CHECK
   standup (predicted >~250 lines added):
   - Apply the concern-split test: does the work map to multiple ratified
     design decisions (two tickets, two beads, two AC sets), or one?
   - Reply via `bd comment <bead-id> "[orchestrator] ORCHESTRATOR-PROCEED"`
     or `"[orchestrator] ORCHESTRATOR-SPLIT: <re-scoped work items>"`.
   - The implementer polls for this and defaults to proceed-as-planned after
     2 unanswered polls; answer promptly to keep the gate meaningful.
5. **Checkpoint gating** - when all Phase N agents complete (or checkpoint):
   - Run the gate verification command from the plan's `gate_cmd` field
   - If met: write `PHASE_GATE_PASSED` event to bead, then spawn Phase N+1 agents
     with Phase N outputs as context (use the Retry Loop in 5.6 for each slot)
   - If not met: invoke the Retry Loop (5.6) for the specific agent slot that
     owns the failed criteria - do not re-run agents that passed
   - **After each phase gate**: prune standup accumulation from your context by
     retaining only the final DONE summary per agent. Drop intermediate standups.
     This limits context growth across multi-phase executions.
6. **Scope creep handling** - when an agent reports out-of-scope work:
   - Gather details from the agent's standup/output
   - Create a linked Jira ticket via `/jira` with enough context for a
     future cold-start `/launch` invocation
   - Tell the agent: "Out of scope. Created MX2-XXXXX for follow-up. Continue
     with the current plan."
7. **Escalation** - stop and ask the user when:
   - An agent needs external verification (Superset query, Datadog dashboard,
     log check) that tools can't provide
   - 3 failed attempts on the same issue (circuit breaker)
   - The plan was wrong (tests reveal the approach doesn't work)

## 5.5: Agent Completion

When all phases complete (all `PHASE_GATE_PASSED` events written for every phase
in the plan), verify final worktree state:
1. Confirm all acceptance criteria are met by re-running gate verification commands
2. If any criterion is unmet at this stage, it means the retry loop exhausted or
   was bypassed - escalate to the user with the specific failure

## 5.6: Retry Loop

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
