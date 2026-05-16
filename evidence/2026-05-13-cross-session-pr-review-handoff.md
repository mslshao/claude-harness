# 2026-05-13: Cross-session PR review handoff via beads memory

**Source**: the author's own bead memories `pending-review:pr-9043:2026-05-13` and `pending-review:pr-9044:2026-05-13`, plus the older anchor `review:pr-5027:2026-03-17`. The mechanism has been used continuously across the author's PR review workflow for two months. Scrubbed for public version (no PR numbers, no team-specific identifiers; the pattern is what matters).

**Context.** PR reviews routinely span multiple sessions. A typical shape: session A reads the PR diff, dispatches specialists via the harness's PR review skill, drafts a structured review, and then needs to defer posting (waiting on a Datadog spot-check, waiting on the author to push another commit, waiting on a teammate's input, or the user has to step away). Session A captures the draft state in beads memory under a typed key. Session B (possibly hours or days later) loads the memory at session start (always-on memory is part of the harness's two-tier doctrine), sees the staged review surface immediately, and can post, revise, or invalidate based on the PR's current state.

**What AI did.** When a `/pr-intel` run produces a structured review but the user defers posting, the assistant writes the review state to `bd remember --key="pending-review:pr-<N>:<YYYY-MM-DD>"` with the full text plus context (PR HEAD SHA at stage time, specialists invoked, verification steps completed, open questions). The next session begins by surfacing all bead memories tagged `pending-review:*` (the always-loaded index makes this automatic). The continuation logic the assistant follows: read the staged memory, fetch current PR state (HEAD diff and new comments since stage time), verify the staged review still applies to the current state, then post unchanged, augment with new information, or invalidate if the PR has changed substantially.

**Baseline.** Without this mechanism, the same workflow has two known failure modes:

1. *Forgotten reviews.* The user remembers "I drafted a review somewhere" but loses track of which PR or what was drafted. The review never lands. Concrete prior instance from the author's pre-harness period: a review draft written in a notebook app, then forgotten when the user closed the window. The PR merged un-reviewed.
2. *Stale reviews.* The user posts a draft that no longer reflects the PR. Concrete prior instance: a review that flagged a logic concern in a function that the PR author had since rewritten in a later commit. The comment landed on a line that no longer matched the prose, confusing the author and forcing a clarification round.

Both failure modes have a measurable cost (one missed review per occurrence in case 1; one round-trip per occurrence in case 2). The mechanism described above prevents both because the bead memory carries enough metadata for the continuation session to detect staleness before posting.

**Verifiability.** The bead memories exist and are queryable (`bd memories pending-review` returns 2 staged reviews from 2026-05-13). The continuation pattern is reproducible: any session reading those memories at session start can re-fetch the PR state and decide whether to post. Beads' Dolt-backed storage means the memories survive compaction, session boundaries, and codespace restarts; the author has restarted the codespace multiple times since the 2026-05-13 stage and the memories are still surfaceable.

**Honest read.**

1. *What this entry supports.* The harness's two-tier memory doctrine (specifically tier 1: always-loaded short facts under typed keys) provides functional cross-session continuation for AI workflows that span boundaries. PR review is one instance; the same pattern (draft state captured in beads, surfaced at next session start, verified and continued) applies to investigation work, deferred refactor candidates, and follow-up beads from larger sessions. The mechanism is rudimentary (typed string keys, free-form bodies) but the user is the discriminator on key namespaces, and it has worked continuously for two months without collision.

2. *What this entry does NOT support.* This is single-user cross-session communication, not multi-user collaboration. Both sessions involved are the same human's Claude Code sessions. Real multi-engineer review handoff (where another teammate finishes my review) is not what this evidences. Also: "memory persists across sessions" is a property of beads as a tool; the harness's contribution is the discipline (typed key namespace, the `pending-review:` prefix convention, the always-load index) that makes the persistent memory usable rather than just a write-only audit log.

## What this case actually evidences about the harness

Memory mechanics aren't the same as memory discipline. Beads-the-tool persists arbitrary key-value entries; that's table stakes. The harness's contribution is the layered discipline that makes those entries reachable:

1. The typed key namespace (`correction:*`, `pending-review:*`, `project:*`, etc., per `scaffolding/key-namespace.md`) means a search like `bd memories pending-review` returns exactly the operational class the user wants, not noise.
2. The always-loaded tier-1 index means session B sees the staged reviews automatically without having to know they exist.
3. The `pending-review:pr-<N>:<date>` shape carries enough context for the continuation session to detect staleness: the PR number is the identity, the date is the stage time, the body holds HEAD SHA at stage.

Without all three layers, the mechanism degrades to a notebook app: durable but unreachable. The discipline is what closes the loop.

## Caveats specific to this entry

- **Workflow evidence, not time-compression evidence.** This entry argues the harness enables a workflow shape that has measurably better completion rates than the alternative. It does not argue any specific PR review took fewer minutes than its baseline. The compression is in completion rate (review actually lands, on current code), not duration.
- **Single-user scope.** Multi-engineer handoff is a different beast. A real "Claude session A drafts, Claude session B posts" workflow inside the same user is closer to "future-me reviewing past-me's draft" than to genuine collaborative review.
- **Selection bias**: the author remembered this pattern because it has worked continuously. Failure modes of the mechanism itself (silent stale-memory drift, key namespace collisions, false-positive surfacing of long-dead memories) are not visible to this anecdote. The `gotcha:beads-memory-namespace-collision` memory documents one known failure mode; more likely exist.

## What would strengthen this entry

A second entry where the cross-session mechanism caught a stale-memory case in practice (session A staged a review; session B detected that the PR had been rewritten and invalidated the draft instead of posting it). That would evidence the staleness-detection step. Currently the author is confident the staleness-detection works because it has been exercised informally, but no specific instance is documented at the bead-memory level.
