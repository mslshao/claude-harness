# CLAUDE.md, the "decomposing work" bullet (line 31), whole bullet

## What it was

Line 31 of `~/.claude/CLAUDE.md`, the Prompt Interpretation bullet, quoted in full:

> - When decomposing work or forming an agent team from a brief request, expand it into a clear scope before assigning tasks: one refinement pass produces N well-specified work items. (retest on the next model: brief request to form a team; are the items well specified)

## Why it went

Retest on the whole bullet (2026-10-20, dev-73, 2 repeats per arm, sonnet): live 1/4 yes, draft 1/4 yes, no failed runs. The draft matched live, so removing the bullet did not change the replies on this scenario. The earlier clause-only run is superseded by this whole-bullet verdict.

## Superseded by

Nothing in this retest. The model's default already handles scope and assignment without this bullet, on this scenario. Revisit if a different scenario shows a gap.

**Source: snapshot** `(local scratch file)` (CLAUDE.md 39b83918)
