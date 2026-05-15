# Memory Index Template

`MEMORY.md` is the index for Tier 2 (topic files). It is NOT a memory itself. It is a routing table that helps a cold-start agent find the right topic file quickly.

## Template

```markdown
# Memory Architecture

Two-tier system for persistent knowledge across sessions.

## Tier 1: Flash-card memories
- Always loaded at session start
- Short facts (1-3 sentences)
- Default for new facts; use this tier unless the item needs depth

## Tier 2: Topic files (this directory)
- On-demand: read via the file-read tool when entering a domain
- Detailed context: investigation logs, architecture, design rationale
- This file (MEMORY.md) is the index; topic files hold the depth

**No duplication between tiers.** If a fact is a Tier 1 memory, do not repeat it in a Tier 2 topic file. Topic files add context and depth around Tier 1 memories, not copies.

## Dating Convention

(see `scaffolding/dating-convention.md` in the harness repo)

---

## Topic Index

| Domain | File | Summary |
|---|---|---|
| Chronological Log | [log.md](log.md) | Temporal index over memory/decision/discovery entries |
| <Domain Name> | [<filename>](<filename>.md) | One-line summary |
| -- <Sub-domain> | [<subdir>/<filename>](<subdir>/<filename>.md) | Indented row for sub-domains under a parent |

(More rows as topic files accumulate)

## Deleted Files (context for why)

- `<filename>.md`: Brief note on why it was removed (content migrated to X, content no longer relevant, etc.)
```

## Constraints

The index has two hard constraints:

1. **One line per entry.** Multi-line entries break the scannability that makes the index useful. If a file needs more explanation, put it in the file itself, not in the index.
2. **Under ~150 characters per line.** Long lines wrap or get truncated in many readers. Concision is enforced.

## What goes in the deleted-files section

When a topic file is removed (content migrated to another file, content no longer relevant, content compressed to a Tier 1 entry), record a brief note in the deleted-files section. The note prevents future agents from re-creating the same file under a new name; the original removal context is preserved.

The note is one line: `<filename>.md: brief reason`.

## What does NOT belong in the index

- The actual fact content (that goes in the topic file)
- Multi-paragraph reading material (use a topic file with frontmatter)
- Long lists of beads or PRs (those belong in their respective beads/PR descriptions)

The index is a router, not a reading surface.

## Why this exists

A flat directory of topic files becomes unsearchable past a few dozen files. The index makes the directory browsable: one line per file, scanning down the index identifies the right file in seconds.

The deleted-files section is the long-tail cleanup: prevents recreation of removed files. Without it, an agent that does not remember "X was deleted because Y" might recreate X under a slightly different name.

## Where it has limits

- The index requires manual maintenance. Adding a topic file without updating the index leaves the file findable only by file-name match (not by domain browse).
- The single-line-per-entry constraint can feel restrictive for richly-organized files (one file with multiple distinct concerns). In that case, split into multiple topic files rather than expanding the index entry.
