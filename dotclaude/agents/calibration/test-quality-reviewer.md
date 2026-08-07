# test-quality-reviewer Calibration

Human-vetted calibration overrides for the `test-quality-reviewer` agent, merged
from calibration drift via `/calibrate`. This is the current-state file; the
append-only audit trail is in `test-quality-reviewer.lookback.md`.

## False-Positive Patterns

- **Verify a code-vs-test mismatch against the actual diff, not memory.** When
  issuing a finding that a code change was NOT made (a raise not converted, a
  call not updated, an assertion not changed) and predicting a CI or test
  failure from it, inspect the ACTUAL diff and the file at the PR head before
  claiming the absence. Do not assert from memory of what "should" be there.
  Instance: PR #8863 (docr-jbus) got a REQUEST_CHANGES on a false claim that a
  line-560 `raise` was not changed to `QuaeroRetryableException`, when the diff
  and a passing `pants tlc` both confirmed it was; the agent never inspected the
  diff. Sibling rule to `correction:verification:absence-claim-context-scan`.
  Source: 2026-05-05 PR #8863 review; merged 2026-07-21.
