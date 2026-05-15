# Bot-Review Calibration

Last reviewed by Michael: 2026-05-07 (initial scaffold; no overrides yet)

This file is read by the `bot-review` agent before every invocation.
The agent emits calibration drift via `bd remember` (key prefix
`calibration:bot-review:`); the `/calibrate` skill is the human review
gate that merges accepted entries into this file. Append-only audit of
merged/rejected entries lives at `bot-review.lookback.md` (created on first
calibration merge).

If this file is empty (or contains only the scaffold below with no rule
overrides), default rules from the agent definition apply. The agent's
calibrate-or-fade doctrine still holds: if the agent produces noise the
user learns to ignore, calibration is the only path back. The 4-week
soak ceiling in `docr-tuqo` forces a promote-or-retire decision so the
agent does not linger personal-tier indefinitely with thin signal.

---

## Rule Overrides

(None yet. Populated via `/calibrate --agent=bot-review` after dismissals
are observed and reviewed.)

---

## Example Dismissals

These are past bot-review outputs the user dismissed, with reasoning. Used as
few-shot calibration so the agent recognizes the pattern next time and either
suppresses or reframes.

(None yet. First entries land after the first round of soak dispatches in
the field.)

---

## Threshold Notes

Domain-specific guidance on where the agent's signal-to-noise boundary sits.
Examples that would land here:

- Symbol categories where the agent should fire less aggressively (e.g.,
  internal-by-convention modules where the public/private boundary is
  documented in `CLAUDE.md` rather than syntactically marked).
- Symbol categories where the agent should fire more aggressively (e.g.,
  Pydantic Settings field changes where consumers are spread across services
  and contract drift is a known incident class).
- Consumer-discovery cap calibration: the default "10 consumer files per
  symbol" cap may be too low for high-fanout symbols (logger, common
  exceptions) or too high for low-fanout symbols (single-service helpers).
- Diff-pattern hints that signal real blast radius vs noise: signature
  changes vs body changes, optional-parameter additions vs required-parameter
  additions, schema-field renames vs deletions.

(None yet.)

---

## How `/calibrate` interacts with this file

The agent emits dismissal memories with keys like
`calibration:bot-review:<short-tag>`. The user runs `/calibrate
--agent=bot-review` periodically (or when prompted by the SessionStart
hook nudge). The skill presents each entry, the user accepts or rejects,
and accepted entries get merged here under the appropriate section.

Rejected entries get logged to `bot-review.lookback.md` so the agent does
not re-emit the same pattern.
