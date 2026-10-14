---
name: calibrate
description: Review and merge calibration drift entries that subagents have emitted via memory topic files. Default agent is decision-maker; override with --agent. Reads each agent's calibration memory topic file, presents each entry with the current calibration file state, lets the user keep/merge/reject per entry. On merge writes to the agent's calibration file and the audit log, then deletes the source memory key. Includes scratch-file reconciliation (warns on orphaned files when scratch fallback is in use). Use when SessionStart hook nudges about unmerged entries, or periodically to review accumulated drift.
argument-hint: "[--agent <name>]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Edit", "Write", "AskUserQuestion"]
---

# Calibrate

Review human gate for agent calibration drift. Subagents (decision-maker today, others later) emit calibration drift as memory topic file entries rather than writing their calibration files directly. This is a deliberate human review gate (calibration changes are vetted before merge), not a write restriction. This skill is the orchestrator side of the loop: it reads the emitted entries, presents them for review, and writes the accepted merges to the agent's calibration file.

## Why This Exists

Without this skill, the calibration channel is write-only: subagents emit drift to a memory topic file, nothing reads it, nothing merges it, the calibration file stays empty. This skill is what makes the calibration system a learning loop instead of a frozen snapshot.

## Input

`/calibrate [--agent <name>]`

- `--agent <name>` (optional): the agent whose calibration to review. Default: `decision-maker`.

## Process

### Phase 1: Discover

1. Determine target agent from `--agent` flag or default to `decision-maker`.
2. Read the agent definition file (`~/.claude/agents/<name>.md`) to confirm it exists. If missing, halt with: "Agent <name> not found at ~/.claude/agents/<name>.md."
3. Determine calibration file path: `~/.claude/agents/calibration/<short-name>.md` (where `<short-name>` is the agent name; e.g., `decision-maker`). If the file does not exist, halt with a message asking the user whether to create it.
4. Determine lookback log path: `~/.claude/agents/calibration/<short-name>.lookback.md`. If missing, create with a header (see template below).

### Phase 2: Harvest

1. Harvest: read `~/.claude/memory/calibration-<agent>.md` (FULL agent name, e.g. `calibration-decision-maker.md`). Each entry is a `### calibration:<agent>:<category>:<specific-slug>` heading and the body under it, up to the next heading. If the file does not exist, there is no drift. Discard any entry whose key does not start with `calibration:<agent>:`. Note: the key uses the full agent name (matching what subagents write), NOT the `<short-name>` used for the file path above. Keys whose second segment is not a known agent (legacy `calibration:pr-intel-*`, `calibration:style:*`, `calibration:user-improvement-stance`) are out of /calibrate scope; triage those by hand (remove or re-key).
2. Parse each memory key. Standard form is 4-segment: `calibration:<agent>:<category>:<specific-slug>`; extract category and specific-slug. **3-segment fallback**: some emitters (blast-radius-reviewer, legacy skeptic entries) use `calibration:<agent>:<short-tag>` with no category segment; treat segment 3 as the specific-slug and route the entry to the agent's default section (`## Rule Overrides`, unless the agent's calibration file documents a different home, e.g. skeptic's `## Example Dismissals`). The remaining body text is the drift content.
3. If no entries, output: "No unmerged calibration drift for <agent>. Calibration file is current as of last merge." and exit.

### Phase 3: Present and Decide

For each entry, in dependency-free order (no inter-entry sequencing required):

1. Read the current calibration file (`~/.claude/agents/calibration/<short-name>.md`).
2. Locate the section for the entry's category using this mapping (create the section if missing):

   | Category (key segment 3) | Calibration-file section |
   |---|---|
   | `proceed-gate`, `iterate-trigger`, `escalate-condition`, `rule-override` | `## Rule Overrides` |
   | `threshold` | `## Threshold Notes` |
   | `false-positive` | `## False-Positive Patterns` |
   | `false-negative` | `## False-Negative Patterns` |
   | `dismissal` (skeptic) | `## Example Dismissals` |
   | 3-segment key (no category) | agent's default section per Phase 2 |

   If the agent's calibration file uses its own documented section names, the file's structure wins; map to the nearest equivalent and say so when presenting the entry. A 4-segment key whose category has no table row (e.g. the gate-context tags `converge`, `ideation`, `launch`, `autopilot` that decision-maker gate prompts use as the category segment) routes to the agent's default section, same as the 3-segment fallback; note the unmapped category when presenting.
3. Search the section for an existing entry with the same specific-slug. Three sub-cases:
   - **No match**: this is a new entry, will be appended.
   - **Match with same content**: this is a redundant emission, recommend reject (the file already has this rule).
   - **Match with different content**: this is a refinement, recommend merge with diff shown.
4. Present to the user (use `AskUserQuestion` for the keep/merge/reject choice):

```
Calibration drift entry: calibration:<agent>:<category>:<specific-slug>
Current state in <short-name>.md (section "<category>"):
  <existing entry body, or "(no existing entry)">

New entry body (from the calibration memory topic file):
  <new entry body>

Sub-case: <new | refinement | redundant>

Choose:
  - merge: write the new content into the calibration file, append to lookback log, delete the source memory key
  - reject: delete the source memory key without writing to the file (the entry was wrong or already covered)
  - keep: leave the memory entry alone (revisit on next /calibrate run; useful when you want to think about it more)
```

### Phase 4: Apply

For each merge-accepted entry:

1. Write to the calibration file. Place the entry in the right section (Rule Overrides, False-Positive Patterns, Threshold Notes, etc.) using the `Edit` tool. If the section does not exist, create it.
2. Append to the lookback log:

```markdown
## YYYY-MM-DD

- **Source key**: `calibration:<agent>:<category>:<specific-slug>`
- **Category**: <category>
- **Action**: new-rule | refinement | reject  (Phase 3 sub-case `new` → new-rule; `refinement` → refinement; reject-accepted entries → reject)
- **Summary**: <one line: what changed>
- **Rationale**: <one line: why merged>
```

3. Delete the source entry: remove its `### <full-key>` block from `~/.claude/memory/calibration-<agent>.md` with the Edit tool.

For each reject-accepted entry:

1. Append a one-line lookback entry (same format as merges, with **Action**: reject and **Rationale**: why rejected) so the producing agent's anti-re-emission contract holds (the calibration scaffolds promise rejected patterns are logged so agents stop re-emitting them).
2. Delete the source entry's `### <full-key>` block from the topic file. Do not write to the calibration file itself.

For each keep-accepted entry:

1. Do nothing. Memory entry persists for the next `/calibrate` run.

### Phase 5: Reconcile (scratch fallback)

Even though Tier 1 does not use scratch fallback, the skill enforces the cleanup contract from day one so Tier 2 is purely additive:

1. Check if the scratch dir exists: `/workspaces/main/.claude/scratch/agent-feedback/<agent>/`. If not, skip this phase.
2. List files in the dir.
3. For each scratch file:
   - If a calibration memory entry referenced it AND that entry was merged or rejected this run, delete the scratch file.
   - If the file is older than 7 days AND no current memory entry references it, warn the user: "Stale scratch file <path> (age: N days, no associated memory key). Delete? (y/n)"
4. Before any future Tier 2 work writes to project scratch, verify `.claude/scratch/` is in `/workspaces/main/.gitignore`. If not, halt with: "Project .gitignore does not cover .claude/scratch/; refusing to write personal scratch files into a checked-in path. Add `.claude/scratch/` to .gitignore first."

### Phase 6: Report

Print a one-block summary:

```
Calibrated <agent>:
  Reviewed: <N> entries
  Merged: <M> entries (<short list of slugs>)
  Rejected: <R> entries
  Kept for next pass: <K> entries
  Scratch files cleaned: <S>
  Stale scratch warnings: <W>

Calibration file: ~/.claude/agents/calibration/<short-name>.md
Lookback log: ~/.claude/agents/calibration/<short-name>.lookback.md
```

## Lookback Log Header Template

If the lookback log does not exist, create with:

```markdown
# <short-name> Calibration Lookback Log

Append-only audit trail of merged and rejected calibration drift entries for the
`<agent-name>` agent. Each `/calibrate` accept appends one entry per merge.

This log is the historical record post-merge; the calibration file is the current
state. Use this log for retrospective review (which rules emerged when, which
calibration drift was rejected and why).
```

## Calibration File Section Template

If a section does not exist when writing an entry, create with:

```markdown
## <Category>

(no entries yet)
```

Then immediately replace `(no entries yet)` with the first entry.

## Rules

- **Never write to calibration file without explicit user accept.** This skill is the human review gate. Auto-merge defeats the purpose.
- **Always delete merged or rejected memory keys.** The calibration file (or the rejection) is the audit; the memory entry is intermediate state. Stale entries clutter the topic file.
- **Lookback log is append-only.** Never edit or remove entries. Use the lookback log for the "what we learned" retrospective; reverts to the calibration file go through git.
- **Refuse to write to project scratch without `.gitignore` coverage.** Hard refuse, not warn. Personal data in a checked-in path is the failure mode this skill exists to prevent.
- **One agent per invocation.** Do not bulk-process across agents in one run. The user reviews one agent's drift at a time so they can attend to each.

## Verification (end-to-end test)

To verify the loop closes from end to end, run the synthetic-drift fixture:

```bash
# 1. Inject a known fixture entry: with the Edit tool, add to ~/.claude/memory/calibration-decision-maker.md
#      ### calibration:decision-maker:proceed-gate:fixture-test-do-not-merge
#      FIXTURE: synthetic drift entry for end-to-end loop test. If this lands in the calibration file, the loop closes.

# 2. Confirm channel
grep -n "fixture-test-do-not-merge" ~/.claude/memory/calibration-decision-maker.md

# 3. Run /calibrate
# 4. Accept the fixture (the test path always accepts; in real use you'd reject)

# 5. Verify file
grep "FIXTURE" ~/.claude/agents/calibration/decision-maker.md

# 6. Verify lookback log gained an entry
grep "fixture-test-do-not-merge" ~/.claude/agents/calibration/decision-maker.lookback.md

# 7. Verify cleanup (the source entry should be gone post-merge)
grep -n "fixture-test-do-not-merge" ~/.claude/memory/calibration-decision-maker.md  # should print nothing

# If still present, the skill run did not remove the entry. Remove its block by hand with the Edit tool.

# 8. Cleanup test artifact: manually remove the FIXTURE entry from the calibration file
```

The fixture data is committed at `~/.claude/agents/calibration/test-fixtures/synthetic-drift.json` for repeatability.
