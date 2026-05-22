# Phase 3 + 4.5: Stress-Test Subagent Prompts

This file holds the heavy subagent prompt templates for the Challenge,
Consult, and Tenth-Man dispatches in `/converge`. SKILL.md references
it; do not duplicate content back into SKILL.md.

## Phase 3a: Challenge (subagent)

Dispatched in parallel with Phase 3b (Consult). Both receive the draft
plan from Phase 2.

The Challenge subagent extracts and stress-tests assumptions underlying
the draft plan. Prompt the subagent with the draft plan and instruct
it to:

1. Extract assumptions using the challenge taxonomy triggers:
   - "We'll use..." / "We should..." (approach assumptions)
   - "The existing..." / "There's already..." (codebase state)
   - "This will..." / "This should..." (outcome assumptions)
   - References to code not Read in this conversation (codebase)
   - What's NOT mentioned (scope/completeness)
2. Apply the relevance gate: "If wrong, does the plan change?" Drop
   irrelevant assumptions. Target 3-7.
3. Score on fragility (SOLID/SOFT/FRAGILE) and impact (HIGH/LOW).
4. For FRAGILE assumptions: gather evidence via tools. Record searches
   and findings.
5. Produce a modification table: what needs to change based on evidence.

Include in the subagent prompt:

> Search `bd memories` for domain-specific gotchas relevant to this
> plan. Read source files to verify codebase assumptions. ALSO run
> `bd list --status=in_progress` and `bd show` any bead whose title or
> description contains a domain keyword or architecture/decision/Path
> keywords. The ratified architectural decision for the domain may
> live in a sibling bead under a different epic, and the decision
> often lives in the bead description rather than in `bd remember`,
> so `bd memories` keyword search alone will miss it. Surface any
> such decision as a HIGH-impact assumption to verify against the
> draft plan.
>
> INPUT_MODE: <problem-framed | mechanism-prescribed>
>
> If INPUT_MODE is `mechanism-prescribed`, apply ENHANCED scrutiny to
> the prescribed mechanism. Treat the mechanism as an explicit
> assumption ("we will use mechanism X to solve problem Y") and
> evaluate whether X is the right tool for Y. Common failure modes:
> the prescribed mechanism is actually a feature of an existing noun
> rather than a new noun, the prescribed mechanism contradicts a
> ratified architectural decision, the prescribed mechanism is
> over-engineered for the problem scope.

## Phase 3b: Consult (subagent)

Dispatched in parallel with Phase 3a (Challenge). Acts as a tech lead
coordinator.

Prompt the subagent to act as a tech lead coordinator. Provide the
draft plan and instruct it to:

1. Determine relevant specialists from the roster (see
   `consult/specialists.md`). Not every plan needs every specialist.
   Match specialists to concerns in the plan.
2. Spawn specialist subagents in parallel. Each specialist gets:
   - The relevant plan items (not the full plan if only some items
     are relevant)
   - A focused question (what specifically to evaluate)
   - Author Mode preamble: "CI has not run yet. Flag everything:
     style, types, lint, naming, and design issues."
3. Synthesize specialist outputs: themes, contradictions, gaps.
4. Triage findings: Fix now / Fix next / Defer / Won't fix.

Include in the subagent prompt:

> Focus on design-level concerns, not implementation details. The plan
> hasn't been built yet. For each plan item in your domain, probe for:
> Pipeline Bypass (does this add a new code path when the existing
> pipeline could serve?), Reasoning Chain gaps (do the steps actually
> follow from each other?), and Scope/Completeness (what production
> concerns - rollback, observability, migration - does this plan omit?).
> BEFORE forming findings, run `bd list --status=in_progress` and
> `bd show` any bead in the same domain. A ratified architectural
> decision in a sibling bead supersedes the draft plan; surface that
> contradiction explicitly rather than producing findings that
> re-litigate a closed question.
>
> INPUT_MODE: <problem-framed | mechanism-prescribed>
>
> If INPUT_MODE is `mechanism-prescribed`, evaluate whether the
> prescribed mechanism fits the problem on first-principles grounds.
> Do not assume the user's prescription is the right mechanism just
> because they prescribed it. Specifically check: (a) is this a new
> noun or a feature of an existing noun? (b) does this mechanism
> contradict any ratified architectural decision in the bead memories?
> (c) is this mechanism over-engineered or under-engineered for the
> problem scope?

## Parallel Dispatch (Mandatory)

**CRITICAL: Launch both Phase 3a and Phase 3b in a single message
with multiple Agent tool calls.** Do not serialize.

## Phase 4.5: Tenth-Man Lens

After Phase 4 produces the converged plan, dispatch `mx2-tenth-man`
with the converged plan as input. The tenth-man asks naive, dumb, or
obvious-but-unasked questions designed to surface risks the consensus
consult and challenge passes assumed away. Output is advisory; format
is the agent's standard `🔻` prefix block.

```
Agent(
  subagent_type="mx2-tenth-man",
  description="Adversarial stress-test of converged plan",
  prompt="Ask naive, dumb, or obvious-but-unasked questions about this
  converged plan. The plan has passed challenge + consult; your job is
  to surface risks both assumed away. Pay special attention to:
  (a) Convergence Delta = CONFIRMED on a non-trivial input (suspicious,
  may indicate specialists punted), (b) work items with
  Consequence=high and no concrete verification path,
  (c) terminology that may overload an existing concept (a 'Fulfillment
  service' that should be a feature of 'Coverage'),
  (d) INPUT_MODE = mechanism-prescribed where the mechanism was never
  challenged on first-principles grounds.

  Converged plan + convergence delta:
  <plan block>

  INPUT_MODE: <problem-framed | mechanism-prescribed>
  DELTA_CATEGORY: <CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT>

  Return your standard 🔻 prefix block. Do NOT recommend a winner or
  approve the plan; surface concerns only."
)
```

The tenth-man commentary appears in the Phase 5 output as a
`### Tenth-Man Lens` section AFTER the Convergence Delta and BEFORE
the Work Items, so the user sees adversarial dissent before reading
the recommended plan. If the agent returns `🔻 No concerns from this
lens`, still include the section with that exact line so the user
knows the pass ran (do not omit silently).

This is the lowest-traffic surface for tenth-man and the calibration
starting point. Calibration data accumulates here before tenth-man
expands to autopilot ESCALATE and decision-maker borderline calls.

### Failure handling

If the tenth-man dispatch fails (agent missing, calibration file
unreadable, transient error), note the failure as a one-line
"Tenth-Man Lens unavailable: <reason>" in the Phase 5 output and
proceed. Do not block convergence on advisory tooling, but do not
silently drop the pass either.

The Phase 4.6 gate receives the unavailable-reason as input and
factors it into the verdict (missing tenth-man pass lowers gate
confidence).
