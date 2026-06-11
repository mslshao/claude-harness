---
name: ideate
description: >
  (personal; shadows the project-tier `ideate` and takes precedence) Delta vs the project version: adds the mx2-decision-maker iterate gate (ITERATE/ESCALATE loops), accepts bead IDs as input, and hands the winner to /converge rather than stopping at presentation.
  Divergent approach generation with evaluative ranking, mandatory skeptic
  pass, and a decision-maker iterate gate. Use when you have a problem but
  do not yet know which of N approaches to pursue: "what are my options for
  X", "brainstorm Y", "tradeoffs between X and Y", "which approach should
  I take". Accepts free-text, Jira, beads, Slack threads, Confluence drafts,
  or transcripts. Produces 3-5 ranked approaches with a recommended winner,
  preserves rejected alternatives, hands off the winner to /converge.
  Distinct from /converge (stress-tests ONE approach), /consult
  (multi-specialist on SAME code), /challenge (assumption-test of an
  EXISTING plan), /pr-intel (PR review), /investigate (root cause).
argument-hint: "[problem statement, bead ID, Jira ticket, Slack URL, Confluence URL, or transcript]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent"]
---

# Ideate

Generate multiple approaches to a problem (divergent), rank them, gate the
winner, and hand off to `/converge`. The user sees one thing: the ranked
approach table plus the recommended winner.

## Why This Exists

The planning pipeline has a coverage gap upstream of `/converge`.
`/converge` starts from a refined approach and stress-tests it. `/consult`
is multi-specialist review on the SAME code. `/challenge` is adversarial
assumption extraction on an EXISTING plan. None solve: "I have a problem,
I do not yet know which of N approaches to pursue."

`/ideate` fills the gap. It produces approaches BEFORE there is a plan,
ranks them, runs an adversarial pass, runs a decision-maker gate, then
hands off the winner.

## Input

One or more of:
- Free-text problem statement (most common)
- Bead ID (`docr-\w+`)
- Jira ticket ID (`MX2-\d+`)
- Slack URL or pasted thread excerpt
- Confluence URL or pasted page body
- Conversation transcript

Mixed inputs are consolidated. Precedence on disagreement: inline text >
Slack/transcript > Confluence > Jira > bead notes. Disagreements surface
in Phase 5 "Open Assumptions".

## Pipeline Overview

```
problem
   |
   v
[Phase 1: Refine] <-------+
   |                      |  (loop-back on ESCALATE-QUESTIONS,
   v                      |   after user answers narrowing Qs)
[Phase 2: Diverge] <----+ |
   |                    | |  (loop-back on ITERATE, scoped to
   v                    | |   the named WEAK_DIMENSION)
[Phase 3: Evaluate] ----+ |
   |                      |
   v                      |
[Phase 4: Gate] ----------+
   |
   | (PROCEED only)
   v
[Phase 5: Present]
   |
   v
[Phase 6: Handoff to /converge]

Phase 4 verdicts:
  PROCEED            -> Phase 5
  ITERATE            -> Phase 2 (cap: 2 rounds)
  ESCALATE-QUESTIONS -> ask user, then Phase 1 (cap: 1 round)
  ESCALATE-ROUTE     -> Phase 5 with no recommendation; suggest a
                        different skill
```

Phases 1-4 are INTERNAL. The only user-facing output before Phase 5 is
the narrowing questions in ESCALATE-QUESTIONS (when fired).

## Process

### Phase 1: Refine (internal)

Load all inputs, strip bias, clarify the problem.

1. **Load inputs.** For each detected input type, fetch and parse:
   - Jira ID: `getJiraIssue` MCP call.
   - Bead ID: `bd show <id>`.
   - Slack URL `https://*.slack.com/archives/<CHANNEL>/p<TS>`: extract
     channel ID and message timestamp, then `slack_read_thread`.
   - Confluence URL `*.atlassian.net/wiki/spaces/<SPACE>/pages/<PAGE_ID>/<slug>`:
     extract `<PAGE_ID>`, then `getConfluencePage`.
   - Pasted text (Slack excerpt, transcript, page body, free-text): use
     as-is.

2. **Detect terseness.** If consolidated input is under ~30 words or
   lacks explicit constraints, invoke the `prompt-refiner` subagent:
   ```
   Agent(
     subagent_type="prompt-refiner",
     description="Refine problem for ideate",
     prompt="Expand this problem statement into a precise, actionable
     problem for divergent approach generation. Surface implicit
     constraints, scope boundaries, success criteria, and any
     codebase/domain context. Do NOT propose approaches or solutions.
     Original: <user input>"
   )
   ```
   Skip when input is already precise.

3. **Pre-load domain context** (best-effort, not a gate):
   ```bash
   bash /home/vscode/.claude/scratch/domain-matcher/match.sh "<problem text>" \
     | cut -d: -f1 | head -10
   ```
   For each matched keyword, `bd memories <keyword>` (top 5). If the
   problem names a known service or path under `src/python/mx2/`, read
   the service-level `CLAUDE.md` when one exists. Matcher misfires
   must NOT block ideation; skip and continue.

4. **Bias-stripping (mandatory).** Build TWO context blocks:
   - `Loaded context (problem only)`: problem framing, constraints,
     prior evidence. NO user solution recommendations.
   - `User's prior thinking`: any solution leanings, prescribed
     mechanisms, or preliminary recommendations from inputs.

   Phase 2 specialists receive ONLY the problem-only block. The
   orchestrator retains the prior-thinking block for Phase 5 narrative.
   Convergence with prior thinking is fine and worth noting; the goal
   is to NOT pre-load the user's answer into the specialists' question.

5. **Detect scope-signal.** Set a `SCOPE_SIGNAL` flag if the problem
   carries scope-signal words (lightweight, simple, minimal, quick,
   basic, just, for most users). When set, Phase 2 treats the
   minimal-viable candidate as the front-runner to beat, and the Phase 3
   right-sizing flag weights proportionality harder.

6. **Output**: refined problem (1-3 sentences with constraints), the two
   context blocks, and the `SCOPE_SIGNAL` flag. Not shown to user.

### Phase 2: Diverge (internal, parallel)

Generate 3-5 distinct candidate approaches via parallel specialists.

For the full protocol (approach-count heuristic, specialist routing
table, fallback logic, complete specialist prompt template, ITERATE
re-dispatch instructions), see [specialists.md](specialists.md).

Key invariants:
- Launch all specialists in a single message with multiple Agent tool
  calls. Serializing defeats parallelism.
- Specialists receive ONLY the problem-only context block. Bias-stripping
  is structural, not advisory.
- `mx2-tech-lead` is always in the roster as the broadest-shape lens.
- **Minimal-viable candidate is mandatory in the candidate pool.** One
  approach is always the minimal-viable version: the smallest thing
  delivering ~80% of the *stated* goal, explicitly labeled. Every
  specialist is asked to steelman, which skews the pool elaborate;
  without a simple anchor on the table the ranking cannot pick simple
  even when simple is correct. It is the reference point for the Phase 3
  right-sizing flag. See [specialists.md](specialists.md) for sourcing.
- Each specialist returns 1-2 approaches with Shape, Context, Steelman,
  Tradeoff, Codebase touch points, Verifiability, Verification path,
  and Consequence per approach (the format Phase 3 consumes).

### Phase 3: Evaluate (internal)

Rank approaches on the multi-criteria scoring matrix, then run mandatory
skeptic on the top-3.

For the full scoring matrix (8 columns: Context, Effort, Risk,
Reversibility, Fit, Rules-alignment, Verifiability, Consequence), the
composite Score formula, the override rules, AND the Phase 3c
skeptic dispatch prompt with edge-case + failure handling, see
[scoring-matrix.md](scoring-matrix.md).

Key invariants:
- Composite Score is a tiebreaker; the qualitative tradeoff drives the
  winner pick.
- An approach that contradicts a `.claude/rules/*.md` rule is forced
  to last place regardless of Score.
- Consequence=high AND Verifiability=low is also forced to last place
  (trust-asymmetry override).
- Skeptic (`mx2-skeptic`) runs on the top-3 by Score. Mandatory,
  not opt-in. Findings fold into Phase 5 as a `Skeptic Lens` block.
  When fewer than 3 approaches survive Phase 2, run on whatever
  exists. If dispatch fails, note "Skeptic Lens unavailable" and
  proceed; do not block on advisory tooling.

### Phase 4: Iterate (internal)

Run a decision-maker gate on the top-3. The gate may PROCEED, ITERATE,
ESCALATE-QUESTIONS, or ESCALATE-ROUTE.

For the full decision-maker dispatch prompt (with ideation-mode
preamble), branch logic per verdict, narrowing-question constraints,
and iteration caps, see [iterate-gate.md](iterate-gate.md).

Key invariants:
- The gate is `mx2-decision-maker` invoked with `MODE: IDEATION GATE`
  preamble. Calibration drift gets recorded with
  `bd remember --key='calibration:mx2-decision-maker:ideation:<topic>'`.
- ITERATE re-runs Phase 2 with a focused WEAK_DIMENSION prompt
  modification. Cap: 2 ITERATE rounds per invocation.
- ESCALATE-QUESTIONS poses 1-3 focused narrowing questions to the user
  via `AskUserQuestion`. Each question must include a WHY clause
  naming what gets unblocked. Cap: 1 user-question round per
  invocation.
- ESCALATE-ROUTE surfaces in Phase 5 with no recommendation and a
  suggested next skill.

### Phase 5: Present

First synthesis-level output the user sees.

```markdown
## Ideate: <problem topic, 3-8 words>

### Refined Problem
<1-3 sentences>

### Iteration Log
<Always present; even Round 0 (no iteration) appears so the user sees
the gate ran. List each round with verdict + action taken.>

### Approaches

| # | Approach | Context | Effort | Risk | Rev | Fit | Rules | Verif | Conseq | Score |
|---|----------|---------|--------|------|-----|-----|-------|-------|--------|-------|
| 1 | <title> | legacy | M | low | easy | match | aligned | high | low | 19 |
| ... |

(Column key: Rev = Reversibility, Verif = Verifiability, Conseq =
Consequence of wrong. Context is annotation, not numerically scored.)

Per-approach narrative (in Score order):

**N. <title>** (Score: <X>, Context: <Y>)
<Steelman + key tradeoff.>
Codebase touch points: <paths>.
Verification path: <how to validate this before committing>.

---

### Recommended Winner: Approach <N>  (low-confidence)?
<Present this section UNLESS final verdict was ESCALATE-ROUTE. 1-3
sentences. State the Consequence-of-wrong / Verifiability pairing
explicitly so the user can sanity-check the asymmetry.

If the Phase 3 right-sizing flag fired (the winner is materially heavier
than the minimal-viable candidate), the rationale MUST justify the extra
complexity against the minimal-viable variant (what each extra component
buys), or switch the recommendation to the minimal-viable candidate. If
SCOPE_SIGNAL was set in Phase 1, lean toward the minimal-viable variant
unless a stated constraint demands more.

If the gate forced a low-confidence PROCEED (2 ITERATE rounds hit the
cap, or the user opted out of ESCALATE-QUESTIONS with "you decide"),
suffix the section header with `(low-confidence)` and add a
`Low-confidence reason:` line at the end of the rationale stating
which path triggered it (e.g., "2 ITERATE rounds exhausted without
resolving Verifiability gap" or "user opted out of narrowing
questions; ideation space remains broad"). Without the suffix +
reason, the user has no signal that the recommendation is provisional.>

### OR: Escalation: No Winner Recommended (only when final verdict was ESCALATE-ROUTE)
<Replaces "Recommended Winner" when the gate fired ESCALATE-ROUTE. 2-3
sentences naming the SUGGESTED_NEXT_SKILL and the reason no
recommendation is being made. Format:

"The decision-maker gate fired ESCALATE-ROUTE: <reason from gate>.
No winner is being recommended; the suggested next step is
<SUGGESTED_NEXT_SKILL: /investigate, /converge, /challenge, or
dispatching mx2-tech-lead>. The candidate approaches and their scoring
are preserved above for reference, but /ideate is not the right tool
for this problem.">

### High-Consequence Callout (only when any candidate has Consequence=high)
<Surface every Consequence=high approach with one-line "what could go
wrong". Even rejected high-consequence approaches deserve this; the
user may override the recommendation.>

### Prior Thinking Comparison (only when input contained a user solution recommendation)
<Compare specialist output against the user's prior framing. One of:
"converged on <prior approach> (positive confirmation)" OR "diverged;
recommended <winner> because <reason>" OR "produced an
adjacent-but-novel approach the prior was reaching toward".>

### Rejected Alternatives
<1 sentence per non-winning approach: why rejected + revisit-trigger
clause naming the condition under which this alternative becomes the
right choice. Per CLAUDE.md "Preserve dissent in durable records".>

### Skeptic Lens
<Verbatim 🔻 block from Phase 3c. Always present (mandatory pass).
Include the "no concerns" line verbatim if that was the result.>

### Open Assumptions
<Any unresolved framing disagreements between mixed inputs, fuzzy
constraints, or other items the user should sanity-check.>

---

### Next Step
Run `/converge "<chosen approach + one-line shape>"` to stress-test the
winner and produce an implementation plan. `/ideate` does not
auto-invoke `/converge`.

If the final verdict was LOW-CONFIDENCE or ESCALATE-ROUTE, do NOT
proceed to `/converge` without addressing the gate's concern.
```

### Phase 6: Handoff (no auto-invocation)

Stop after Phase 5. Do NOT call `/converge` automatically. The user
reads the table, picks a winner (which may differ from the
recommendation), and runs `/converge` manually with the chosen approach
as input.

Rationale: the user may refine the winner's phrasing, combine elements
of two approaches, or reject the table entirely. Auto-invocation
removes that judgment.

## Distinctions

Order matches the frontmatter description:

- **vs `/refine`**: `/refine` takes terse user input and produces a
  precise prompt. `/ideate` takes a precise problem and produces
  approaches. `/ideate` may invoke `prompt-refiner` internally in
  Phase 1.
- **vs `/converge`**: `/ideate` is divergent then convergent on a
  winner. `/converge` starts from ONE approach and stress-tests it
  through refine + decompose + challenge + consult + synthesize.
  `/ideate` produces the input to `/converge`.
- **vs `/challenge`**: `/challenge` extracts assumptions from an
  EXISTING plan. `/ideate` has no plan yet; it produces candidate
  approaches before any plan exists.
- **vs `/consult`**: `/consult` runs parallel specialists with
  DIFFERENT lenses on the SAME code. `/ideate` runs parallel
  specialists generating DIFFERENT approaches to the SAME problem.

## When NOT to Use

- **One obvious approach exists**: skip `/ideate`, go straight to
  `/converge`. `/ideate` is overhead when the divergent step has only
  one candidate.
- **Code review or PR context**: use `/pr-intel`.
- **Bug investigation**: use `/investigate`. If the investigation
  reveals multiple fix candidates, THEN `/ideate` over those candidates.
- **Stress-testing one plan**: use `/challenge`.

## Dry-Run Walkthroughs

Two end-to-end examples (PROCEED on Round 0; ESCALATE-QUESTIONS then
ITERATE then PROCEED) live in [walkthroughs.md](walkthroughs.md).

## Rules

- **No intermediate output.** Phases 1-4 are invisible. Phase 5 is the
  first synthesis-level visible output. Exception: the narrowing
  questions in ESCALATE-QUESTIONS are explicitly user-facing.
- **Parallel is mandatory.** Phase 2 specialists run in parallel via
  a single message with multiple Agent calls. Serializing defeats the
  point.
- **No auto-invocation of /converge.** Phase 6 is a suggested next
  step, not a tool call.
- **Strip user solution bias before Phase 2.** Specialists receive only
  the problem-only context block. Convergence with prior thinking is a
  positive confirmation signal; same conclusions are fine, but
  pre-loading the user's answer into the specialists' question
  defeats the purpose.
- **Mixed-input precedence is fixed.** Inline text > Slack/transcript
  > Confluence > Jira > bead notes. Surface disagreements in Open
  Assumptions.
- **Steelman, do not strawman.** Each approach in Phase 2 must be the
  strongest version of itself.
- **Distinct approaches, not variants.** Merge near-duplicates during
  Phase 2 collection.
- **Minimal-viable candidate always on the table.** One of the 3-5
  approaches is the minimal-viable version (~80% of the goal), explicitly
  labeled. When it is materially lighter than the recommended approach,
  the Phase 3 right-sizing flag fires and Phase 5 must justify the extra
  complexity against it; YAGNI is the default (CLAUDE.md Scope
  discipline). Scope built for a hypothetical future is a tradeoff to
  name, not a free win.
- **Score is a tiebreaker, not the rationale.** Composite Score drives
  ordering; the qualitative tradeoff drives the winner pick.
- **Rules contradictions always lose.** Forced last place regardless
  of Score. Existing rules encode hard-won lessons.
- **Consequence-of-wrong outweighs upside-of-right.** One wrong call
  that destroys a workstream costs more than nine right calls. The
  Consequence=high / Verifiability=low override forces last place
  regardless of how well the approach scores elsewhere. When two
  approaches tie on the rest of the matrix but differ on Consequence,
  the lower-Consequence approach wins decisively.
- **Skeptic is mandatory, not optional.** Phase 3c runs on the
  top-3 by Score (or fewer if Phase 2 produced fewer).
- **Iterate when the gate says iterate.** ITERATE cap is 2 rounds.
  Beyond that, force PROCEED with low-confidence annotation OR
  ESCALATE-ROUTE.
- **Ask the user when ideation feels infinitely bounded.**
  ESCALATE-QUESTIONS cap is 1 round per invocation. Max 3 questions
  per round, each with a WHY clause. The user can reply "you decide"
  to opt out.
- **Iteration log is always visible.** Even Round 0 appears so the
  user can see the gate ran.
- **Preserve dissent.** Rejected alternatives appear in Phase 5 with
  "why rejected" + revisit-trigger clause. Per CLAUDE.md "Preserve
  dissent in durable records".
- **Calibration soak is expected.** The decision-maker invoked in
  Phase 4 was calibrated for autopilot and launch gates, not
  ideation. First 3-5 `/ideate` invocations are calibration soak.
  Drift gets recorded via
  `bd remember --key='calibration:mx2-decision-maker:ideation:<topic>'`.
- **Calibrated for code-shaped problems.** The specialist roster, the
  Fit-to-codebase column, and the Verification-path framing assume
  the output is a codebase change. Non-coding mode is best-effort;
  several matrix columns become "N/A" and qualitative narrative
  carries more weight.

## Additional Resources

- [specialists.md](specialists.md): Phase 2 roster table, fallback
  logic, full specialist prompt template, ITERATE re-dispatch.
- [scoring-matrix.md](scoring-matrix.md): Phase 3 column definitions,
  composite Score formula, overrides.
- [iterate-gate.md](iterate-gate.md): Phase 4 decision-maker dispatch
  prompt, branch logic, caps.
- [walkthroughs.md](walkthroughs.md): two end-to-end examples.
