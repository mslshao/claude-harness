# Multi-Window Discipline

## The pattern

Design every agent output (and every harness component that produces output) for a user whose attention is fragmented across multiple AI tool windows simultaneously. The reality this assumes: the author runs up to five Claude Code windows at once, plus a browser, plus an editor, plus chat. Attention is not undivided; it is sampled in 30-second slices.

Implications for output design:

- **Lead with what matters most.** Highest-impact information first. Never bury blockers or risks in prose. The user might read only the first paragraph before context-switching.
- **End-of-turn summaries are scannable in under 30 seconds.** Tables, severity-tagged callouts, code blocks for IDs that get pasted elsewhere. If the summary requires careful reading, it has failed its purpose.
- **Visual signals direct attention.** Severity tags, prefix characters, fenced code blocks for content that gets copied. The user's eye picks up the structural cue faster than the prose.
- **State results and decisions directly.** No "I considered X but...". No reasoning narration. The result, the decision, the next step.

## Why this exists

A user who runs one AI window at a time can afford verbose narration; they read every word. A user who runs five windows samples each one. The fragmented-attention case is the harder bar to clear: an output that works under fragmented attention also works under focused attention, but not the reverse.

The pattern also serves a second purpose. A user under fragmented attention may accept reflexively (clicking "yes" or "approve" without reading) when the output buries the consequential detail. Leading with the high-impact information makes it harder to miss something that warrants attention.

## The safety-net agent

A specific defensive pattern in this harness: an "adversarial advisor" agent (`mx2-skeptic.md` in this author's setup) whose job is to ask naive, dumb, or obvious-but-unasked questions about autonomous-pipeline outputs. Designed precisely as a safety net for the fragmented-attention failure mode. The agent is advisory only, never blocks, never participates in approvals. Its only function is to surface what a careful reader would notice but a sampling reader might miss.

Invoking the safety-net agent on high-blast-radius decisions costs roughly one minute and one model invocation. The cost of missing a load-bearing detail in autonomous-pipeline output is hours of misdirected work. The asymmetry is severe enough that the safety net is worth the cost on every decision where the user's reflexive accept is the failure mode.

## End-of-turn discipline

The most concrete enforcement of multi-window discipline lives in the end-of-turn behavior:

- One or two sentences. What changed and what is next. Nothing else.
- Tables and bullet lists are reports, not summaries; use them only when the user explicitly asked for status across multiple items.
- If the answer to "what changed and what is next" is more than two sentences, you are re-explaining work the user already saw in the body of the response.
- Substance the user received in interim updates does not need recap at end-of-turn.

## How this compounds

Adopted as a default across all agents in a harness, the discipline produces predictable output shape. The user learns to scan in fixed patterns: top of message for the headline, end for the next step, fenced blocks for IDs to copy. The harness becomes more usable under fragmented attention than it was under focused attention previously, because the structure is consistent across agents and skills.

## Where it has limits

- Some content genuinely requires long-form prose (design discussions, multi-source synthesis, complex investigations). The discipline applies to the wrapper (the headline, the summary, the close), not necessarily to the body.
- A user with single-window attention can find the discipline curt or under-explanatory. The fix is asymmetric: the multi-window user benefits from concision; the single-window user can ask for elaboration. Optimizing for the harder case is the right call.
