# Phase 4.6: Convergence Gate

The proceed/iterate/escalate gate that prevents shipping weak
convergence to the user. SKILL.md references this file; do not
duplicate content.

## Why Phase 4.6 Exists

The plan has passed challenge + consult + skeptic (Phases 3 + 4 +
4.5), but a plan that survived stress-testing might still fail a
decision-maker's "would you bet on this" check, especially when
DELTA_CATEGORY is CONFIRMED on a mechanism-prescribed input
(specialists may have punted rather than challenged the prescription).
Phase 4.6 is the calibration layer that catches this.

## Phase 4.6a: Dispatch the Decision-Maker

The gate receives the synthesized plan, convergence delta, delta
category, INPUT_MODE classification, and skeptic findings (or
unavailable-reason if Phase 4.5 failed). A missing skeptic pass is
itself a signal: PROCEED carries lower confidence when adversarial
check did not run.

```
Agent(
  subagent_type="mx2-decision-maker",
  description="Proceed/iterate gate on converged plan",
  prompt="**MODE: CONVERGENCE GATE.** You are gating a converged plan
  from /converge (not an autopilot checkpoint, not an ideation gate).
  Calibration context: the plan has passed challenge + consult +
  skeptic. Your job is to call PROCEED, ITERATE, ESCALATE-QUESTIONS,
  or ESCALATE-ROUTE on the plan before Phase 5 Present.

  The autopilot Evidence Trail input contract does not apply here; the
  artifact you are gating is a converged plan plus its stress-test
  outputs (challenge, consult, skeptic), described below. Treat absent
  autopilot-specific fields as waived and a missing iteration history
  as 'First evaluation'.

  If you detect calibration drift during this invocation, record via
  `bd remember --key='calibration:mx2-decision-maker:converge:<topic>' '...'`.
  Tag with `converge:` so calibrate reviews can keep convergence-specific
  calibration separate from autopilot/launch and ideation calibration.

  PROCEED if the plan is defensible: convergence delta is concrete,
  work items have verification paths, Consequence=high items have
  matching verification paths or are explicitly downgraded, skeptic
  findings either resolved or surfaced as Open Assumptions, and the
  scope matches the input intent. CONFIRMED delta is acceptable IF the
  input was simple or specialists offered concrete evidence; suspicious
  otherwise. PROCEED also requires the plan is PROPORTIONATE: if the
  input carries scope-signal words (lightweight / simple / minimal /
  quick / for most users) OR the plan is materially heavier than a
  minimal-viable 80/20 version, the extra complexity must be justified
  component-by-component; if it is not, do not PROCEED, fire ITERATE with
  WEAK_DIMENSION=proportionality.

  ITERATE if the plan is uncertain BUT another challenge+consult pass
  with a focused weak-dimension target would plausibly resolve it.
  Specify WEAK_DIMENSION (one of: verification, consequence, scope,
  decomposition, mechanism, proportionality). The mechanism case is
  canonical for
  catching Fulfillment-vs-Coverage: INPUT_MODE=mechanism-prescribed
  combined with DELTA_CATEGORY=CONFIRMED on a non-trivial plan
  usually means the prescribed mechanism was rubber-stamped, not
  challenged.

  ESCALATE-QUESTIONS if the plan space is too ambiguous to converge
  and 1-3 narrowing questions to the user would meaningfully focus the
  next pass. Use this for: 'I cannot tell whether X is in scope', 'the
  user-prescribed mechanism Y has two reasonable interpretations',
  'this could be a feature of existing Z or a new noun, the choice
  matters'. Constraints: max 3 questions, each with a WHY clause
  naming what the answer unblocks.

  ESCALATE-ROUTE if /converge is the wrong skill: the input is too
  rough and needs /ideate first (multiple plausible mechanisms,
  user hasn't picked one), or the root cause is unknown and needs
  /investigate first, or the problem is actually trivial and needs
  direct execution rather than a plan.

  Converged plan + convergence delta + delta category:
  <plan block>

  INPUT_MODE: <problem-framed | mechanism-prescribed>
  DELTA_CATEGORY: <CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT>

  Skeptic findings (or 'Skeptic Lens unavailable: <reason>' if
  the Phase 4.5 dispatch failed):
  <skeptic block>

  Return VERDICT (PROCEED / ITERATE / ESCALATE-QUESTIONS /
  ESCALATE-ROUTE), REASON (1-3 sentences), and:
  - if ITERATE: WEAK_DIMENSION (one of: verification, consequence,
    scope, decomposition, mechanism, proportionality).
  - if ESCALATE-QUESTIONS: NARROWING_QUESTIONS (1-3 questions, each
    with a WHY clause).
  - if ESCALATE-ROUTE: SUGGESTED_NEXT_SKILL (one of: /ideate,
    /investigate, direct execution)."
)
```

## Phase 4.6b: Branch on Verdict

### PROCEED
Continue to Phase 5 (Present). Record verdict + reason in the
iteration log.

### ITERATE
Re-run Phase 2 (Scope & Decompose) and Phase 3 (Challenge + Consult)
with a focused WEAK_DIMENSION instruction:

- `verification`: "Every work item must include a verification path
  achievable in under 1 hour before committing."
- `consequence`: "Identify each work item's Consequence-of-wrong
  rating; for high-Consequence items, add explicit risk-reduction
  sub-items (rollback plan, feature flag, observability)."
- `decomposition`: "Re-evaluate work item granularity; merge
  over-decomposed items, split under-decomposed items."
- `mechanism`: "Treat the user-prescribed mechanism as one candidate
  among many. Evaluate at least one alternative mechanism and surface
  the comparison in the convergence delta. This is the canonical
  Fulfillment-vs-Coverage check."
- `scope`: "Identify what is in vs out of scope; surface any items
  that crossed the boundary in either direction."
- `proportionality`: "Re-decompose toward the minimal-viable variant.
  Name the smallest 80/20 plan that meets the stated goal, then keep
  only the work items whose extra value over that minimal plan is
  justified by a STATED constraint (not a hypothetical future). Surface
  the minimal-viable comparison in the convergence delta."

Re-synthesize (Phase 4). Re-run skeptic (Phase 4.5). Re-gate
(Phase 4.6).

### ESCALATE-QUESTIONS
Surface NARROWING_QUESTIONS to the user via the AskUserQuestion tool
(preferred for 2-3 multiple-choice; supports an automatic "Other"
option for free-text answers) or as a numbered list in chat (for 1
open-ended question). Show each question with its WHY clause inline
so the user knows what each answer unblocks.

Frame: "I have a few narrowing questions before convergence would be
productive. If you don't want to answer, reply 'you decide' and I'll
proceed with the current draft as a low-confidence plan."

Non-interactive callers (agent dispatch, /autopilot, a /launch-internal
convergence, any context where no human can answer): do NOT block on
AskUserQuestion. Treat as the 'you decide' opt-out: force a
low-confidence PROCEED and carry the unanswered narrowing questions
into the output's Open Assumptions section.

Constraints on questions:
- Max 3. One focused question is usually better than three.
- Each must name what specifically gets unblocked by the answer (the
  WHY clause). Questions without a clear consequence in the next
  pass are not worth a user cycle.
- Phrase as choices when possible, not as open-ended prompts.
- Do NOT ask about implementation details; ask about constraints,
  priorities, or problem-framing decisions.

After user answers (or opts out), fold answers into the refined scope
(Phase 1), re-run Phase 2 + 3 + 4 + 4.5 + 4.6. If user opted out,
force PROCEED with low-confidence annotation.

ESCALATE-QUESTIONS can fire AT MOST ONCE per `/converge` invocation.

### ESCALATE-ROUTE
Surface in Phase 5 output. No work items, no recommendation. Just the
SUGGESTED_NEXT_SKILL and the reason /converge is not the right tool.
Common cases:

- "Multiple plausible mechanisms; user has not picked one" maps to
  suggest `/ideate` first.
- "Root cause unknown" maps to suggest `/investigate` first.
- "Plan is one obvious action with one obvious test" maps to suggest
  direct execution.

## Phase 4.6c: Iteration Caps

Two separate caps, tracked independently:

- **ITERATE cap**: maximum 2 ITERATE rounds. After 2 ITERATE verdicts,
  force PROCEED with a "low-confidence" annotation OR fire
  ESCALATE-ROUTE if the underlying problem clearly cannot be converged
  to a defensible plan.
- **ESCALATE-QUESTIONS cap**: maximum 1 user-question round per
  invocation. The user's cycles are precious; do not chain
  question-rounds.

## Iteration Log Format

Every round appears in the Phase 5 output, including Round 0 (no
iteration needed). The user sees how many cycles were needed and what
each round produced.

```
Iteration log:
- Round 0 (initial): N work items drafted; DELTA_CATEGORY=<X>.
- Round 1 (if any): VERDICT (REASON). Action: <what changed>.
- Round 2 (if any): VERDICT (REASON). Action: <what changed>.
- Final verdict: PROCEED | LOW-CONFIDENCE | ESCALATE-ROUTE.
```
