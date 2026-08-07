# module-cohesion-reviewer Calibration

Human-vetted calibration overrides for the `module-cohesion-reviewer` agent, merged
from calibration drift via `/calibrate`. This is the current-state file; the
append-only audit trail is in `module-cohesion-reviewer.lookback.md`.

## False-Positive Patterns

- **Cross-boundary identical-field models are two contracts, not duplication.** Two
  models with identical fields on opposite sides of a service boundary (for example
  an HTTP request-body model and the SQS envelope model carrying the same payload)
  are separate contracts, each free to evolve independently: the HTTP schema is the
  caller-facing API, the SQS envelope is the internal queue contract. Do NOT flag
  them as duplication to consolidate into one shared model; the coupling that
  consolidation would create is the actual anti-pattern. Also informs bot-review: a
  change to one contract does not automatically ripple to the other, precisely
  because they are separate contracts. (Source: the engineering lead's reply on
  PR #10714, 2026-07-20.)
