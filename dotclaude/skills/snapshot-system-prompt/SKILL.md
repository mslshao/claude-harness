---
name: snapshot-system-prompt
description: >
  Capture the current Claude Code system prompt's behavioral sections to a versioned
  snapshot file under ~/.claude/scratch/system-prompt-snapshots/, then diff against
  the most recent prior snapshot to surface drift. Use when the snapshot-drift.py
  SessionStart hook reports that a newly installed Claude Code version's prompt
  changed, or when asked. Triggers: "snapshot system prompt", "capture system
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
hardening backlog codifies the load-bearing defaults at project tier so
behavior remains stable across version drift.

This skill is the periodic capture mechanism that makes drift detection possible.
Without it, snapshots age out and the audit table goes stale.

The first snapshot on this machine is `~/.claude/scratch/system-prompt-snapshots/2.1.280-2026-09-23.md`.
Reference it for the file shape. The 2.1.117 seed and the 2.1.170 Fable file cited below
were written on the previous machine and are not here.

## Input

No arguments. The skill reads the current session's system prompt directly.

## Process

### Step 1: Detect current Claude Code version

```bash
jq -r 'select(.version) | .version' ~/.claude/projects/*/$CLAUDE_CODE_SESSION_ID.jsonl | tail -1
```

This reads the version from this session's own transcript. Do not run `claude --version`:
the CLI hangs when invoked from inside a session (`~/.claude/rules/environment.md`).
If the command prints nothing, stop and surface the failure to the user; do not write a
snapshot with an unknown version.

### Step 2: Find the most recent prior snapshot

```bash
ls -1 ~/.claude/scratch/system-prompt-snapshots/*.md 2>/dev/null | grep -v -e '-binary-' -e '/diff-' | sort -V | tail -1
```

If no prior snapshot exists, this is the seed capture; skip the diff step at the end.

**Model-variant rule (added 2026-06-11):** prompt shape is MODEL-conditional, not just
version-conditional (verified: 2.1.170 ships a different prompt under Fable 5 vs Opus
4.8 on the same build). When model-variant snapshots exist for the version, diff
against the most recent prior snapshot OF THE SAME MODEL; a cross-model diff compares
restructurings, not version drift. Comparing across models is a deliberate, separate
analysis (see `2.1.170-fable5-2026-06-11.md` for the reference cross-model drift table).

### Step 3: Determine output path

Output path: `~/.claude/scratch/system-prompt-snapshots/<version>-<YYYY-MM-DD>.md`
when the session's main-loop model matches the most recent snapshot for this version.
When it does NOT (a model variant on the same build), insert the model slug:
`<version>-<model-slug>-<YYYY-MM-DD>.md` (e.g., `2.1.170-fable5-2026-06-11.md`).
The unsuffixed name implicitly means Opus-era main loop for snapshots before
2026-06-11; the header's "Captured by" line is authoritative.

If a file with that exact name already exists (same version captured today), append
`-N` suffix starting at `-2` (so `2.1.117-2026-05-05.md`, then `2.1.117-2026-05-05-2.md`,
etc.). Do not overwrite a same-day capture; treat as a separate observation.

### Step 4: Capture behavioral sections verbatim

Read the current session's system prompt and capture **every behavioral / instructional
section present in THIS version, verbatim**. Do NOT treat the list below as a fixed
contract: the prompt structure changes across versions (the Opus 4.8 condensation,
v2.1.162, collapsed four discrete sections into a terse `# Harness` block plus inline
paragraphs). If the prompt has been restructured, capture the new sections under their
actual headings and map old->new in the Step 7 drift table; if a previously-captured
section is gone, record its disappearance as drift rather than silently omitting it.

The 4.7-era reference structure (present through v2.1.153, partially or wholly dropped
in 4.8) was:

- `# Doing tasks` (the load-bearing behavioral list)
- `# Executing actions with care` (destructive ops, blast radius, confirmation)
- `# Using your tools` (tool-use mechanics; lower drift risk but capture for completeness)
- `# Tone and style` (style and voice defaults)
- `# Text output (does not apply to tool calls)` (narration discipline)
- `# Context management` (operational note about context compression)

Under 4.8 the behavioral content lives in `# Harness`, an inline executing-with-care
paragraph (no heading), and `# Context management`; capture whatever is actually there.
Under 2.1.280 with Opus 5.5 it is the preamble, `# Harness`, unheaded paragraphs
(pronouns, executing with care, act without re-deriving), `# Session-specific guidance`
and `# Context management` (see `2.1.280-2026-09-23.md`).
Note: this version-agnostic capture matters beyond Opus, and the fleet is now MIXED
(verified 2026-06-11, on the previous machine): IDE/Claude Code windows run Opus 4.8 (org ZDR blocks Fable 5
there pending 30-day retention), while CLI sessions
may run Fable 5, whose prompt restructures the behavioral sections (new
`# Communicating with the user` with restored comment discipline, expanded
`# Context management`; see `2.1.170-fable5-2026-06-11.md`). Capture whatever the
live session actually carries and name the file per the Step 3 model-variant rule.

**Skip** these sections (they are environment-conditional, not version-driven):
- `# System` (tool-mechanics; per-tool, low behavioral drift)
- `# VSCode Extension Context` (varies by host)
- `# Memory`, formerly `# auto memory` (varies by directory presence)
- `# Environment` (per-session metadata)

### Step 5: Apply em-dash transformation

This machine's `block-em-dash.py` PreToolUse hook rewrites U+2014 and U+2013 in any
Markdown file written under `~/.claude/`, silently. Anthropic's system prompt uses
U+2014 freely. To preserve position fidelity for future diffs, replace every U+2014
in the captured content with the literal placeholder string `[EMDASH]` and every
U+2013 with `[ENDASH]` before writing. Document the transformation in the file header
so the original text is recoverable.

### Step 6: Write snapshot file

File structure (model on the seed snapshot):

```markdown
# Claude Code System Prompt Snapshot

**Claude Code version:** <version>
**Captured:** <YYYY-MM-DD>
**Captured by:** <user> via in-session <model name>
**Machine:** <host and working directory>
**Capture method:** verbatim copy of behavioral sections from the live system prompt, with two transformations: U+2014 em-dash characters in the source have been replaced with the literal string `[EMDASH]`, and U+2013 en-dash characters with `[ENDASH]`, because this machine's `block-em-dash.py` PreToolUse hook (its Edit and Write arm) rewrites both dashes in a Markdown file. Position fidelity is preserved so future diffs against new snapshots remain meaningful. To recover the original text, substitute `[EMDASH]` back to U+2014 and `[ENDASH]` back to U+2013.
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

For each change, cross-reference the audit table from the 2026-05-05 plan. These six
behaviors are codified in the Code Discipline section of the portfolio file
`~/dev/claude-harness/dotclaude/CLAUDE.md`; this machine's `~/.claude/CLAUDE.md` does not
carry it. The `docr-*` test beds lived in the previous machine's beads store; beads was
removed here on 2026-08-27:

- **Comment discipline** (default-no-comments + no-callers-references)
- **YAGNI / scope discipline** (no-features-beyond-task)
- **Don't error-handle for impossible scenarios**
- **Prefer edit over create**
- **UI-verify before claiming done**
- **Backwards-compat hacks**

If a drift entry affects one of these audit-table behaviors, flag it explicitly:
"Drift affects audit-table behavior: <name>. The Code Discipline rule in the portfolio
file (`~/dev/claude-harness/dotclaude/CLAUDE.md:171`) holds the contract regardless of
the system-prompt shift; surface the drift so the wording
can be re-checked against the new prompt text."

### Step 8: Update the state file

Skip on this machine. The drift hook, `~/.claude/hooks/snapshot-drift.py`, keeps no state
file: it acts when the newest version under `~/.local/share/claude/versions/` has no
`<version>-binary-*.md` snapshot, which Step 9's script writes.

### Step 9: a version with no live session

For an installed version you have no session on, run
`python3 ~/.claude/scratch/scripts/snapshot-system-prompt-from-binary.py ~/.local/share/claude/versions/<version>`
and `--diff` the result against the previous version's binary snapshot. It recovers the
source text of each prompt piece, with `${…}` where a value is spliced in at run time; it
cannot say which pieces a session receives.

## Output

Concise summary to the user:

```
Snapshot captured: ~/.claude/scratch/system-prompt-snapshots/<version>-<date>.md

Drift vs prior snapshot (<prior_version>-<prior_date>):
| Section | Change |
|---|---|
| ... | ... |

Audit-table impact: <none | bullet list of affected behaviors with open-chores.md refs>

Next action: <none | "Re-run /converge on the affected item" | "File a follow-up">
```

## Rules

- **Verbatim is load-bearing.** The whole point is empirical comparison. Do not
  paraphrase, summarize, or "improve" the captured text. The dash placeholders,
  `[EMDASH]` for U+2014 and `[ENDASH]` for U+2013, are the only allowed transformation.
- **Do not commit snapshots to the project repo.** They live in personal scratch.
  Cross-account team sharing is a separate decision.
- **Always run the diff.** A snapshot without a drift summary is half the value.
  If no prior snapshot exists, say so and skip the diff section; do not silently
  proceed.
- **Stop on version-detection failure.** Do not write a snapshot with version
  `unknown` in the filename; the version is the primary index for future
  comparisons.

## Related References

- `docr-ojx5` (closed, previous machine) - SessionStart hook that nudges to invoke this skill on drift
- `project:rule-architecture-version-changelog-mirror` (memory) - a deferred 2026-05-05
  rough idea for a project-tier companion file; not acted on, and the skill does not
  depend on it
