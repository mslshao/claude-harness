# TypeScript Reviewer Calibration

Last reviewed by Michael: 2026-04-30 (initial scaffold; first /calibrate run pending)

This file is read by the `mx2-typescript-reviewer` agent before every invocation.
The agent emits calibration drift via `bd remember` (key prefix
`calibration:mx2-typescript-reviewer:`); the `/calibrate` skill is the human
review gate that merges accepted entries into this file. Append-only audit of
merged/rejected entries lives at `typescript-reviewer.lookback.md` (created on
first calibration merge).

If this file contains only the scaffold below with no rule overrides, default
rules from the agent definition apply.

---

## Rule Overrides

### no-self-correction-mid-output (merged 2026-04-30)

If confidence drops below WARNING threshold during composition, drop the finding entirely. Do not emit retractions in the output (e.g. "Correction: that warning is clear" mid-paragraph); that is calibration-loop cost, not signal. Source: PR #8424 baseline test, 2026-04-30.

### collapse-low-confidence-warnings (merged 2026-04-30)

If you find yourself writing "cosmetically", "effectively correct", "fine in practice", or similar softeners on a WARNING, downgrade to SUGGESTION or drop. Severity should match confidence; mismatch produces noise. Source: PR #8424 baseline test, 2026-04-30.

---

## Example Dismissals

These are past TS-reviewer outputs the user dismissed, with reasoning. Used as
few-shot calibration so the agent recognizes the pattern next time and either
suppresses or reframes.

(None merged yet. Pending entries from 2026-04-30 baseline are emitted as
`bd memories calibration:mx2-typescript-reviewer:*` and await `/calibrate`
review.)

---

## Threshold Notes

Domain-specific guidance on where the agent's signal-to-noise boundary sits.

(None yet. Populated as patterns emerge from real PR reviews.)

---

## How `/calibrate` interacts with this file

The agent emits dismissal memories with keys like
`calibration:mx2-typescript-reviewer:<short-tag>`. The user runs `/calibrate
--agent=mx2-typescript-reviewer` periodically (or when prompted). The skill
presents each entry, the user accepts or rejects, and accepted entries get
merged here under the appropriate section.

Rejected entries get logged to `typescript-reviewer.lookback.md` so the agent
does not re-emit the same pattern.
