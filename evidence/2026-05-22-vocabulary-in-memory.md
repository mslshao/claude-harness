# 2026-05-22: User vocabulary lives in memory, not in the agent's working assumption (own-loop)

**Source**: the author's own session, 2026-05-22. The user asked to back up the harness; the conversation produced (1) a bug fix to an existing archive script, (2) a new snapshot script for state outside `~/.claude/`, (3) a recovery audit closing three gaps, and (4) a memory architecture entry that future sessions can consult. Scrubbed for public version.

**Context.** The author's personal Claude Code harness lives across three durability tiers: `~/.claude/` (config, skills, agents, hooks), a beads/Dolt database (the bd memory store), and dotfiles outside `~/.claude/` (`~/.bashrc`, `~/.gitconfig`, `~/.aws/config`). A backup script existed and synced `~/.claude/` to S3 with an explicit allowlist that deliberately excluded JSONL session transcripts. An archive script also existed for point-in-time tarballs that included transcripts. Two scripts, two different durability needs.

The user's mental model was a single word: "backup". The scripts had different names and different scopes. The gap was invisible to the user because the user never typed the script names; they typed "back up the harness" and assumed both ran. The agent had been running only the sync script in prior sessions, silently leaving transcripts and the beads database unsnapshotted.

**What AI did.** The work split into four phases:

1. *Surface the gap.* When asked to back up the harness, the agent ran the sync script and reported explicitly that the existing filter excluded transcripts by design (to avoid PII surface area in S3). The user clarified they wanted transcripts included. The vocabulary gap surfaced naturally.

2. *Fix the bug under the gap.* The archive script that handles transcripts exited code 1 mid-run. The agent diagnosed two bugs: (a) the script's `EPHEMERAL_EXCLUDES` array was defined but never wired into the tar invocation, so tar was reading its own growing output tarball from the staging directory; (b) GNU tar 1.35 returns exit code 1 on file-changed-during-read even with `--warning=no-file-changed`, contradicting the script's original comment that claimed the flag suppressed the exit code. A `tar_or_tolerate` helper that accepts exit 1 but fails on exit >= 2 plus actually wiring the excludes resolved both. Verified end-to-end with `--config-only` and `--convos-only` runs.

3. *Close the vocabulary gap.* The shell alias `claude-backup` was updated to chain both scripts. A bd memory entry under the key `tooling:claude-config-backup` was written with the vocabulary mapping explicit: "when the user says 'backup' they mean both scripts together; the alias chains them". The user's word now maps to the right mechanism in memory, not in any single session's working assumption.

4. *Close the recovery gaps.* When asked "if the codespace died right now, could we recover the full harness?", the agent surfaced three remaining gaps: bd memories were not replicated anywhere off-codespace, `~/.bashrc` was not in any backup, and a stale OAuth credentials file from a prior backup still sat in S3. All three were closed in the same session: a new `snapshot-extras.sh` script was added to the alias chain to capture dotfiles and the beads database, and the stale credentials file was deleted from S3 (versioning preserved the prior version so the action was reversible).

5. *Promote the memory.* The bd memory entry had grown dense (vocabulary + bug fix + script details + recovery playbook). The agent split it into a breadcrumb (the bd memory stays as a short pointer that loads at every SessionStart) plus a topic file (the full architecture, recovery playbook, S3 layout, history). The two-tier split matches the harness's memory architecture: always-loaded breadcrumbs for breadth, on-demand topic files for depth.

**Baseline.** Without the harness's discipline, each of the four phases had a quieter failure mode:

- *Without "verify before asserting"* (from `verification.md`): the agent would have reported the backup as complete after running just the sync script, because the existing chain "succeeded" by its own exit code. The transcript-exclusion gap would have stayed invisible.
- *Without the `tar_or_tolerate` work*: a future session running the archive script would have hit the same exit-1 failure, possibly without diagnosing it. The script would have stayed broken with no signal.
- *Without the vocabulary mapping in memory*: every future session would have re-derived the meaning of "backup" from scratch, with the same risk of partial execution. The author runs multiple Claude Code windows in parallel; one of them would have continued doing sync-only forever.
- *Without the recovery audit*: the three gaps would have stayed unaddressed until the codespace actually died, at which point the harness would have lost the last 9 days of bd memories plus today's bashrc edits.

**Verifiability.** The S3 bucket state is observable. The script fixes live at `~/.claude/scripts/backup/archive.sh` and the new `snapshot-extras.sh`. The shell alias change lives at `~/.bashrc`. The bd memory under `tooling:claude-config-backup` should now contain the vocabulary mapping plus a pointer to the topic file (which lives in personal memory and is intentionally not in this public repo per the privacy boundary).

**Honest read.**

1. *What this entry supports.* A single two-hour conversation produced a real bug fix, a vocabulary-to-mechanism alignment, a recovery audit with three gaps closed, and a durable memory entry that future sessions can consult. The four artifacts compounded: the bug fix surfaced because the vocabulary clarification ran the broken path; the recovery audit happened because the verification discipline was on; the memory promotion happened because the bd entry got too dense to stay a single fact. None of these were the user's original ask. The original ask was "back up the harness". The expansion is the kind of thing the harness's posture makes possible.

2. *What this entry does NOT support.* This is one session; selection bias applies (the author remembers and writes up the session because it worked). The work was bounded (no production system at risk, no other stakeholders); the same approach on a system with more constraints would move slower. The vocabulary mapping ("backup means both") is hyper-personal; the general pattern transfers, the specific word does not.

3. *Caveats specific to this entry.* The author is the same person whose memory architecture is referenced; the verification path is self-referential. An external reader cannot replicate the bd memory state (different beads workspace). What they CAN replicate is the pattern: when the user's word does not match the agent's mechanism, the fix is to write the mapping into memory so future sessions read it on entry.

## The core pattern: vocabulary in memory

User vocabulary precedes mechanism. When the user says "backup" and the mechanism is "sync only", the gap is invisible to the user but corrosive over time. The fix is to encode the vocabulary in a place future sessions read on entry (bd memory at SessionStart), so the next session interprets the word the user's way without asking, and dispatches the right artifact.

This generalizes. Any time a user's word maps to multiple possible mechanisms in the agent's repertoire, the mapping belongs in memory, not in the agent's working assumption. The cost of writing the bd memory is a one-time write; the cost of misinterpreting the word across N future sessions is N misalignments. The asymmetry is the reason the harness leans on memory for vocabulary alignment rather than on the agent's per-session inference.

## Sharper distillation: memory closes the vocabulary loop

The harness's two-tier memory architecture is what makes the pattern work in practice. A breadcrumb in beads (always loaded at SessionStart) ensures the vocabulary mapping is in context every session. A topic file (on-demand) holds the depth: the architecture, the recovery playbook, the history. The breadcrumb says "if backup work comes up, see backup-architecture.md"; the topic file says "here is how the three scripts compose and how to recover from a codespace loss".

Without the breadcrumb, the depth file is unfindable. Without the depth file, the breadcrumb runs out of room. Together they are a closed loop: vocabulary in memory, mechanism in topic file, breadcrumb to bridge them. Future-me reads the breadcrumb on entry, recognizes the domain when it comes up, loads the topic file, and acts with full context.

## Why this entry matters for the repo

Most of `evidence/` so far is shaped around AI doing a thing a human would have done slower. This entry is a different shape: AI noticed a gap a human would not have noticed because the gap was invisible from outside. The harness's discipline (verify before asserting, memory architecture, multi-window operational reality) made the noticing automatic. The artifact is the noticing, not the doing.
