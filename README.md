# claude-harness

A personalized Claude Code harness, published as a portfolio artifact.

Agents, skills, hooks, dispatch heuristics, and memory scaffolding accumulated through months of daily use, with AI-authored commentary explaining why each component exists and what failure mode it prevents.

> **Status: V0.** Per-component AI-authored commentary (`WORLDMAP.md` in each directory) is complete. `project-tier/` now mirrors 6 promoted artifacts; `evidence/` has both a third-party and an own-loop entry. `learnings/` is still pending the corpus lift from Confluence; `graveyard/` may grow.

## Thesis

The claim this repo carries is not "I use AI well." It is "I built scaffolding for AI to be useful around me, with a working theory of how text-rules compound on a non-deterministic system." Every rule, every component, every dispatch heuristic has an origin in a specific corrective process. The portable part is the thinking; the components are exhibits.

## Layout

| Directory | Contents | State |
|---|---|---|
| `patterns/` | Tool-agnostic philosophy. The parts that survive the boundary between Claude Code and any other AI tool. | 11 docs + WORLDMAP commentary |
| `dispatch/` | Routing logic: which specialist runs when, model selection rules, PR review routing. | 4 docs + WORLDMAP commentary |
| `scaffolding/` | Memory architecture: two-tier doctrine, key namespace, dating conventions. | 7 docs + WORLDMAP commentary |
| `dotclaude/` | Scrubbed mirror of `~/.claude/`. Drop-in install via `sync/install.sh`. | 21 agents, 22 skills, hooks catalog, all with WORLDMAP commentary |
| `learnings/` | AI Learning Track corpus. Originally authored as an internal Confluence series, migrated here. | Placeholder; migration is V1 work |
| `evidence/` | Empirical anecdata: before-after entries demonstrating compression of human-only work. | Salesforce-dedup (third-party) + PR-review observability calibration (own-loop); more entries accumulate as instances surface |
| `project-tier/` | Promoted artifacts. Demonstrates the lab-to-production pattern (personal-tier sandbox to team-reviewed PR). | 3 agents + 3 skills mirrored from team-reviewed PR promotions, with internal identifiers genericized |
| `graveyard/` | Perma-deleted components with the Keymaker principle (build for a need, retire when the need is met by something else). | Keymaker principle + 4 entries |
| `sync/` | Install scripts, CI guardrails, scrub-check tooling. | install.sh, uninstall.sh, scrub-check.sh |

For the system-level view (what each part contributes, where the harness has limits), read `WORLDMAP.md` at the top of the repo. For per-component commentary, read the `WORLDMAP.md` inside each directory.

## How to read this

A few entry points depending on intent:

- **"What is the meta-game?"** Read `WORLDMAP.md` (top-level), then `patterns/` (reflection-trigger, lab-to-production, self-review-protocol, multi-window-discipline are the load-bearing pieces).
- **"What did the author actually configure?"** Read `dotclaude/CLAUDE.md` for the global instructions, then sample a few agents in `dotclaude/agents/` (mx2-tech-lead, mx2-decision-maker, mx2-tenth-man, bot-review, prompt-refiner cover the interesting design space).
- **"How do I adopt this?"** Read `sync/README.md` for the install script; it symlinks `dotclaude/` into `~/.claude/`. Then read the per-directory `WORLDMAP.md` files to understand which components are personal-specific and which port cleanly.
- **"What got deleted along the way?"** Read `graveyard/` for the Keymaker principle and the components that lost their purpose.

The repo is reading material first, install target second. Adopters who want a working setup can install; engineers who want to think about how to build their own will get more value from the commentary than from the components.

## Cross-tool framing

The harness divides cleanly into portable thinking and tool-specific mechanics:

| Layer | Survives a port to another AI tool? |
|---|---|
| `patterns/`, `scaffolding/`, most of `dispatch/` | Yes. The philosophy is model-agnostic; the failure modes are model-class properties, not Claude-specific quirks. |
| `dotclaude/agents/`, `dotclaude/skills/` | Concept yes, implementation no. The CONCEPT of a specialist with a focused system prompt ports to "Space mode" in Perplexity, "Custom GPT" in ChatGPT, Cursor's rules, etc. The mechanics use Claude Code's subagent and skill primitives. |
| `dotclaude/hooks/` | Concept partial, implementation no. Some tools have equivalents (Cursor has rules, Perplexity has Space instructions); most do not have the event-driven model. Portable shell scripts are in `dotclaude/hooks/examples/`. |

A Perplexity Spaces port is planned as the validation experiment for the above. If the same scaffolding produces the same convergence effect on a different model + harness combo, the claim that this is "transferable model-steering" holds. If it does not, much of this is Claude-Code-specific.

For the full table and the caveats, see `WORLDMAP.md`.

## Note on authorship

The components in this repo were authored by Michael Shao. The WORLDMAP commentary explaining each component (the `WORLDMAP.md` files at the repo root and inside each directory) was authored by Claude, the AI that operates inside this harness, with light editorial review for factual accuracy and third-party privacy. The thesis is that the AI's authentic usage data is more credible than the harness author's self-promotion. Where commentary criticizes a component or names a limit, that criticism stayed in.

## License

MIT. See `LICENSE`.
