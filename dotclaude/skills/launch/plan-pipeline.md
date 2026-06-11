# Plan Pipeline Protocol

Phases 2 through 3.6 of `/launch`. Takes the implementation brief from
Phase 1 and produces a converged, stress-tested, gated plan with a
parallelization strategy.

SKILL.md references this file for the orchestration shape; the heavy
subagent prompts live in:
- [stress-test-prompts.md](stress-test-prompts.md) for Phase 3a + 3b
- [gate-prompts.md](gate-prompts.md) for Phase 3.5 + 3.6

## Phase 2: Initial Plan (Internal)

Feed the implementation brief into the converge pipeline as internal
processing. This mirrors `/converge` phases 1-4 but uses the enriched
brief (not a rough idea) as the seed.

### 2.1: Refine

Expand the brief with:
- Current git state (`git status`, `git log --oneline -5`)
- Active beads (`bd list --status=in_progress`)
- Codebase patterns (grep for similar implementations in `src/python/mx2/`)

### 2.2: Decompose

Identify natural seams in the work:
- **By layer**: infra (HCL/Terraform), scaffolding (BUILD files,
  `__init__.py`), implementation (models, services, handlers), tests
- **By domain**: if the ticket spans services, each service boundary
  is a seam
- **By dependency**: work that must happen before other work starts

For each seam, draft a work item with:
- Title (imperative, scoped)
- Description (what and why)
- Acceptance criteria (observable, verifiable outcomes)
- Design notes (patterns to follow, codebase references)
- Agent assignment (implementer, tester, or flex-{role})
- Phase assignment (A, B, C based on dependencies)
- **Verification path**: how the implementer (and the orchestrator
  during checkpoint gating) will know this item is correct BEFORE
  committing. Cite the specific test, command, log signal, or pattern
  to inspect/prototype against. 1-2 sentences. Distinct from phase
  gate criteria: phase gates are programmatic checks at phase
  boundaries; Verification paths are per-item "how would I test the
  design" sentences the implementer can act on in-loop.
- **Consequence of wrong**: `low` / `med` / `high`. If this work item
  ships but the design turns out to be wrong, what is the blast radius?
  - `low` = single PR revert, no data loss, no customer impact.
  - `med` = data migration to undo, customer-visible regression.
  - `high` = data corruption, irreversible state, trust loss, lost
    workstream.
- **Context**: `greenfield` / `legacy` / `hybrid`. Building net-new,
  adjusting existing production code, or both. Annotation only; it
  affects how the reviewer reads Effort and Risk.

Items with `Consequence=high` AND no concrete Verification path are
workstream-killers. The Phase 3.6 decision-maker gate enforces this
by firing ITERATE with WEAK_DIMENSION=verification when it sees the
pattern. Synthesis (3c) should pre-empt by either adding a
verification path or downgrading the scope of high-Consequence items.

### 2.3: Pipeline Reuse Gate

**Before designing any new code path**, check:
1. Does the existing pipeline already handle this? Search for similar
   handlers, processors, or services in `src/python/mx2/`.
2. What happens if we send one message through the normal path?
3. Would a small modification to an existing path be cheaper than a
   new one?

New paths mean new bugs and new contracts. The existing path is
tested. If reuse works, the plan should leverage it.

### 2.4: Preliminary Agent Roster

Based on the decomposition, draft the agent roster:

| Agent | Role | Phase | Input |
|-------|------|-------|-------|
| implementer | Core implementation | B | Work items for src/python/mx2/ |
| tester | Tests | C | Work items for tests/, implementer output |
| flex-infra | Infrastructure | A | Work items for infra/, app/ |

The roster is preliminary - Phase 3 may modify it.

### 2.5: Stage Event Write

After decompose completes, write a `[LAUNCH_STAGE stage=decompose ...]`
entry to the bead. Heavy work-item lists go to scratch.

```bash
ROUND=${ITERATE_ROUND:-0}  # 0 for initial pass, 1+ for ITERATE re-runs
N_ITEMS=$(echo "$WORK_ITEMS" | jq '. | length')

if [ "$ITEMS_SIZE" -lt 2048 ]; then
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=decompose round=$ROUND status=drafted n_items=$N_ITEMS ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
else
  ITEMS_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/decompose-$ROUND.md"
  echo "$WORK_ITEMS_FORMATTED" > "$ITEMS_PATH"
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=decompose round=$ROUND status=drafted n_items=$N_ITEMS path=$ITEMS_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
fi
```

## Phase 3: Stress Test (Parallel)

Launch the Challenge subagent (3a) AND all selected consult
specialists (3b, roster: `~/.claude/skills/consult/specialists.md`)
as parallel Agent tool calls: 1 + N dispatches, no consult-coordinator
subagent (subagents cannot spawn subagents). Every dispatch receives
the relevant plan content + the INPUT_MODE classification from
Phase 1. INPUT_MODE-aware framing in the prompts ensures
mechanism-prescribed inputs get enhanced scrutiny (the
Fulfillment-vs-Coverage guard).

**CRITICAL: Launch all of them in a single message. Do not serialize.**

For the full Phase 3a (Challenge) and Phase 3b (per-specialist)
prompt templates, see
[stress-test-prompts.md](stress-test-prompts.md).

### 3c: Synthesize

When the Challenge subagent and all specialists return:

1. **Merge findings**: deduplicate, connect themes, resolve
   contradictions.
2. **Apply to plan**: revise work items based on findings.
   - INVALIDATED assumptions: remove or revise affected items.
   - "Fix now" concerns: incorporate into work items or acceptance
     criteria.
   - Gaps: add items or criteria.
3. **Finalize parallelization strategy**: the stress test may have
   changed dependencies, added work items, or shifted agent
   assignments.
4. **Categorize the Convergence Delta** with ONE of four labels:
   - **CONFIRMED**: specialists agreed; no structural changes; only
     minor clarifications. The plan actually withstood scrutiny.
     Suspicious when input was complex or `mechanism-prescribed`;
     bias toward MINOR_ADJUSTMENTS unless specialists offered
     concrete evidence (file paths, function names, pattern citations).
   - **MINOR_ADJUSTMENTS**: structure kept; small number of items
     adjusted (added AC, narrowed scope, swapped pattern).
   - **MAJOR_REVISIONS**: goal kept; materially different approach
     recommended (different agent assignments, different mechanism,
     different decomposition).
   - **SCRAPPED_AND_REBUILT**: different framing entirely. Original
     mechanism was wrong. Canonical Fulfillment-vs-Coverage outcome:
     specialists recommend folding the prescribed mechanism into an
     existing noun rather than creating a new one.

   The category label feeds into Phase 3.6 decision-maker gate AND
   appears in the Phase 4 approval-gate output so the user sees the
   depth of pushback at a glance.

Output: converged plan + parallelization-strategy YAML + DELTA_CATEGORY
label. Phase 3.5 (Skeptic Lens) consumes this directly.

### 3c Stage Event Write

After synthesize completes, write a `[LAUNCH_STAGE stage=synthesize ...]`
entry. The converged plan is always heavy enough to warrant scratch.

```bash
ROUND=${ITERATE_ROUND:-0}
DELTA=$(echo "$DELTA_CATEGORY" | tr '[:upper:]' '[:lower:]' | tr '_' '-')
# Maps to: confirmed | minor-adjustments | major-revisions | scrapped-and-rebuilt

PLAN_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/synthesize-$ROUND.md"
echo "$CONVERGED_PLAN_AND_YAML" > "$PLAN_PATH"
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_STAGE stage=synthesize round=$ROUND status=$DELTA path=$PLAN_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

The `status` field IS the DELTA_CATEGORY (lowercased + hyphenated). This
means cold-start can read the synthesize entry and know the convergence
delta category without parsing the scratch file.

## Phase 3.5: Skeptic Lens

Dispatch `mx2-skeptic` for an adversarial pass on the converged
plan. Mandatory. For the full dispatch prompt, no-concerns case
handling, and failure-mode handling, see
[gate-prompts.md](gate-prompts.md).

## Phase 3.6: Decision-Maker Gate

Dispatch `mx2-decision-maker` with `MODE: LAUNCH GATE` preamble.
Returns PROCEED / ITERATE / ESCALATE-QUESTIONS / ESCALATE-ROUTE.
Mandatory. For the full dispatch prompt, branch logic per verdict,
WEAK_DIMENSION instructions, narrowing-question constraints,
SUGGESTED_NEXT_SKILL mapping, and iteration caps, see
[gate-prompts.md](gate-prompts.md).

Key invariants:
- ITERATE cap: 2 rounds per invocation.
- ESCALATE-QUESTIONS cap: 1 user-question round per invocation.
- Calibration drift recorded via
  `bd remember --key='calibration:mx2-decision-maker:launch:<topic>'`.
- The mechanism case (INPUT_MODE=mechanism-prescribed +
  DELTA_CATEGORY=CONFIRMED on a non-trivial plan) is the canonical
  Fulfillment-vs-Coverage check; gate fires ITERATE+WEAK_DIMENSION=mechanism.

## Parallelization Strategy Output

The Phase 3.6 output (when verdict is PROCEED) MUST include this
structure (passed to Phase 4 for the approval artifact):

```yaml
agents:
  - name: implementer
    template: launch-implementer
    phase: B
    input: [work item IDs]
    specialists: [mx2-code-reviewer, mx2-silent-failure-hunter]
  - name: tester
    template: launch-tester
    phase: C
    input: [work item IDs, depends on implementer output]
    specialists: [test-quality-reviewer]
  - name: flex-infra
    template: launch-flex
    role: "Infrastructure Engineer"
    phase: A
    input: [work item IDs]
    specialists: [mx2-devops-build-deploy]

phases:
  A:
    agents: [flex-infra]
    gate:
      criteria:
        - "All .hcl files in infra/<service>/ parse without error"
        - "Module paths referenced in terragrunt.hcl exist"
      verification: "Run: terragrunt hcl-validate in worktree"
  B:
    agents: [implementer]
    depends_on: A
    gate:
      criteria:
        - "All public functions have implementations (no pass/NotImplementedError)"
        - "pants check src/python/mx2/<module> passes"
      verification: "Run: pants check <targets> in worktree"
  C:
    agents: [tester]
    depends_on: B
    gate:
      criteria:
        - "All test files import and reference the target module"
        - "pants test <test-targets> passes"
      verification: "Run: pants test <targets> in worktree"

commits:
  strategy: "single | behavior-gated"
  gates: ["description of each commit boundary, if behavior-gated"]
```

This structure is used by the orchestrator in Phase 5 to spawn agents,
verify gates, and manage phasing. Vague criteria ("tests are written")
are rejected during Phase 3a Challenge - every gate must be
programmatically verifiable.

When the Phase 3.6 verdict is ESCALATE-ROUTE, no parallelization
strategy is produced; Phase 4 shows the user the gate's reason and
the suggested next skill instead.
