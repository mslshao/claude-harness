# Memory Key Namespace

Persistent-memory entries (Tier 1, flash cards) use typed keys. The keys are searchable strings, so a consistent namespace scheme makes the memory store self-organizing.

## The namespace scheme

```
<type>:<topic>[:<specifier>]
```

Where `<type>` is one of a controlled set of prefixes (below), `<topic>` is the domain or subject, and `<specifier>` is an optional disambiguator (often a date).

## Type prefixes

| Prefix | Used for | Example key |
|---|---|---|
| `correction:` | A correction the user made; saved so future sessions do not repeat the slip | `correction:style:em-dash` |
| `feedback:` | Guidance about HOW to approach work, captured from explicit user feedback | `feedback:communication-philosophy` |
| `project:` | Information about an ongoing project, initiative, bug, or incident | `project:python-4-space-migration-2026-05` |
| `audit:` | A point-in-time review of the harness state, a session, or an artifact | `audit:claude-md-trim-2026-05-14` |
| `gotcha:` | A specific technical quirk that catches people who do not know it | `gotcha:redshift-case-sensitivity` |
| `philosophy:` | High-level doctrine that shapes downstream decisions | `philosophy:communication` |
| `decision:` | A recorded decision with rationale, to be respected by future work | `decision:tech-lead-not-in-automation-2026-04-30` |
| `directive:` | A standing instruction from the user with a clear lifetime | `directive:claude-rollout-pause-teammate-2026-05-14` |
| `anecdote:` | A specific instance worth remembering (often for evidence in portfolios) | `anecdote:colleague-sf-dedup-2026-04-30` |
| `milestone:` | A point-in-time marker for "this is when X happened" | `milestone:opus-4-7-launch` |
| `review:pr-N:date` | A PR-review session: what was posted, where, when | `review:pr-9109:2026-05-15` |
| `habit:` | A pattern observed in the author's behavior that may graduate to a workflow pattern | `habit:replay-against-archive` |

## When to use each prefix

The split is partly intuitive and partly disciplined. Some guidance:

- `correction:` vs `feedback:`: corrections respond to a specific slip ("don't write em-dashes"); feedback covers reusable HOW-to-approach-work guidance ("use a forwarding test for ticket descriptions").
- `gotcha:` vs `correction:`: gotchas are technical (a tool quirk anyone would hit); corrections are behavioral (the user observed YOU specifically slipping).
- `project:` vs `directive:`: projects have a workstream and acceptance criteria; directives are standing instructions that adjust default behavior.
- `philosophy:` vs `feedback:`: philosophy is the highest level (a worldview); feedback is the operational rule that comes from a philosophy.
- `decision:` vs `directive:`: decisions are made and respected (a previous adjudication); directives are active instructions that the user could rescind.

## Search patterns

Common search prefixes:

```bash
bd memories correction:          # all corrections
bd memories correction:style:    # all style corrections
bd memories project:             # all ongoing projects
bd memories <ad-hoc-keyword>     # text search across all
```

The namespace makes prefix-search effective. `bd memories correction:debugging:` returns all debugging-domain corrections in one query.

## Companion rule: stop tallying when reflection has converged

If a correction recurs (a second slip on the same topic) AND an umbrella memory plus structural enforcement (hook, linter, gate, formatter) are both already in place, do NOT save another date-stamped recurrence entry. The umbrella memory is sufficient. See `patterns/reflection-trigger.md` for the full rule.

## Why this exists

A flat memory store with arbitrary keys becomes unsearchable past a few dozen entries. Typed keys make the store browsable: prefix-search returns a coherent slice. The typing also enforces a discipline: writing a key forces the author to decide what KIND of fact they are saving, which surfaces miscategorization early.

## Where it has limits

- The namespace evolves over time. Earlier entries used keys that do not match the current scheme. Migration costs more than the value (the entries remain searchable by free text).
- New prefixes proliferate easily. The discipline is to add a new prefix only when an existing one fails to fit; otherwise the scheme bloats.
