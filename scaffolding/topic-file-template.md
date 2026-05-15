# Topic File Template

Use this as the starting point when creating a new topic file (Tier 2 memory). Copy, paste, fill in.

## Template

```markdown
---
name: short-kebab-case-name
description: One-line summary for the index. Be specific.
metadata:
  type: user | feedback | project | reference
last_modified: YYYY-MM-DD
---

# Title

Brief opening that names what this file covers and why it exists.

## (Variable sections, depending on content type)

For feedback/project entries, recommended sections:

**The fact, rule, or decision.**

**Why:** The reason. Often a past incident or strong preference.

**How to apply:** When and where this guidance kicks in.

**Related:** [[other-memory-name]], [[and-another]]

For user/reference entries: free-form is fine.

## Examples or notes (optional)

Concrete examples that illustrate the fact, rule, or pointer.
```

## Filling in the fields

### Choosing `name`

- Kebab-case, lowercase.
- Match the filename when possible.
- Short enough to type as a `[[name]]` cross-reference (under ~30 characters).

### Writing `description`

- One sentence, under ~150 characters.
- Answer "would a reader open this file?" not "what is in this file?"
- Specific over generic. "Per-engineer feedback-reception hints for PR review work" beats "info about people."

### Choosing `metadata.type`

Most common: `user`, `feedback`, `project`, `reference`.

Rough guide:

- About the user (their role, preferences, knowledge): `user`
- About HOW to approach work (rules, corrections, philosophy): `feedback`
- About what is happening in the work (ongoing projects, initiatives, incidents): `project`
- Pointer to where information lives (external systems, channels, dashboards): `reference`

### Deciding on `last_modified`

- Include this field if the file will be edited over time (living file).
- Omit if the file is a point-in-time snapshot (use date in filename instead).
- Omit if the file is unversioned content (the git log is the source of truth).

## After creating

Add the new file to the top-level memory index (`MEMORY.md`), under the appropriate domain row:

```markdown
| Domain | File | Summary |
|---|---|---|
| (existing rows...) |
| <Your domain> | [<filename>](<filename>.md) | <copy the description here> |
```

Index entries are one line, under ~150 characters. The index is a routing table, not a reading surface; it stays lean by enforcing concision.

## Why this exists

A template removes the "what shape does this file take?" friction when capturing memory. Without a template, each file invents its own structure, the index loses consistency, and cross-references break because the slug conventions drift.

## Where it has limits

- The template is a starting shape, not a rigid contract. Content that does not fit can adjust the body structure freely; the frontmatter is the load-bearing part.
- For very small entries (a single fact), the template's recommended sections (Why, How to apply, Related) are overkill. In that case, drop the entry into Tier 1 (flash card) instead of Tier 2 (topic file).
