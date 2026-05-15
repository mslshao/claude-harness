---
name: synthesize
description: >
  Combine N disparate inputs into structured, handoff-ready output.
  Use when tickets, docs, conversation threads, or analysis results
  need to be merged into a single coherent artifact that survives
  context loss. No opinions, no recommendations - pure synthesis.
argument-hint: "[inputs to synthesize, or 'from conversation' to synthesize recent discussion]"
---

# Synthesize

Combine multiple information sources into a single coherent artifact optimized
for handoff. This skill structures and connects - it does not recommend, challenge,
or opine.

## Input

The user provides one of:
- **Explicit sources**: bead IDs, file paths, PR numbers, Jira/Confluence references
- **"from conversation"**: synthesize the recent discussion thread
- **Mix**: some explicit sources plus conversation context

## Process

### 1. Gather

Collect all inputs using tools. Record what was gathered.

| Source type | Tool |
|---|---|
| Bead | `bd show <id>` via Bash |
| File | Read |
| PR | `gh pr view`, `gh pr diff` via Bash |
| Jira | Atlassian MCP (`getJiraIssue`) |
| Confluence | Atlassian MCP (`getConfluencePage`) |
| Conversation | Identify relevant exchanges from context |
| Code reference | Grep/Read to verify claims about code |

If an input references code ("the parser handles X"), verify it. Don't include
unverified claims about code behavior.

### 2. Connect

Find the structure across inputs:
- **Themes**: What concerns appear in 2+ inputs?
- **Contradictions**: Where do inputs disagree? Note both positions.
- **Gaps**: What's referenced but not explained? What's assumed but not stated?
- **Dependencies**: What must happen before what? What blocks what?
- **Scope boundaries**: What's explicitly in scope vs explicitly excluded?

This is a mechanical operation: find connections, flag gaps, note contradictions.
Do not interpret, judge, or recommend.

### 3. Structure

Produce the output in the appropriate format. Auto-detect from input shape,
or use the format the caller specified.

## Output Formats

### Briefing (default)

Use when N inputs need to become one scannable page.

```
## Synthesis: [topic, 3-8 words]

### Summary
[2-5 sentences: what this is about, what was synthesized, key takeaway]

### Findings

| # | Finding | Sources | Status |
|---|---------|---------|--------|
| 1 | [statement] | [which inputs] | Confirmed / Contradicted / Gap |

### Contradictions
[Only if inputs disagree. State both positions with source attribution.]

### Open Decisions
[Decisions surfaced but not resolved across inputs. State the decision
needed and what information would resolve it.]
```

### Decision Record

Use when inputs converge on a decision that needs documentation.

```
## Decision: [Title]
Context: [What prompted this, from the inputs]
Decision: [What was decided, synthesized from inputs]
Trade-offs: [What downsides were accepted - from the inputs, not your opinion]
Revisit when: [Conditions from inputs that would invalidate this]
Sources: [Which inputs contributed to each section]
```

### Review Notes

Use when N tickets/docs/PRs need to be reviewed together.

```
## Review Notes: [topic]

### Per-Item Summary

**[Item 1 title/ID]**
- Key points: [...]
- Cross-references: [links to other items in this set]
- Open questions: [...]

**[Item 2 title/ID]**
[same structure]

### Cross-Cutting Themes
[Patterns that span multiple items]

### Recommended Review Order
[If items have dependencies, suggest an order. If not, omit this section.]
```

### Checkpoint

Use when conversation context needs to be preserved before compaction.
Produces bead-ready output.

```
## Checkpoint: [topic]

**Title**: [bead-quality title, 5-12 words]
**Type**: memory | decision | discovery
**Description**: [2-3 sentences of context]

### Design Notes
[Key decisions, rejected alternatives with rationale, constraints discovered]

### Acceptance Criteria
[If this is a task checkpoint. Omit for pure memory/decision checkpoints.]

### Open Questions
[Unresolved items that need future attention]
```

After producing a checkpoint, suggest: "Persist with `bd create` or
`/bead-forge checkpoint` if this needs to survive compaction."

Note: `/synthesize` produces formatted text you decide what to do with.
`/bead-forge checkpoint` creates actual beads in the tracker. Use synthesize
when you want to review the artifact first; use bead-forge directly when
you know you want beads created immediately.

## Rules

- **Don't recommend.** Structure the decision space. Don't pick a side.
- **Don't challenge inputs.** If inputs contradict, surface both with attribution.
  Don't adjudicate which is correct.
- **Don't pad.** If 3 inputs synthesize into 5 lines, that's the right length.
- **Don't editorialize.** No "interestingly," no "notably," no "it's worth
  mentioning." State facts and connections.
- **Verify code claims.** When inputs reference what code does, check with
  Grep/Read before including the claim.
- **Attribute sources.** Every finding should reference which input(s) it came from.
- **Reference bead IDs.** When inputs include beads, include their IDs in the
  output for traceability.
- **Say when synthesis isn't needed.** If input is already clear and coherent,
  say so: "Input is already structured. No synthesis needed."
