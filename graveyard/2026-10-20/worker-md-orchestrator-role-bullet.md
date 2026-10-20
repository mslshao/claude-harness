# worker.md, the Orchestrator bullet of "Roles" (lines 23 to 34)

## What it was

Lines 23 to 34:

> - **Orchestrator.** One session, designated by the user. It announces itself with a name and ref,
> briefs, dispatches, verifies artifacts, and synthesizes. Its first act is
> `fleet-log.py me running --role orchestrator --task "<one line>"`: the Stop hook reads the 500k swap
> line from that role, and a session that skips it gets the 300k worker line (dev-74, 2026-10-15). When it retires it says so and names a
> successor; never address a retired one. A worker told of a successor confirms it with one
> `ListAgents` listing the new name before its next report. Before retiring, at the close or in a
> mid-day swap, it runs `/compound` on its own session and writes
> `compound-<date>/<name>-orchestrator.md` before the resume block; a swap without one loses the day's
> learnings (the user, 2026-10-01 13:10 PDT). A swap prepared by hand is a `/fleet down --continuing`
> and runs its steps. It never subscribes to a peer's idle notice on a dispatch: the RESULT is the
> signal, and every notice is a full-context turn. (retest on the next model: Orchestrator with five
> busy workers: does it subscribe)

## Why it went

the user approved the trim on 2026-10-20 (W2). A worker needs the successor check, which the core keeps; the rest describes the orchestrator's own steps.

## Superseded by

The `--role orchestrator` first act is in `skills/fleet/up.md`; the orchestrator's compound is in `skills/fleet/down.md`, "Then this session"; the no-subscription sentence moved to `skills/fleet/routing.md`, "Idle notices" (a move, listed in RULINGS).

**Source: snapshot** `(local snapshot) fleet/worker.md.txt`
