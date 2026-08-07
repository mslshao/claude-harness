# Skeptic Calibration

Last reviewed by Michael: 2026-04-30 (initial scaffold; no overrides yet)

This file is read by the `mx2-skeptic` agent before every invocation.
The agent emits calibration drift via `bd remember` (key prefix
`calibration:mx2-skeptic:`); the `/calibrate` skill is the human review
gate that merges accepted entries into this file. Append-only audit of
merged/rejected entries lives at `skeptic.lookback.md` (created on first
calibration merge).

If this file is empty (or contains only the scaffold below with no rule
overrides), default rules from the agent definition apply. The agent's
"Calibrate or fade" doctrine still holds: if the agent produces noise the
user learns to ignore, calibration is the only path back.

---

## Rule Overrides

(None yet. Populated via `/calibrate --agent=mx2-skeptic` after dismissals
are observed and reviewed.)

---

## Example Dismissals

These are past skeptic outputs the user dismissed, with reasoning. Used as
few-shot calibration so the agent recognizes the pattern next time and either
suppresses or reframes.

### Strand-scenario dismissed on pipeline order-of-operations, residual kept (2026-07-17, campaign gate)

Headline claimed node K+1 forks BEFORE node K's Phase-4 gate approval, so a
non-PROCEED could strand published downstream PRs. Dismissed the premise: cursor
advance requires K terminal_success (gate passed, PR created, CI green) before
K+1 forks, so gate-fails-after-fork cannot occur within one node. KEPT the
residual: a mid-chain halt (node K+2 fails) leaves earlier-forked downstream
drafts live with only draft status as the merge gate; folded
halt-comments-on-downstream-PRs + termination-gate-on-every-entry + a lock-race
drill into the plan. Lesson: check pipeline order-of-operations before crediting
a strand scenario, but always extract the residual state-liveness concern
underneath (the premise can be wrong while a real concern hides below it).

### "Citation fabricated" dismissed after direct-grep verification (2026-07-09, /converge overwatch)

Challenge agent claimed a 15min-start / back-off-to-30-60 interval citation was
fabricated (it found only different 30min/8h-cap numbers in another file).
Dismissed after direct grep: the exact quoted guidance DID exist in the
office-hours transcript captured earlier in the same session. Kept the citation;
added a note distinguishing it from the different (shift-bounded) numbers.
Lesson: a specialist's grep-based "source does not exist" claim can miss a file
written earlier in the SAME session; verify via direct grep before accepting a
not-cited or fabrication finding, especially when the orchestrator authored the
cited source moments earlier.

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

The ORCHESTRATOR (dispatching session) emits dismissal memories with keys
like `calibration:mx2-skeptic:dismissal:<short-tag>` (4-segment; legacy
3-segment keys route to Example Dismissals by default; the agent cannot
observe dismissals itself). The user runs `/calibrate
--agent=mx2-skeptic` periodically (or when prompted by the SessionStart
hook nudge). The skill presents each entry, the user accepts or rejects,
and accepted entries get merged here under the appropriate section.

Rejected entries get logged to `skeptic.lookback.md` so the agent does
not re-emit the same pattern.
