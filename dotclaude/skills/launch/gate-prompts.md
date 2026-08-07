# Phase 3.5 + 3.6: Skeptic Lens and Decision-Maker Gate

This file holds the adversarial-pass and proceed/iterate-gate prompts
that run after Phase 3 synthesize. SKILL.md and plan-pipeline.md
reference it; do not duplicate content back into either.

## Why These Phases Exist

The plan has passed challenge + consult (Phase 3a + 3b) and been
synthesized (Phase 3c). But specialists may have punted, and a plan
that survived stress-testing might still fail a "would you bet on
this" check. The cost of a bad plan in `/launch` is real commits,
real PR review burden, and worktree cleanup, so two more safety
checkpoints run before the user sees anything: an adversarial pass
(3.5) and a decision-maker gate (3.6).

## Phase 3.5: Skeptic Lens

Dispatch `mx2-skeptic` for an adversarial pass on the converged
plan. The agent asks naive, dumb, or obvious-but-unasked questions
designed to surface risks the consensus challenge + consult passes
assumed away.

```
Agent(
  subagent_type="mx2-skeptic",
  description="Adversarial stress-test of launch plan",
  prompt="Ask naive, dumb, or obvious-but-unasked questions about this
  launch plan. The plan has passed challenge + consult; your job is to
  surface risks both assumed away BEFORE the agent team starts writing
  code. Pay special attention to:
  (a) DELTA_CATEGORY = CONFIRMED on a non-trivial input (suspicious,
  may indicate specialists punted),
  (b) work items with Consequence=high and no concrete Verification
  path,
  (c) terminology that may overload an existing concept (the
  Fulfillment-vs-Coverage failure mode: prescribed noun should be a
  feature of an existing noun),
  (d) INPUT_MODE = mechanism-prescribed where the mechanism was never
  challenged on first-principles grounds,
  (e) phase gates that read programmatic but actually require human
  judgment to verify,
  (f) Proportionality: is this plan over-built for the goal's stated
  weight? Is there a materially simpler 80/20 plan? If the goal carries
  scope-signal words (lightweight / simple / minimal / quick / for most
  users), name the minimal-viable variant and what each extra component
  buys before the agent team writes code against it.

  Converged plan + convergence delta:
  <plan block>

  INPUT_MODE: <problem-framed | mechanism-prescribed>
  DELTA_CATEGORY: <CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT>

  Return your standard 🔻 prefix block. Do NOT approve the plan or
  recommend a winner among approaches; surface concerns only."
)
```

### No-concerns case

If the agent returns `🔻 No concerns from this lens`, include that
line verbatim in the Phase 4 output so the user can see the pass ran.
Do NOT omit silently.

### Failure handling

If the dispatch fails (agent missing, transient error), note the
failure as a one-line "Skeptic Lens unavailable: <reason>" in the
Phase 4 output and proceed. Do not block on advisory tooling. The
Phase 3.6 gate receives the unavailable-reason as input and factors
it into the verdict (a missing skeptic pass lowers gate confidence).

### Stage Event Write

After skeptic returns (or fails), write a `[LAUNCH_STAGE stage=skeptic ...]`
entry. The 🔻 block is usually inline-sized (<2KB); only goes to scratch
if concerns are extensive.

```bash
ROUND=${ITERATE_ROUND:-0}

if [ "$SKEPTIC_STATUS" = "unavailable" ]; then
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=skeptic round=$ROUND status=unavailable reason=$REASON ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
elif [ "$SKEPTIC_CONCERNS" = "" ]; then
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=skeptic round=$ROUND status=no-concerns ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
elif [ "$SKEPTIC_SIZE" -lt 2048 ]; then
  # Inline the 🔻 block in the entry (escape newlines as needed)
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=skeptic round=$ROUND status=concerns concerns=$(echo "$SKEPTIC_OUTPUT" | tr '\n' ' ' | tr ' ' '_') ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
else
  mkdir -p "$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID"
  SKEPTIC_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/skeptic-$ROUND.md"
  echo "$SKEPTIC_OUTPUT" > "$SKEPTIC_PATH"
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=skeptic round=$ROUND status=concerns path=$SKEPTIC_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
fi
```

## Phase 3.6: Decision-Maker Gate

Dispatch `mx2-decision-maker` for a proceed/iterate gate on the
synthesized plan. This is the calibration safety net before burning
a worktree and an agent team.

```
Agent(
  subagent_type="mx2-decision-maker",
  description="Proceed/iterate gate on launch plan",
  prompt="**MODE: LAUNCH GATE.** You are gating an implementation plan
  from /launch (not an autopilot checkpoint, not an ideation gate,
  not a convergence gate). Calibration context: the plan has passed
  challenge + consult + skeptic, and IS ABOUT TO drive an agent
  team that writes real code and creates a real PR. The cost of a
  bad plan is real commits, real PR review burden, and a worktree
  cleanup; the gate's threshold should reflect that.

  If you detect calibration drift, record via
  `bd remember --key='calibration:mx2-decision-maker:launch:<topic>' '...'`.

  PROCEED if the plan is defensible: convergence delta is concrete,
  every work item has a Verification path, Consequence=high items
  have matching Verification paths or are explicitly downgraded,
  phase gates are programmatically verifiable, skeptic findings
  either resolved or surfaced as Open Assumptions for user adjudication.
  CONFIRMED delta is acceptable IF the input was simple or specialists
  offered concrete evidence; suspicious otherwise.

  ITERATE if the plan is uncertain BUT another challenge+consult pass
  with a focused weak-dimension target would plausibly resolve it.
  Specify WEAK_DIMENSION (one of: verification, consequence, scope,
  decomposition, mechanism, phase-gates, proportionality).
  - mechanism is canonical for Fulfillment-vs-Coverage: INPUT_MODE =
    mechanism-prescribed AND DELTA_CATEGORY = CONFIRMED on a non-trivial
    plan usually means the prescribed mechanism was rubber-stamped.
  - verification: work items lack Verification paths.
  - consequence: high-Consequence items have no risk-reduction analysis.
  - phase-gates: gate criteria are not programmatically verifiable
    (e.g., 'implementation complete' rather than 'pants check passes').

  ESCALATE-QUESTIONS if the plan space is too ambiguous to launch on
  and 1-3 narrowing questions to the user would meaningfully focus
  the next pass. Use this for: 'the ticket prescribes mechanism Y
  with two reasonable interpretations', 'this could be a feature of
  existing Z or a new noun, the choice changes the agent roster',
  'the scope crosses service boundaries; one or two?'. Constraints:
  max 3 questions, each with a WHY clause naming what gets unblocked.

  ESCALATE-ROUTE if /launch is the wrong skill: the ticket is too
  rough and needs /converge to produce a plan first (no clear
  mechanism, scope undefined), or multiple plausible approaches and
  the user hasn't picked one (route to /ideate), or root cause is
  unknown (route to /investigate before fixing).

  Converged plan + convergence delta + delta category:
  <plan block>

  INPUT_MODE: <problem-framed | mechanism-prescribed>
  DELTA_CATEGORY: <CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT>

  Skeptic findings (or 'Skeptic Lens unavailable: <reason>'):
  <skeptic block>

  Iteration History: <prior gate verdicts this /launch invocation, or
  'First evaluation'>

  Return VERDICT (PROCEED / ITERATE / ESCALATE-QUESTIONS /
  ESCALATE-ROUTE), REASON (1-3 sentences), and:
  - if ITERATE: WEAK_DIMENSION.
  - if ESCALATE-QUESTIONS: NARROWING_QUESTIONS (1-3 questions, each
    with a WHY clause).
  - if ESCALATE-ROUTE: SUGGESTED_NEXT_SKILL (one of: /converge,
    /ideate, /investigate)."
)
```

### Branch on Verdict

#### PROCEED
Continue to Phase 4 (user approval). Record verdict + reason in the
iteration log; the iteration log appears in the Phase 4 approval output.

#### ITERATE
Re-run Phase 2 (decompose) and Phase 3 (challenge + consult) with a
focused WEAK_DIMENSION instruction:

- `verification`: "Every work item must include a Verification path
  achievable in under 1 hour before committing."
- `consequence`: "For high-Consequence items, add explicit
  risk-reduction sub-items (rollback plan, feature flag, observability)."
- `mechanism`: "Treat the user-prescribed mechanism as one candidate
  among many. Evaluate at least one alternative mechanism and surface
  the comparison in the convergence delta. Canonical
  Fulfillment-vs-Coverage check."
- `decomposition`: "Re-evaluate work item granularity; merge
  over-decomposed items, split under-decomposed items."
- `scope`: "Identify what is in vs out of scope; surface items that
  crossed the boundary."
- `phase-gates`: "Re-write each phase gate as a programmatically
  verifiable command. No prose criteria."
- `proportionality`: "Re-decompose toward the minimal-viable variant.
  Name the smallest 80/20 plan that meets the stated goal, then keep only
  the work items whose extra value over it is justified by a STATED
  constraint (not a hypothetical future). The cost here is real commits,
  so right-sizing before the agent team starts matters."

Re-synthesize (Phase 3c). Re-run skeptic (Phase 3.5). Re-gate
(Phase 3.6).

#### ESCALATE-QUESTIONS
Surface NARROWING_QUESTIONS to the user via the AskUserQuestion tool
(preferred for 2-3 multiple-choice questions; supports an "Other"
option for free-text answers) or as a numbered list in chat (for 1
open-ended question). Each question shows its WHY clause inline so
the user knows what each answer unblocks.

Non-interactive callers (agent dispatch, /autopilot embedding, any
context where no human can answer): do NOT block on AskUserQuestion.
Treat as the 'you decide' opt-out: orchestrator-derive
VERDICT=LOW_CONFIDENCE, proceed, and carry the unanswered narrowing
questions into the plan's Open Assumptions.

EXCEPTION: `--gate=agent` launches (unattended epic nodes, docr-mpgav) do
NOT use the LOW_CONFIDENCE opt-out. Unattended nodes run pre-converged
plans; if 3.6 still has narrowing questions, the node's spec was not
actually converged, and proceeding on low confidence unattended compounds
the error across a stacked chain. Halt loudly per durable-state.md
"Unattended decision-point policy" and fold the questions into the halt
report. (/autopilot embedding keeps the LOW_CONFIDENCE path: its own Gate 1
supervises the outcome.)

Frame the ask: "I have a few narrowing questions before launching
the agent team would be productive. If you don't want to answer,
reply 'you decide' and I'll proceed with the current plan as
low-confidence."

Constraints on questions:
- Max 3. One focused question is usually better than three.
- Each must name what specifically gets unblocked by the answer (the
  WHY clause).
- Phrase as choices when possible, not as open-ended prompts.
- Do NOT ask about implementation details; ask about constraints,
  priorities, or problem-framing decisions.

After user answers (or opts out), fold answers into the brief
(Phase 1), re-run Phase 2 + 3 + 3.5 + 3.6. If user opted out, force
PROCEED with low-confidence annotation in the Phase 4 output.

ESCALATE-QUESTIONS can fire AT MOST ONCE per `/launch` invocation.

#### ESCALATE-ROUTE
Surface in Phase 4 output. No agent team is dispatched. Show the
user the converged plan + the gate's reason + the SUGGESTED_NEXT_SKILL.
Common cases:

- "Multiple plausible mechanisms; user has not picked one" maps to
  suggest `/ideate` first.
- "Plan is too rough; needs convergence first" maps to suggest
  `/converge` first.
- "Root cause unknown" maps to suggest `/investigate` first.

### Iteration Caps

Two separate caps, tracked independently:

- **ITERATE cap**: maximum 2 ITERATE rounds. After 2 ITERATE verdicts,
  force PROCEED with a "low-confidence" annotation OR fire
  ESCALATE-ROUTE if the underlying problem clearly cannot be planned
  to a defensible state.
- **ESCALATE-QUESTIONS cap**: maximum 1 user-question round per
  invocation. The user's cycles are precious; do not chain
  question-rounds.

Cap counts are derived from `[LAUNCH_STAGE stage=gate ...]` entries
in the bead notes:
- ITERATE count = `grep -c 'stage=gate.*status=iterate' notes`
- ESCALATE-QUESTIONS count = `grep -c 'stage=gate.*status=escalate-questions' notes`

This means the caps survive cold-start: if a launch died after gate
round 1 said iterate, cold-start sees one iterate entry and knows it
has one more iterate budget before forcing PROCEED.

### Stage Event Write (Gate)

After the gate returns, write a `[LAUNCH_STAGE stage=gate ...]` entry.
The verdict + reason are small (inline). WEAK_DIMENSION,
NARROWING_QUESTIONS, or SUGGESTED_NEXT_SKILL go inline when short or
to scratch when extensive.

```bash
ROUND=${ITERATE_ROUND:-0}
# The agent returns HYPHENATED verdicts (ESCALATE-QUESTIONS / ESCALATE-ROUTE);
# normalize to underscores so the case patterns match. LOW_CONFIDENCE is never
# returned by the agent: the ORCHESTRATOR sets VERDICT=LOW_CONFIDENCE itself
# when forcing a low-confidence proceed (ITERATE cap hit, or the user opted
# out of narrowing questions with "you decide").
VERDICT=$(echo "$VERDICT" | tr '-' '_')
# Event values must not contain spaces (durable-state event format rule):
REASON_SHORT=$(echo "$REASON_SHORT" | tr ' ' '_')

case "$VERDICT" in
  PROCEED)
    bd update "$LAUNCH_BEAD_ID" --append-notes \
      "[LAUNCH_STAGE stage=gate round=$ROUND status=proceed ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
    ;;
  LOW_CONFIDENCE)
    bd update "$LAUNCH_BEAD_ID" --append-notes \
      "[LAUNCH_STAGE stage=gate round=$ROUND status=low-confidence verdict_reason=$REASON_SHORT ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
    ;;
  ITERATE)
    WEAK_DIM_LOWER=$(echo "$WEAK_DIMENSION" | tr '[:upper:]' '[:lower:]')
    bd update "$LAUNCH_BEAD_ID" --append-notes \
      "[LAUNCH_STAGE stage=gate round=$ROUND status=iterate weak_dimension=$WEAK_DIM_LOWER verdict_reason=$REASON_SHORT ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
    ;;
  ESCALATE_QUESTIONS)
    QUESTIONS_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/gate-$ROUND-questions.md"
    echo "$NARROWING_QUESTIONS_FORMATTED" > "$QUESTIONS_PATH"
    bd update "$LAUNCH_BEAD_ID" --append-notes \
      "[LAUNCH_STAGE stage=gate round=$ROUND status=escalate-questions path=$QUESTIONS_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
    ;;
  ESCALATE_ROUTE)
    SKILL_LOWER=$(echo "$SUGGESTED_NEXT_SKILL" | tr -d '/')
    bd update "$LAUNCH_BEAD_ID" --append-notes \
      "[LAUNCH_STAGE stage=gate round=$ROUND status=escalate-route suggested_next_skill=$SKILL_LOWER verdict_reason=$REASON_SHORT ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
    ;;
esac
```

For ESCALATE-QUESTIONS specifically, when the user answers, write a
second entry:

```bash
ANSWERS_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/gate-$ROUND-answers.md"
echo "$USER_ANSWERS" > "$ANSWERS_PATH"
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_STAGE stage=gate round=$ROUND status=user-answered path=$ANSWERS_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

Cold-start sees gate=escalate-questions without user-answered →
re-prompt. Sees both → fold answers into refined scope and resume
Phase 1 round=N+1.

## Phase 4 Agent Approval Gate (`--gate=agent`)

Added 2026-07-17 (docr-he4j9; decision record docr-1vqfg). When the invocation
carries `--gate=agent`, the Phase 4 approval hard-stop is performed by
`mx2-decision-maker` instead of the human. This is a DIFFERENT call site and a
DIFFERENT job than the Phase 3.6 gate above: 3.6 judges plan quality
mid-pipeline; Phase 4 authorizes execution. Keep them distinguishable in
dispatch and in calibration data.

**Double-run guard (before dispatching)**: if this run's bead log already
contains a `[LAUNCH_STAGE stage=gate ... status=proceed]` entry from Phase 3.6
(non-bypass runs), Phase 4 auto-passes on that durable evidence: write the
approval event (below) with `via=3.6-evidence` and continue. A resumed or
rolled-over session that lands at Phase 4 WITHOUT that event re-runs this
dispatch; never auto-pass from an unrecorded verdict. Bypass runs (the normal
/campaign path) skipped 3.6 entirely, so this dispatch always runs there.

```
Agent(
  subagent_type="mx2-decision-maker",
  description="Phase 4 approval gate (agent-substituted)",
  prompt="**MODE: LAUNCH GATE, POSITION: approval.** You are substituting for
  the HUMAN at /launch's Phase 4 execution-approval hard stop (--gate=agent;
  unattended run, typically a /campaign node on a pre-converged bead). This is
  NOT the Phase 3.6 plan-quality gate: your question is 'authorize executing
  this plan now', the one-shot commitment a human would otherwise make.

  Record calibration drift under
  calibration:mx2-decision-maker:launch-approval:<topic> (distinct namespace
  from the 3.6 gate's launch:* entries).

  Verdict semantics for THIS position: PROCEED authorizes execution. Use
  anything else ONLY for a genuine stop-condition: the plan/bead is not
  actually pre-converged (bypass elements missing), a still-in-force ESCALATE
  condition fires (security/PII, hard-to-reverse, cross-team), or the artifact
  contradicts a ratified decision. Do NOT return ITERATE for polish: there is
  no converge loop behind this gate to iterate into.

  <converged node plan: the bead description + evidence>

  Return your standard output contract (DECISION/VERDICT + GATES block +
  CALIBRATION on PROCEED)."
)
```

**Unattended verdict contract (branching)**: PROCEED continues to Phase 5.
ANY other verdict = node failure: write the event, then halt loudly per
durable-state.md "Unattended decision-point policy" (PushNotification + bead
comment + stop). Never loop into bypass-skipped phases; never surface
ESCALATE-QUESTIONS to a user who is not there (fold the questions into the
halt report instead).

**Stage event write**:

```bash
# via = agent | 3.6-evidence | human (the default path writes human)
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_STAGE stage=approval status=$STATUS via=$VIA ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

Cold-start rule: Phase 5 must never start without a
`stage=approval status=proceed` event in the log; a resumed session that finds
execution artifacts but no approval event halts loudly (this is the durable
equivalent of the human hard-stop).

## Iteration Log Format

Every round (including Round 0) appears in the Phase 4 approval-gate
output's Iteration Log so the user can see how many cycles were needed
and what each round produced.

```
Iteration log:
- Round 0 (initial): N work items drafted; DELTA_CATEGORY=<X>.
- Round 1 (if any): VERDICT (REASON). Action: <what changed>.
- Round 2 (if any): VERDICT (REASON). Action: <what changed>.
- Final verdict: PROCEED | LOW-CONFIDENCE | ESCALATE-ROUTE.
```
