# graveyard/

Perma-deleted components and why they were retired.

## The Keymaker principle

> Components in this harness exist for a specific purpose. When the purpose is superseded (by a more specific child or a more generic parent), the component is deleted, not archived. The harness carries no legacy maintenance burden.

The name comes from the Matrix Reloaded character whose role was so narrow that, once his purpose was fulfilled, he was scheduled for deletion. The discipline cuts the same way: build for a need, retire when the need is met by something else, do not keep the artifact around "just in case."

## Reconstruction caveat

Personal-tier `~/.claude/` is not git-versioned by default, so perma-deleted personal-tier files are unrecoverable in a strict sense. This directory captures what we can reconstruct from memory and from project-tier git history. Entries that are reconstructed from recall are marked as such; entries with documented history (project-tier removals) are marked separately.

## Planned contents

- `agentcore.md` (early generic agent, purpose absorbed by dispatch heuristic and the tech-lead agent)
- `medical-legal-specialist.md` (early domain agent, split into a generic security auditor and per-domain context)
- More entries as memory and git scans surface them
