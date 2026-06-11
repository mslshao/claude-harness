---
name: capture-transcript
description: "Ingest a pasted meeting/standup/1:1 transcript (INBOUND) and route it to the right capture: a scannable action breakdown for an ephemeral standup, or a durable memory file plus recall bead plus index row for a sync or 1:1. The inbound complement to the slack plugin /standup command (which GENERATES an outbound standup from the user's own activity). Use when the user says 'capture this standup', 'break down this transcript', 'capture this sync', 'capture this 1:1', 'here is the transcript', or pastes a standup/sync/1:1 transcript with capture intent. Distinct from /standup (outbound), /handoff (cold-start prompt), /bead-forge checkpoint (in-flight analysis), and bd remember (single fact)."
argument-hint: "[standup | sync | 1:1]"
---

# Capture Transcript

Ingest a pasted meeting, standup, or 1:1 transcript and route it to the correct capture: a scannable action-item breakdown for an ephemeral standup, or a durable `memory/` file plus recall bead plus index row for a sync or 1:1. This is the INBOUND complement to the slack plugin's `/standup` command, which generates an OUTBOUND standup from Michael's own activity. This skill consumes someone else's transcript; it does not author Michael's status.

## Why this exists

Pasted transcripts are high-value and high-loss. They carry org signals, decisions, and action items, but they arrive garbled (names mangled by transcription) and ephemeral (lost to compaction unless captured). The two-tier memory architecture has exact conventions for where each kind of capture lands: standups are usually ephemeral and want a fast action breakdown; syncs and 1:1s want a durable `memory/` file, a recall bead, a `log.md` entry, and an index row under the length lint. Without a skill, each capture re-derives those conventions and slips on the identity, sensitivity, and length disciplines. This skill encodes them once.

## When to invoke

- The user types `/capture-transcript` (optionally with a `standup | sync | 1:1` hint) and a transcript is present.
- The user says "capture this standup", "break down this transcript", "capture this sync", "capture this 1:1", or "here is the transcript".
- A standup, sync, or 1:1 transcript is pasted into the conversation alongside any of those capture phrases.

## When NOT to use

- **Generating Michael's own standup from his activity.** Use the slack plugin `/standup`. That is outbound; this is inbound.
- **A cold-start prompt for the next session.** Use `/handoff`.
- **Capturing in-flight analysis or design decisions against compaction.** Use `/bead-forge` checkpoint mode. This skill is for meeting transcripts, not conversation state.
- **A single fact.** Use `bd remember`.

## Workflow

### STEP 0: Locate the transcript (both caller paths)

- **Interactive human, no transcript in context**: ask once, "Paste the transcript." Do not proceed without it.
- **Non-interactive agent caller, no transcript in args**: use the most recent pasted transcript already in conversation context. Do not block.
- **Streamed in chunks (live/in-progress meeting fed across turns)**: the user pastes the transcript in pieces ("continuation", "not done yet", "last chunk"). Do NOT re-run the full capture per chunk. Append each chunk verbatim under `## Raw transcript`, keep ONE `PARTIAL` banner at the top, and let analysis sections accrue per segment as decisions land (dated subsections, e.g. "## Convergence (HH:MM)"). Defer finalization to the closing chunk: flip the banner to complete, drop `PARTIAL` from the bead title + index row, and append to `log.md` once. The per-write dash-strip (Hard Constraints) still runs after each chunk, since pasted transcript is the guaranteed em/en-dash trip point.

### STEP 1: Classify into one TYPE

Auto-detect from content; a stated type hint always overrides detection.

- **STANDUP**: team round-robin status (several people, quick updates, a TL or PM running it). Example: a Jesup standup.
- **SYNC / ORG MEETING**: broad org, strategy, or all-hands (senior voices, announcements, strategy). Example: a bi-weekly Product-Eng sync.
- **ONE-ON-ONE (1:1)**: two people, candid, often org or people content. Example: an ad-hoc 1:1.

A standup that holds a named decision, an owned open question, or a strategy/direction statement is durable content even though its form is a standup: route it through STEP 3B regardless of the STANDUP label (the 2026-05-11 <service> standup is the precedent; it lives in `memory/` and is indexed in `meetings/README.md`). If ambiguous: state the inferred type and proceed. An interactive human may get a one-line confirm; an agent caller infers and proceeds. Never block on classification.

### STEP 2: Identity and style discipline (before writing anything)

- **Resolve every name and title against `memory/org-context.md` (the source of truth).** Transcripts garble names, and senior execs plus non-English-origin names are the highest-frequency garble points (one real name routinely transcribed as several different phonetic spellings across a single meeting). If a name will not resolve, mark it tentative (e.g. `[unverified: "<phonetic-guess>"?]`); never invent one. Do not embed the org chart here; org-context.md owns it and drifts.
- **Gender-neutral always.** Name-first or singular they. Never infer pronouns from a name and never inherit pronouns from the transcript text.
- **One-man-army resourcing.** When framing action items, never assume added, SME, or extra engineering resourcing is available. See `bd memories feedback:resourcing:one-man-army`.
- **No fabrication.** Capture only facts present in the transcript. Do not invent decisions, owners, or dates.

### STEP 3: Route by type

#### A) STANDUP -> scannable action-item breakdown (ephemeral by default)

The default deliverable is a breakdown for Michael in chat, NOT a durable file (standups are usually ephemeral).

1. Lead with **Michael's own action items**, highest-impact first, deadlines flagged.
2. Then a brief **team-FYI** section (what others reported that touches his work).
3. Optionally ground one item with its real PR or ticket via a lightweight lookup (one `gh` or Jira call) when that makes the item concrete. Offer this; do not force a broad fan-out.
4. Durable capture decision:
   - **Interactive human**: offer a durable capture and write only on confirmation, OR write without asking if the standup held a decision worth preserving (STEP 1).
   - **Non-interactive agent caller**: write a durable capture (via STEP 3B) if and only if the standup contains a decision, commitment, or org signal worth preserving; otherwise produce the chat breakdown only and write no file.
   - A durable standup follows STEP 3B exactly and is indexed in `meetings/README.md` (standups are not a separate directory).

#### B) SYNC / ORG MEETING -> durable capture

1. **Write the file** `memory/<topic-slug>-YYYY-MM-DD.md` (point-in-time snapshot, in `memory/` ROOT, not a subdir; use the actual current date). Frontmatter (match an existing capture for the live shape):
   ```
   ---
   name: <topic-slug>-YYYY-MM-DD
   description: "<one-line used for recall>. Bead <id>."
   metadata:
     node_type: memory
     type: meeting-capture
     date: YYYY-MM-DD
   ---
   ```
   `originSessionId` is appended automatically by the harness; do not author it. The description ends with the recall bead id once it exists (create the bead first, or update the description after), matching the existing capture files so the file<->bead link is bidirectional. Body sections in order: a "Why it matters for MShao" section (signals relevant to his work), org/strategy context, adjacent-team FYI, any action surfaced (self-assess against his actual scope), then the verbatim transcript under a "## Raw transcript" heading.
2. **Create the recall bead** (memory category = `type=task` plus the `memory` label):
   ```
   bd create --type=task --priority=3 --title="[memory] <readable-type> YYYY-MM-DD (<who/topic>)" --description="<summary + pointer to memory/<topic-slug>-YYYY-MM-DD.md>"
   bd label add <id> memory
   ```
   `<readable-type>` is a human label ("Product-Eng sync", "standup"), not the STEP 1 enum.
3. **Append to `log.md`** (the temporal index): `python3 ~/.claude/skills/bead-forge/log-append.py <id>`. Best-effort; it exits 0 on failure.
4. **Add an index row** to `memory/meetings/README.md`, newest-first at the top of the table. Row format: `| YYYY-MM-DD | <Topic> | [file](../<topic-slug>-YYYY-MM-DD.md) | <one-line with bead id appended> |`. The one-line cell MUST be under 150 chars (200 hard cap, `lint-memory.py`); the bead id goes at the END of that cell, not a separate column.

#### C) ONE-ON-ONE (1:1) -> durable capture

1. **Write the file** `memory/1on1-YYYY-MM-DD-<name>.md` (in `memory/` ROOT, not `memory/1on1s/`). Frontmatter as in B, with `metadata.type: 1on1-capture`.
2. **Sensitivity gate.** Set `metadata.sensitivity: private` AND add a header note ("PRIVATE. Do not surface in shared beads, Slack, or PR/Jira.") if the 1:1 hits any of: a named person plus a negative evaluation ("X is not ready", "X is struggling"); career-level, performance, or compensation content; or org-politics content naming specific individuals. Anything else defaults to non-private. The candid content stays in the LOCAL FILE ONLY.
3. Body sections: context and framing; the substantive work content (technical points, decisions, action items as a clear list); and, if private, the org/people read under a clearly labeled section.
4. **Create the recall bead** plus `bd label add <id> memory` and the `log.md` append, exactly as in B. The recall bead and any work-tracking bead carry ONLY non-sensitive work content and cross-reference the private file by name. If the sensitivity gate fired, the bead title uses a generic label ("[memory] 1:1 YYYY-MM-DD") WITHOUT the person's name, since bead descriptions sync via Dolt across accounts; the file reference inside the description is fine.
5. **Add an index row** to `memory/1on1s/README.md`, newest-first. Row format: `| YYYY-MM-DD | <Name> | [1on1-YYYY-MM-DD-<name>.md](../1on1-YYYY-MM-DD-<name>.md) | <one-line> |`. Note the second column header is `With`, not `Topic`. A private one says "PRIVATE" plus a terse non-sensitive hook and the bead id; same under-150-char rule.

### STEP 4: Deliverable and gate

- Present the breakdown or summary in chat: action items for a standup; a tight summary plus a "what was captured" line for a sync or 1:1.
- Writing the capture artifacts (file plus bead plus log entry plus index row) is the requested action of the skill for SYNC and 1:1, so write them. For a 1:1 where the sensitivity gate fired, state in the chat summary that candid content was kept local (PRIVATE) so the user knows where it lives.
- **Inline any extracted IDs** (PR numbers, ticket keys, bead ids) in the chat summary as a code block. Michael copy-pastes from chat; do not bury IDs in the file only.

### STEP 5: Index hygiene

- Keep every sub-index row under 150 chars (200 hard cap, `lint-memory.py`). The same em-dash and en-dash ban applies to the README rows you write; index rows are the highest-frequency slip surface. The file-link cell (`[name](../name.md)`) plus the date and With/Topic columns consume ~80 chars before the one-line even starts, so the 150 ideal is usually unreachable: aim to keep the one-line cell itself under ~110 chars and the whole row under the 200 hard cap on the first write (existing rows legitimately run 150-200).
- The index holds a one-line only; depth goes in the capture file.
- Never put capture content in MEMORY.md or in a README. Those are indexes, not stores.

## Distinctions

| Vs | Difference |
|---|---|
| slack plugin `/standup` | Outbound generation from Michael's OWN activity. This skill is inbound capture of someone else's transcript. |
| `/handoff` | Cold-start prompt for the NEXT session. This skill captures a meeting that already happened. |
| `/bead-forge checkpoint` | Preserves in-flight conversation analysis against compaction. This skill captures a meeting transcript. |
| `bd remember` | Stores a single fact. This skill produces a structured breakdown or a durable file plus recall bead plus log entry plus index row. |

## Anti-patterns

- Capturing a standup to a durable file by default (standups are ephemeral; durable only on decision content or request).
- Misrouting a decision-bearing standup to ephemeral output because its form is a standup (escalate to STEP 3B).
- Putting candid 1:1 people-content (or the person's name in a sensitive bead title) anywhere outside the local file.
- Index rows over the 150-char length limit, or a one-line that duplicates the file's depth.
- Writing a 1:1 or sync file into a subdir (`memory/1on1s/`, `memory/meetings/`) instead of `memory/` ROOT, which breaks the `../` index links.

## Hard constraints

- For a 1:1, candid or sensitive people-content NEVER leaves the local `memory/` file. The recall bead and any work bead carry non-sensitive work content only, cross-reference the private file by name, and use a name-free title when the sensitivity gate fired (beads sync via Dolt).
- Resolve every name and title against `memory/org-context.md` before writing. Mark unresolved names tentative; never fabricate names, decisions, owners, or dates not present in the transcript.
- No em-dashes (U+2014) or en-dashes (U+2013) anywhere in chat output, capture files, or index rows. Use hyphens, colons, or parentheses. The `block-em-dash` hook enforces only the U+2014 (em-dash) ban; the U+2013 (en-dash) strip is this skill's own responsibility via the perl one-liner below. The `## Raw transcript` section is the guaranteed trip point: pasted Zoom/Otter transcripts carry these dashes, so verbatim reproduction will block on the `block-em-dash` hook. After writing any capture file, run `perl -CSD -i -pe 's/\x{2014}/-/g; s/\x{2013}/-/g' <file>` to strip both in one pass, then continue.
- Gender-neutral always: name-first or singular they; never infer pronouns from a name or inherit them from the transcript.
