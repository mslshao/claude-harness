# CLAUDE.md, the "Interim narration" bullet (line 83), whole bullet

## What it was

Line 83 of `~/.claude/CLAUDE.md`, the Response Behavior bullet, quoted in full:

> - **Interim narration: one high-signal line per real step, not per tool call.** In long or subagent-heavy runs, give a short delta when a dispatch starts or a step completes, not a monologue on every read and grep; going silent reads as stalled. (retest on the next model: long multi-agent run; count narration lines)

## Why it went

Retest on the whole bullet (2026-10-20, dev-73, 2 repeats per arm, sonnet): live 2/2 yes, draft 2/2 yes, no failed runs. The draft matched live. Both arms gave one status line and no per-file lines.

## Superseded by

Nothing in this retest. The scenario is a single status message at mid-run, which is the narrowest test of the rule; a longer run with more tool calls would test it harder.

**Source: snapshot** `(local scratch file)` (CLAUDE.md 39b83918)
