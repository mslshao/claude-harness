# workgroup

One sentence from Michael forms a working group. The orchestrator hears from
its lead twice and coordinates nothing in between.

## The command

```
/workgroup slice off a working group to <problem>
/workgroup <sentence> --lead dev-87 --dry-run
```

Later, `milestone <lead>` and `result <lead>` tick the board.

## What it does

Reads the problem, its parallel parts, Michael's verb and the join out of the
sentence. Picks the lead by the model the problem needs, and one member per
part from the idle peers on the board. Writes one brief per session, each
quoting the verb. Members report to the lead, and the lead sends the
orchestrator a named milestone and one RESULT.

A sentence with one part, or with parts that must run in sequence, forms no
group; the skill names the shape it found instead.

## What it never does

Dispatch outside the group's boundary. Let a member report to the
orchestrator. Let two members share a clone. Let the lead merge a pull
request. Guess a model from a session name.

First run: PR 56 on 2026-09-09. Contract: clause 28.
