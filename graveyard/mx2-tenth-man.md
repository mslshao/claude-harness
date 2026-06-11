---
component: mx2-tenth-man
type: agent
status: renamed
source: repo history
superseded_by: [mx2-skeptic]
---

# mx2-tenth-man

An adversarial-advisor agent: it asks the naive, dumb, or obvious-but-unasked question about plans, decisions, and autonomous-pipeline outputs, as a safety net for fragmented attention (the multi-window operational reality). Advisory only, never blocks.

This is a graveyard entry for a NAME, not a capability. The agent still exists and still does exactly this job; it now lives as `mx2-skeptic` (`dotclaude/agents/mx2-skeptic.md`). The system prompt and behavior were kept intact across the rename; only the surface vocabulary changed.

## The name it carried

"Tenth man" is borrowed from the Israeli intelligence convention sometimes called the tenth-man rule: if nine people look at a situation and reach the same conclusion, the tenth is obligated to take the opposite position, not because the tenth is likely right, but because unexamined consensus is the dangerous state and an awkward question is cheaper than a missed assumption. The agent was that tenth voice for autonomous workflows: when the decision-maker says PROCEED and the specialists agree, it asks what everyone is taking on faith.

## Why the name was retired

The function was right; the name was not self-documenting. An agent's `name:` and `description:` are read at the retrieval surface (by the dispatch layer, and by the model deciding whether to invoke it) far more often than the clever origin is ever appreciated. "Tenth-man" means nothing until you already know the intelligence-community reference; "skeptic" says what the agent does in the word itself. The obscure-but-clever label was a standing decode-tax on every dispatch decision, paid in exchange for a flourish almost no reader cashed in.

The rename to `mx2-skeptic` changed only the surface: same posture ("your job is to disagree"), same advisory-not-blocking contract, same not-this-agent routing to the thinking-partner and the decision gate. The agent opens the same way; it just announces itself plainly now.

## Lessons captured

This belongs to the same family as the `contrapositive-proof` pattern in `patterns/`: an artifact's retrieval surface is read literally and often, so cleverness that needs decoding is a cost, not a flourish. The usual Keymaker case retires a component whose purpose was superseded. This is the rarer variant where the purpose persists but the label was a liability, and the fix is a rename rather than a deletion. The honest read: this was a low-stakes change (a rename, fully reversible, no behavior touched), recorded here mainly because the reasoning (name for the reader who scans, not the reader who studies) generalizes to every agent and skill description in the harness.
