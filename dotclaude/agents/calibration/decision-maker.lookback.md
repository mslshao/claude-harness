# decision-maker Calibration Lookback Log

Append-only audit trail of merged and rejected calibration drift entries for the
`mx2-decision-maker` agent. Each `/calibrate` accept appends one entry per merge.

This log is the historical record post-merge; the calibration file is the
current state. Use this log for retrospective review (which rules emerged when,
which calibration drift was rejected and why).

Format per entry:

```
## YYYY-MM-DD

- **Source key**: `calibration:decision-maker:<category>:<specific-slug>`
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
