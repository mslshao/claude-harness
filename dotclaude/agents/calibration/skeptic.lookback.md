# skeptic Calibration Lookback Log

Append-only audit trail of merged and rejected calibration drift entries for the
`mx2-skeptic` agent. Each `/calibrate` accept appends one entry per merge.

This log is the historical record post-merge; the calibration file is the current
state. Use this log for retrospective review (which dismissals emerged when, which
calibration drift was rejected and why).

## 2026-07-21

- **Source key**: `calibration:mx2-skeptic:dismissal:campaign-gate-fork-order`
- **Category**: dismissal
- **Action**: new-rule
- **Summary**: Strand-scenario premise (K+1 forks before K gate) dismissed on pipeline order-of-operations; residual state-liveness concern kept and folded into the plan.
- **Rationale**: Verified, generalizable few-shot dismissal; teaches "check order-of-ops before crediting a strand scenario, but extract the residual underneath."

- **Source key**: `calibration:mx2-skeptic:dismissal:overwatch-interval-citation-2026-07-09`
- **Category**: dismissal
- **Action**: new-rule
- **Summary**: "Citation fabricated" claim dismissed after direct-grep verification (source existed, written earlier the same session).
- **Rationale**: Verified, generalizable; teaches direct-grep before accepting a not-cited/fabrication finding, especially for same-session-authored sources.
