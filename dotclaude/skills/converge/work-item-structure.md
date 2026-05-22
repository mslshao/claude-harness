# Phase 2 + Phase 5: Work Item Structure

This file defines the work item field structure used in Phase 2
(Scope & Decompose) and the presentation format used in Phase 5
(Present). SKILL.md references it; do not duplicate content.

## Phase 2 Decompose: Work Item Fields

Break the refined scope into work items with these fields:

- **Title** (imperative, scoped). Example: "Add `deleted_at` field to
  folio document model".
- **Description** (what and why). 2-4 sentences.
- **Acceptance criteria** (observable outcomes). Bullet list, each
  item independently verifiable.
- **Design notes** (approach, patterns to follow, codebase references).
  1-3 sentences. Cite specific paths where possible.
- **Dependencies** (what blocks what). Reference other work items by
  number, or "none".
- **Verification path**: how the implementer will know this work item
  is correct BEFORE committing to it. Cite the specific test, command,
  log signal, or pattern to inspect/prototype against. 1-2 sentences.
  The "how would I test the design" before writing the code. Items
  without a verification path are tech debt waiting to ship.
- **Consequence of wrong**: `low` / `med` / `high`. If this work item
  ships but turns out to be wrong, what is the cost?
  - `low` = single PR revert, no data loss, no customer impact.
  - `med` = data migration to undo, customer-visible regression.
  - `high` = data corruption, irreversible state, trust loss, lost
    workstream.
- **Context**: `greenfield` / `legacy` / `hybrid`. Building net-new,
  adjusting existing production code, or both. Annotation, not scored;
  it affects how the reviewer reads Effort and Risk in the work item.

## Field-Level Invariants

- **Verification path is mandatory.** Items without it trigger
  ITERATE in Phase 4.6 with WEAK_DIMENSION=verification. The
  verification path is the implementer's "I'd know this is right
  because <X>" sentence; absence of it means we'll only find out the
  approach was wrong AFTER shipping.
- **Consequence=high requires either a matching verification path
  OR an explicit risk-reduction note.** Items with Consequence=high
  and no concrete way to validate them pre-commit are
  workstream-killers. Phase 4.6 enforces this; Phase 4 synthesis can
  pre-empt by either adding a verification path or downgrading scope.
- **Context is annotation only.** It changes how the user reads other
  fields (legacy + small Effort is impressive; greenfield + small
  Effort is expected). Do not score on Context.

## Category Assignment

Each work item gets a bead category label:
- `task` (default)
- `memory` (when the work item captures durable knowledge, not
  executable code)
- `decision` (when the work item is "decide X" with no implementation)
- `discovery` (when the work item is "find out X" or "investigate Y")
- `review` (when the work item is "review existing X for Y")

Apply the granularity check from bead-forge: each item should be
completable in one focused session. If an item is too large,
decompose further.

## Phase 5 Presentation Format

In the Phase 5 Present output, each work item appears in dependency
order with this format:

```markdown
#### [N]. [Title]
**Type**: [task/feature/bug/decision/discovery]
**Priority**: [P0-P4]
**Context**: [greenfield / legacy / hybrid]
**Depends on**: [item numbers or "none"]

[Description: 2-4 sentences. What and why.]

**Acceptance criteria:**
- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

**Design notes:** [Approach, patterns, codebase references. 1-3 sentences.]

**Verification path:** [How the implementer will know this is correct
BEFORE committing. Cite the specific test, command, log signal, or
pattern to inspect. 1-2 sentences.]

**Consequence of wrong:** [low | med | high. If high, must include a
matching verification path OR an explicit risk-reduction note.]
```

The Phase 5 template in SKILL.md uses this format under the
`### Work Items` heading.
