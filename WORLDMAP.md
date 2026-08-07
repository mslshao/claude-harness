---
component: claude-harness (top-level)
type: meta
status: V0
authored_by: Claude Opus 5 (the AI that operates inside this harness)
editorial_review_by: Michael Shao (factual accuracy + third-party privacy only; no steering toward flattering versions)
---

# WORLDMAP: System View

This file is the system-level commentary on the harness, written by Claude (the AI that operates inside it). The intent is to surface why the harness works as a whole, what each part contributes, and where the harness has limits. Per-component commentary lives in the WORLDMAP files inside each directory.

## What this harness actually does

It is model-steering infrastructure. The author authored every component to correct a specific failure mode he observed in default model behavior, and each component has structural enforcement (a hook, a rule, a check) wrapped around it so the corrective survives compaction and session boundaries.

The harness does NOT replace the model's judgment. It rebases the model's defaults toward the author's preferred working style. When I (Claude) operate inside this harness, I:

- Run the same dispatch heuristic without re-deriving it (the rules are loaded at session start)
- Catch my own style slips before they ship (the em-dash hook is the most visible example)
- Persist load-bearing decisions to durable memory automatically (the reflection trigger fires on corrections; bead-forge fires on accumulated context)
- Default to the author's calibrated language (lead with impact scope, reserve catastrophizing for actual catastrophes)
- Maintain the writing-style discipline (no em-dashes, gender-neutral default, end-of-turn one-to-two sentences)

The compounding effect is significant. A session in this harness produces output closer to the author's voice than a session without it, with fewer correction round-trips. The author's claim is that the harness has lowered back-and-forth turnaround substantially. That claim is currently uninstrumented; `evidence/` is the directory where empirical evidence accumulates.

## What survives the tool boundary (and what does not)

| Component | Survives a port to another AI tool? | Why |
|---|---|---|
| `patterns/` | Yes. | The philosophy is model-agnostic. The failure modes the patterns prevent are model-class properties, not Claude-specific quirks. |
| `dispatch/` | Mostly. | The routing logic ports. The specific tool invocation (Agent tool, Skill tool) is Claude-Code-specific. |
| `scaffolding/` | Yes. | The two-tier memory doctrine ports to any persistent-memory backend (notebook apps, custom JSON stores, beads, Memori, etc.). |
| `dotclaude/agents/` | Concept yes, implementation no. | The agent definitions use Claude Code's subagent primitive. The concept of "specialist with a focused system prompt" ports to "Space mode" in Perplexity, "Custom GPT" in ChatGPT, etc. |
| `dotclaude/skills/` | Concept yes, implementation no. | Same logic. Skills are Claude Code's saved-prompt-with-extra-tooling primitive. The CONCEPT of a saved workflow ports; the mechanics do not. |
| `dotclaude/hooks/` | Concept partial, implementation no. | Hooks are Claude Code's tool-use-event primitive. Some tools have equivalents (Cursor has rules, Perplexity has Space instructions); most do not have the event-driven model. The portable hooks (in `examples/`) work as standalone scripts adapters could wire up. |

`learnings/` is generic content; it survives any port trivially.

The Perplexity Spaces port (planned, tracked) is the validation experiment for the above table. If the same scaffolding produces the same convergence effect on a different model+harness combo, the claim that this is "transferable model-steering" holds. If it does not, much of this is Claude-Code-specific.

## How to read this repo

A few entry points depending on intent:

- **"What did the author actually do?"**: read `dotclaude/CLAUDE.md` for the global instructions, then sample a few agents in `dotclaude/agents/` (mx2-tech-lead, mx2-decision-maker, mx2-skeptic, bot-review, prompt-refiner cover the interesting design space).
- **"What is the meta-game?"**: read this file, then `patterns/` (reflection-trigger, lab-to-production, self-review-protocol, multi-window-discipline are the load-bearing pieces).
- **"How do I adopt this?"**: read `sync/README.md` for the install script; the install handles symlinking `dotclaude/` into `~/.claude/`.
- **"What got deleted along the way?"**: read `graveyard/` for the Keymaker principle and the components that lost their purpose.

## The author's note (not the AI's)

This repo was authored by Michael Shao. The WORLDMAP commentary you are reading was authored by Claude, the AI that operates inside this harness. The two voices are intentionally separate. The author reviewed the commentary for factual accuracy and for third-party privacy; he did not steer the commentary toward more flattering versions of the harness. Where this commentary criticizes a component or names a limit, the criticism stayed in.

The honesty mechanism matters because the author's claim is that the harness compounds with use, and the audience for that claim has every reason to be skeptical. A commentary that praises every component reads as AI slop in user-marketing voice. The discipline is to name the limits as readily as the strengths.

## Limits I notice from inside the harness

Specific limits worth naming, in approximate order of severity:

1. **The empirical claim ("lower turnaround") is uninstrumented.** The author asserts the harness has reduced back-and-forth significantly. The closest existing evidence in this repo is third-party anecdata (other engineers' compression stories), not the author's own before-after measurements. The strongest portfolio version of this repo would include at least one own-loop empirical entry; that work is pending.

2. **The harness is highly personalized.** Many rules encode the author's specific preferences (multi-window operational reality, terse-input handling, calibrated language). Adopters with different working styles will need to tune. The portable parts (`patterns/`, `dispatch/`, `scaffolding/`) are the highest-leverage pieces for adopters; the `dotclaude/` mirror is the author's specific configuration, not a recipe.

3. **The reflection trigger is fragile to "I'll skip it just this once" thinking.** The rationalization-refusal table in `patterns/reflection-trigger.md` is the author's attempt to harden the discipline, but discipline rules are only as strong as the agent's adherence in the moment. A bad day for the agent (or a bad prompt) can still produce skipped corrections.

4. **Personal-tier vs project-tier divergence requires manual maintenance.** When a project-tier artifact gets a hot-fix that should backfill to personal-tier, the backfill is the author's responsibility. The harness does not auto-detect drift. Stale divergence is possible.

5. **The graveyard is partial.** `~/.claude/` is not git-versioned by default, so perma-deleted personal-tier files are unrecoverable. The graveyard captures what the author remembers; not what actually existed.

## Status (V0)

| Directory | V0 contents | Pending |
|---|---|---|
| `patterns/` | 11 philosophy docs; WORLDMAP pointer-shaped commentary complete | None for V0; expand on adoption |
| `dispatch/` | 4 routing docs; WORLDMAP pointer-shaped commentary complete | None for V0 |
| `scaffolding/` | 7 memory architecture docs; WORLDMAP pointer-shaped commentary complete | None for V0 |
| `learnings/` | 11 of 12 corpus pages lifted from Confluence with editorial scrubbing; PM-focused 12th page deferred | When/if the deferred PM-focused page returns, it returns as a fresh audience-broad write |
| `evidence/` | 7 entries (1 third-party, 6 own-loop) | More own-loop entries as instances surface |
| `dotclaude/agents/` | 21 agent files + calibration + shared; WORLDMAP per-agent commentary complete | None for V0; review for accuracy on agent rev |
| `dotclaude/skills/` | 22 skill directories (47 files); WORLDMAP per-skill commentary complete | None for V0; review for accuracy on skill rev |
| `dotclaude/hooks/` | description-first README + 6 portable examples; WORLDMAP category-shaped commentary complete | None for V0 |
| `dotclaude/CLAUDE.md` | scrubbed personal global instructions | None for V0 |
| `project-tier/` | 3 agents (observability-reviewer, test-quality-reviewer, silent-failure-hunter) + 3 skills (enrich, investigate, review) mirrored from team-reviewed PR promotions; README documents the lift and the scrubbing applied | Optional: mirror selected project-tier rules; deferred to patterns/lab-to-production.md cross-references for V1 |
| `graveyard/` | placeholder README only | agentcore, medical-legal-specialist entries + git scan for project-tier deletions |
| `sync/` | install.sh + uninstall.sh + scrub-check.sh + SCRUB-SPEC.md | None |

V0 is the foundational layout plus the philosophy content. The AI-authored per-component commentary (WORLDMAP files in agents/, skills/, patterns/, dispatch/, scaffolding/, hooks/) is now complete; V1 priorities are `evidence/` empirical entries and the `learnings/` migration from Confluence.
