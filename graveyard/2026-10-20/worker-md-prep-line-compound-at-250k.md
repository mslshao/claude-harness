# worker.md, the prep line that compounds in the seat (lines 46 to 50)

## What it was

The Worker bullet's prep-line text, lines 46 to 50:

> 300k, 600k and 800k on the new model; compare error rate) The prep line is 250k, five points under
> it: a worker at or past 250k takes the same steps through `Swap-ready` at the end of its RESULT turn,
> or of any turn that leaves it idle, without waiting for a new task, then holds for the user's
> `/clear` (the user's call, 2026-10-20: sessions at 26 to 29 percent sat idle waiting for a task
> instead of compounding). Holding is not stopping: a worker past either

## Why it went

the user approved C3 on 2026-10-20, as a trial today with full production tomorrow if it works: at 250k a seat sends Swap-ready and lets the SessionEnd queue compound it, instead of running a full-context `/compound` itself. rules-ab on Sonnet gave the draft the better of live on the C3 scenario.

## Superseded by

The core's "Your context line" bullet and `memory/harness-history.md` (provenance of the 2026-10-20 call). Lines 39 to 45 and 53 to 60 moved to `skills/fleet/down.md`.

**Source: snapshot** `(local snapshot) fleet/worker.md.txt`
