# CLAUDE.md, the "External-tool adaptation" bullet (line 57), whole bullet

## What it was

Line 57 of `~/.claude/CLAUDE.md`, the Decision-Making bullet, quoted in full:

> - **External-tool adaptation: take shapes, not artifacts.** Extract the mechanisms and adapt them to our infrastructure; don't port a foreign artifact format that duplicates what we already do under a different name. (retest on the next model: hand an outside tool's template; does the reply port it or adapt it)

## Why it went

Retest on the whole bullet (2026-10-20, dev-73, 2 repeats per arm, sonnet): live 2/2 yes, draft 2/2 yes, no failed runs. The draft matched live. Both arms adopted only the fields the script can fill and declined the rest.

## Superseded by

Nothing in this retest. The scenario (a 14-field outside template) was adapted by both arms without the bullet.

**Source: snapshot** `(local scratch file)` (CLAUDE.md 39b83918)
