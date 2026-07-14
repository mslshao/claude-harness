---
name: reflect
description: "Invoked when a user correction matches a prior correction in beads memory (two-strike pattern). Reads the target artifact, checks for existing coverage, proposes a single targeted edit. Do NOT invoke directly - the behavioral trigger in CLAUDE.md handles invocation."
argument-hint: "[correction context + matched prior memory]"
---

# Reflect

Propose a single, targeted improvement to a rule, skill, or agent definition based
on a recurring user correction. This skill is invoked by the Reflection Trigger in
CLAUDE.md when a correction matches a prior correction in beads memory.

## Input

The invoking context provides:
- The current correction (what the user said, what went wrong)
- The matched prior memory (key and value from `bd memories`)

## Process

### 1. Route

Use the domain from the memory key to identify the target file:

| Domain | Target |
|--------|--------|
| `testing` | `.claude/rules/testing.md` |
| `style` (Python/code style) | `.claude/rules/code-style.md` |
| `style` (prose/register: em-dash, catastrophizing, http-verb-caution, mirrored informality, output length) | `~/.claude/CLAUDE.md` Writing Style |
| `architecture` | `.claude/rules/architecture.md` |
| `security` | `.claude/rules/security.md` |
| `debugging` | `.claude/rules/debugging.md` |
| `verification` | `~/.claude/CLAUDE.md` Decision-Making (verification rules live there; `.claude/rules/verification.md` only for project-wide gate changes) |
| `workflow` | `~/.claude/CLAUDE.md` |
| `communication` | `~/.claude/CLAUDE.md` (Writing Style or Response Behavior, nearest section) |
| `identity` | `~/.claude/CLAUDE.md` Writing Style |
| `scope` | `~/.claude/CLAUDE.md` Prompt Interpretation |
| `skill:<name>` | `~/.claude/skills/<name>/SKILL.md` |
| `agent:<name>` | `~/.claude/agents/<name>.md` |
| (domain not in table) | `~/.claude/CLAUDE.md`, matching the nearest existing section |

The style split matters: prose-register corrections (the most common kind)
must NOT land in the Python style file. Decide by what the correction is
about, not by the literal domain tag.

### 2. Read

Read the target file entirely. Understand the existing structure and conventions.

### 3. Collision Check

Search the file for existing coverage of the correction topic. Use Grep to find
keywords related to the correction. Record the result:
- "Existing coverage at line N: [quote]"
- "No existing coverage found"

### 4. Draft

- If existing coverage found: propose a **refinement** of the existing rule. Sharpen
  it, add a case it missed, or clarify ambiguity. Do not duplicate.
- If no existing coverage: propose an **addition**. Match the style and structure of
  the surrounding content.
- One change only. If the correction suggests multiple updates, propose the
  highest-impact one.

### 5. Present

```
## Proposed Rule Update

**Trigger**: You corrected [topic] (2nd occurrence, prior: [date from memory])
**Target**: `[file path]` line [N]
**Collision check**: [existing coverage quote or "no existing coverage found"]

### Diff
```diff
[unified diff showing the proposed change in context]
```

**Apply? (y/n/edit)**
```

### 6. Apply

**Landing path by tier (decide BEFORE applying).** Personal-tier targets
(`~/.claude/CLAUDE.md`, `~/.claude/skills/`, `~/.claude/agents/`, memory files) apply
directly with Edit and ship immediately. Project-tier targets (`.claude/rules/`, the
project `CLAUDE.md`, project `.claude/skills`/`.claude/agents`) are committed team
files: per CLAUDE.md "Implement in a worktree, never branch in the main checkout" and
the lab-to-production rule, they land via a worktree + PR, never a direct Edit on
`main`. Most Route-table domains (testing, code-style, architecture, security,
debugging) are project-tier, so worktree + PR is the default; surface that in the
proposal rather than implying a direct edit.

- **y**: Apply per the target's tier above (direct Edit for personal-tier; worktree +
  PR for project-tier). Update the correction memory with the resolution:
  `bd remember --key="<same key>" "<date>: Resolved - added to <file>"`
- **edit**: Accept the user's modifications, apply the revised edit, update memory.
- **n**: Discard. Do NOT save a date-stamped recurrence memory if an umbrella memory (`correction:<domain>:<topic>`) plus structural enforcement (hook, linter, gate, formatter) are both already in place; recurrence tallies entrench adversarial framing without changing default behavior (CLAUDE.md Reflection Trigger step 5). If the same correction recurs after /reflect concludes "no edit", surface it back to the user as a mechanical question (which different enforcement layer would catch this?), not as another dated memory. The exception: save a recurrence memory only if the prior memory is missing context that would meaningfully sharpen future matching (a new structural variant, a new context category), and the surplus is genuinely additive rather than performative.

## Guidelines

- Propose refinements of existing rules over new rules. The rule set should get
  sharper, not larger.
- Do not propose changes that contradict existing rules. If a conflict exists, flag
  it for the user rather than resolving it unilaterally.
- Include the date in all correction memories for TTL evaluation.
- Match the tone and formatting conventions of the target file.
- The output of this skill is a proposal, never an auto-applied change. The user
  always has final say.
