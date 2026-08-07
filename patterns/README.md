# patterns/

Tool-agnostic philosophy. The parts of this harness that survive the boundary between Claude Code and any other AI tool (Perplexity Spaces, ChatGPT custom GPTs, Cursor, IDE assistants).

Each file is a self-contained pattern with:

1. The corrective process that produced it (which slip prompted the rule)
2. What failure mode it prevents
3. How it compounds with use
4. Where it has limits

All 12 docs are written, and each one has a WORLDMAP entry. What is not established is the claim at the top of this file: no port to another tool has been run, so "survives the boundary" is a design intent rather than a measured result. The Perplexity Spaces experiment that would test it is still planned.

## Contents

- `lab-to-production.md` (personal-tier sandbox to team-reviewed promotion)
- `reflection-trigger.md` (two-strike pattern, mid-conversation correction to durable rule)
- `self-review-protocol.md` (2-pass small, 4-pass large)
- `contrapositive-proof.md` (author principles unconditionally; mark thresholds as one-way triggers)
- `multi-window-discipline.md` (designing for fragmented attention)
- `cost-via-delegation.md` (Opus retains oversight, Sonnet executes)
- `prompt-interpretation.md` (terse-input handling, scope-probe pattern)
- `writing-style-discipline.md` (calibrated language, gender-neutral default)
- `code-discipline.md` (no-comment default, YAGNI, cleanup)
- `decision-making-rules.md` (verification before assertion, skeptic lens)
- `response-behavior.md` (destructive-op discipline, no auto-reconfirm)
- `context-loading-protocol.md` (what to load before substantive work)
