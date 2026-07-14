# Phase 3 + 4.5: Stress-Test Subagent Prompts

This file holds the heavy subagent prompt templates for the Challenge,
Consult, and Skeptic dispatches in `/converge`. SKILL.md references
it; do not duplicate content back into SKILL.md.

## Phase 3a: Challenge (subagent)

Dispatched in parallel with Phase 3b (Consult). Both receive the draft
plan from Phase 2.

The Challenge subagent extracts and stress-tests assumptions underlying
the draft plan. Dispatch explicitly as
`Agent(subagent_type="general-purpose", description="Challenge draft plan", prompt=...)`;
do NOT leave the type implicit (`mx2-tech-lead` is forbidden in this
roster per `decision:tech-lead-not-in-automation-2026-04-30`). The prompt
provides the draft plan and instructs the subagent to:

1. Extract assumptions by reading the full taxonomy at
   `~/.claude/skills/challenge/assumption-taxonomy.md` and applying its
   9 categories and their subtriggers (Serialization Safety, Infrastructure
   Completeness, Identity/Uniqueness Key, Control-Verb State-Transition
   Completeness, Mechanism-Homogeneity, and any added since). Do NOT
   re-derive a condensed trigger list from memory: a prior version of
   this dispatch embedded its own 5-bullet summary inline, which meant
   the taxonomy file's own subtriggers (Serialization Safety,
   Infrastructure Completeness) never actually reached this dispatch, and
   the 3 subtriggers below were added to the file 2026-07-10 specifically
   because a converge run (the overwatch skill) hit all 3 gaps and none
   were covered by the condensed list. Reading the file directly is the
   only way a future taxonomy addition reaches this dispatch without a
   second edit here.
2. Apply the relevance gate: "If wrong, does the plan change?" Drop
   irrelevant assumptions. Target 3-7.
3. Score on fragility (SOLID/SOFT/FRAGILE) and impact (HIGH/LOW).
4. For FRAGILE assumptions: gather evidence via tools. Record searches
   and findings. Before asserting a cited fact "doesn't exist" or "is
   fabricated," check whether it could be a same-session artifact (a
   file the orchestrator wrote earlier in THIS conversation, not yet
   part of your training data or prior context, but fully readable via
   Read/Grep right now). A grep that misses because it searched the
   wrong file, not because the citation is false, is a false-negative
   absence claim; verify against the freshest matching file before
   concluding fabrication.
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

## Phase 3b: Consult (orchestrator-dispatched specialists)

Dispatched in parallel with Phase 3a (Challenge). YOU (the orchestrator,
in the main conversation) dispatch the specialists directly. Do NOT
delegate the fan-out to a coordinator subagent: subagents cannot spawn
subagents (no Agent tool inside subagents, verified 2026-06-09), so a
coordinator silently roleplays its specialists in one context and you
cannot tell the difference from real fan-out.

1. Read the roster at `~/.claude/skills/consult/specialists.md` and
   select relevant specialists. Not every plan needs every specialist;
   match specialists to concerns in the plan.
2. Dispatch each selected specialist via
   `Agent(subagent_type="<specialist>", ...)` in the SAME single message
   as the Phase 3a Challenge dispatch. Each specialist gets:
   - The relevant plan items (not the full plan if only some items
     are relevant)
   - A focused question (what specifically to evaluate)
   - Author Mode preamble: "CI has not run yet. Flag everything:
     style, types, lint, naming, and design issues."
3. When all specialists return, YOU synthesize: themes, contradictions,
   gaps. Triage findings: Fix now / Fix next / Defer / Won't fix.

Include in EACH specialist's prompt:

> Focus on design-level concerns, not implementation details. The plan
> hasn't been built yet. For each plan item in your domain, probe for:
> Pipeline Bypass (does this add a new code path when the existing
> pipeline could serve?), Reasoning Chain gaps (do the steps actually
> follow from each other, and if the item names 2+ parallel-looking
> cases under one mechanism, does each case's actual detection shape
> match the others, per the Mechanism-Homogeneity subtrigger in
> `~/.claude/skills/challenge/assumption-taxonomy.md`?), and
> Scope/Completeness (what production concerns - rollback, observability,
> migration - does this plan omit?).
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

**CRITICAL: Launch the Phase 3a Challenge subagent and ALL selected
Phase 3b specialists in a single message with multiple Agent tool
calls.** Do not serialize, and do not interpose a coordinator subagent.

## Phase 4.5: Skeptic Lens

After Phase 4 produces the converged plan, dispatch `mx2-skeptic`
with the converged plan as input. The skeptic asks naive, dumb, or
obvious-but-unasked questions designed to surface risks the consensus
consult and challenge passes assumed away. Output is advisory; format
is the agent's standard `🔻` prefix block.

```
Agent(
  subagent_type="mx2-skeptic",
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
  challenged on first-principles grounds,
  (e) Proportionality: is this plan over-built for the goal's stated
  weight? Is there a materially simpler 80/20 plan? If the goal carries
  scope-signal words (lightweight / simple / minimal / quick / for most
  users), name the minimal-viable variant and what each extra component
  buys.
  (f) Control-verb completeness: for any item describing operator
  control over a recurring or background mechanism (start/stop/pause/
  resume/restart/cancel), ask whether a leftover or already-queued
  action from a PRIOR state can silently undo the most recent operator
  action. This is a standing category, not a per-run addition, because a
  round given a custom focus elsewhere has otherwise crowded out this
  question organically (observed 2026-07-10, overwatch skill: 3 skeptic
  rounds each had a different assigned focus and none asked this).

  Converged plan + convergence delta:
  <plan block>

  INPUT_MODE: <problem-framed | mechanism-prescribed>
  DELTA_CATEGORY: <CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT>

  Return your standard 🔻 prefix block. Do NOT recommend a winner or
  approve the plan; surface concerns only."
)
```

The skeptic commentary appears in the Phase 5 output as a
`### Skeptic Lens` section AFTER the Convergence Delta and BEFORE
the Work Items, so the user sees adversarial dissent before reading
the recommended plan.

**Dismissal capture (orchestrator duty)**: when the user dismisses a
Skeptic Lens concern with reasoning ("not a real concern", "covered by
X"), record it before moving on:
`bd remember --key="calibration:mx2-skeptic:dismissal:<short-tag>" "<date>: <pattern>. <why dismissed>. <how to recognize next time>."`
The skeptic cannot observe dismissals (they happen after it returns);
this step is the only thing that makes its calibrate-or-fade loop real. If the agent returns `🔻 No concerns from this
lens`, still include the section with that exact line so the user
knows the pass ran (do not omit silently).

This is the lowest-traffic surface for skeptic and the calibration
starting point. Calibration data accumulates here before skeptic
expands to autopilot ESCALATE and decision-maker borderline calls.

### Failure handling

If the skeptic dispatch fails (agent missing, calibration file
unreadable, transient error), note the failure as a one-line
"Skeptic Lens unavailable: <reason>" in the Phase 5 output and
proceed. Do not block convergence on advisory tooling, but do not
silently drop the pass either.

The Phase 4.6 gate receives the unavailable-reason as input and
factors it into the verdict (missing skeptic pass lowers gate
confidence).
