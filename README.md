# claude-harness

A personalized Claude Code harness, published as a portfolio artifact.

Agents, skills, hooks, dispatch heuristics, and memory scaffolding accumulated through months of daily use, with AI-authored commentary explaining why each component exists and what failure mode it prevents.

> **Status: V0 scaffolding.** Substantive content lands progressively. The directory tree below is the target shape; many directories currently hold only a placeholder README.

## Thesis

The claim this repo carries is not "I use AI well." It is "I built scaffolding for AI to be useful around me, with a working theory of how text-rules compound on a non-deterministic system." Every rule, every component, every dispatch heuristic has an origin in a specific corrective process. The portable part is the thinking; the components are exhibits.

## Layout

| Directory | Contents |
|---|---|
| `patterns/` | Tool-agnostic philosophy. The parts that survive the boundary between Claude Code and any other AI tool. |
| `dispatch/` | Routing logic: which specialist runs when, model selection rules, PR review routing. |
| `scaffolding/` | Memory architecture: two-tier doctrine, key namespace, dating conventions. |
| `learnings/` | AI Learning Track corpus. Originally authored as a Confluence series, migrated here. |
| `evidence/` | Empirical anecdata: before-after entries demonstrating compression of human-only work. |
| `dotclaude/` | Scrubbed mirror of `~/.claude/`. Drop-in install via `sync/install.sh`. |
| `project-tier/` | Promoted artifacts. Demonstrates the lab-to-production pattern (personal-tier sandbox to team-reviewed PR). |
| `graveyard/` | Perma-deleted components with the Keymaker principle (build for a need, retire when the need is met by something else). |
| `sync/` | Install scripts, CI guardrails, scrub-check tooling. |

## Note on authorship

The components in this repo were authored by Michael Shao. The WORLDMAP commentary explaining each component (the `WORLDMAP.md` files inside each directory) was authored by Claude, the AI that operates inside this harness, with light editorial review for factual accuracy and third-party privacy. The thesis is that the AI's authentic usage data is more credible than the harness author's self-promotion. Where commentary criticizes a component, that criticism stayed in.

## License

MIT. See `LICENSE`.
