# Frontmatter Specification

Topic files (Tier 2 memory) use YAML frontmatter for the indexable metadata. The body of the file is free-form markdown.

## Required fields

```yaml
---
name: short-kebab-case-slug
description: One-line summary used to decide relevance in future conversations. Be specific.
metadata:
  type: user | feedback | project | reference
---
```

### `name`

A short kebab-case slug that uniquely identifies the topic file. Often matches the filename (`name: org-context` for `org-context.md`).

Used for cross-references: link related memories with `[[name]]` syntax in the body. A `[[name]]` that does not match an existing memory is fine; it marks something worth writing later, not an error.

### `description`

A one-line summary that helps decide whether to open the file. The description appears in index listings (the top-level `MEMORY.md` table) and in the at-a-glance preview. Specificity matters: "info about X" is useless; "X's reporting structure, key context, and current open decisions" is useful.

### `metadata.type`

One of a small controlled vocabulary:

- `user`: facts about the user's role, goals, responsibilities, knowledge
- `feedback`: guidance about HOW to approach work (corrections and confirmations)
- `project`: ongoing work state, initiatives, bugs, incidents
- `reference`: pointers to external systems where information lives

Used by tooling that filters memory by type. The boundary between types follows the `correction:*` vs `feedback:*` vs `project:*` distinction from the key namespace doc.

## Optional fields

### `last_modified`

For living topic files (see `dating-convention.md`). Format: `YYYY-MM-DD`. Updated on each substantive edit.

```yaml
last_modified: 2026-05-14
```

### `bead_ref` or `ticket_ref`

For files that anchor to a specific work item in a task tracker. Convention varies by tracker:

```yaml
bead_ref: docr-NNNN
```

### `superseded_by`

For files that should not be relied on going forward (the content is preserved but the reader should redirect to a newer file):

```yaml
superseded_by: <name-of-replacement>
```

## Body structure

For `feedback` and `project` types, the body has a recommended structure:

```markdown
**The fact, rule, or decision.**

**Why:** The reason. Often a past incident or strong preference.

**How to apply:** When and where this guidance kicks in.

**Related:** [[other-memory-name]], [[and-another]]
```

For `user` and `reference` types, free-form is fine. The structure exists where it adds value (feedback and project entries benefit from the why+how+related shape; user/reference entries usually do not).

## Why this exists

A topic file without metadata is opaque: the reader cannot tell at a glance whether it is current, whether it has been superseded, what type of content it holds. Frontmatter adds the metadata in a machine-readable format that tooling can index and humans can read.

The `[[name]]` cross-reference convention turns topic files into a graph. A reader can follow links from one memory to a related one without going through the index. The graph emerges from the content itself.

## Where it has limits

- Discipline is required: frontmatter that drifts out of date (description no longer matches body, `last_modified` not updated on edits) erodes the value. The convention is "audit on touch", not "audit on schedule"; some drift accumulates between touches.
- The controlled vocabulary for `metadata.type` does not cover every case cleanly. Some content sits ambiguously between types. Acceptable: pick the closest type and move on; the body of the file carries the precise content.
