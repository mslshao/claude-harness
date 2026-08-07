---
name: campaign
description: >
  Walk-away epic runner: takes an epic whose PR-sized node beads were
  pre-converged by ONE up-front human /converge, and drives /launch per node
  unattended (--gate=agent), producing a chain of stacked draft PRs with
  crash-resumable cursor state. Use when a multi-ticket epic is fully planned
  and you want to kick it off and leave: "run the campaign for <epic>",
  "campaign docr-XXXX", "execute the epic unattended", "walk-away build the
  stack". Does NOT plan or converge (input must be pre-converged; use
  /converge first, /ideate before that); does NOT run single tickets (that is
  /launch); does NOT merge, flip drafts ready, or perform terminal Jira
  transitions (human-owned); sequential nodes only in v1 (no parallel DAG
  branches). Born from the 2026-07 epic-runner pilot + ideate docr-9bp1b.
argument-hint: "[epic bead | MX2 epic | node-bead list] [--abandon] [--dry-run]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Skill", "ScheduleWakeup", "PushNotification"]
---

# Campaign

Sequences an epic's pre-converged node beads through `/launch` unattended.
One human `/converge` happens BEFORE this skill runs; `/campaign` adds no
planning, no judgment about WHAT to build, and no new execution machinery:
each node runs through `/launch`'s own pipeline (bypass -> agent approval ->
agent team -> draft PR) inline in this session. What `/campaign` owns is only
the epic layer: node ordering, stack bases, cursor durability, halt/abandon
semantics, and the run report.

Decision record: `docr-1vqfg`. Plan lineage: ideate `docr-9bp1b` -> converge
2026-07-17. Drills gate: `docr-k8l6y` (core-3 green before any real epic).

## When NOT to invoke

| Instead | When |
|---|---|
| `/launch <ticket>` | One ticket, or you will be present to approve. |
| `/converge` | The epic is not decomposed into pre-converged node beads yet. |
| `/ideate` | You do not know which mechanism to pursue at all. |
| A teammate's recipe (internal Confluence page) | You want the human-in-the-loop variant: same shape, human clicks per node. |

## Input contract (hard preconditions)

- An epic bead (or explicit node-bead list). Node beads are connected by
  `bd dep` blocked-by links encoding the real order.
- EVERY node bead is bypass-shaped per `launch/SKILL.md` "Bypass:
  pre-converged input": (a) work-item scope with file targets, (b) acceptance
  criteria, (c) verification path, (d) consequence-of-wrong. The construction
  gate (below) verifies this and applies the `decision:` label; it does not
  waive it. A node bead that says "implement the design" is a construction
  failure, not something to improvise around.

## 1. Preflight (every invocation, idempotent)

1. Identities: `gh auth status`, `git config user.name` (live, never cached).
2. Find or create the **epic-cursor bead**: `bd list --label=campaign-state
   --status=all --json`, matched on this epic's id in the title. Create on
   first run (`--type=task --priority=3 --label=campaign-state`; title
   `campaign: <epic-id> cursor state`). NOTE: `campaign-state` is the runtime
   label; planning beads use the `campaign` label. Never conflate them.
3. **Termination gate** (runs BEFORE any mutation, on every entry including
   queued ScheduleWakeup fires): read cursor state from the bead notes.
   - `ABANDONED`: stop immediately, no output beyond one line. Only a human
     editing the state resurrects an abandoned campaign; wakeups and bare
     re-invocations never do.
   - `HALTED`: re-derive the blocking node's status from its bead events. If
     the blocker is still failed/needs_human, re-halt QUIETLY (no repeat
     notification; the transition already notified). If the human resolved
     it, clear HALTED and continue.
   - `COMPLETE`: report the prior run's report pointer and stop.
4. **Single-writer lock**: cursor state carries `writer_session` +
   `writer_ts`. If another session's `writer_ts` is fresher than 45 minutes,
   the campaign is live elsewhere: stop and surface. Takeover (stale writer)
   additionally requires checking the in-flight node's launch bead Step 4e
   lock before re-driving anything; a live inner launch converts takeover
   into a loud halt, never a re-drive. Refresh `writer_ts` on every state
   write (heartbeat). The 45-minute threshold is deliberately longer than
   launch's 30-minute Step 4e window so the inner lock always expires first.

## 2. Construction gate (attended, at kickoff)

For every node bead, verify the four bypass elements are present and apply
the `decision:` label (`bd label add <node> decision`). Derive the DAG from
`bd dep` links; detect cycles. On ANY deficiency: fail loudly listing every
deficient bead and the missing element, and STOP. This is the last attended
moment; a malformed bead that slipped through would silently fall through
launch's bypass into a full unattended re-converge, which is the exact
incoherence failure this design exists to prevent.

`--dry-run` stops here, printing the derived order, stack bases, and per-node
verification summary without invoking anything.

## 3. Cursor state (single JSON blob in the cursor bead's notes)

```json
{
  "epic": "docr-XXXX",
  "state": "RUNNING | HALTED | ABANDONED | COMPLETE",
  "halted_reason": null,
  "stack_base": "origin/main",
  "writer_session": "<session-id>",
  "writer_ts": "<iso>",
  "nodes": [
    {"bead": "docr-A", "branch": "launch-...", "status": "terminal_success"},
    {"bead": "docr-B", "branch": null, "status": "not_started"}
  ]
}
```

Node `status` values: `not_started | in_flight | terminal_success |
terminal_failure | needs_human`. Status is ALWAYS re-derived from the node
bead's own event log (`AGENT_SPAWNED`/`AGENT_COMPLETED`/`PHASE_GATE_PASSED`/
`stage=approval status=proceed` + PR URL metadata) on every entry; the cursor
copy is a cache for reporting, never the source of truth for dispatch
decisions. This derivation is what makes kill-mid-node resume no-double-fire:
an `in_flight` node with a live launch lock is WAITED ON, never re-driven.

## 4. Drive loop (sequential; one node at a time)

For the first node whose derived status is `not_started` (or `in_flight`
with a DEAD launch lock, which resumes via launch's own cold-start):

1. Write cursor: node -> `in_flight`, heartbeat.
2. Invoke inline:
   `Skill(skill="launch", args="<node-bead> --gate=agent --base-ref=<stack_base> -- convergence already done, do NOT re-converge")`.
   This session IS the node's launch orchestrator (Skill calls load inline;
   there is no return channel and none is needed: confirmation comes from
   the node bead's events). Launch handles worktree, agents, review
   fan-out, approval event, draft PR via its finalization Path B
   (`gt track`/`gt submit --stack`); campaign never hand-rolls PR creation.
   FIRST-NODE EXCEPTION (drill finding F2, docr-k8l6y 2026-07-20): launch
   finalization routes base==main to Path A (raw `gh pr create`), leaving
   node 1's branch UNTRACKED in Graphite and breaking node 2's
   `gt track --parent <node-1-branch>`. After node 1's PR exists, run
   `gt track <node-1-branch> --parent main` (from any worktree) so the stack
   registers end-to-end. Also: `gt submit` has NO `--body-file` flag; submit
   plain, then set title/body via `gh api -X PATCH repos/<org>/<repo>/pulls/<n>`.
3. Confirm node-terminal from the node bead: `stage=approval status=proceed`
   event + PR URL metadata + finalization evidence. No evidence -> treat as
   failure path, never assume.
4. **CI-settled advance gate**: poll `gh pr checks <node-pr>` via an
   iteration-bounded `run_in_background` poll (the ratified pattern in
   `memory/workflow.md`; ScheduleWakeup is NOT used for CI waits). Advance
   requires green. Red after launch's own retries -> failure path.
   Known bound: a codespace that sleeps mid-wait kills the poll; the cursor
   bead makes recovery a bare re-invocation, and this bound is the
   documented walk-away limitation.
5. Advance cursor: node -> `terminal_success`; `stack_base` ->
   `origin/<node-branch>`; heartbeat.
6. **Context budget check**: past ~30% remaining, write the cursor, arm ONE
   ScheduleWakeup whose prompt is the bare `/campaign <epic>` re-invocation
   (turn-boundary rollover, the ROUTINE path per `memory/workflow.md`), and
   end the turn. The termination gate makes a late-firing wakeup on a
   finished/halted/abandoned campaign a no-op.

**Resync-on-merge**: if polling reveals an earlier node's PR MERGED mid-run
(human merged bottom-up while the chain still runs): `git fetch origin`,
then for each open downstream branch in order: `gt sync` / restack, push
with `--force-with-lease=<branch>:<expected-sha>` computed from the
just-fetched ref. Never bare `--force`; never raw `git push` where `gt` owns
the branch (PR #8971 lesson). GitHub's auto-retarget reports MERGEABLE even
when stale (documented 2026-06-03 memory); the explicit resync is the fix.
RESYNC IS A LOUD-HALT POINT in unattended runs (ratified 2026-07-20, drill
F3 on docr-k8l6y): the auto-mode classifier denies force-with-lease without
a per-round human verb, so on detecting a mid-run merge, HALT per section 5
(halted_reason names the merged PR and the exact lease-push commands ready
to run) instead of attempting the push. The human resumes attended, names
the push, and the chain continues. Pinned pipelining means merges mid-run
are optional; a human who defers merging to chain-end never hits this.

## 5. Failure semantics (whole-chain halt)

Any node failure (launch unattended halt per the "Unattended decision-point
policy", non-PROCEED approval verdict, circuit breaker, CI red) halts the
WHOLE chain:

1. Write cursor FIRST: `state=HALTED`, `halted_reason`, node ->
   `terminal_failure` or `needs_human`.
2. Post a status comment on EVERY open draft PR in the chain (upstream greens
   included: the chain is halted as a unit, and even a green parent must not
   be merged mid-halt). AUDIENCE-NEUTRAL wording only: bead IDs and bd-CLI
   vocabulary are BLOCKED on gh surfaces by block-personal-tier-vocab.sh
   (drill finding F1, docr-k8l6y 2026-07-20). Drilled wording: "Automated
   pipeline drill/run halt: the unattended pipeline run building this PR
   chain has halted at node <N> (<neutral reason>). Do not flip ready or
   merge any PR in this chain until the halt is resolved." The bead pointer
   goes in the epic bead comment (step 3), never in the PR comment.
3. `bd comment` the epic bead: failed node, evidence pointers (its launch
   bead events, circuit-breaker reasons), stack position, not-started nodes.
4. PushNotification naming the epic and the failed node. 5. Stop.

Resume: the human resolves or closes the failed node, then bare
`/campaign <epic>` re-invocation (the termination gate re-derives and
continues). Downstream nodes NEVER start on a failed node's base.

## 6. Abandon (`--abandon`, or the human says so)

1. Write `state=ABANDONED` FIRST (termination gate now blocks everything,
   including queued wakeups).
2. Close open node PRs (`gh pr close`: reversible) each with the comment
   "Epic abandoned; left in draft; no auto-cleanup performed."
3. Do NOT delete remote branches (irreversible ref loss; the report lists
   the `git push origin --delete <branch>` commands for the human).
4. Worktree GC (below), final report, PushNotification.

## 7. Worktree GC (runs at COMPLETE, HALTED, and ABANDONED)

Diff `git worktree list` against the cursor's expected active node; `git
worktree remove` orphans under `.launch-worktrees/`. Note in the report that
local branch refs persist until `git branch -D` (listed, not executed).

## 8. Run report (COMPLETE)

`bd comment` on the epic bead: per-node PR links, CI evidence, deviations,
halts survived, and a cost pointer (transcript-ledger method, see
docr-q5p2k design). Set cursor `state=COMPLETE`. PushNotification with the
summary line. Terminal Jira transitions belong to the human after review;
surface the list ("N nodes In Review await your verification"), never
perform them (block-jira-transition.sh enforces terminal denial regardless).

## Verification

Drills live on `docr-k8l6y`; the core-3 (kill-mid-node no-double-fire,
fault-injection halt incl. resume-after-halt and the downstream-PR-comment
assertion, 3-node throwaway soak) MUST be green before the first real epic.
Record results on that bead.

## Bounds (hard rules; read these last, they win over everything above)

- Never merge, never flip a draft ready, never terminal Jira transitions.
- Never bare `--force`; lease pushes computed from a just-completed fetch.
- Never re-converge a node; a node that needs converging is a construction
  failure that stops the campaign attended.
- Never run nodes in parallel (v1): worktree/branch naming is
  second-resolution and collides under concurrency; a v2 parallel mode
  requires session-qualified naming in launch execution.md 5.1 first.
- Never mutate cursor state without the writer lock; never take over a
  cursor whose in-flight node holds a live launch lock.
- Every entry (invocation or wakeup) passes the termination gate before any
  mutation. ABANDONED is permanent absent explicit human reversal.
