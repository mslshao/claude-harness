# Dry-Run Walkthroughs

Two end-to-end examples that exercise the full skill. SKILL.md references
this file; do not duplicate inline.

## Walkthrough 1: Single Pass, Clear Winner (folio document deletion)

Example problem: "How should we add document deletion to the folio API?"

**Phase 1 (refine)**: Input is 12 words and lacks constraints, so the
problem statement is expanded in-place. Refined: "Add a
document-deletion endpoint to the folio API. Concerns: respect
existing audit-log fields, handle soft-vs hard delete semantics,
propagate to downstream consumers (<service> index, dyn2red replica).
Scope: folio API only; downstream cleanup is out-of-scope for v1."
Loaded context: domain context loading surfaces that folio writes via
dyntastic with conditional writes for deduplication.

**Phase 2 (diverge)**: Approach count = 4 (problem is design-shaped,
not bug-fix-shaped). Roster: `code-reviewer` (default), `mx2-security
-auditor` (audit-log keyword), `observability-reviewer` (propagation
concern). Parallel dispatch returns 5 approaches; merge near-duplicates
to 4:
1. Soft delete via `deleted_at` timestamp; consumers filter.
2. Hard delete with audit row in a separate `deletions` table.
3. Tombstone record with TTL; consumers process tombstones.
4. Two-phase delete: mark pending, async sweep.

**Phase 3 (evaluate)**. Each row computes per the formula in
`scoring-matrix.md`. Approach 4 has Verif=low AND Conseq=high, so the
composite override forces it to last place regardless of raw Score:

| # | Approach | Context | Effort | Risk | Rev | Fit | Rules | Verif | Conseq | Score |
|---|----------|---------|--------|------|-----|-----|-------|-------|--------|-------|
| 1 | Soft delete + filter | legacy | S | low | easy | match | aligned | high | low | 22 |
| 2 | Tombstone + TTL | hybrid | M | med | easy | new | aligned | low | med | 13 |
| 3 | Hard delete + audit row | legacy | M | med | hard | match | aligned | med | high | 10 |
| 4 | Two-phase delete | hybrid | L | high | hard | new | aligned | low | high | 5 (override: last) |

Skeptic dispatched on top-3 by Score (approaches 1, 2, 3). Returns
🔻 with no concerns: the recommended winner is dominant on every
column, the gap to top-2 is wide (22 vs 13), and the high-consequence
candidates (3 and 4) are not in the recommendation slot.

**Phase 4 (present)**: Winner is approach 1 (Soft delete + filter).
Rationale: matches existing folio pattern (dyntastic conditional
writes), easy to revert (single field), downstream consumers already
filter on status fields. The Verifiability=high / Consequence=low
pairing is load-bearing. High-consequence callout fires for approaches
3 (Hard delete) and 4 (Two-phase delete). Rejected alternatives with
revisit triggers (by Score rank):

- Approach 2 (Tombstone + TTL): introduces a new pattern with no
  clear benefit over soft delete; revisit if downstream consumers
  need a pull-based deletion signal rather than a filter.
- Approach 3 (Hard delete + audit row): blast radius across
  downstream replicas, hard reversibility, high consequence; revisit
  if compliance requires hard-erasure within an SLA the soft approach
  cannot meet.
- Approach 4 (Two-phase delete): effort + async complexity + high
  blast radius + low verifiability; revisit only if approaches 1-3
  all hit a constraint we discover later.

Skeptic Lens: `🔻 No concerns from this lens.`

**Phase 5 (handoff)**: The human reads the table, agrees with the
recommendation, and proceeds to implementation using approach 1 as
the guide. Before committing, they run `/review` on the resulting
diff to catch structural issues.

## Walkthrough 2: Two Passes via Manual Re-Run (re-ingestion)

Example problem: "We need a better way to handle document re-ingestion
when the source schema changes."

### Pass 1: Initial Ideation

**Phase 1 (refine)**: Input is 16 words, no constraints. Refined: "Add
a mechanism to handle document re-ingestion when the source schema
changes. Constraints unknown: scale (is this 100 docs or 10M?),
greenfield vs retrofit, urgency unclear." No Confluence draft, no Jira
ticket. Pure free-text problem.

**Phase 2 (diverge)**: Approach count = 5 (open-ended). Roster:
`code-reviewer`, `observability-reviewer` (schema-change monitoring
concern), `silent-failure-hunter` (re-ingestion error handling). 5
approaches returned, ranging across "schema-version pinning", "lazy
re-ingestion on read", "eager backfill via batch job", "event-driven
on schema-change SNS", "no-op + telemetry to scope first."

**Phase 3 (evaluate)**: Top-3 cluster at Scores 11/10/9 with no clear
winner. All three are mid-Verifiability and mid-Consequence. Skeptic
returns:

```
🔻 The top-3 cluster because the problem framing leaves the corpus shape ambiguous; the right approach depends on whether this is retrofit at scale or greenfield design, and the matrix cannot adjudicate without that constraint.

Supporting questions:
- What is the corpus size: 1K, 100K, or 10M+ docs?
- Is this retrofit on existing production docs, or greenfield?
- What is the acceptable lag between schema change and re-ingestion?

If I'm right: narrow the problem framing before re-ranking; without the corpus-shape constraint, the matrix is choosing among approaches that solve different problems.
```

**Phase 4 (present)**: All five approaches surface, recommended winner
is the top-1 (schema-version pinning) at Score 11, but the Skeptic
Lens block explicitly calls out the framing ambiguity. The
"Recommended Winner" rationale acknowledges the cluster: "the top-3
all score 9-11 and the skeptic flags an unresolved framing question;
read the Skeptic Lens before acting on this recommendation."

**Human gate**: The user reads the Skeptic Lens, agrees that the
framing ambiguity needs resolving before committing, and decides to
iterate. They do NOT act on the top-1; they re-run `/ideate` with the
narrower scope.

### Pass 2: Re-run with Narrower Scope

**Phase 1 (refine)**: Refined problem now includes "retrofit on 2M
existing docs". Phase 2 dispatches with the narrowed constraint.

**Phase 2 (diverge)**: Returns 4 approaches focused on retrofit:
"lazy on read + background sweep", "schema-version-pinned shadow
index", "eager batch backfill with throttling", "tombstone-then
-reingest". The previous round's broad candidates (greenfield
event-driven) drop out because the narrowed problem rules them out.

**Phase 3 (evaluate)**: Top-1 = "lazy + sweep" at Score 17 (now
Verifiability=high because a 1K dev-table slice prototype is feasible
in 30 minutes), top-2 = "shadow index" at Score 14. Clear separation.
Skeptic returns `🔻 No concerns from this lens.`

**Phase 4 (present)**: Winner is "lazy + sweep" with a 30-minute
verification path. Rejected alternatives preserved with revisit
triggers.

**Phase 5 (handoff)**: User proceeds to implementation. Runs `/review`
on the resulting diff before committing.

The walkthrough demonstrates that the human gate is what made the
difference: the skill itself did not iterate, but the skill DID surface
the framing ambiguity (via skeptic) loudly enough that the user knew to
narrow the scope and re-run rather than ship the low-confidence top-1.
One human-driven re-run collapsed the candidate space from "all of
retrofit and greenfield" to "retrofit at 2M docs" and made the matrix
decisive.

The implicit lesson: when the skeptic surfaces a framing concern, the
correct human-gate response is usually to re-run with a narrower
problem statement, not to act on the top-1 anyway. The skeptic's
🔻 prefix is load-bearing for that signal.
