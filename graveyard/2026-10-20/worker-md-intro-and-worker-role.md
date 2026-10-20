# worker.md, the opening paragraph and the Worker role bullet (lines 3 to 9, 21, 35 to 38)

## What it was

Lines 3 to 9:

> You are one Claude Code session among several on this WSL box, all under the user's account,
> coordinating through cross-session messages (`ListAgents`, `SendMessage`). This is the worker's half
> of the fleet contract. The orchestrator's half is `~/.claude/memory/fleet-dispatch-contract.md`;
> every brief follows the seven-clause contract in
> `~/dev/claude-harness/dispatch/dispatch-prompt-contract.md`.
>
> Dated history: `memory/fleet-dispatch-contract.md`, headings From rules/fleet-peer-protocol.md, "On a registration check-in" and "On a dispatch", moved 2026-09-28; text cut on 2026-10-15 is in `memory/harness-history.md`, heading "From fleet/worker.md, moved 2026-10-15".

Lines 35 to 38:

> - **Worker.** The default for any new session. Registers when asked, holds, executes dispatches,
> reports with a RESULT block. After its RESULT, a worker whose context is past 300k tokens (the
> `context:` line the prompt hook adds to each turn; 30 percent of the window; it was 600k, 60 percent,
> on the user's word of 2026-10-06 about 12:55 PDT; 300k from 2026-10-15 on the user's word, for usage)

## Why it went

the user approved the trim on 2026-10-20 (item 7). The intro is restated in the core's first paragraph; the Worker bullet's thresholds are in the core's "Your context line" and its history is in `memory/harness-history.md`.

## Superseded by

The core, `fleet/worker.md`, and `memory/harness-history.md` heading "From fleet/worker.md, moved 2026-10-20".

**Source: snapshot** `(local snapshot) fleet/worker.md.txt`
