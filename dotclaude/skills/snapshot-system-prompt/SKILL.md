---
name: snapshot-system-prompt
description: >
  Capture the current Claude Code system prompt's behavioral sections to a versioned
  snapshot file under ~/.claude/scratch/system-prompt-snapshots/, then diff against
  the most recent prior snapshot to surface drift. Use when the version-drift
  SessionStart hook (check-cc-version-drift.sh) nudges that current Claude Code
  version no longer matches the latest snapshot, or proactively when a new Claude
  Code version is installed. Triggers: "snapshot system prompt", "capture system
  prompt", "/snapshot-system-prompt".
argument-hint: "(no args - reads version and content from current session)"
---

# Snapshot System Prompt

Capture the current Claude Code system prompt's behavioral sections to a versioned
snapshot file. Diff against the most recent prior snapshot to surface drift in the
behaviors that the project rules architecture (`.claude/rules/*.md`) silently
inherits today.

## Why This Exists

The Claude Code system prompt encodes behavioral defaults (the `# Doing tasks`
section among others). The team is not version-locked, so each IC's effective
defaults vary by which Claude Code version they have installed. The personal-tier
hardening backlog (beads `docr-95m8`, `docr-z1qt`, `docr-rtce`, `docr-d0r9`,
`docr-lga9`, `docr-kpe4`) codifies the load-bearing defaults at project tier so
behavior remains stable across version drift.

This skill is the periodic capture mechanism that makes drift detection possible.
Without it, snapshots age out and the audit table goes stale.

The seed snapshot lives at `~/.claude/scratch/system-prompt-snapshots/2.1.117-2026-05-05.md`.
Reference it for the file shape.

## Input

No arguments. The skill reads the current session's system prompt directly.

## Process

### Step 1: Detect current Claude Code version

```bash
claude --version
```

Extract the semantic version (e.g., `2.1.117`). If the binary is missing or output
format has changed, stop and surface the failure to the user; do not write a
snapshot with an unknown version.

### Step 2: Find the most recent prior snapshot

```bash
ls -1 ~/.claude/scratch/system-prompt-snapshots/*.md 2>/dev/null | sort -V | tail -1
```

If no prior snapshot exists, this is the seed capture; skip the diff step at the end.

### Step 3: Determine output path

Output path: `~/.claude/scratch/system-prompt-snapshots/<version>-<YYYY-MM-DD>.md`.

If a file with that exact name already exists (same version captured today), append
`-N` suffix starting at `-2` (so `2.1.117-2026-05-05.md`, then `2.1.117-2026-05-05-2.md`,
etc.). Do not overwrite a same-day capture; treat as a separate observation.

### Step 4: Capture behavioral sections verbatim

Read the current session's system prompt and extract these sections **verbatim**:

- `# Doing tasks` (the load-bearing behavioral list)
- `# Executing actions with care` (destructive ops, blast radius, confirmation)
- `# Using your tools` (tool-use mechanics; lower drift risk but capture for completeness)
- `# Tone and style` (style and voice defaults)
- `# Text output (does not apply to tool calls)` (narration discipline)
- `# Context management` (operational note about context compression)

**Skip** these sections (they are environment-conditional, not version-driven):
- `# System` (tool-mechanics; per-tool, low behavioral drift)
- `# VSCode Extension Context` (varies by host)
- `# auto memory` (varies by directory presence)
- `# Environment` (per-session metadata)

### Step 5: Apply em-dash transformation

The personal `block-em-dash.sh` PostToolUse hook scans every file write for U+2014.
Anthropic's system prompt uses U+2014 freely. To preserve position fidelity for
future diffs while satisfying the hook, replace every U+2014 in the captured
content with the literal placeholder string `[EMDASH]`. Document the transformation
in the file header so the original text is recoverable.

### Step 6: Write snapshot file

File structure (model on the seed snapshot):

```markdown
# Claude Code System Prompt Snapshot

**Claude Code version:** <version>
**Captured:** <YYYY-MM-DD>
**Captured by:** <user> via in-session <model name>
**Codespace:** <pwd or workspace path>
**Capture method:** verbatim copy of behavioral sections from the live system prompt, with one transformation: U+2014 em-dash characters in the source have been replaced with the literal string `[EMDASH]` to satisfy the project's `block-em-dash.sh` PostToolUse hook. Position fidelity is preserved so future diffs against new snapshots remain meaningful. To recover the original text, substitute `[EMDASH]` back to U+2014.
**Purpose:** Empirical baseline for detecting drift in Anthropic-shipped harness instructions across Claude Code versions. The project rule architecture (`.claude/rules/*.md`) silently inherits these behaviors today; documenting the baseline lets us identify which behaviors we depend on and codify the load-bearing ones at project tier so they remain stable when this snapshot's content shifts in future versions.

---

## Section: # Doing tasks

```
<verbatim section content with [EMDASH] substitution>
```

---

## Section: # Executing actions with care

```
<verbatim section content with [EMDASH] substitution>
```

---

(repeat for each behavioral section)

---

## Sections excluded from this snapshot

(same exclusion list as the seed snapshot)

---

## Capture cadence

(same cadence note as the seed snapshot)
```

### Step 7: Diff against the prior snapshot

If a prior snapshot exists:

```bash
diff <prior_snapshot> <new_snapshot>
```

Summarize the drift in a concise table for the user:

| Section | Change | Notes |
|---|---|---|
| `# Doing tasks` | bullet added / bullet removed / bullet reworded | Quote the changed text |
| ... | ... | ... |

For each change, cross-reference the audit table from the 2026-05-05 plan:

- **Comment discipline** (default-no-comments + no-callers-references)
- **YAGNI / scope discipline** (no-features-beyond-task)
- **Don't error-handle for impossible scenarios**
- **Prefer edit over create**
- **UI-verify before claiming done**
- **Backwards-compat hacks**

If a drift entry affects one of these audit-table behaviors, flag it explicitly:
"Drift affects audit-table behavior: <name>. See bead `docr-XXXX` for the project-tier
codification status. If that bead has not landed yet, the system-prompt drift could
silently change effective behavior; if it has landed, the project rule continues to
hold the contract."

### Step 8: Update the state file

After writing the snapshot, update the drift-detection hook's state file so the
nudge stops firing today:

```bash
date +%Y-%m-%d > ~/.claude/state/last-drift-check
```

This is belt-and-suspenders: the hook already updates this file on its own first
run, but if the user invoked this skill manually before the hook fired, syncing
the state avoids a redundant nudge later in the day.

## Output

Concise summary to the user:

```
Snapshot captured: ~/.claude/scratch/system-prompt-snapshots/<version>-<date>.md

Drift vs prior snapshot (<prior_version>-<prior_date>):
| Section | Change |
|---|---|
| ... | ... |

Audit-table impact: <none | bullet list of affected behaviors with bead refs>

Next action: <none | "Re-run /converge on the affected bead" | "File a follow-up">
```

## Rules

- **Verbatim is load-bearing.** The whole point is empirical comparison. Do not
  paraphrase, summarize, or "improve" the captured text. Em-dash placeholder is
  the only allowed transformation.
- **Do not commit snapshots to the project repo.** They live in personal scratch.
  Cross-account team sharing is a separate decision (`bd memories project:rule-architecture-version-changelog-mirror`).
- **Always run the diff.** A snapshot without a drift summary is half the value.
  If no prior snapshot exists, say so and skip the diff section; do not silently
  proceed.
- **Stop on version-detection failure.** Do not write a snapshot with version
  `unknown` in the filename; the version is the primary index for future
  comparisons.

## Related Beads

- `docr-ojx5` (closed) - SessionStart hook that nudges to invoke this skill on drift
- `project:rule-architecture-version-changelog-mirror` (memory) - rough idea for
  eventual project-tier companion file once 2-3 drifts have been observed
