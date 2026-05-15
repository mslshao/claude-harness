# Anecdata Pattern

Running log of one-off engineering stories where AI demonstrably moved a task that was previously human-only. The collection is selection-biased and not controlled data; the discipline below is what keeps the corpus honest.

## Purpose

Counter the "AI is not useful" premise common among skeptic-leaning engineers. Skeptics and proponents are both prone to anecdote; this corpus's goal is to keep the anecdote inventory honest, dated, and labeled with the caveats that apply.

## Caveats to apply when citing any entry

- **Selection bias**: each story is told because it worked. The misses are invisible.
- **N=1** per entry. No controlled comparison.
- **Time-savings claims are self-reported** and rarely include prep / prompt iteration time.
- **Year-old human baselines often predate long-context inference and dataset-dump workflows.** The comparison is partly tooling generation, not human vs AI.
- An anecdote that survives "would a skeptic accept this?" is one that has an objective signal (test pass rate, dataset coverage, reviewer parity, post-merge bug count), not just a feeling.

## Format per entry

```
### YYYY-MM-DD: <one-line summary> (<source>)

**Context.** What was the underlying problem and what had been tried.

**What AI did.** Concrete description of the AI workflow used and the artifact produced.

**Baseline.** What the human-only alternative was, and what it had cost.

**Verifiability.** What objective signal supports the claim.

**Honest read.** What this entry actually supports and what it does not.
```

## What does not belong here

- Generic "AI changed my workflow" claims with no task, no baseline, no signal.
- Personal wins on AI tooling that the harness author built. Those go in beads memories or skill-specific topic files.
- Claims that double as marketing material. The audience for this file is internal skeptics and external honest readers; tone is honest, not promotional.

## Why this corpus matters for this repo

The harness's load-bearing empirical claim is that it lowers back-and-forth turnaround on real work. That claim is currently uninstrumented; the entries below are the closest existing evidence, plus a template for adding more.

The strongest portfolio version of this corpus would include at least one own-loop before/after entry (the harness author's own measurable compression), not just third-party anecdotes. That entry is the load-bearing piece for the empirical claim and is pending.
