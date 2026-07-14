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
The terminal RESULT block defined in the Terminal RESULT Contract section
(canonical source: `skills/launch/SKILL.md`, summary key `result-contract`) is
the SINGLE terminal contract. The SubagentStop enforcement hook and the /launch
orchestrator read only `RESULT:` plus `STATUS: done|partial|blocked`; do not
substitute any other completion marker.

Optional RESULT fields, added when they apply:
- `BRANCH: <name>` when your commits are on a branch in the shared worktree.
- `PR: <url>` when a draft PR was produced.
- `WORKTREE: <path>` and `UNCOMMITTED: yes|no` whenever STATUS is partial or
  blocked, so the orchestrator can resume you with a continuation prompt or
  recover the work itself.

Status mapping for interrupted runs: stopped-per-user-instruction is
`STATUS: blocked` with the instruction noted; ran-out-of-turns is
`STATUS: partial` with the gap in REMAINING. Do not let a turn limit produce
an upstream `status: completed` with no RESULT block in your own final
message; the orchestrator reads the block to decide whether to resume or
re-dispatch.
<!-- END SHARED-PROTOCOL:final-result-block -->

### bead-comment-channel

<!-- BEGIN SHARED-PROTOCOL:bead-comment-channel -->
## Mid-flight Updates from User

When your startup prompt names a bead (`docr-\w+`), the user can leave comments
on that bead while you work to send real-time guidance, course corrections, or
stop instructions. Poll for new comments at major checkpoints.

**Startup snapshot**: run `bd comments <bead-id>` once at the start of work.
Record the latest comment timestamp/ID. Treat anything before this snapshot as
"already seen."

**Polling cadence** (whichever comes first):
- After each verification pass (lint, test, `terraform fmt`, `pants tlc`)
- Before each commit, push, or amend
- Before declaring done in your final result block
- Approximately every 5 minutes during long-running operations

**On poll**:
1. Run `bd comments <bead-id>`.
2. For new comments authored by you (prefixed with `[agent ack]` or `[agent
   status]`; see hygiene below), skip.
3. For new comments authored by the user, treat as input.

**Acting on a user comment**:
- **Informational** ("FYI: deploy unblocked"): acknowledge with `bd comment
  <bead-id> "[agent ack] received; continuing"` and proceed.
- **Course correction** (changes scope, alters AC, pivots strategy): apply the
  change. Acknowledge with `bd comment <bead-id> "[agent ack] applied:
  <one-line summary>"`.
- **STOP / ABORT / PAUSE**: exit cleanly. Acknowledge with `bd comment
  <bead-id> "[agent ack] stopping per instruction; worktree state: <summary>"`.
  End with the terminal RESULT block: `STATUS: blocked`, `stopped per user
  instruction` noted, and worktree state (uncommitted changes, branch, last
  completed step) covered in the block.

**Self-comment hygiene**: prefix every comment YOU post with `[agent status]`
or `[agent ack]` so future polls (yours and other agents') can filter them
out. Examples:
- `bd comment <bead-id> "[agent status] verification passed; amending commit"`
- `bd comment <bead-id> "[agent ack] received scope-change; updating monitor threshold"`

**No bead ID in startup prompt**: skip this section. The user is running you
without a tracked bead context.
<!-- END SHARED-PROTOCOL:bead-comment-channel -->

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

`launch-implementer` includes an extra clause after the standup-emission
sentence ("Emit the STANDUP block in your output stream... Do not skip
standups"): "the orchestrator uses them to coordinate phasing, dispatch
specialists, and unblock you." `launch-flex` and `launch-tester` do not.
(2026-06-09: standup delivery is output-stream emission, not SendMessage;
subagents have no messaging tool and cannot dispatch sub-agents.) The implementer does the most parallel work and is
most likely to drop standups under turn pressure; the trailer is intentional
emphasis, not drift.

### Completion step 1 (verification command)

| Agent | Step 1 verification |
|-------|---------------------|
| launch-flex | "Run any relevant verification commands for your domain" |
| launch-implementer | "Run `pants check` on all your changed files" |
| launch-tester | "Run `pants test <test-targets>` on all your test files" |

The command is role-specific because the verification is role-specific.

### Implementer pre-push poll (after the bead-comment-channel fence)

`launch-implementer` carries one extra polling requirement immediately AFTER
its bead-comment-channel fence (outside it, so the fence stays byte-identical):
poll once more after verification passes clean and before any push or
PR-creation command. PR-creation commands collapse push + PR + reviewer
assignment into one step, and orchestrator adjudications (e.g.
`[orchestrator] ORCHESTRATOR-SPLIT`) can arrive exactly there. Implementer-only
because pushes/PR commands are implementer-tier actions.

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

When editing one of the fenced sections (`final-result-block`,
`bead-comment-channel`):

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
