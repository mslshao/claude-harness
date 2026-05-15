# Dating Convention

Topic files (Tier 2 memory) follow one of three patterns for dating. Each pattern fits a different content type.

## Pattern 1: Point-in-time snapshots

**Filename includes the date:** `<topic>-YYYY-MM-DD.md`

**Properties:**

- Never updated after creation. A later snapshot is a new file.
- Used for content that captures state at a specific moment.
- Multiple files can coexist (`review-activity-snapshot-2026-04-16.md`, `review-activity-snapshot-2026-07-22.md` would be different snapshots).

**Examples of when to use:**

- 1:1 meeting notes (`1on1-2026-04-28-team-lead.md`)
- Review activity captures (review counts, PR stats over a window)
- Pre-milestone state snapshots (system-prompt snapshots before a major Claude Code version)
- Investigation logs for resolved incidents

## Pattern 2: Living topic files

**Filename excludes the date:** `<topic>.md`

**Frontmatter includes `last_modified: YYYY-MM-DD` on each substantive edit:**

```markdown
---
name: org-context
description: People, reporting lines, ownership snapshot
last_modified: 2026-03-20
---
```

**Properties:**

- Single file evolves over time.
- The `last_modified` date is updated on each substantive edit, NOT on cosmetic changes.
- Do NOT bulk-backfill `last_modified` to existing files; apply forward the first time each file is edited under the new convention.

**Examples of when to use:**

- Org context (people, reporting lines, ownership)
- Active project state (current phase, open decisions, blockers)
- Architectural doctrine that evolves with the codebase
- Per-engineer feedback-reception hints (people-hints.md, updated when each person's feedback patterns shift)

## Pattern 3: Untracked (no in-file date)

**No date in filename, no `last_modified` in frontmatter.**

**Properties:**

- Version control history is the source of truth for when the file was edited.
- Used for files where in-file dating would add maintenance overhead without value.

**Examples of when to use:**

- Skill files (`.claude/skills/<skill>/SKILL.md`)
- Agent definitions (`.claude/agents/<agent>.md`)
- CLAUDE.md files (project and personal)
- Hooks (`.sh` and `.py` scripts)

For these, the `git log` output and milestone memory entries (`milestone:*`) together answer "when was this last touched? was it before or after major event X?"

## Why this exists

The three patterns reflect three different content lifetimes:

- **Snapshots** capture a moment that will not be revisited. The date IS the content (a snapshot dated 2026-04-16 is meaningless without the date).
- **Living files** evolve continuously but the reader needs to know recency at a glance. The frontmatter date answers "is this still current?" without opening the file.
- **Untracked** files are themselves versioned (in git). Re-stating the version in the file body or frontmatter is redundant and rot-prone.

## Naming consistency

Within each pattern, naming is consistent:

- Snapshots: `<topic>-YYYY-MM-DD.md` (review-activity-snapshot, 1on1-meeting-notes)
- Living: short noun phrases describing the topic (org-context, atlassian-mcp, infrastructure-tech-debt)
- Untracked: standard filenames per the artifact convention (SKILL.md, agent-name.md, README.md)

## Where it has limits

- The split between "snapshot" and "living" requires judgment at file creation. A file written as a snapshot can become a living file if the author keeps updating it; the date in the filename then becomes misleading. The fix: when a snapshot starts getting updates, rename it to drop the date.
- The `last_modified` discipline is easy to forget on cosmetic edits. The convention is "substantive edits only" but the boundary is fuzzy. Acceptable: occasional staleness in `last_modified` does less damage than systematic backfilling.
