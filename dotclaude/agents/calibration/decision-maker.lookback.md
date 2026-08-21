# decision-maker Calibration Lookback Log

Append-only audit trail of merged and rejected calibration drift entries for the
`mx2-decision-maker` agent. Each `/calibrate` accept appends one entry per merge.

This log is the historical record post-merge; the calibration file is the
current state. Use this log for retrospective review (which rules emerged when,
which calibration drift was rejected and why).

Format per entry:

```
## YYYY-MM-DD

- **Source key**: `calibration:mx2-decision-maker:<category>:<specific-slug>`
- **Category**: <category>
- **Action**: merge | refinement | new-rule | reject
- **Summary**: <one line: what changed>
- **Rationale**: <one line: why merged or rejected>
```

---

## 2026-04-28

- **Source key**: `calibration:decision-maker:proceed-gate:fixture-test-do-not-merge`
- **Category**: proceed-gate (Rule Overrides)
- **Action**: new-rule
- **Summary**: End-to-end loop verification fixture merged to confirm /calibrate closes the channel.
- **Rationale**: Verification path per skill SKILL.md; user accepted merge to confirm the loop. Manual cleanup of the FIXTURE entry from decision-maker.md is the documented next step.

## 2026-05-21

- **Source key**: `calibration:decision-maker:proceed-gate:plan-must-specify-exception-coverage`
- **Category**: proceed-gate (Rule Overrides)
- **Action**: new-rule
- **Summary**: Added "Fail-closed semantics: plan must name concrete exception classes" rule; ITERATE at Gate 1 when fail-closed handling around an external library call doesn't enumerate concrete exception classes.
- **Rationale**: Evidence-backed by PR #9193 / docr-5x7j ES-rescue: `elasticsearch.ApiError` is sibling (not subclass) of `TransportError`, so deferring to "existing class contract" let 401/403/400 escape and inverted the fail-closed intent. Surfaced by `mx2-silent-failure-hunter` at Gate 2. Worth promoting to a Gate-1 plan-check.

## 2026-06-10

- **Source key**: `calibration:mx2-decision-maker:converge:comprehension-anchor`
- **Category**: converge (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: ITERATE-refine on silent re-scope of locked targets + missing designed read events.
- **Rationale**: Merged trimmed; the lighter-alternative trigger is covered by the standing proportionality criterion.

- **Source key**: `calibration:mx2-decision-maker:converge:over-engineering`
- **Category**: converge
- **Action**: reject
- **Summary**: Over-built plan PROCEEDed pre-proportionality-rule (Auto Mode guardrail incident).
- **Rationale**: Self-declared superseded; proportionality became a standing agent-definition criterion 2026-06-04. This lookback entry is the surviving incident record.

- **Source key**: `calibration:mx2-decision-maker:false-negative:delta-category-kind-over-count`
- **Category**: false-negative
- **Action**: new-rule
- **Summary**: Pin reversals / reopened structural conflicts tip confirmation-mode delta to MAJOR regardless of addition count.
- **Rationale**: No confirmation-mode DELTA_CATEGORY rubric existed; concrete same-day false-negative instance (MX2-NNNNN).

- **Source key**: `calibration:mx2-decision-maker:ideation:pr-intel-cross-cutting`
- **Category**: ideation (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: All-candidates-target-unconfirmed-mechanism routes ESCALATE-ROUTE to /investigate.
- **Rationale**: Load-bearing in practice (cited by name at the 2026-06-09 harness-ideate gate); aligns gate behavior with debugging.md Iron Law.

- **Source key**: `calibration:mx2-decision-maker:ideation:verify-checkable-data-params`
- **Category**: ideation (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: Verify checkable data parameters with one tool call before rating verif/conseq.
- **Rationale**: Same-day proven (35d-vs-90d retention check flipped PROCEED to ITERATE); cheap, falsifiable, generalizes.

## 2026-07-21

- **Source key**: `calibration:mx2-decision-maker:converge:overwatch-skill`
- **Category**: converge (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: A high-signal ITERATE names a concrete missed alternative from a known-good source; evaluate-and-document-decline can satisfy it.
- **Rationale**: Well-grounded (2026-07-09 overwatch converge ITERATE caught a real missed bg-poll alternative); merged as a consolidated Rule Override.

- **Source key**: `calibration:mx2-decision-maker:ideation:overwatch-skill`
- **Category**: ideation (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: Ideation-gate rubric gaps: grade decision/ranking quality (not mechanism-executes), declare tier when tier is open, Diverge must enumerate a zero-code candidate.
- **Rationale**: 2x-confirmed at merge; folded with the autopilot 3rd confirmation into one consolidated "Ideation-gate rubric gaps" Rule Override.

- **Source key**: `calibration:mx2-decision-maker:ideation:autopilot-recurs-overwatch-formula-gaps`
- **Category**: ideation (gate-context tag, routed to Rule Overrides)
- **Action**: refinement
- **Summary**: 3rd confirmation of the same three ideation-rubric gaps; folded into the consolidated rule.
- **Rationale**: Confirmation, not distinct content; strengthened the merged rule and flagged the /ideate-rubric structural fix (goal-fit column, capability-proving Verifiability, mandatory zero-code enumeration) as a separate unmerged follow-up.

- **Source key**: `calibration:mx2-decision-maker:ideation:fit-column-missing-user-constraint-root`
- **Category**: ideation (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: Fit weakness rooted in a missing user constraint routes to ESCALATE-QUESTIONS, not a second re-diverge ITERATE.
- **Rationale**: Distinct 4th gap; merged as its own Rule Override.

## 2026-08-19

- **Source key**: `calibration:mx2-decision-maker:converge:deterministic-enforcement-precedes-lens`
- **Category**: converge (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: Before approving a probabilistic-lens capability, check whether the target is deterministically enumerable (one grep/awk/tflint pass); if so the lens is the wrong mechanism.
- **Rationale**: Evidence-backed: one awk pass found 17 unset config blocks a per-diff lens would never see, matching a known prior prod defect shape.

- **Source key**: `calibration:mx2-decision-maker:converge:gating-query-positive-control`
- **Category**: converge (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: A plan gating execution on a zero/clean live-state query result must name a positive control and a credential/field-visibility assertion.
- **Rationale**: Extends the already-standing "prove the search can return something" CLAUDE.md rule to the gate specifically for zero-result-as-gate-condition plans; distinct from the ideation absence-claim rule merged the same day.

- **Source key**: `calibration:mx2-decision-maker:false-negative:promotion-samename-config-shadowing`
- **Category**: false-negative (False-Negative Patterns)
- **Action**: new-rule
- **Summary**: The personal-shadows-project naming convention silently defeats a promotion whose value is a lockdown, if a same-named unrestricted definition already exists at the shadowing scope.
- **Rationale**: Concrete instance where the promoter's own post-rebuild check would have tested the wrong (unrestricted) definition and returned a false pass.

- **Source key**: `calibration:mx2-decision-maker:ideation:burned-precedent-promotes-verifiability`
- **Category**: ideation (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: A burned precedent on the same surface promotes Verifiability from one ranking column to the dominant term; a hard-constraint violator still stays in the candidate pool as the control arm.
- **Rationale**: Corrects a real ranking inversion (MED-verifiability candidate scored above the only HIGH-verifiability one with a mechanical replay).

- **Source key**: `calibration:mx2-decision-maker:ideation:unratified-decision-absence-claim`
- **Category**: ideation (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: A candidate proposing a new ratification must have its "no prior ratified decision exists" claim checked against the decision corpus before rating.
- **Rationale**: Concrete instance where a prior lead-ratified decision on the same axis existed and the artifact's absence claim was simply unverified.

- **Source key**: `calibration:mx2-decision-maker:launch:absence-claim-eliminating-option-class`
- **Category**: launch (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: An absence claim that eliminates an entire option class (and substitutes a different deliverable for the bead's own ACs) must be independently re-verified at the gate; added an intent-fidelity AC-diff criterion too.
- **Rationale**: Same-session instance: a plan concluded no e2e harness existed after 5 search passes; the harness existed with a documented "deferred to v2" coverage gap, not an absence. This session's own /launch on docr-nuie8.

- **Source key**: `calibration:mx2-decision-maker:launch:shared-infra-module-additive-carveout`
- **Category**: launch (gate-context tag, routed to Rule Overrides)
- **Action**: new-rule
- **Summary**: Named carve-out under which a shared-infrastructure-module edit is PROCEED-eligible rather than auto-ESCALATE (additive, no-op default, full call-site shape audit, one zero-diff plan per shape family).
- **Rationale**: An unconditional ESCALATE reading would have blocked a correct, evidence-backed P1 cutover-gating fix; the carve-out is conditioned tightly enough to preserve the example's protective intent.

- **Source key**: `calibration:mx2-decision-maker:launch:surfaced-mechanism-deviation-delta-category`
- **Category**: launch (gate-context tag, routed to False-Negative Patterns as a refinement)
- **Action**: refinement
- **Summary**: A pinned-mechanism reversal that is evidence-verified AND surfaced as an Open Assumption stays MINOR (capped at MEDIUM confidence) instead of being forced to MAJOR_REVISIONS.
- **Rationale**: Refines the existing "Delta categorization: kind of change over count of changes" rule; forcing MAJOR here would have added a gate round with no new information, since the user-visibility purpose was already satisfied via the Open Assumption.

- **Source key**: `calibration:mx2-decision-maker:proceed-gate:blind-vs-retrospective-replay`
- **Category**: proceed-gate (Rule Overrides)
- **Action**: new-rule
- **Summary**: Verifiability evidence for a detector/lens must be a held-out (blind) artifact, not a retrospective replay on a known-answer case, which proves reproduction rather than discrimination.
- **Rationale**: A round-1 ITERATE demanding replay evidence was satisfiable by a non-blind replay, leaving a documented false-positive-rate objection unresolved.

- **Source key**: `calibration:mx2-decision-maker:proceed-gate:enumerate-populations-per-path`
- **Category**: proceed-gate (Rule Overrides)
- **Action**: new-rule
- **Summary**: A plan gating/dropping traffic on a multi-population path (live/replay/backfill/re-ingest/sweep-requeue) must assign semantics per population, not a uniform drop.
- **Rationale**: Concrete instance extended a drop to populations a ratified decision explicitly left open both ways; same shape as an existing but uncovered project-tier correction.

- **Source key**: `calibration:mx2-decision-maker:proceed-gate:orchestrator-verification-not-evidence`
- **Category**: proceed-gate (Rule Overrides, refinement)
- **Action**: refinement
- **Summary**: An orchestrator-asserted "I verified this live" claim must be re-run at the gate when load-bearing, same as a stale handoff status claim; refines "Verify checkable data parameters before rating."
- **Rationale**: A false "fresh live finding" (an actually-unchanged YAML field) sat undetected next to a genuinely correct falsification, which is what made it easy to wave through.
