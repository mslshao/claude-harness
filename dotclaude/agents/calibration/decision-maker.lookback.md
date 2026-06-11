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
- **Rationale**: No confirmation-mode DELTA_CATEGORY rubric existed; concrete same-day false-negative instance (MX2-XXXXX).

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
