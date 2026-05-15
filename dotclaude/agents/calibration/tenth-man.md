# Tenth-Man Calibration

Last reviewed by Michael: 2026-04-30 (initial scaffold; no overrides yet)

This file is read by the `mx2-tenth-man` agent before every invocation.
The agent emits calibration drift via `bd remember` (key prefix
`calibration:mx2-tenth-man:`); the `/calibrate` skill is the human review
gate that merges accepted entries into this file. Append-only audit of
merged/rejected entries lives at `tenth-man.lookback.md` (created on first
calibration merge).

If this file is empty (or contains only the scaffold below with no rule
overrides), default rules from the agent definition apply. The agent's
"Calibrate or fade" doctrine still holds: if the agent produces noise the
user learns to ignore, calibration is the only path back.

---

## Rule Overrides

(None yet. Populated via `/calibrate --agent=mx2-tenth-man` after dismissals
are observed and reviewed.)

---

## Example Dismissals

These are past tenth-man outputs the user dismissed, with reasoning. Used as
few-shot calibration so the agent recognizes the pattern next time and either
suppresses or reframes.

(None yet. First entries land after the first round of `/converge` Phase 4.5
runs in the field.)

---

## Threshold Notes

Domain-specific guidance on where the agent's signal-to-noise boundary sits.
Examples that would land here:

- Topics where the agent should fire less aggressively (e.g., naive questions
  on mature areas where context already addresses them).
- Topics where the agent should fire more aggressively (e.g., new architectural
  decisions, cross-team boundary changes).
- User attention-state heuristics: when fragmented attention is signaled, lead
  with single highest-blast-radius concern; under-deliver supporting questions.

(None yet.)

---

## How `/calibrate` interacts with this file

The agent emits dismissal memories with keys like
`calibration:mx2-tenth-man:<short-tag>`. The user runs `/calibrate
--agent=mx2-tenth-man` periodically (or when prompted by the SessionStart
hook nudge). The skill presents each entry, the user accepts or rejects,
and accepted entries get merged here under the appropriate section.

Rejected entries get logged to `tenth-man.lookback.md` so the agent does
not re-emit the same pattern.
