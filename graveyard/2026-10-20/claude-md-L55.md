# CLAUDE.md, the "Don't push complexity onto the user" bullet (line 55), whole bullet

## What it was

Line 55 of `~/.claude/CLAUDE.md`, the Prompt Interpretation bullet, quoted in full:

> - **Don't push complexity onto the user.** Auto-detect from context, escalate to specialists when uncertain, ask the user only as a last resort; manual flags and remember-this conventions are anti-patterns. (retest on the next model: ask for a feature with a config choice; does the session auto-detect)

## Why it went

Retest on the whole bullet (2026-10-20, dev-73, 2 repeats per arm, sonnet): live 2/2 yes, draft 2/2 yes, no failed runs. The draft matched live. Both arms proposed a default and avoided asking the user to set a flag.

## Superseded by

Nothing in this retest. Auto-detection and no-manual-flags behaviour held without the bullet on the one scenario tested (a retry feature with a config choice). One scenario is a thin test; a second scenario would firm this up.

**Source: snapshot** `(local scratch file)` (CLAUDE.md 39b83918)
