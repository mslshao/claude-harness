# Phase 4: Iterate Gate

The proceed/iterate/escalate gate that prevents shipping weak ideation.
SKILL.md references this file; do not duplicate content.

## Why Phase 4 Exists

Phase 3 produces a ranked top-3 with tenth-man findings, but a high
absolute Score does not guarantee a defensible recommendation. The
top-1 might score well yet still fail a decision-maker's "would you
bet on this" check. Phase 4 is the calibration layer.

## Phase 4a: Dispatch the Decision-Maker

The gate receives the top-K candidates (K = 3 normally, fewer if Phase 2
produced fewer surviving approaches; the dispatch prompt below handles
both cases). It also receives the tenth-man findings OR the
unavailable-reason if Phase 3c's tenth-man pass failed. A missing
tenth-man pass is itself a signal: PROCEED carries lower confidence
when adversarial check did not run.

```
Agent(
  subagent_type="mx2-decision-maker",
  description="Proceed/iterate gate on ideate top-K",
  prompt="**MODE: IDEATION GATE.** You are gating a candidate winner
  from an ideation pass (not an autopilot checkpoint, not a launch
  phase gate). Your calibration context for this invocation is
  ideation: candidates are still-being-evaluated approaches, not
  built artifacts. The Evidence Trail input contract does not apply
  here; the artifact you are gating is a multi-approach scoring
  matrix plus a tenth-man stress-test (or its unavailable-reason),
  described below.

  If you detect calibration drift during this invocation (your
  intuition disagrees with the formula, or the formula adjudicates a
  case you think it should not), record the drift via
  `bd remember --key='calibration:mx2-decision-maker:ideation:<topic>' '...'`
  with the topic and your reasoning. Tag with `ideation:` so calibrate
  reviews can keep ideation-specific calibration separate from
  autopilot/launch calibration.

  The user has not yet seen any of this. Your job is to call PROCEED,
  ITERATE, ESCALATE-QUESTIONS, or ESCALATE-ROUTE on the top-1, given
  the top-3 context, the tenth-man stress-test findings, and the
  consequence-of-wrong / verifiability columns.

  PROCEED if the top-1 is a defensible recommendation: rationale holds
  under tenth-man scrutiny, Consequence-of-wrong is acceptable for its
  Verifiability, and the gap to top-2 is meaningful (clear winner).

  ITERATE if the top-1 is uncertain BUT another Diverge pass with a
  focused weak-dimension target would plausibly resolve it: tenth-man
  surfaced an unaddressed high-impact concern, OR all top-3 cluster at
  similar Score with no clear winner, OR all top-3 share a weakness
  (e.g., all low-Verifiability with med+ Consequence). Specify which
  dimension is weak so the next Diverge pass can target it.

  ESCALATE-QUESTIONS if the ideation space feels infinitely bounded
  and 1-3 narrowing questions to the user would meaningfully focus the
  next pass. Use this when the candidates span fundamentally different
  problem framings (e.g., greenfield-vs-legacy is unresolved; the user
  has not signaled whether reversibility or speed matters more; the
  constraint set is undefined and the matrix cannot adjudicate). The
  cost of asking is one round-trip; the cost of not asking is wasted
  ideation on the wrong sub-problem. Prefer this over a low-confidence
  PROCEED when 1-2 focused questions would change which family of
  approaches wins.

  ESCALATE-ROUTE if the problem is mis-scoped for /ideate entirely:
  the candidates are not actually divergent (Phase 2 underperformed),
  the problem needs /investigate before /ideate (root cause is
  unknown), or the consequence space is too large for the
  verifiability available regardless of approach. No question to the
  user would help; the right move is a different skill.

  Top-K with full scoring matrix (K = 3 normally; fewer if Phase 2
  produced fewer):
  <top-K block>

  Tenth-man findings (or "Tenth-Man Lens unavailable: <reason>" if
  the Phase 3c dispatch failed):
  <tenth-man block>

  Return VERDICT (PROCEED / ITERATE / ESCALATE-QUESTIONS /
  ESCALATE-ROUTE), REASON (1-3 sentences), and:
  - if ITERATE: WEAK_DIMENSION (one of: verifiability, consequence,
    effort, distinctness, fit).
  - if ESCALATE-QUESTIONS: NARROWING_QUESTIONS (1-3 questions, each
    with a WHY clause stating what specifically gets unblocked by the
    answer). Keep total question count low; 1 focused question beats
    3 broad ones.
  - if ESCALATE-ROUTE: SUGGESTED_NEXT_SKILL (one of: /investigate,
    /converge, /challenge, human consultation)."
)
```

## Phase 4b: Branch on Verdict

### PROCEED
Continue to Phase 5 (Present). Record the verdict and reason in the
iteration log.

### ITERATE
Run another Diverge pass focused on the WEAK_DIMENSION (see
`specialists.md` ITERATE Re-dispatch section for the prompt
modifications per dimension). Merge new approaches into the candidate
pool. Re-score in Phase 3a-b. Re-run tenth-man (Phase 3c). Re-gate
(Phase 4a).

### ESCALATE-QUESTIONS
Surface the NARROWING_QUESTIONS to the user via the AskUserQuestion
tool (preferred for 2-3 multiple-choice questions; supports an
automatic "Other" option for free-text) or as a numbered list in chat
(for 1 open-ended question). Show each question with its WHY clause
inline so the user knows what each answer unblocks.

Frame the ask: "I have a few narrowing questions before the next
ideation pass would be productive. If you don't want to answer, reply
'you decide' or 'help me find it' and I'll commit to the top-1 with a
low-confidence annotation."

Constraints on questions:
- Max 3. One focused question is usually better than three.
- Each must name what specifically gets unblocked by the answer (the
  WHY clause). Questions without a clear consequence in the next
  Diverge pass are not worth a user cycle.
- Phrase as choices when possible, not as open-ended prompts.
  Multiple-choice has lower cognitive overhead.
- Do NOT ask about implementation details; ask about constraints,
  priorities, or problem-framing decisions.

After the user answers (or opts out): fold answers into the refined
problem (Phase 1), re-run Phase 2 (Diverge) with the narrowed scope,
re-run Phase 3 (Evaluate + tenth-man), and re-gate (Phase 4a). If the
user opted out, treat as a forced PROCEED with low-confidence
annotation.

ESCALATE-QUESTIONS can fire AT MOST ONCE per `/ideate` invocation.
After one user-question round, the next gate verdict must be PROCEED,
ITERATE, or ESCALATE-ROUTE.

### ESCALATE-ROUTE
Surface in Phase 5 output. Do not produce a recommendation; instead
present the candidates with the escalation reason and the
SUGGESTED_NEXT_SKILL. Common cases:
- "Root cause unknown" maps to suggest `/investigate` first.
- "Problem is actually a single approach, just unspecified" maps to
  suggest `/converge` directly.
- "Need a tech-lead's read on the problem space" maps to suggest
  dispatching `mx2-tech-lead` for sense-making.

## Phase 4c: Iteration Caps

Two separate caps, tracked independently:

- **ITERATE cap**: maximum 2 ITERATE rounds. After 2 ITERATE verdicts,
  force PROCEED with a "low-confidence" annotation OR fire
  ESCALATE-ROUTE if the underlying problem clearly cannot be ideated
  to a defensible answer.
- **ESCALATE-QUESTIONS cap**: maximum 1 user-question round per
  invocation. The user's cycles are precious; do not chain
  question-rounds.

## Iteration Log Format

Every round appears in the Phase 5 output, including Round 0 (no
iteration needed). The user sees how many cycles were needed and what
each round produced.

```
Iteration log:
- Round 0 (initial): 4 approaches generated, 3 survived dedup.
- Round 1: ESCALATE-QUESTIONS. Asked: "Is this greenfield or
  retrofit?" (WHY: greenfield approaches are bounded by 4
  considerations; retrofit approaches by 12). User answered:
  retrofit. Re-ran Diverge with retrofit constraint.
- Round 2: ITERATE (weak dimension: verifiability). Added 2
  approaches with verification paths.
- Round 3: PROCEED. Top-1 verifiability rose to high; tenth-man clean.
- Final verdict: PROCEED.
```
