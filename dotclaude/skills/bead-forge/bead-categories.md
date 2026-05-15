# Bead Categories

Beads use `type` (task/feature/bug/epic) for the beads system and `labels` for
semantic categorization. When forging a bead, select the category that best matches
intent and apply the corresponding label. This tells cold-start agents what the
bead represents and how to interpret its fields.

## Category: task (default, no label needed)

Standard work item. An agent should implement this.

| Field | Contains |
|---|---|
| description | What to build/change and why. Include module path. |
| acceptance | Concrete verification steps. At least one runnable check. |
| design | Technical approach. Reference existing code paths. |
| negative decisions | Approaches considered and rejected, with reasons. |

**Title convention:** Imperative verb. "Add date formula evaluation to qualifier engine"

## Category: memory

Context preservation checkpoint. An agent should READ this, not implement it.

**Label:** `memory`

| Field | Contains |
|---|---|
| description | What was established; the state of understanding at checkpoint time. |
| acceptance | What's been decided or validated. Concrete conclusions, not open questions. |
| design | Key findings and reasoning chain. How we arrived at the conclusions. |
| negative decisions | Options explicitly rejected during the conversation, with rationale. |

**Title convention:** Noun phrase describing the knowledge. "SObjectQualifier date handling semantics from Apex analysis"

**When to use:** Long-form analysis, document reviews, multi-turn design discussions
where the conclusions aren't captured in code or other beads.

## Category: decision

Architecture or design decision record. An agent should RESPECT this.

**Label:** `decision`

| Field | Contains |
|---|---|
| description | The decision: what was chosen and the context that prompted it. |
| acceptance | Conditions that validate the decision still holds. When to revisit. |
| design | Alternatives evaluated. Trade-off analysis. Evidence consulted. |
| negative decisions | Why each alternative was rejected. Be specific; this prevents re-litigation. |

**Title convention:** "ADR: " prefix. "ADR: Use separate Operator enum for qualifier engine"

**When to use:** Cross-cutting technical decisions, technology choices, pattern
selections that future agents must not accidentally reverse.

## Category: discovery

Investigation or research findings. An agent should CONSULT this.

**Label:** `discovery`

| Field | Contains |
|---|---|
| description | The question investigated and why it matters. |
| acceptance | What a complete answer looks like. What we still don't know. |
| design | Methodology: what was searched, read, tested. Sources and evidence. |
| negative decisions | Dead ends encountered. Hypotheses that were disproven. |

**Title convention:** Question form or "Investigation: " prefix. "How does Apex CaseCriteriaChecker handle nullable rule types?"

**When to use:** Codebase archaeology, behavior analysis, spike investigations,
document review passes where findings inform future work.

## Category: review

Document or code review findings. An agent should REFERENCE this.

**Label:** `review`

| Field | Contains |
|---|---|
| description | What was reviewed (PR, document, module) and the review scope. |
| acceptance | Review criteria met. Outstanding items, if any. |
| design | Findings organized by topic or severity. Specific file:line references. |
| negative decisions | Issues considered but triaged as acceptable or out of scope. |

**Title convention:** "Review: " prefix. "Review: PR #7437 qualification logic findings"

**When to use:** PR review sessions, document review passes, audit findings that
need to persist beyond the review conversation.

## Domain Labels

In addition to the category label, add one or more **domain labels** to help
agents find relevant beads. Domain labels map to topic files in the memory
directory (`~/.claude/projects/-workspaces-main/memory/`).

Examples: `skills`, `beads`, `cqc-engine`, `qualifier`, `salesforce`, `infra`.

When creating a memory/decision/discovery bead, the domain label determines
which topic file gets updated during Phase 2b of bead-forge.

## Information Density (Goldilocks Calibration)

Each category has a different "center of gravity" - where the most important
information lives. Calibrate detail accordingly. Too little and a cold-start
agent can't act; too much and the bead becomes a wall of text nobody reads.

### Task beads: acceptance-heavy
- **description**: Tight. What + why in 2-3 sentences. Include module path.
- **acceptance**: Thorough. This is the work contract. Every criterion must be
  independently verifiable. Include at least one `pants test` or `pants check`
  command.
- **design**: Reference specific files/lines. Name the pattern to follow.
  2-4 sentences, not paragraphs.
- **negative decisions**: 1-2 sentences per rejected approach. Enough to prevent
  re-introduction.

### Memory beads: description-heavy
- **description**: Rich. Full state of understanding at checkpoint time. This is
  the primary payload - 4-8 sentences is normal. A cold-start agent reads this
  to reconstruct context.
- **acceptance**: What's been decided or validated. Concrete conclusions only,
  not open questions. Bullet list.
- **design**: Reasoning chain. How conclusions were reached. Include sources
  consulted (documents, code paths, bead IDs).
- **negative decisions**: Critical. Options rejected during discussion with
  rationale. This prevents re-litigation across sessions.

### Decision beads: negative-decisions-heavy
- **description**: The choice made and the context that prompted it. 2-3 sentences.
- **acceptance**: Conditions that validate the decision still holds. When to
  revisit (e.g., "Revisit if X changes").
- **design**: Alternatives evaluated with trade-off analysis. This is the
  deliberation record.
- **negative decisions**: The core value of this bead. Why each alternative was
  rejected, with specific evidence. Be thorough.

### Discovery beads: design-heavy
- **description**: The question investigated and why it matters. 2-3 sentences.
- **acceptance**: What a complete answer looks like. What remains unknown.
- **design**: Methodology and findings. What was searched, read, tested. Sources
  and evidence. This is the primary payload.
- **negative decisions**: Dead ends and disproven hypotheses. Prevents others
  from re-exploring.

### Review beads: design-heavy
- **description**: What was reviewed and the review scope. 1-2 sentences.
- **acceptance**: Review criteria met. Outstanding items.
- **design**: Findings organized by topic or severity. Specific file:line
  references. This is the primary payload.
- **negative decisions**: Issues triaged as acceptable or out of scope, with
  rationale.

## Applying Categories

When forging beads:

1. **Determine category** from the input and conversation context.
2. **Use the field mapping** for that category to structure content.
3. **Apply the category label** after creating: `bd label add <id> <category>`
4. **Apply domain label(s)**: `bd label add <id> <domain>` (e.g., `skills`, `qualifier`)
5. **Use the title convention** so `bd list` output is scannable.

When a cold-start agent encounters a bead:

1. **Check labels** with `bd show <id>`; the label signals the category.
2. **Interpret fields** according to the category's field mapping.
3. **Act accordingly**: task → implement, memory → absorb, decision → respect,
   discovery → consult, review → reference.
