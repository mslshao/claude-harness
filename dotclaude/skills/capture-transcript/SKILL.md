---
name: capture-transcript
description: "Ingest a pasted meeting/standup/1:1 transcript (INBOUND) and route it to the right capture: a scannable action breakdown for an ephemeral standup, or a durable memory file plus index row for a sync or 1:1, cross-linking the capture to related memories and tracked work clusters. The inbound complement to the slack plugin /standup command (which GENERATES an outbound standup from the user's own activity). Use when the user says 'capture this standup', 'break down this transcript', 'capture this sync', 'capture this 1:1', 'here is the transcript', or pastes a standup/sync/1:1 transcript with capture intent. Distinct from /standup (outbound), /handoff (cold-start prompt), a project-type memory topic file (in-flight analysis), and a direct memory-topic-file write (single fact)."
argument-hint: "[standup | sync | 1:1]"
---

# Capture Transcript

Ingest a pasted meeting, standup, or 1:1 transcript and route it to the correct capture: a scannable action-item breakdown for an ephemeral standup, or a durable `memory/` file plus index row for a sync or 1:1. This is the INBOUND complement to the slack plugin's `/standup` command, which generates an OUTBOUND standup from Michael's own activity. This skill consumes someone else's transcript; it does not author Michael's status.

## Why this exists

Pasted transcripts are high-value and high-loss. They carry org signals, decisions, and action items, but they arrive garbled (names mangled by transcription) and ephemeral (lost to compaction unless captured). This machine's memory has exact conventions for where each kind of capture lands: standups are usually ephemeral and want a fast action breakdown; syncs and 1:1s want a durable `memory/` file and a `MEMORY.md` index row. Without a skill, each capture re-derives those conventions and slips on the identity, sensitivity, and length disciplines. This skill encodes them once, for this machine (`~/.claude/rules/environment.md`, "Skill gather steps on this machine").

## When to invoke

- The user types `/capture-transcript` (optionally with a `standup | sync | 1:1` hint) and a transcript is present.
- The user says "capture this standup", "break down this transcript", "capture this sync", "capture this 1:1", or "here is the transcript".
- A standup, sync, or 1:1 transcript is pasted into the conversation alongside any of those capture phrases.

## When NOT to use

- **Generating Michael's own standup from his activity.** Use `/standup-prep` (git/PR source) or the slack plugin `/standup` (Slack-messages source). Those are outbound generation; this is inbound capture.
- **A cold-start prompt for the next session.** Use `/handoff`.
- **Capturing in-flight analysis or design decisions against compaction.** Write a `project`-type topic file under `~/.claude/memory/` with an index row. This skill is for meeting transcripts, not conversation state.
- **A single fact.** Write it directly to a memory topic file.

## Workflow

### STEP 0: Locate the transcript (both caller paths)

- **Interactive human, no transcript in context**: ask once, "Paste the transcript." Do not proceed without it.
- **Non-interactive agent caller, no transcript in args**: use the most recent pasted transcript already in conversation context. Do not block.
- **Streamed in chunks (live/in-progress meeting fed across turns)**: the user pastes the transcript in pieces ("continuation", "not done yet", "last chunk"). Do NOT re-run the full capture per chunk. Append each chunk verbatim under `## Raw transcript`, keep ONE `PARTIAL` banner at the top, and let analysis sections accrue per segment as decisions land (dated subsections, e.g. "## Convergence (HH:MM)"). Defer finalization to the closing chunk: flip the banner to complete, drop `PARTIAL` from the file's title and index row, REFRESH the file's description from its chunk-1 opening-only text to the converged final state (the streaming description goes stale otherwise; if the meeting maps to a tracked epic, also note the outcomes in the `reference:` anchor memory). Every chunk is written with the Edit tool, so `block-em-dash.py` rewrites both U+2014 and U+2013 on that same write; there is no separate strip pass to defer or schedule.
  A write boundary that excludes the anchor file skips that anchor note too, as in B step 3.
- **Truncated paste (one complete transcript cut at the 50k paste limit)**: a paste ends mid-line with a harness marker like "[Message truncated - exceeded 50,000 character limit]", or ends abruptly mid-sentence. Do NOT assume it is complete. Capture what is present (do not block on the full transcript), note in the file that it is truncated pending the remainder, finalize what you have, and THEN ask the user for the rest: the user often does not realize the paste was cut off, so do not wait silently for a follow-up that may never come. (A non-interactive agent caller cannot ask, so it notes the truncation and proceeds.) When the remainder does arrive, it may come as a second `/capture-transcript` (often labeled "second part" / "cut off from the 50k limit"); treat it as a continuation of the SAME capture, never a fresh invocation: do NOT create a second file or index row. Since you finalized the first segment, the remainder is the post-finalization case: Read the existing file with the Read tool first to satisfy the edit-guard, but a default Read of a LARGE capture file truncates at the token cap (~25k tokens) and a truncated Read does NOT satisfy the guard: the first Edit then bounces with "File has not been read yet". Read the specific target region (offset/limit around your edit anchor) so the Read actually covers the lines you will edit. This applies to ANY append to an existing large capture (a requested delta-append, not only the truncated-paste remainder). Append the remainder as a new segment under `## Raw transcript` (label the parts, e.g. "Segment 1 (truncated at paste limit)", "Segment 2 (continuation)"), refresh only the analysis sections and the file's description the new content changes, and drop the truncation note; the Edit tool's own dash rewrite covers this write like any other. If the remainder happens to arrive BEFORE you finalized, merge both into one capture instead.

- **A source file on disk that can change under you (a Cowork capture, a transcript saved under `scratch/`)**: take its sha256 at the start. Compare it with the hash a brief names, or, on a continuation, the hash the existing capture file names. Take it again just before the write in STEP 3. A live meeting's capture keeps growing, and a Cowork edit can land between the read and the write. Where the hashes differ, re-read the changed part before writing. Then name both hashes with the time of each in the capture file and in the chat summary or RESULT, so a reader knows which version the capture reflects.

### STEP 1: Classify into one TYPE

Auto-detect from content; a stated type hint always overrides detection.

- **STANDUP**: team round-robin status (several people, quick updates, a TL or PM running it). Example: a Jesup standup.
- **SYNC / ORG MEETING**: broad org, strategy, or all-hands (senior voices, announcements, strategy). Example: a bi-weekly Product-Eng sync.
- **ONE-ON-ONE (1:1)**: two people, candid, often org or people content. Example: an ad-hoc 1:1.

A standup that holds a named decision, an owned open question, or a strategy/direction statement is durable content even though its form is a standup: route it through STEP 3B regardless of the STANDUP label (`eng-standup-2026-09-17-build-order.md` is the precedent; it lives in `memory/` and is indexed in `meetings-index.md`). If ambiguous: state the inferred type and proceed. An interactive human may get a one-line confirm; an agent caller infers and proceeds. Never block on classification.

### STEP 2: Identity and style discipline (before writing anything)

- **Resolve every name and title by grepping `~/.claude/memory/`, the source of truth on this machine.** Transcripts garble names, and senior execs plus non-English-origin names are the highest-frequency garble points (one teammate's first name can surface as three different spellings within a single transcript, and a short surname can be transcribed as an unrelated word). **Searching past a garble**: grepping the garbled spelling alone is the trap - it returns no hit even when the person is named elsewhere in memory under their real name. Before marking a name tentative, search by ROLE, TEAM, or ADJACENT PERSON (e.g. grep the team name, or the PM who sits near them), and scan same-day sibling capture files under `memory/sync-YYYY-MM-DD-*.md` and `memory/eng-standup-YYYY-MM-DD-*.md` (a name added by another capture earlier today will not be in your mental model). Only mark tentative after the role/team/adjacent search also comes up empty. If a name will not resolve, mark it tentative (e.g. `[unverified: "<garbled spelling>"?]`); never invent one. Known handles are recorded verbatim in `sdlc-orchestration-project.md`'s "People, GitHub handles" line; a handle not there is asked for, not constructed.
- **Feed org deltas back into the record they belong to.** While resolving names, note any org-structure fact the transcript reveals that is new or changed: a new person, promotion, role/title change, departure, or team move. Surface these in the chat deliverable (STEP 4) as a proposed addition to the memory record that already tracks that fact (the "People, GitHub handles" line, or a new fact worth its own line), since a name resolved once and never written down reintroduces the same garble next time. Propose, do not auto-write; the user adjudicates the edit.
- **Gender-neutral always.** Name-first or singular they. Never infer pronouns from a name and never inherit pronouns from the transcript text.
- **One-man-army resourcing.** When framing action items, never assume added, SME, or extra engineering resourcing is available.
- **No fabrication.** Capture only facts present in the transcript. Do not invent decisions, owners, dates, or a person's role/title/team. A role inferred from surrounding context (e.g. assuming someone discussed in an engineering promo-cycle thread is an engineer) is a fabrication: attribute a role/title/team only when the transcript states it or an existing memory record confirms it, otherwise mark it tentative or omit it.

### STEP 3: Route by type

#### A) STANDUP -> scannable action-item breakdown (ephemeral by default)

The default deliverable is a breakdown for Michael in chat, NOT a durable file (standups are usually ephemeral). Exception worth offering proactively: a recurring TEAM standup carrying multiple distinct cross-team threads (different owners, different workstreams) leans durable even without one hard decision, because the threads collectively are worth eyes-on. For Michael's own team standup (Jesup; captured durably most days), proactively offer the full durable capture (STEP 3B) on a harness-visibility basis, not just the chat breakdown, and name visibility as a valid trigger alongside decision content. The user still confirms; do not auto-write.

1. Lead with **Michael's own action items**, highest-impact first, deadlines flagged.
2. Then a brief **team-FYI** section (what others reported that touches his work).
3. Optionally ground one item with its real PR or ticket via a lightweight lookup (one `gh` call) when that makes the item concrete. Offer this; do not force a broad fan-out.
4. Durable capture decision:
   - **Interactive human**: offer a durable capture and write only on confirmation, OR write without asking if the standup held a decision worth preserving (STEP 1).
   - **Non-interactive agent caller**: write a durable capture (via STEP 3B) if and only if the standup contains a decision, commitment, or org signal worth preserving; otherwise produce the chat breakdown only and write no file.
   - A durable standup follows STEP 3B exactly, filed as `eng-standup-YYYY-MM-DD-<slug>.md` and indexed in `meetings-index.md` (standups are not a separate directory or a separate index).

#### B) SYNC / ORG MEETING -> durable capture

1. **Write the file** `memory/sync-YYYY-MM-DD-<slug>.md` (point-in-time snapshot, in `memory/` ROOT, not a subdir; use the actual current date; `<slug>` after the date, matching `sync-2026-09-24-booking-flow-task-breakdown.md` and its siblings). A durable standup uses the `eng-standup-YYYY-MM-DD-<slug>.md` prefix instead (`eng-standup-2026-09-17-build-order.md` is the precedent). Frontmatter (match an existing capture for the live shape):
   ```
   ---
   name: sync-YYYY-MM-DD-<slug>
   description: "<one-line used for recall>."
   metadata:
     node_type: memory
     type: project
   ---
   ```
   Use `type: project` (the auto-memory taxonomy this machine runs: `user`, `feedback`, `project`, `reference`; there is no `meeting-capture` type here). `node_type: memory` goes first under `metadata`, as in `sync-2026-09-28-sprint-planning.md` and its two same-day siblings. `originSessionId` and any `modified` stamp are appended automatically by the harness; do not author them.

   Body sections in order: a "Why it matters for MShao" section (signals relevant to Michael's work), org/strategy context, adjacent-team FYI, any action surfaced (self-assessed against his actual scope), then the transcript under a "## Raw transcript" heading. If the source is a Cowork capture, point at it and read it in place instead of copying it. Per `~/.claude/rules/usage.md` rule 8, the capture and the fleet's own analysis of it stay on this box: never Notion, Slack, a repository, or another person.
2. **Add an index row** to `~/.claude/memory/meetings-index.md`'s table, newest at the bottom. Row format: `| Meetings | [sync-YYYY-MM-DD-<slug>.md](sync-YYYY-MM-DD-<slug>.md) | <one-line> |`. Every capture type (sync, standup, 1:1) indexes in this one table; there is no separate sub-index for any of them.

   Aim for the one-line cell near 300 bytes. `~/.claude/scratch/scripts/index-check.py` prints, but does not fail on, any full row over 400 bytes. It fails only on the whole file's 25 KB / 200-line caps, so a long cell is a nudge, not a hard block. Run it on `~/.claude/memory/meetings-index.md` and quote its output.
3. **If the meeting refines or decides on an existing tracked work cluster, cross-link the cluster.** The Meetings rows alone may not be enough: a future cold-start agent working the cluster from `open-chores.md` will not automatically reach this capture. Do all of:
   - **Always-loaded anchor (highest leverage, do this first):** create or update a `reference:<cluster-slug>` topic file under `~/.claude/memory/` (with its `MEMORY.md` index row added in the same turn) naming the cluster + the capture file + the locked and open decisions. `MEMORY.md` loads at session start, so this is the one surface that survives a cold start.
     Optional when the caller's brief sets a write boundary that excludes the anchor file. Then skip it. Name the anchor you would have written, with its locked and open decisions, in the RESULT as a follow-up for whoever owns that file.
   - **Top-index row (cluster anchors only):** if the cluster is a significant ongoing initiative a cold-start agent would seek from the top index, add ONE pointer row (not content) to `MEMORY.md` under the relevant domain section. Skip for routine captures: the Meetings row is enough, and a row per meeting bloats `MEMORY.md` (the 2026-09-25 index cut exists because of exactly this).
   - **Sensitivity:** if the STEP 3C gate fired, the anchor memory carries ONLY non-sensitive work content and references the private file by name.

#### C) ONE-ON-ONE (1:1) -> durable capture

1. **Write the file** `memory/1on1-YYYY-MM-DD-<name>.md` (in `memory/` ROOT; there is no `memory/1on1s/` subdir on this machine). Frontmatter as in B, with `metadata.type: project` or `metadata.type: feedback` (whichever the auto-memory taxonomy's own test picks: content that is mostly work substance is `project`; content that is mostly a correction or a read on how to work with someone is `feedback`; `1on1-2026-09-16-<name>.md` and `1on1-2026-09-17-<name>.md` are the two precedents, one of each).
2. **Sensitivity gate.** If the 1:1 hits any of: a named person plus a negative evaluation ("X is not ready", "X is struggling"); career-level, performance, or compensation content; or org-politics content naming specific individuals, keep that content out of the file this skill writes and out of its index row. Say so in the file itself: "candid content kept local", or "candid content stays with the Cowork capture, not copied here". This machine has no `metadata.sensitivity` field in live use. The gate is what the file and the row say, not a flag, on top of the blanket rule that every capture, sensitive or not, stays off Notion, Slack, a repository and any other person (`~/.claude/rules/usage.md` rule 8). Anything that clears the gate is captured plainly.
3. Body sections: context and framing; the substantive work content (technical points, decisions, action items as a clear list); and, if private, the org/people read under a clearly labeled section, kept local per the gate above.
4. If the 1:1 maps to a tracked work cluster, apply B step 3 cross-linking too, sensitivity-gated: the anchor memory carries non-sensitive work content only.
5. **Add an index row** to `~/.claude/memory/meetings-index.md`'s table, the same table STEP 3B writes to. Row format: `| Meetings | [1on1-YYYY-MM-DD-<name>.md](1on1-YYYY-MM-DD-<name>.md) | <one-line> |`. A gated 1:1's one-line names that candid content was kept local, never the content itself; same near-300-byte aim as STEP 3B.

### STEP 4: Deliverable and gate

- Present the breakdown or summary in chat: action items for a standup; for a sync or 1:1, LEAD with the so-what (2-4 takeaways pulled from the file's "Why it matters for MShao" section: what the meeting means for Michael's work and any signal or decision to act on), THEN the tight summary and the "what was captured" line. For a meeting Michael attended or hosted, the takeaways are the deliverable he wants; a "what was captured" recap alone forces a follow-up "any takeaways?" (observed 2026-07-16, office-hours capture).
- Writing the capture artifacts (file plus index row) is the requested action of the skill for SYNC and 1:1, so write them. For a 1:1 where the sensitivity gate fired, state in the chat summary that candid content was kept local (PRIVATE) so the user knows where it lives.
- **Inline any extracted IDs** (PR numbers, ticket keys) in the chat summary as a code block. Michael copy-pastes from chat; do not bury IDs in the file only.
- **If B step 3 fired** (cluster cross-link), state in the chat summary which surfaces were linked: the `reference:` memory key and any MEMORY.md row. This is the proof the capture is findable from a cold start. An anchor skipped for a write boundary is named as skipped, with the boundary that excluded it.

### STEP 5: Index hygiene

- Aim for the one-line cell near 300 bytes; `~/.claude/scratch/scripts/index-check.py ~/.claude/memory/meetings-index.md` prints any full row over 400 bytes as a nudge (not a hard failure) and fails only on that file's own 25 KB / 200-line caps. The same em-dash and en-dash ban applies to the row you write, same as any other write into a `.md` under `~/.claude/`; the Write and Edit tool hooks catch both (STEP 2, and Hard constraints below).
- Read `~/.claude/memory/meetings-index.md` with the **Read tool** before the index-row Edit. A `head`/`cat`/`grep` of it to eyeball sibling rows does NOT satisfy the harness Read-before-Edit guard: the first `Edit` then bounces with "File has not been read yet".
- The index holds a one-line only; depth goes in the capture file.
- Never put capture CONTENT in MEMORY.md; it is an index, not a store. A one-line POINTER row to a cluster-anchor capture (B step 3) is the only exception, and only for significant ongoing initiatives, never routine captures.

## Distinctions

| Vs | Difference |
|---|---|
| slack plugin `/standup` | Outbound generation from Michael's OWN Slack activity. This skill is inbound capture of someone else's transcript. |
| `/standup-prep` | Outbound generation of Michael's own status from his git/PR activity (the spoken talk-track he brings to a standup). This skill is inbound capture of a pasted transcript. Complementary halves of a meeting: prep-before vs capture-after. |
| `/handoff` | Cold-start prompt for the NEXT session. This skill captures a meeting that already happened. |
| A `project`-type memory topic file | Preserves in-flight conversation analysis against compaction. This skill captures a meeting transcript. |
| Direct memory-file write | Stores a single fact. This skill produces a structured breakdown or a durable file plus index row. |

## Anti-patterns

- Capturing a standup to a durable file by default (standups are ephemeral; durable only on decision content or request).
- Misrouting a decision-bearing standup to ephemeral output because its form is a standup (escalate to STEP 3B).
- Putting candid 1:1 people-content (or the person's name in a sensitive capture-file title) anywhere outside the local file.
- An index row that bloats past the near-300-byte aim, or a one-line that duplicates the file's depth.
- Writing a 1:1 or sync file into a subdir instead of `memory/` ROOT (there is no `memory/1on1s/` or `memory/meetings/` on this machine; both existing and non-existing would break the flat-path links `MEMORY.md` uses).
- Stripping dashes by hand with a shell one-liner, `sed -i`, or any other write into a `.md` under `~/.claude/` outside the Write or Edit tool: `block-md-redirect.py` refuses it outright, and the Write/Edit tool hooks already handle both dash characters (Hard constraints below).
- Capturing a decision that maps to a tracked work cluster without cross-linking it (B step 3): an orphaned capture that the meetings index alone does NOT surface on a cold start. The `reference:` anchor memory is the fix. Skipping the anchor silently is the same defect when a write boundary excluded it: name the skip (STEP 4).

## Hard constraints

- For a 1:1, candid or sensitive people-content NEVER leaves the local `memory/` file. Any work-tracking artifact created for it carries non-sensitive work content only, cross-references the private file by name, and uses a name-free title when the sensitivity gate fired.
- Resolve every name and title by grepping `~/.claude/memory/` before writing (STEP 2). Mark unresolved names tentative; never fabricate names, decisions, owners, dates, or a person's role/title/team not present in the transcript (a role inferred from surrounding context is a fabrication).
- No em-dashes (U+2014) or en-dashes (U+2013) anywhere in chat output, capture files, or index rows. Use hyphens, colons, or parentheses. Write the capture file and the index row with the **Write or Edit tool** only, never a shell redirect, heredoc, `sed -i`, or `cp` into a `.md` under `~/.claude/`: `block-md-redirect.py` refuses the shell write outright.

   On this machine `block-em-dash.py` runs on Edit, Write and MultiEdit. It rewrites both U+2014 and U+2013 on a prose file, so there is no separate dash-strip pass to run. The `## Raw transcript` section is still the highest-volume trip point, since pasted Zoom or Otter transcripts hold these dashes; the hook catches it on the same write.

   For a verbatim copy of the source needed outside the capture file, use a `.txt` under `~/.claude/scratch/` by shell redirect, never a `.md`. The redirect hook guards only `.md` files.
- Gender-neutral always: name-first or singular they; never infer pronouns from a name or inherit them from the transcript. The pronoun hook (`pre-write-pronoun.py`) blocks a write that raises the gendered-pronoun count on a markdown file under `~/.claude/`, so a slip is caught at write time, not just at review.
- Write inside the limits plain-check enforces: a sentence over 35 words fires LENGTH, three clauses joined by commas fire CHAIN, and `carry` in any form or `held` fires TELL.
- Run `python3 ~/.claude/scratch/scripts/plain-check.py <file>` and `python3 ~/.claude/scratch/scripts/pronoun-check.py <file>` on the capture file before the chat deliverable (STEP 4); quote both outputs in the RESULT for a non-interactive caller.
- This is a one-shot skill for a non-interactive agent caller: infer and proceed through STEP 0 to STEP 4 without a mid-run question (STEP 0 and STEP 1 already say this for their own cases; it is the rule for the skill as a whole).
