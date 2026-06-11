# graveyard/

Perma-deleted components and what superseded them.

## The Keymaker principle

> Components in this harness exist for a specific purpose. When the purpose is superseded (by a more specific child or a more generic parent), the component is deleted, not archived. The harness carries no legacy maintenance burden.

The name is borrowed from the Matrix Reloaded character whose role was so narrow that, once his purpose was fulfilled, he was scheduled for deletion. The discipline cuts the same way: build for a need, retire when the need is met by something else, do not keep the artifact around "just in case."

## Reconstruction caveat

Personal-tier `~/.claude/` is not git-versioned by default, so perma-deleted personal-tier files are unrecoverable in a strict sense. Entries below are reconstructed from author recall plus project-tier git history. Reconstructed entries (memory-only) are marked `**Source: recall**`; entries with documented history (project-tier removals visible in git log) are marked `**Source: git log**`.

## Files

| File | Source | Superseded by |
|---|---|---|
| `agentcore.md` | recall | dispatch heuristic + tech-lead agent |
| `medical-legal-specialist.md` | recall | mx2-security-auditor + per-domain context |
| `project-tier-best-practices-rule.md` | git log | restructured into separate scoped rules (tenets, code-style, debugging, verification) |
| `project-tier-project-context-rule.md` | git log | absorbed into hierarchical CLAUDE.md restructure |
| `mx2-tenth-man.md` | repo history | renamed/reframed to `mx2-skeptic` (capability intact; the obscure name was the liability) |

Note: `mx2-tenth-man.md` is the one entry here that is a RENAME, not a deletion. The agent still exists as `mx2-skeptic`; the entry records why the name was retired (a retrieval-surface label that needed decoding before it meant anything). It is kept in the graveyard because the reasoning generalizes, even though the Keymaker "build for a need, retire when superseded" framing is usually about deletion.

## Pattern observation

Project-tier `.claude/` has been mostly additive over its history (only the two rule deletions above; no agent or skill deletions). This is a working signal: the lab-to-production discipline filters artifacts before promotion, so promoted artifacts tend to survive. Personal-tier `~/.claude/` is where iteration and deletion happens; project-tier is where stability lives.

The harness's "build for a need, retire when superseded" discipline is therefore primarily a personal-tier discipline. The graveyard captures personal-tier history that the file system did not preserve.
