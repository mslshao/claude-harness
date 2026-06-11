# Dry-Run Walkthroughs

Two end-to-end examples that exercise the full skill. SKILL.md references
this file; do not duplicate inline.

## Walkthrough 1: PROCEED on Round 0 (folio document deletion)

Example problem: "How should we add document deletion to the folio API?"

**Phase 1 (refine)**: Input is 12 words, lacks constraints. Invoke
`prompt-refiner`. Refined: "Add a document-deletion endpoint to the
folio API. Concerns: respect existing audit-log fields, handle soft-vs
hard delete semantics, propagate to downstream consumers (<service> index,
dyn2red replica). Scope: folio API only; downstream cleanup is
out-of-scope for v1." Loaded context: `bd memories folio` surfaces
prior decision that folio writes via dyntastic with conditional writes
for deduplication.

**Phase 2 (diverge)**: Approach count = 4 (problem is design-shaped,
not bug-fix-shaped). Roster: `mx2-tech-lead`, `mx2-code-reviewer`,
`mx2-security-auditor` (audit-log keyword), `observability-reviewer`
(propagation concern). Parallel dispatch returns 5 approaches; merge
near-duplicates to 4:
1. Soft delete via `deleted_at` timestamp; consumers filter.
2. Hard delete with audit row in a separate `deletions` table.
3. Tombstone record with TTL; consumers process tombstones.
4. Two-phase delete: mark pending, async sweep.

**Phase 3 (evaluate)**. Each row computes per the formula in
`scoring-matrix.md`. App 4 has Verif=low AND Conseq=high, so the
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

**Phase 4 (iterate)**. mx2-decision-maker called PROCEED: top-1 scored
22/22, dominant on every column including Verifiability=high and
Consequence=low; clear gap to top-2 (Score 13). No iteration round
needed. Iteration log records "Round 0: 5 approaches generated, 4
survived dedup. Final verdict: PROCEED."

**Phase 5 (present)**: Winner is approach 1 (Soft delete + filter).
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

**Phase 6 (handoff)**: User runs `/converge "Soft delete in folio API:
add deleted_at timestamp; consumers filter; out-of-scope: downstream
cleanup"`.

## Walkthrough 2: ESCALATE-QUESTIONS then ITERATE then PROCEED

Example problem: "We need a better way to handle document re-ingestion
when the source schema changes."

**Phase 1 (refine)**: Input is 16 words, no constraints. Refined: "Add
a mechanism to handle document re-ingestion when the source schema
changes. Constraints unknown: scale (is this 100 docs or 10M?),
greenfield vs retrofit, urgency unclear." No Confluence draft, no Jira
ticket. Pure free-text problem.

**Phase 2 (diverge)**: Approach count = 5 (open-ended). Roster:
mx2-tech-lead, mx2-code-reviewer, mx2-pr-precedent. 5 approaches
returned, ranging across "schema-version pinning", "lazy re-ingestion
on read", "eager backfill via batch job", "event-driven on
schema-change SNS", "no-op + telemetry to scope first."

**Phase 3 (evaluate)**: Top-3 cluster at Scores 11/10/9 with no clear
winner. All three are mid-Verifiability and mid-Consequence. Skeptic
returns: "I don't know which of these is right because I don't know
if you're optimizing for backwards-compat with 10M existing docs or
for forward-cleanliness on a new corpus."

**Phase 4 (gate, Round 1)**: mx2-decision-maker calls
ESCALATE-QUESTIONS. NARROWING_QUESTIONS:
1. Is this a retrofit on existing production docs, or greenfield?
   **WHY**: retrofit approaches need migration paths and back-compat
   guards; greenfield approaches do not. The top-3 cluster because the
   matrix cannot pick without knowing this.
2. What is the corpus scale: 1K, 100K, or 10M+ docs?
   **WHY**: batch backfill is feasible at 1K, prohibitive at 10M; the
   event-driven approach is over-engineered for 1K but correct for 10M.

User answers via AskUserQuestion: "retrofit, ~2M docs."

**Phase 1-3 re-run with narrowed scope**: Refined problem now includes
"retrofit on 2M existing docs". Phase 2 dispatches with the constraint;
returns 4 approaches focused on retrofit: "lazy on read + background
sweep", "schema-version-pinned shadow index", "eager batch backfill
with throttling", "tombstone-then-reingest". Phase 3 scores: top-1 =
"lazy + sweep" at Score 17, top-2 = "shadow index" at Score 14.

**Phase 4 (gate, Round 2)**: mx2-decision-maker calls ITERATE.
WEAK_DIMENSION = verifiability (top-1 is low-Verifiability; no
existing pattern in the codebase for the lazy-load + background sweep
combo). The next Diverge pass asks specialists to add a verification
path to each candidate.

**Phase 2 re-run with verifiability framing**: Specialists return
revised approaches that all include a verification path. Top-1 is now
"lazy + sweep" at Verifiability=high (verification path: "prototype
sweep against a 1K dev-table slice in 30 minutes; confirm idempotency
and throttling fit budget"). Score rises to 19.

**Phase 4 (gate, Round 3)**: PROCEED. Clear winner, Verifiability=high,
Consequence=med (acceptable given Verifiability), skeptic clean.

**Phase 5 (present)**: Iteration log shows Round 0, then Round 1
(ESCALATE-QUESTIONS, 2 questions, user answered), then Round 2
(ITERATE on verifiability), then Round 3 (PROCEED). Winner: "lazy +
sweep" with verification path. Rejected alternatives preserved with
revisit triggers.

**Phase 6 (handoff)**: User runs `/converge "Lazy re-ingestion on
read + background sweep for the 2M-doc retrofit; verification: 1K
dev-table slice prototype first."`

The walkthrough demonstrates that the gate's narrowing-question lever
is what made the difference: without it, the skill would have either
shipped a low-confidence PROCEED on a top-1 that scored 11 (which the
user would have ignored) or burned 2 ITERATE rounds optimizing the
wrong dimension. One question to the user collapsed the candidate
space from "all of retrofit and greenfield" to "retrofit at 2M docs"
and made the matrix decisive.
