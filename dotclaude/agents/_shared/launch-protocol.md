# Launch Protocol (canonical reference)

This file is the canonical source for protocol text shared across the three
`/launch` subagent files: `launch-flex.md`, `launch-implementer.md`,
`launch-tester.md`. It is documentation, not loaded at runtime.

The agent files keep the protocol inline (not via Read indirection at startup).
Sections that should remain byte-identical across the three agent files are
wrapped with HTML-comment fences in the agent definitions:

```
<!-- BEGIN SHARED-PROTOCOL:<name> -->
... canonical text ...
<!-- END SHARED-PROTOCOL:<name> -->
```

The `~/.claude/scripts/check-launch-protocol-drift.sh` script extracts each
fenced region from the three agent files, compares them against the canonical
text in this file, and exits non-zero on drift. Run manually before edits to
the launch-* agents.

## Why this approach

The 2026-04-29 /converge cycle (bead `docr-81yn`) rejected runtime extraction
patterns (Read-first instruction; Skill invocation at startup) on silent-failure
grounds: a launch agent that skips the Read leaves no STANDUP block, which the
orchestrator cannot detect. Inline text plus drift detection is safer than
runtime indirection for protocol-critical content.

## Fenced sections (byte-identical across all three agent files)

### final-result-block

<!-- BEGIN SHARED-PROTOCOL:final-result-block -->
Your final response (the one returned to the orchestrator) MUST include one of:
- `BRANCH: <name>` and `PR: <url>` lines if commits + draft PR are produced.
- `INCOMPLETE: <reason>` if you ran out of turns or hit a blocker. Include
  `WORKTREE: <path>` and `UNCOMMITTED: yes|no` so the orchestrator can either
  re-dispatch with a continuation prompt or know to recover the work itself.

A response with `status: completed` upstream but no BRANCH/PR/INCOMPLETE marker
in your own result is misleading; orchestrators read your result block to
decide whether to re-dispatch. Do not let a turn limit produce an empty
"completed" signal.
<!-- END SHARED-PROTOCOL:final-result-block -->

## Role-tuned variations (intentionally NOT fenced)

Several sections share structure across the three launch-* agents but contain
deliberate role-specific wording that should NOT be flattened. They live inline
in each agent file and are documented here so editors know what is intentional
divergence vs accidental drift.

### Standup Protocol DONE-field hint

The 4-field STANDUP block (DONE / NEXT / BLOCKED / RISK) is structurally
identical, but each agent uses a role-tuned hint for the DONE field:

| Agent | DONE field hint |
|-------|-----------------|
| launch-flex | `[what you just completed - be specific to your domain]` |
| launch-implementer | `[what you just completed - file path, function/class name]` |
| launch-tester | `[what you just completed - test file, test names, what behavior they verify]` |

The hint shapes what the agent reports; preserving role-tuning produces more
useful standup output.

### Communication section trailer ("the orchestrator uses them...")

`launch-implementer` includes an extra sentence after "Send via SendMessage to
the orchestrator. Do not skip standups": "the orchestrator uses them to
coordinate phasing, spawn specialists, and unblock you." `launch-flex` and
`launch-tester` do not. The implementer does the most parallel work and is
most likely to drop standups under turn pressure; the trailer is intentional
emphasis, not drift.

### Completion step 1 (verification command)

| Agent | Step 1 verification |
|-------|---------------------|
| launch-flex | "Run any relevant verification commands for your domain" |
| launch-implementer | "Run `pants check` on all your changed files" |
| launch-tester | "Run `pants test <test-targets>` on all your test files" |

The command is role-specific because the verification is role-specific.

### Retry Context Handling steps 2 and 4

The 6-step Retry Context list has steps 1, 3, 5, 6 byte-identical across all
three agents. Steps 2 and 4 are role-tuned:

**Step 2 ("Read the [...] before touching anything"):**
- launch-flex: "Read the files you already produced before touching anything."
- launch-implementer: "Read the files listed under \"Prior commits\" before touching anything."
- launch-tester: "Read the test files you already wrote before touching anything."

**Step 4 ("Do NOT modify [...] listed under \"What is already correct.\""):**
- launch-flex: "Do NOT modify items listed under..."
- launch-implementer: "Do NOT modify files listed under..."
- launch-tester: "Do NOT modify tests listed under..."

These tell each role what its source set is. Flattening to a single phrasing
would lose the cue.

The Retry Context section is NOT fenced for drift checking (only steps 1, 3,
5, 6 would be eligible, and fencing four non-contiguous lines inside a numbered
list adds more confusion than value).

## How to update

When editing one of the fenced sections (currently only `final-result-block`):

1. Update the canonical text in this file first.
2. Update the corresponding fenced region in each of the three agent files
   to match byte-for-byte.
3. Run `~/.claude/scripts/check-launch-protocol-drift.sh` to confirm no drift.

When editing a role-tuned variation (Standup hint, Communication trailer,
Completion step 1, Retry step 2/4): update the table above to keep the
documentation in sync, then update the agent file.

## References

- Bead `docr-81yn` (audit and converged plan)
- 2026-04-29 /converge stress-test agents: challenge `abf6a0a5dfd388f08`,
  consult `a102372faa53475af`
- Pre-refactor backup: `/tmp/launch-backup-1777427679/`
