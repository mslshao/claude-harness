---
name: converge
description: >
  End-to-end planning pipeline with challenge + consult stress-test,
  mandatory skeptic pass, and decision-maker proceed/iterate gate. Use
  when the user has a rough idea and wants a production-quality plan
  without manually orchestrating each skill. Accepts free-text, Jira
  tickets, beads, Slack threads, Confluence rough-drafts, or transcripts.
  Produces a converged plan (no code written) with iteration log,
  convergence delta category, and verification paths per work item.
  Detects mechanism-prescribed inputs and forces specialists to challenge
  the prescribed mechanism rather than rubber-stamp it. For hands-off
  implementation from a well-scoped ticket (plan + code + PR), use
  /launch. For divergent approach generation BEFORE a plan exists, use
  /ideate.
argument-hint: "[rough idea, feature description, bead ID, Jira ticket, Slack URL, Confluence URL, or transcript]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "WebFetch", "AskUserQuestion"]
---

# Converge

Orchestrate the full planning pipeline: refine a rough idea, decompose
it into a plan, stress-test assumptions, get specialist review,
synthesize findings, run an adversarial skeptic pass, run a
decision-maker proceed/iterate gate, then present the converged result
for signoff. The user sees one synthesis-level output: the final plan.

## Why This Exists

Without this skill, the user manually invokes `/refine`, `/bead-forge`,
`/challenge`, `/consult`, and `/synthesize` in sequence, passing
context between each. They review intermediate output they don't care
about. This skill runs the full pipeline internally and presents only
the converged result.

## Input

One or more of:
- A rough idea or feature description (text)
- A bead reference (`bd show <id>` output or bead ID)
- A Jira ticket ID (`MX2-\d+`)
- A Slack thread URL or pasted thread excerpt
- A Confluence page URL or pasted page body (often a rough-draft doc)
- A PR reference (`#\d+` or `gh pr` URL)
- A conversation transcript
- A mix of the above

Mixed inputs are consolidated. Precedence on disagreement:
**inline text > Slack/transcript > Confluence > Jira/PR > bead notes**.
Disagreements surface in Phase 5 "Open Assumptions".

For the full input-loading protocol, URL parsing rules, mixed-input
precedence handling, and bias-detection (INPUT_MODE classification),
see [input-loading.md](input-loading.md).

## Pipeline Overview

```
rough idea (text, Jira, bead, Slack, Confluence, transcript)
    |
    v
[Phase 1: Refine] <-------+
    |                     |  (loop-back on ESCALATE-QUESTIONS,
    v                     |   after user answers narrowing Qs)
[Phase 2: Scope & Decompose] <----+
    |                             |  (loop-back on ITERATE, scoped
    +--------+--------+           |   to the named WEAK_DIMENSION)
    |                 |           |
    v                 v           |
[Phase 3a:         [Phase 3b:     |
 Challenge]         Consult]      |
    |                 |           |
    +--------+--------+           |
             |                    |
             v                    |
[Phase 4: Synthesize] ------------+
             |                    |
             v                    |
[Phase 4.5: Skeptic Lens]       |
             |                    |
             v                    |
[Phase 4.6: Convergence Gate] ----+
             |
             | (PROCEED only)
             v
[Phase 5: Present]          First synthesis-level user-facing output.
             |
       [user approval]
             |
             v
[Phase 6: Create]           Beads created, optional gate.

Phase 4.6 verdicts:
  PROCEED            -> Phase 5
  ITERATE            -> Phase 2 (cap: 2 rounds)
  ESCALATE-QUESTIONS -> ask user, then Phase 1 (cap: 1 round)
  ESCALATE-ROUTE     -> Phase 5 with no plan; suggest a different
                        skill (/ideate, /investigate, direct execution)
```

Phases 1-4.6 are INTERNAL. The only user-facing output before Phase 5
is the narrowing questions in ESCALATE-QUESTIONS (when fired). Phase 5
is the first synthesis-level visible output.

## Process

### Phase 1: Refine (internal)

Load all inputs, detect bias mode, clarify scope.

For the full protocol (multi-input loading with URL parsing,
mixed-input precedence, bias-detection / INPUT_MODE classification,
domain context pre-load, sibling-bead sweep, enrich, expand
specificity), see [input-loading.md](input-loading.md).

Key invariants:
- Detect `INPUT_MODE: problem-framed` vs `INPUT_MODE: mechanism-prescribed`
  in step 0. Mechanism-prescribed triggers enhanced scrutiny in Phase 3
  and the Prior Thinking Comparison section in Phase 5.
- Sibling-bead sweep is mandatory, not optional. Ratified architectural
  decisions in sibling beads supersede any plan formed fresh.
- Domain-matcher misfires must NOT block convergence (best-effort).
- **Underlying-defect precondition.** When the problem is review-quality,
  process-quality, or "how do we catch X sooner", check whether the defect
  that motivated it is still unfixed. If it is, say so BEFORE running the
  pipeline and offer to fix it first. A planning pass on how to have caught
  a bug faster, run while the bug is live, inverts the priority for the
  entire duration of the pipeline. Observed 2026-08-06: two `/ideate` rounds
  and two `/converge` rounds on a review-lens gap while the prod monitor that
  motivated them stayed broken for 13 days, with its one-line fix already
  filed as MX2-NNNNN on day one.

Output: refined scope (1-3 sentences with constraints surfaced) plus
the `Loaded context:` block and the `INPUT_MODE:` classification.

### Delta-reconvergence (input already carries a stress-tested brief)

When the input ticket/bead carries a prior converged brief (structural
check: pinned decisions, work items with AC, verification paths, an
iteration/stress-test provenance note), do NOT re-run the full pipeline
against the original problem, and do NOT bypass (that is launch's move
for execution). Instead:

1. **Verify the brief's load-bearing citations at current HEAD** in
   Phase 2 (files, line-shapes, "X does not exist yet" claims, open
   decisions). Every stale citation is a delta.
2. **Scope Phase 3 dispatches to the deltas**: instruct every specialist
   to challenge only the drift (shipped siblings, changed contracts,
   resolved blockers), explicitly listing the ratified core as
   not-to-be-relitigated.
3. **Output shape**: an AMENDMENTS block (authoritative where it
   conflicts) prepended over the preserved prior body, versioned
   (v3 -> v4), updating the canonical comment IN PLACE
   (addCommentToJiraIssue supports commentId updates) so there is one
   brief, not a trail of partial supersessions.
4. Open PRs in the same ticket family are part of the drift surface:
   dispatch at least one specialist against the open PR's actual
   contract/behavior, not just main (the 2026-07-22 MX2-NNNNN run found
   a completion-quorum bug in the open Phase 2 PR this way).

Convergence Delta compares against the PRIOR BRIEF, not against a fresh
draft: CONFIRMED means the brief survived the drift check.

### Phase 2: Scope & Decompose (internal)

Using the refined scope, perform the core bead-forge analysis:

1. **Understand scope**: Read source files mentioned. Search the MX2
   codebase for existing patterns. Identify natural seams.

   **Verify "mirrors/ports from X" claims now, not at Phase 3.** Any work
   item you draft that says a pattern is "ported from," "mirrors," or
   "copies" an existing file must be checked against that file directly
   (Read/Grep) in this same pass, citing the specific section. An
   unverified mirroring claim is exactly the failure mode Phase 3
   (Challenge/Consult) and Phase 4.5 (Skeptic) exist to catch, but
   catching it there costs a full stress-test-and-re-synthesize cycle;
   catching it here costs one Read call. The same verification applies to
   precedents cited in Phase 3 dispatch prompts: confirm the artifact
   exists on `origin/main` before naming it as precedent in a specialist's
   framing; an in-flight PR's artifact must be labeled as unmerged
   (2026-07-17: a dispatch cited a client class living only on an open PR
   and a specialist spent its pass refuting the framing).

   **Infrastructure pull-up**: Before scoping to the named service,
   check whether the prompt touches a cross-cutting concern
   (observability, worker lifecycle, error handling, queueing). If so,
   search for shared base classes and infrastructure modules. A fix at
   the base class often outweighs N individual service fixes. Check
   `mx2.worker.worker`, `mx2.sqs.*`, `mx2.telemetry.*`, and relevant
   Terraform/infrastructure config before deciding where changes
   belong.

2. **Pipeline reuse gate** _(the Pipeline Bypass assumption category
   from `challenge/assumption-taxonomy.md`)_: Before designing any new
   code path, check whether the existing pipeline already provides the
   needed behavior. Ask: "What happens if we just send one message
   through the normal path?" New paths mean new bugs and new contracts.
   The existing path is tested. If reuse works, the plan should
   leverage it even with small overhead (e.g., one redundant Lambda
   invocation that early-exits). Highest-ROI single review question.

3. **Codebase collision check**: Search for existing code that
   overlaps. Note where new code must stay separate and why.

4. **Terminology-collision check**: Cross-reference each new concept
   the plan introduces (new bead title, new function name, new module
   name, new domain noun) against the `Loaded context:` section from
   Phase 1. If a name collides, surface to the user: "You named this
   X, but bead memories define X as Y. Are you proposing to extend Y
   or introduce something orthogonal?" If orthogonal, propose a
   sub-term so the plan does not silently overload an existing concept.

5. **Decompose**: Break into work items. For the full work item field
   structure (Title, Description, AC, Design notes, Dependencies,
   Verification path, Consequence of wrong, Context) and field-level
   invariants, see [work-item-structure.md](work-item-structure.md).

6. **Category assignment**: Each item gets a bead category label
   (task/memory/decision/discovery/review).

Apply the granularity check from bead-forge: each item should be
completable in one focused session. If an item is too large, decompose
further.

Key invariants:
- Every work item has a Verification path. Absent VP triggers ITERATE.
- Consequence=high items must have matching Verification path OR an
  explicit risk-reduction note.
- Context (greenfield/legacy/hybrid) is annotation, not scored.

Output: an internal "draft plan" with work items, dependencies, and
dependency graph. Not shown to user yet.

### Phase 3: Stress Test (parallel, internal)

Dispatch the Phase 3a Challenge subagent AND all selected Phase 3b
consult specialists (roster: `~/.claude/skills/consult/specialists.md`)
in ONE message: 1 + N Agent tool calls. All receive the draft plan plus
the INPUT_MODE classification. There is NO consult-coordinator subagent:
subagents cannot spawn subagents, so YOU dispatch the specialists
directly and synthesize their findings yourself.

For the full Challenge and per-specialist prompt templates (including
the enhanced-scrutiny instructions for mechanism-prescribed inputs),
see [stress-test-prompts.md](stress-test-prompts.md).

Key invariants:
- **Parallel is mandatory.** Launch the Challenge subagent and every
  selected specialist in a single message with multiple Agent tool
  calls. Serializing defeats the purpose.
- When INPUT_MODE=mechanism-prescribed, every dispatch receives
  enhanced-scrutiny instructions: treat the prescribed mechanism as
  an explicit assumption to evaluate on first-principles grounds, not
  a given.
- Every dispatch must check sibling beads for ratified architectural
  decisions that supersede the draft plan.

### Phase 4: Synthesize (internal)

When the Challenge subagent and all Phase 3b specialists return, merge
the findings (the consult-side synthesis is YOUR job now, not a
coordinator's):

1. **Gather**: Collect challenge modifications and consult findings.
2. **Connect**: Find themes across both. Where do challenge and consult
   agree? Where do they contradict?
3. **Deduplicate**: Multiple sources may flag the same issue. Merge.
4. **Apply to plan**: Rate every finding Fix now / Fix next / Defer /
   Won't fix BEFORE incorporating (per `consult/specialists.md`'s
   dispatch heuristics). Do not default every finding to Fix now: a
   high hit rate on "fix everything" is itself a signal to re-check
   proportionality before the plan reaches Phase 4.6. Then modify the
   draft plan:
   - INVALIDATED assumptions: remove or revise affected plan items.
   - Fix now: incorporate into plan items.
   - Fix next / Defer / Won't fix: do NOT incorporate; carry the
     rated-but-deferred findings into Phase 5's Convergence Delta so
     the user sees what was consciously left out, not just what was
     fixed.
   - Gaps identified by either source: add items or acceptance criteria.
   - Contradictions: make the judgment call, note the trade-off. For
     FRAGILE+HIGH contradictions, use the decision record format from
     `consult/report-format.md`.
5. **Capture what changed**: Record a "convergence delta" with ONE of
   four labels. The label appears in Phase 5 output so the user knows
   the depth of pushback:

   - **CONFIRMED**: specialists agreed; no structural changes; only
     minor clarifications. Means the plan actually withstood scrutiny.
   - **MINOR_ADJUSTMENTS**: structure kept; small number of items
     adjusted (added AC, narrowed scope, swapped pattern).
   - **MAJOR_REVISIONS**: goal kept; materially different approach
     recommended.
   - **SCRAPPED_AND_REBUILT**: different framing entirely. Original
     mechanism was wrong. The canonical Fulfillment-vs-Coverage
     outcome.

   **Watch for false CONFIRMED.** CONFIRMED is suspicious when the
   input was complex or mechanism-prescribed; bias toward
   MINOR_ADJUSTMENTS unless specialists offered concrete evidence
   (file paths, function names, pattern citations). Empty
   challenge + empty consult on a non-trivial mechanism-prescribed
   input usually means specialists punted, not that the plan is solid.
   The Phase 4.6 gate catches this and fires
   ITERATE+WEAK_DIMENSION=mechanism.

Output: the converged plan (modified work items + convergence delta
prose + DELTA_CATEGORY label).

### Phase 4.5: Skeptic Lens (internal)

Dispatch `mx2-skeptic` for an adversarial pass on the converged
plan. The agent asks naive, dumb, or obvious-but-unasked questions
designed to surface risks the consensus passes assumed away. Output
is advisory.

For the full Skeptic dispatch prompt and failure handling, see
[stress-test-prompts.md](stress-test-prompts.md).

Key invariants:
- Skeptic is mandatory, not opt-in. Findings fold into Phase 5 as a
  `Skeptic Lens` block.
- If dispatch fails, note "Skeptic Lens unavailable: <reason>" and
  proceed. Do not silently drop the pass.
- The Phase 4.6 gate receives skeptic output (or unavailable-reason)
  as input. Missing skeptic pass lowers gate confidence.

### Phase 4.6: Convergence Gate (internal)

Run a decision-maker gate on the synthesized plan. The gate may PROCEED,
ITERATE, ESCALATE-QUESTIONS, or ESCALATE-ROUTE.

For the full decision-maker dispatch prompt (with `MODE: CONVERGENCE
GATE` preamble), branch logic per verdict, WEAK_DIMENSION instructions
for ITERATE, narrowing-question constraints for ESCALATE-QUESTIONS,
suggested-skill mapping for ESCALATE-ROUTE, and iteration caps, see
[convergence-gate.md](convergence-gate.md).

Key invariants:
- The gate is `mx2-decision-maker` invoked with `MODE: CONVERGENCE GATE`
  preamble. Calibration drift gets recorded with
  `bd remember --key='calibration:mx2-decision-maker:converge:<topic>'`.
- ITERATE re-runs Phase 2 + 3 with a focused WEAK_DIMENSION
  modification (verification / consequence / scope / decomposition /
  mechanism / proportionality). Cap: 2 ITERATE rounds per invocation.
- ESCALATE-QUESTIONS poses 1-3 focused narrowing questions to the
  user via `AskUserQuestion`. Each question must include a WHY clause.
  Cap: 1 user-question round per invocation.
- ESCALATE-ROUTE surfaces in Phase 5 with no plan, just the suggested
  next skill (`/ideate`, `/investigate`, direct execution).
- The mechanism case is canonical for catching Fulfillment-vs-Coverage:
  INPUT_MODE=mechanism-prescribed AND DELTA_CATEGORY=CONFIRMED on a
  non-trivial plan triggers ITERATE with WEAK_DIMENSION=mechanism.

### Phase 5: Present

First synthesis-level output the user sees.

> **Deliverable adaptation.** The format below assumes the deliverable
> is a set of work items. When the deliverable is a communication
> artifact (PR comment, decision doc, briefing, Slack draft), replace
> the "Work Items" section with the draft artifact ready to copy/post.
> The Convergence Delta, Open Assumptions, Iteration Log, and
> Checkpoint Recommendation still apply unchanged. The Phase 6 "Create"
> step is replaced by user signoff to send/post.

Present the converged plan using the template in
[present-template.md](present-template.md). The template is the structural
contract: an H2 `## Converged Plan` (with `(low-confidence)` suffix when the
Phase 4.6 gate forced a low-confidence PROCEED), then Summary, Iteration Log
(always present so the user sees the gate ran), Convergence Delta (with
CATEGORY tag), Prior Thinking Comparison (mechanism-prescribed inputs only),
the mandatory Skeptic Lens block, Work Items (per work-item-structure.md),
Dependency Graph, Open Assumptions, the ESCALATE-ROUTE-only "No Plan Produced"
variant, and the closing "Approve this plan?" prompt. Populate every applicable
section in order; do not free-form narrate the plan.

### Phase 6: Create (on approval)

When the user approves:

0. **Self-reference preflight (run BEFORE the first `bd create`).** Every
   check in Phases 2-4.6 runs on the draft plan TEXT, before this plan's
   own beads exist, so none of them can see a collision between a label
   this step is about to mint and an artifact the plan's own work-item
   text says a later build will create (a runtime bead, a table, a
   file). Using the FINAL post-synthesis work-item text: extract every
   forward-reference to an artifact this plan's own future code/runtime
   will create (bead labels/titles, table names, file paths, function/
   module names, any phrasing like "the skill/service creates/writes/
   persists X"), then cross-reference that list against the label/naming
   scheme THIS invocation is about to apply to the planning beads
   themselves. If they overlap, or a work item leaves a to-be-created
   artifact's label unspecified while this step is about to claim the
   obvious default name, surface it and get a disambiguated pair before
   executing any `bd create`. Added 2026-07-10 after a plan's 7 planning
   beads were labeled `--labels=overwatch` while a work item's own text,
   written in the same session, described a runtime tracking bead the
   skill would create at first run with no label specified; the two
   would have collided under the obvious default name.
1. Create beads via `bd create` for each work item. Use `--title`,
   `--description`, `--type`, `--priority`. Include AC, design notes,
   verification path, and consequence-of-wrong in the description.
2. Wire dependencies via `bd dep add`.
3. If the plan has 3+ implementation items, ask: "Add a signoff gate?
   This blocks implementation beads in `bd ready` until you explicitly
   resolve the gate." If yes, create a gate bead with
   `--type=task --title="Signoff: [plan topic]"` and make
   implementation items depend on it.
4. Present the created bead IDs and the dependency graph.

If the user provides feedback instead of approving, revise the plan
and re-present (Phase 5 again). Do not loop more than twice; if the
user has extensive changes, suggest they provide the feedback and
you'll run `/bead-forge` with the converged context directly.

## Checkpoint Protocol

If this skill produces findings that would be lost to compaction
(especially the convergence delta and rejected alternatives), include
a Checkpoint Recommendation block in the Phase 5 output:

```
## Checkpoint Recommendation
Category: decision
Domain: [relevant domain]
Title: "PLAN DECISION: [topic] - converged approach with rationale"
Context to preserve:
- [Key design decision and why]
- [Rejected alternative and why rejected]
- [Assumption that was invalidated and what replaced it]
Rationale: convergence analysis produced decisions that inform implementation
```

The main agent should persist this via `/bead-forge checkpoint` if the
plan is approved.

## Distinctions

- **vs `/ideate`**: `/ideate` is upstream of `/converge`. `/ideate`
  generates 3-5 candidate approaches and ranks them; `/converge` takes
  ONE approach and stress-tests it. When the user has not yet picked
  an approach, the Phase 4.6 gate fires ESCALATE-ROUTE with
  SUGGESTED_NEXT_SKILL=/ideate.
- **vs `/launch`**: `/launch` writes code and produces a draft PR.
  `/converge` writes a plan (no code). For hands-off implementation
  from a well-scoped ticket, use `/launch`.
- **vs `/challenge`**: `/challenge` extracts assumptions from an
  EXISTING plan. `/converge` produces the plan. `/converge` invokes
  `/challenge`-style assumption extraction internally in Phase 3a.
- **vs `/consult`**: `/consult` runs parallel specialists with
  DIFFERENT lenses on the SAME code. `/converge` invokes
  `/consult`-style specialist orchestration internally in Phase 3b.
- **vs `/investigate`**: `/investigate` finds root cause for a
  production error. `/converge` produces a plan AFTER the root cause
  is known. When root cause is unknown, the Phase 4.6 gate fires
  ESCALATE-ROUTE with SUGGESTED_NEXT_SKILL=/investigate.

## Rules

- **No intermediate output.** Phases 1-4.6 are invisible. Phase 5 is
  the first synthesis-level visible output. Exception: the narrowing
  questions in ESCALATE-QUESTIONS are explicitly user-facing.
- **Parallel is mandatory.** Phase 3's Challenge subagent and all
  selected consult specialists run in parallel via separate Agent tool
  calls in the same message (no coordinator subagent).
- **Beads are created last.** Do not create beads during Phases 1-4.6.
  The whole point is convergence before commitment.
- **Don't rubber-stamp.** A CONFIRMED delta category is suspicious
  when the input was complex or mechanism-prescribed. Bias toward
  MINOR_ADJUSTMENTS unless specialists offered concrete evidence
  (file paths, function names, pattern citations). The Phase 4.6
  gate enforces this.
- **Scope guard.** If the refined input is too large for a single
  converge pass (10+ work items likely), say so in Phase 5 and
  suggest breaking into sub-features.
- **Proportionality is gated.** Phase 4.6 must check the plan is
  right-sized to the goal: scope-signal inputs or plans materially
  heavier than a minimal-viable 80/20 version must justify the extra
  complexity, or the gate fires ITERATE with
  WEAK_DIMENSION=proportionality. See convergence-gate.md.
- **Mixed-input precedence is fixed.** Inline text > Slack/transcript
  > Confluence > Jira/PR > bead notes. Surface disagreements in
  Phase 5 Open Assumptions.
- **Detect mechanism-prescription up front.** Phase 1 must classify
  the input as `problem-framed` or `mechanism-prescribed`.
  Mechanism-prescribed requires ENHANCED scrutiny in Phase 3 and a
  Prior Thinking Comparison section in Phase 5. The
  Fulfillment-vs-Coverage failure mode (refining the wrong noun
  because the user prescribed it without challenge) is the canonical
  risk.
- **Verification path is mandatory per work item.** Items without it
  trigger ITERATE with WEAK_DIMENSION=verification.
- **Consequence-of-wrong is mandatory per work item.** Consequence=high
  AND no concrete verification path is a workstream-killer; synthesis
  must either add the path or downgrade scope.
- **Convergence Delta gets a category, not just prose.** One of
  CONFIRMED / MINOR_ADJUSTMENTS / MAJOR_REVISIONS /
  SCRAPPED_AND_REBUILT.
- **Skeptic is mandatory.** Phase 4.5 runs always. If dispatch
  fails, note "Skeptic Lens unavailable" and proceed; do not
  silently drop.
- **Convergence gate is mandatory.** Phase 4.6 runs always. PROCEED
  is not the default; the gate must affirmatively reach it. ITERATE
  cap is 2 rounds; ESCALATE-QUESTIONS cap is 1 round per invocation.
- **Ask the user when convergence space is too ambiguous.** Phase 4.6
  can fire ESCALATE-QUESTIONS with 1-3 narrowing questions. Max 3
  questions, each with a WHY clause. User can reply "you decide" to
  opt out (forces low-confidence PROCEED).
- **Calibration soak is expected.** The decision-maker invoked in
  Phase 4.6 was calibrated for autopilot and launch gates, not
  convergence. First 3-5 `/converge` invocations are calibration
  soak. Record drift via
  `bd remember --key='calibration:mx2-decision-maker:converge:<topic>'`.
- **Iteration log is always visible.** Phase 5 shows it even when
  Round 0 was final.
- **/converge is downstream of /ideate.** When the input is rough
  and multiple plausible mechanisms exist with no clear winner, the
  gate fires ESCALATE-ROUTE with SUGGESTED_NEXT_SKILL=/ideate.

## Additional Resources

- [input-loading.md](input-loading.md): Phase 1 multi-input loading,
  URL parsing, mixed-input precedence, bias-detection.
- [stress-test-prompts.md](stress-test-prompts.md): Phase 3a Challenge,
  Phase 3b Consult, and Phase 4.5 Skeptic dispatch prompts.
- [convergence-gate.md](convergence-gate.md): Phase 4.6 decision-maker
  dispatch, branch logic, caps, iteration log format.
- [work-item-structure.md](work-item-structure.md): Phase 2 work item
  field structure and Phase 5 presentation format.
- [present-template.md](present-template.md): Phase 5 converged-plan
  output template (Summary, Iteration Log, Convergence Delta, Work Items,
  Dependency Graph, ESCALATE-ROUTE variant).
