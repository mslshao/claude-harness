# module-cohesion-reviewer Calibration Lookback Log

Append-only audit trail of merged and rejected calibration drift entries for the
`module-cohesion-reviewer` agent. Each `/calibrate` accept appends one entry per merge.

This log is the historical record post-merge; the calibration file is the current
state. Use this log for retrospective review (which rules emerged when, which
calibration drift was rejected and why).

## 2026-07-21

- **Source key**: `calibration:module-cohesion-reviewer:cross-boundary-identical-models`
- **Category**: none in key (3-segment); routed to False-Positive Patterns as a do-not-flag rule
- **Action**: new-rule
- **Summary**: cross-boundary identical-field models (HTTP body vs SQS envelope) are two contracts, not duplication; do not flag for consolidation.
- **Rationale**: verified and well-grounded (the engineering lead's reply on PR #10714); a real false-positive class for the duplication lens.
