# typescript-reviewer Calibration Lookback Log

Append-only audit trail of merged and rejected calibration drift entries for the
`mx2-typescript-reviewer` agent. Each `/calibrate` accept appends one entry per merge.

This log is the historical record post-merge; the calibration file is the current
state. Use this log for retrospective review (which rules emerged when, which
calibration drift was rejected and why).

## 2026-04-30

- **Source key**: `calibration:typescript-reviewer:rule-overrides:no-self-correction-mid-output`
- **Category**: rule-overrides
- **Action**: new-rule
- **Summary**: drop low-confidence findings instead of self-correcting mid-paragraph
- **Rationale**: emerged from PR #8424 baseline test; output discipline matters for multi-window readers who scan in <30s

- **Source key**: `calibration:typescript-reviewer:rule-overrides:collapse-low-confidence-warnings`
- **Category**: rule-overrides
- **Action**: new-rule
- **Summary**: collapse heavily-hedged WARNINGs to SUGGESTION or drop
- **Rationale**: emerged from PR #8424 baseline test; severity should match confidence, hedging language signals miscalibration
