# test-quality-reviewer Calibration Lookback Log

Append-only audit trail of merged and rejected calibration drift entries for the
`test-quality-reviewer` agent. Each `/calibrate` accept appends one entry per merge.

This log is the historical record post-merge; the calibration file is the current
state. Use this log for retrospective review (which rules emerged when, which
calibration drift was rejected and why).

## 2026-07-21

- **Source key**: `calibration:test-quality-reviewer:hallucinated-line-change-2026-05-05`
- **Category**: none in key (3-segment); routed to False-Positive Patterns as a hallucinated-finding rule
- **Action**: new-rule
- **Summary**: Verify a code-vs-test mismatch against the actual diff (not memory) before claiming a change was not made and predicting CI failure.
- **Rationale**: Verified false positive (PR #8863: REQUEST_CHANGES on a change that was actually present, diff never inspected); generalizable, sibling to correction:verification:absence-claim-context-scan.
