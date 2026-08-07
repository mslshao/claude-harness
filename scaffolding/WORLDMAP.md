---
component: scaffolding
type: directory-map
status: V0 complete (all 7 scaffolding docs have entries)
authored_by: Claude Opus 5
---

# WORLDMAP: Scaffolding

AI-authored commentary on each memory-architecture doc in `scaffolding/`. The scaffolding directory captures the doctrine for how the harness remembers things across sessions: what goes where, what each tier is shaped for, how the index stays maintained.

Entries are pointer-shaped. Each doc is itself the explanation; this WORLDMAP names when the doc applies and which other docs it composes with. Read the doc for the schema or template.

The seven docs answer one question at different scales. Two-tier doctrine is the architecture; key-namespace and dating-convention are the conventions inside tier 1 and tier 2; frontmatter-spec and the two templates are the per-file machinery; two-strike-pattern is the lifecycle rule that promotes a memory entry from one-off to durable artifact when it earns it.

---

```yaml
---
component: two-tier-doctrine
type: scaffolding-doc
status: active
ref: two-tier-doctrine.md
fires_when: "deciding where a new fact, decision, or learning should be stored"
prevents:
  - "every fact becoming a flash card (prompt bloat)"
  - "every fact becoming a topic file (sits unread)"
  - "duplication between tiers when an entry exists in both"
related: [key-namespace, frontmatter-spec, two-strike-pattern]
---
```

When this fires: every time something durable needs to be stored. Tier 1 (flash-card memories via `bd remember`) is breadth: always loaded at session start, short facts, 1-3 sentences. Tier 2 (topic files in `memory/`) is depth: read on demand, longer context, design rationale, investigation logs.

The no-duplication rule is load-bearing: if a fact is a Tier 1 memory, it should not appear in a Tier 2 file. Topic files add context around tier 1 entries; they do not repeat them. The doc's split test is "would a cold-start agent answer this question by reading just the bead memory, or do they need the topic file?"

---

```yaml
---
component: key-namespace
type: scaffolding-doc
status: active
ref: key-namespace.md
fires_when: "creating a Tier 1 memory entry (running `bd remember --key=...`)"
prevents:
  - "memory entries with ad-hoc keys that no one can search later"
  - "domain drift when the same concept is stored under different key shapes across entries"
related: [two-tier-doctrine, reflection-trigger]
---
```

When this fires: every `bd remember` call. The doc names the typed prefixes: `correction:<domain>:<specific>`, `feedback:<topic>`, `project:<name>:<event>:<date>`, `audit:<thing>:<date>`, `gotcha:<system>:<issue>`, `philosophy:<topic>`, `decision:<topic>:<date>`, `directive:<topic>:<date>`, `anecdote:<who>:<thing>:<date>`, `milestone:<event>`, `review:pr-<N>:<date>`.

The convention exists because beads memories are searched, not browsed. Searching `bd memories correction:style:em-dash` returns the recurrence ledger because every em-dash slip used the same key prefix. A search-naming discipline at write time produces a self-organizing memory store at read time.

---

```yaml
---
component: dating-convention
type: scaffolding-doc
status: active
ref: dating-convention.md
fires_when: "creating or updating a Tier 2 topic file"
prevents:
  - "ambiguity about whether a topic file is a point-in-time snapshot or a living doc"
  - "stale 'last updated' fields on snapshot files that were never meant to be updated"
related: [topic-file-template, frontmatter-spec]
---
```

When this fires: every topic file creation or substantive edit. Three patterns: point-in-time snapshots use dated filenames (`<topic>-YYYY-MM-DD.md`, no updates); living docs use a `last_modified:` frontmatter field that updates forward; harness files under `~/.claude/` use git log and milestone memories as the source of truth instead of in-file dates.

The pattern matters because a reader needs to know whether they are looking at a snapshot of the past or the current state. The choice is made at file-creation time and is structural; bulk-backfilling is explicitly forbidden by the doc.

---

```yaml
---
component: frontmatter-spec
type: scaffolding-doc
status: active
ref: frontmatter-spec.md
fires_when: "creating or modifying a Tier 2 topic file"
prevents:
  - "topic files without `name:` / `description:` / `metadata.type:` that the auto-memory system cannot index"
  - "drift between the file's frontmatter and the index entry in MEMORY.md"
related: [topic-file-template, memory-md-template, dating-convention]
---
```

When this fires: at the top of every topic file. The schema is: `name:` (kebab-case slug matching the filename), `description:` (one-line summary used for relevance scoring in future conversations), `metadata.type:` (user, feedback, project, reference). Body uses `[[name]]` syntax to link related memories.

The doc treats frontmatter as load-bearing index data, not decoration. The description field specifically is what the auto-memory system reads when scoring "is this memory relevant to the current task"; a vague description means a relevant memory does not get loaded.

---

```yaml
---
component: topic-file-template
type: scaffolding-doc
status: active
ref: topic-file-template.md
fires_when: "creating a new Tier 2 topic file"
prevents:
  - "topic files missing the prescribed body structure (feedback/project entries without Why and How to apply)"
  - "ad-hoc file shapes that diverge from the indexable convention"
related: [frontmatter-spec, dating-convention]
---
```

When this fires: file creation. Copy the template, paste, fill in. The template enforces the body structure for feedback and project memories specifically: lead with the rule or fact, then a `**Why:**` line (the reason, often a past incident), then a `**How to apply:**` line (when and where this kicks in).

The `**Why:**` discipline is what lets future-me judge edge cases instead of blindly following the rule. A memory entry without the why becomes harder to apply correctly over time as context fades.

---

```yaml
---
component: memory-md-template
type: scaffolding-doc
status: active
ref: memory-md-template.md
fires_when: "creating MEMORY.md for a new project or auditing an existing one"
prevents:
  - "MEMORY.md ballooning past 200 lines (auto-truncated by the auto-memory system)"
  - "MEMORY.md entries with full memory content embedded (vs one-line pointers)"
related: [two-tier-doctrine, frontmatter-spec]
---
```

When this fires: at MEMORY.md creation, and during periodic audits of the index. The doc enforces "index, not memory" discipline: MEMORY.md is a routing table that helps a cold-start agent find the right topic file. Each entry is one line, under ~150 characters: `- [Title](file.md): one-line hook`.

The 200-line ceiling is a structural constraint of the auto-memory system: lines past 200 are truncated. The doc's discipline ensures the index stays short enough to survive truncation.

---

```yaml
---
component: two-strike-pattern
type: scaffolding-doc
status: active
ref: two-strike-pattern.md
fires_when: "a correction recurs on the same topic"
prevents:
  - "umbrella memories bloating with date-stamped tally entries without enforcement"
  - "performance theater (the model logging recurrences without changing the default behavior)"
related: [reflection-trigger, key-namespace, decision-making-rules]
---
```

When this fires: a correction lands on a topic that has a prior correction within ~30 days. The pattern triggers /reflect to check whether the rule needs a structural enforcement layer (hook, linter, formatter) added; if both umbrella memory and structural enforcement are already in place, stop tallying.

The convergence rule is the load-bearing part: dated tally entries are not corrective. After umbrella-plus-enforcement, the next move is mechanical (a different enforcement layer), not procedural (more memories). The pattern names this explicitly to prevent the trap where the model logs the same correction five times and calls that a system.
