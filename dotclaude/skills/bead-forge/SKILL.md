---
name: bead-forge
description: Craft high-quality beads from a feature description, converging in 1-2 rounds instead of 4-5. Use when the user asks to "forge beads", "create beads from a feature", "decompose a feature into beads", or "plan work items". Also invoke proactively when conversation context is deep and contains uncaptured decisions, findings, or analysis that would be lost to compaction.
argument-hint: "[feature description, source file, bead/epic reference, or 'checkpoint']"
---

# Bead Forge

Produce beads that are ready to work on (or ready to REMEMBER) without the user
needing to refine them. Front-load the questions the user would ask in revision
rounds 2-4 into internal reasoning.

## Modes

Bead-forge operates in two modes based on context:

### Task Decomposition (default)
Break a feature or port into actionable work items with acceptance criteria,
design notes, and dependency graphs. This is the primary use case.

**Flow:** Phase 1 (full) -> 1.5 (if needed) -> 2 -> 2.5 (if multi-bead) -> 2b (if memory/decision/discovery) -> 3 -> 4 -> 5

### Memory Checkpoint (fast-path)
Preserve critical conversation context before it's lost to compaction. Use this
when the conversation contains decisions, findings, analysis, or rationale that
a cold-start agent would need to continue the work. If you want to review the
artifact before committing to beads, use `/synthesize` checkpoint format instead
- it produces the same structured text without creating beads.

**Flow:** Phase 2 (draft from conversation context) -> 3 (self-check, memory section) -> 4 (present, lightweight) -> 5 (create)

Skip Phase 1 (you already have the context in the conversation - don't explore
the codebase). Skip 1.5 and 2.5 (no scope ambiguity or plan-level challenges
for checkpoints). Phase 2b still runs (memory index maintenance).

Beads aren't just tasks. Each bead carries a **category label** that tells
cold-start agents how to interpret it: task (implement), memory (absorb),
decision (respect), discovery (consult), review (reference). The standard
bead fields adapt meaning based on category.

For the full category catalog with field mappings, title conventions, and
usage guidance, see [bead-categories.md](bead-categories.md).

**When to checkpoint:** When you notice the conversation has accumulated
significant uncaptured context - design decisions made through discussion,
document review findings, analysis conclusions, rejected approaches with
rationale. If a compaction would force the next agent to re-derive these
conclusions, checkpoint now.

**When NOT to checkpoint:** Routine coding sessions where the code itself
captures the decisions. Don't persist what the codebase already records.

## Input

One of:
- A feature description (plain text)
- A source file to port (e.g., Apex .cls, legacy Python)
- A reference to an existing bead/epic to decompose
- "checkpoint" or context indicating memory preservation mode
- A combination of the above

The input may come from the user directly or from an agent that determined this work
needs forge-quality beads (per the forge-vs-create heuristic). When agent-initiated,
treat the gathered context as the feature description and proceed through all phases.

## Process (INTERNAL - do not show intermediate steps)

### Phase 1: Understand Scope
**Skip for memory checkpoints** - the context is already in the conversation.
- Read any source files mentioned
- Search the MX2 codebase for existing patterns that handle similar concerns
- Identify the natural seams - where does one unit of work end and another begin?
- **Codebase collision check:** Search for existing code that handles overlapping concepts
  (other enums for the same domain, other type registries, other exception hierarchies).
  Note where new code must stay intentionally separate from existing code, and document
  WHY in the relevant bead's design notes.

### Phase 1.5: Scope Confirmation

Present a scope summary when Phase 1 found collision points, scope is ambiguous,
or multiple decomposition directions are viable. Also fire for agent-initiated
forges (the human validates scope, not the calling agent).

```
## Scope Check
- Existing patterns: [1 line]
- Collision points: [1 line or "none"]
- Decomposition direction: [1-2 lines]
- Key assumption: [the ONE riskiest premise]
Proceed? (y / adjust)
```

Skip when scope is unambiguous and no collisions were found. Skip for single-bead
plans, memory checkpoints, or when the user explicitly opts out ("just forge it").

### Phase 2: Draft Beads
For each bead, draft ALL of these fields (not just title):
- **title**: Imperative, specific, includes the target module path
- **type**: task | feature | bug | epic
- **priority**: 0-4 (0=critical blocker, 2=standard, 4=backlog)
- **description**: What and WHY. Include the module path. Length varies by category
  (see [bead-categories.md](bead-categories.md) Information Density section).
  When the bead modifies existing behavior (not greenfield), structure the description
  as ADDED / MODIFIED / REMOVED sections to make the delta explicit.
- **acceptance**: Concrete, testable criteria. Must include at least one runnable check
  for task beads; concrete conclusions for memory beads.
- **design**: Key technical decisions. Reference existing code paths. Primary payload
  for discovery and review beads.
- **deps**: Which other beads must complete first, and why.
- **estimate**: Minutes. If 120+, the bead is too big - split it.

### Phase 2.5: Challenge Gate (multi-bead plans only)

Before self-checking individual beads, challenge PLAN-LEVEL assumptions.
Follow the embedded challenge protocol from
[challenge/embed-protocol.md](../challenge/embed-protocol.md).

If fragile assumptions are found: revise affected beads, document invalidated
assumptions as negative decisions. If unverifiable: add "ASSUMPTION (unverified):"
prefix in the bead description.

Skip for single-bead plans or memory checkpoints.

### Phase 2b: Memory Index Maintenance (memory/decision/discovery beads only)

When creating a memory, decision, or discovery bead, update the memory index:

1. Check if a topic file exists for the bead's domain label(s) in the memory
   directory (`~/.claude/projects/-workspaces-main/memory/`).
2. If yes, append a one-line entry with the bead ID and title to the relevant
   section of that topic file.
3. If no topic file exists for this domain, create one with a header and the
   first entry. Then add a row to the Topics table in `MEMORY.md`.

This is best-effort. If the memory directory doesn't exist or the domain is
unclear, skip this step. The system works without it.

Phase 2b writes the **per-domain** index (topic files keyed by domain label).
Phase 5 additionally writes a **temporal** index (`log.md` keyed by date) via
the `log-append.py` helper. Both fire on the same trigger
(memory/decision/discovery/review label) but produce different views; do not
collapse them into one.

### Phase 3: Self-Check Gate

For EACH bead, answer internally. If any answer is "no", revise before presenting.
For the full checklist, see [self-check-gate.md](self-check-gate.md).

The gate has conditional sections: task beads check boundaries, testable acceptance,
and real code references. Memory/decision/discovery beads check reconstructability,
rejected alternatives, and actionable boundaries. All beads check actionability,
size, dependencies, and negative decisions.

### Phase 4: Present

Show beads in this format:

```
## [type] title
Priority: P{n} | Estimate: {m}min
Depends on: {bead titles or "none"}

**Description:** ...

**Acceptance Criteria:**
- [ ] criterion 1
- [ ] criterion 2

**Design Notes:**
...
```

After ALL beads, show the dependency graph. Then **proceed directly to Phase 5**
(create). Do not block on user approval. The forge output is already higher
quality than a raw `bd create`, and waiting adds friction without adding value.

After creating, note: "Created N beads. Adjust with `bd update <id>` if needed."

### Phase 5: Create (MANDATORY - beads must exist after forge)

Create the beads immediately after presenting them. Do not present and move
on - the forge is not complete until `bd show` returns the bead. The user can
adjust scope, split, or close beads after creation via `bd update` / `bd close`.

For each bead, in dependency order (dependencies first):

```bash
# Create the bead
bd create --title="<title>" --type=<type> --priority=<N> \
  --description="<description>" --json

# Add labels (category + domain)
bd label add <id> <category>    # memory, decision, discovery, review (skip for task)
bd label add <id> <domain>      # qualifier, cqc-engine, infra, etc.

# Add dependencies (if any)
bd dep add <id> <depends-on-id>

# Update with acceptance criteria and design notes
bd update <id> --notes="Acceptance:\n- [ ] criterion 1\n- [ ] criterion 2\n\nDesign:\n<design notes>"

# Append to chronological log if memory/decision/discovery/review (best-effort,
# non-blocking; helper exits 0 even on failure).
python3 ~/.claude/skills/bead-forge/log-append.py <id>
```

The `log-append.py` helper is a no-op for task beads (no category label) and
for any bead where `bd show --json` fails. It produces one line per bead in
`~/.claude/projects/-workspaces-main/memory/log.md` of the form
`## [YYYY-MM-DD] <category> | <domain-csv> | bead <id> | <title>`. Bead
creation must never be blocked by log issues.

**Checkpoint summary format** (for agent-initiated checkpoints):

```
Checkpointed: [title] ([id]) - [1-line summary of what was preserved]
```

## Subagent Context Handoff

Subagents (skills like `/pr-intel`, `/challenge`, specialist agents) cannot
invoke `/bead-forge` directly. When a subagent discovers context worth
preserving, it should include a structured handoff block in its response:

```
## Checkpoint Recommendation
Category: [memory|decision|discovery|review]
Domain: [domain label]
Title: [proposed bead title]
Context to preserve:
- [key finding or decision 1]
- [key finding or decision 2]
Rationale: [why this needs a bead - what would be lost to compaction]
```

The main agent, upon receiving a checkpoint recommendation from a subagent,
should invoke `/bead-forge checkpoint` with the recommendation as input.
This is not optional - if a subagent flags context for preservation, act on it.

When building prompts for subagents, include this instruction:
"If your analysis produces findings, decisions, or conclusions that would be
lost to conversation compaction, include a Checkpoint Recommendation block
in your response."

## Mid-Execution Handoff Comments

When you are mid-execution on a multi-front task and context-window pressure
forces you to stop before everything ships, post a `[HANDOFF v<N>]` comment on
the active task bead so a fresh agent (or a future you) can pick up cleanly.
The structure below is the canonical template; a fresh agent reading the most
recent comment should have everything it needs to continue without re-deriving.

```
[HANDOFF v<N>] Mid-execution context for fresh agent. Picking up from
<prior pivot point>. <one-line summary of why checkpointing now>.

================================================================
WORKTREE LOCATIONS (use these, do NOT re-create)
================================================================
- <description>: <absolute path>  (branch <name>)
- ...

================================================================
FRONT <K> (PR #<num>) STATUS
================================================================
<item id>: ADDRESSED v<N> | DEFERRED v<N> | NOT STARTED. <one-paragraph
explanation: what shipped, where, what's left, why deferred if applicable>.

Resume options (when DEFERRED with a real blocker):
  (A) <approach 1> - <tradeoff>
  (B) <approach 2> - <tradeoff>
  Recommendation: <which> because <reason>. Estimated <time>.

================================================================
COMMIT/PUSH MECHANICS (worktree quirks observed in this session)
================================================================
- <any non-obvious git/gt observation that would surprise a fresh agent>

================================================================
REPLY OBLIGATIONS
================================================================
After completing each item, post `bd comment <bead-id> "[ADDRESSED v<N>: <PR# / item>]"`
or `[DEFERRED v<N>: <reason>]`.

================================================================
DO NOT
================================================================
- <each prohibition the user explicitly stated>
```

Use this template the moment you decide to checkpoint. It is faster to fill
out than to recover from a fresh agent re-deriving state. Each section is
optional only if it doesn't apply (e.g. no worktrees -> drop that block).

- For the full self-check gate checklist, see [self-check-gate.md](self-check-gate.md)
- For granularity heuristics and anti-patterns, see [granularity.md](granularity.md)
