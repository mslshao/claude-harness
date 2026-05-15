# Lab-to-Production Promotion

## The pattern

The harness has two tiers for agents, skills, and rules:

- **Personal tier** (`~/.claude/`): the lab. Sharper, opinionated, sometimes idiosyncratic. Edited freely, no review gate. Mirrored to `dotclaude/` in this repo.
- **Project tier** (`<repo>/.claude/`): the production. Scrubbed of personal preference, reviewed by teammates, shipped via PR. Mirrored to `project-tier/` in this repo.

Promotion is unidirectional: personal-leads-project, never the reverse. When a personal-tier agent or skill proves itself through repeated use, it gets scrubbed (third-party preferences removed, team-neutral framing) and submitted as a project-tier PR.

## Why this exists

Code review is a smoothing process. Reviewers ask "is this how we do things?" and that question, applied to an opinionated agent definition or a sharp self-review protocol, often softens the edge that made the artifact useful. The personal tier is a deliberate sandbox where the edge stays sharp.

The project tier still gets the benefits (the team adopts the proven pattern) but in a form the team can collectively maintain. The author can then iterate further in personal tier without breaking the team artifact.

## Promotion criteria

A personal-tier artifact is ready for promotion when:

1. It has been used in real work for at least several weeks.
2. Its behavior is predictable enough that you could explain when it fires and when it does not.
3. The underlying need is generic (multiple engineers would benefit), not tied to the author's specific workflow.
4. Scrubbing leaves the artifact useful (if removing the personal framing kills its value, it is not ready).

## What gets divergent

Personal and project versions of the same artifact CAN diverge intentionally. Examples observed in practice:

- The project-tier code reviewer has limited tool access (read-only file operations). The personal-tier variant has write-capable tools and can invoke the skill catalog. The divergence is intentional: project tier is for team-wide use where unsupervised writes are risky; personal tier is for the author's own loop where the trust calculus differs.
- Personal CLAUDE.md and project CLAUDE.md cover related material with different framing. Personal version uses first-person rules; project version uses team-tier conventions.

The convention: divergence is fine. Promote what generalizes; keep what is personal in personal.

## Audit discipline

Audits that compare personal and project files MUST NOT flag personal-vs-project content differences as "duplication." They are intentionally separate copies of artifacts that started in personal and got promoted. Flagging this as duplication is a category error.

What IS still bloat: rule duplication within personal tier itself, where a personal agent re-states a project-tier rule that is already loaded into every session via the project rules directory. Personal agents should reference the project rule, not re-state it.

## The name-overlap convention

When promoting a personal-tier agent or skill that should also exist at project tier, the `name:` field in both versions stays identical. The Claude Code resolution order is personal-first: when both exist, the personal version runs locally, so the richer and more recent personal variant wins. The project version stays as the team-tier fallback that everyone else gets.

## How this compounds

Over time, the project tier accumulates proven patterns that the team can rely on, while personal tier remains the experimental edge. The two tiers do not compete; they cooperate. The author benefits from both: the project tier propagates good ideas to the team; the personal tier lets the author keep iterating without team-review smoothing.

## Where it has limits

- Promotion requires PR-shaped work (scrubbing, framing, review). If the author is not willing to invest that, the pattern stays personal forever. That is fine for highly idiosyncratic artifacts; not fine for patterns that would help the team.
- The two-tier model is harder to maintain across many engineers with different personal styles. The convention scales for "individuals each curating their own personal tier"; it does not scale for "the team standardizes on one personal tier."
