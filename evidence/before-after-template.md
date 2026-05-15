# Before/After Template

Use this template when adding a new entry to `evidence/`. Copy, paste into a new dated file (`YYYY-MM-DD-<short-slug>.md`), fill in.

The format is deliberately structured to force honesty: every section has a discipline against the natural tendency to over-claim.

## Template

```markdown
# YYYY-MM-DD: <one-line summary>

**Source**: where this anecdote came from (a teammate's chat, your own session, a PR discussion). Note if scrubbed for public version.

**Context.** What was the underlying problem and what had been tried before the AI workflow was applied. Include the alternative approach in concrete terms.

**What AI did.** Concrete description of the AI workflow used and the artifact produced. Be specific: what was the prompt, what tools were involved, what was the output. Avoid generic "AI helped with X."

**Baseline.** What the human-only alternative was, and what it had cost. Wall-clock time, calendar days, attempts before solution, etc. If the baseline is "a different engineer working on similar problem a year ago," note that explicitly.

**Verifiability.** What objective signal supports the claim? Test pass rate, dataset coverage, reviewer parity, post-merge bug count, etc. A signal-less anecdote is not evidence; it is testimony.

**Honest read.** Two parts:

1. What this entry actually supports. State the narrowest claim the evidence justifies.
2. What this entry does NOT support. State what the evidence does not let you conclude.

## Caveats specific to this entry

- (Selection bias note: was this remembered because it worked?)
- (Tooling-generation note: would the human baseline have been faster with current tools?)
- (Sample-size note: is N=1 enough to conclude anything beyond "this one case worked"?)
```

## Worked example

See `2026-04-30-salesforce-dedup.md` for an entry that follows this template.

## What does NOT belong in an entry

- Generic "AI changed my workflow" claims with no task, no baseline, no signal.
- Self-promotional framing ("Claude completely transformed our team"). The audience for this file is honest readers, not enthusiasts.
- Disparaging framing of the human baseline ("the old engineer was slow"). The fair framing is "the tools were different."
- Anecdotes that double as marketing material.

## Notes on the own-loop entry

The strongest entry in this corpus would be a before/after from the author's own work, with measurable compression (time, attempts, correction round-trips, etc.). The Salesforce dedup entry is third-party anecdata; it supports the general pattern but does not directly evidence the author's claim that the harness lowers turnaround on his own work.

A pending entry: the author's own measurable before/after on a specific workflow that the harness has compressed. Format and discipline are above; the entry itself awaits a session where the measurement can be made.
