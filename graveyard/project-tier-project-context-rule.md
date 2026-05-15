---
component: .claude/rules/project-context.md (project tier)
type: rule
status: deleted
source: git log (PR #8104)
superseded_by: hierarchical CLAUDE.md restructure (top-level CLAUDE.md + path-scoped rules)
---

# project-context.md (project tier)

A project-tier rule file that captured high-level context about the codebase: monorepo structure, domain, architecture overview, key principles. Removed when the project CLAUDE.md hierarchy was introduced.

## What it did

The file served as the "what is this codebase about" document for agents working in the repo. New agents could read it once to orient themselves: what kind of system this is, what languages and frameworks are in use, what the principles are.

## Why it was retired

The orientation content belonged at the CLAUDE.md level, not as a separate rule. When the hierarchical CLAUDE.md restructure landed (PR #8104), the top-level `CLAUDE.md` became the canonical orientation surface, and the `.claude/rules/` directory was reserved for prescriptive rule content (style, testing, verification, etc.). Mixing orientation and prescription in `project-context.md` was confusing the boundary.

## Replacement structure

The orientation content moved to the top-level `CLAUDE.md`, which now has a fixed structure:

- Monorepo overview
- Rule scoping table (which rule files load for which paths)
- Domain summary
- Architecture summary
- Key principles
- Available agents (with usage hints)
- Available slash commands

The `.claude/rules/` directory was reserved for prescriptive rules only.

## Lessons captured

The split codified the orientation-vs-prescription boundary. Orientation tells the model "what this codebase is" (descriptive, useful once at session start); prescription tells the model "what to do" (rules, loaded on every task in scope). Mixing them produced rules that read like project tours and orientation that read like prescriptive rules; neither was effective at its purpose.

A second-order lesson: **CLAUDE.md is the canonical orientation surface**. New developers, new agents, anyone coming to the codebase reads CLAUDE.md to get oriented. Putting orientation in a sibling file made it less likely to be loaded at the right time.
