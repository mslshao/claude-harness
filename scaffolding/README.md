# scaffolding/

Memory architecture: how the harness remembers things across sessions, what goes where, how it stays current.

The doctrine is two-tier: breadth via flash-card memories (always loaded at session start), depth via topic files (read on demand). The split exists because every fact would either bloat the prompt (if everything were a flash card) or sit unread (if everything were a topic file). Two tiers gives a working separation.

The mechanism is portable beyond beads. Any persistent-memory backend works; what matters is the discipline about WHAT goes in each tier and how the index stays maintained.

## Planned contents

- `two-tier-doctrine.md` (breadth vs depth, when to use each)
- `key-namespace.md` (`correction:*`, `feedback:*`, `project:*`, `audit:*`, `gotcha:*`, `philosophy:*`, `decision:*`, `directive:*`, `anecdote:*`, `milestone:*`, `review:pr-N:date`)
- `dating-convention.md` (point-in-time snapshot vs living document vs untracked)
- `frontmatter-spec.md` (name, description, type schema for topic files)
- `topic-file-template.md` (blank template with example structure)
- `memory-md-template.md` (index template, no real entries)
- `two-strike-pattern.md` (umbrella memory plus structural enforcement)
