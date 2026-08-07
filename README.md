# claude-harness

A personalized Claude Code harness, published as a portfolio artifact.

Agents, skills, hooks, dispatch heuristics, and memory scaffolding accumulated through months of daily use, with AI-authored commentary explaining why each component exists and what failure mode it prevents.

> **Status: V3.** The `dotclaude/` mirror is caught up to personal-tier state as of 2026-08-07: 22 agents, 32 skills (`campaign` and `cold-review` are new this pass), and a `commands/` directory (`jira`, `confluence`) that `install.sh` and `uninstall.sh` now symlink alongside agents, skills, and hooks. The hooks catalog now documents all 72 hooks across 10 sections plus a shared-library entry, with 8 portable runnable examples. `project-tier/` mirrors 17 promoted artifacts (6 agents, 4 skills, 7 rules), re-synced against the live project tier this pass after all 7 previously-mirrored artifacts were found drifted; `evidence/` has 8 entries (one third-party, seven own-loop); `learnings/` has 11 of 12 pages lifted from the original Confluence corpus with editorial scrubbing applied.
>
> This pass also closed a privacy gap. The Tier 1 real-name pattern list (`sync/scrub-names.local`) is gitignored by design, and it was missing, so `scrub-check.sh` had been running with the real-name scan disabled and reporting a qualified pass while teammate names sat in the published mirror. The list is restored, the names are scrubbed, and the mirror now scans clean on all four tiers. `sync/SCRUB-SPEC.md` documents the failure mode and the fresh-clone recovery steps, and its Tier 3 section was corrected to match what the detector actually enforces (bead IDs stay; they were never scrubbed).
>
> Not done: the 12th `learnings/` page (PM workflows) is still deferred; the Perplexity Spaces port described below is still planned, not run, so the transferability claim it exists to test remains untested. `graveyard/` may grow as more historical context is reconstructed.

## Thesis

The claim this repo carries is not "I use AI well." It is "I built scaffolding for AI to be useful around me, with a working theory of how text-rules compound on a non-deterministic system." Every rule, every component, every dispatch heuristic has an origin in a specific corrective process. The portable part is the thinking; the components are exhibits.

## Layout

| Directory | Contents | State |
|---|---|---|
| `patterns/` | Tool-agnostic philosophy. The parts that survive the boundary between Claude Code and any other AI tool. | 12 docs + WORLDMAP commentary |
| `dispatch/` | Routing logic: which specialist runs when, model selection rules, PR review routing. | 4 docs + WORLDMAP commentary |
| `scaffolding/` | Memory architecture: two-tier doctrine, key namespace, dating conventions. | 7 docs + WORLDMAP commentary |
| `dotclaude/` | Scrubbed mirror of `~/.claude/`. Drop-in install via `sync/install.sh`. | 22 agents, 32 skills, 2 commands, a hooks catalog covering all 72 hooks with 8 portable examples; WORLDMAP commentary covers every subdirectory: agents (20 entries for 22 files, the launch trio shares one), skills (32 entries), commands (2 entries), and hooks (per-category, with per-hook detail in the catalog) |
| `learnings/` | AI Learning Track corpus. Originally authored as an internal Confluence series, migrated here with editorial scrubbing. | 11 of 12 pages lifted; 12th (PM workflows) deferred |
| `evidence/` | Empirical anecdata: before-after entries demonstrating compression of human-only work. | 8 entries: Salesforce-dedup (third-party) + 7 own-loop (PR-review observability calibration, cross-session handoff, vocabulary-in-memory, enforcement ladder, agent-tier eval, guardrail self-protection, rules-as-executable-specs); more accumulate as instances surface |
| `project-tier/` | Promoted artifacts. Demonstrates the lab-to-production pattern (personal-tier sandbox to team-reviewed PR). | 6 agents + 4 skills + 7 rules mirrored from team-reviewed PR promotions, with internal identifiers genericized. Membership determined by first-commit authorship, so team-authored artifacts in the same live directory are excluded. Snapshots go stale silently; re-synced each harness sync pass, with nothing enforcing it automatically |
| `graveyard/` | Perma-deleted components with the Keymaker principle (build for a need, retire when the need is met by something else). | Keymaker principle + 5 entries |
| `sync/` | Install scripts, CI guardrails, scrub-check tooling. | install.sh, uninstall.sh, scrub-check.sh, SCRUB-SPEC.md; the Tier 1 real-name pattern list (`scrub-names.local`) is gitignored and must be recreated on a fresh clone |

For the system-level view (what each part contributes, where the harness has limits), read `WORLDMAP.md` at the top of the repo. For per-component commentary, read the `WORLDMAP.md` inside each directory.

## How to read this

A few entry points depending on intent:

- **"What is the meta-game?"** Read `WORLDMAP.md` (top-level), then `patterns/` (reflection-trigger, lab-to-production, self-review-protocol, multi-window-discipline are the load-bearing pieces).
- **"What did the author actually configure?"** Read `dotclaude/CLAUDE.md` for the global instructions, then sample a few agents in `dotclaude/agents/` (mx2-tech-lead, mx2-decision-maker, mx2-skeptic, bot-review, prompt-refiner cover the interesting design space).
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
