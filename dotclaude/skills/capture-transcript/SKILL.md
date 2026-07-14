---
name: capture-transcript
description: "Ingest a pasted meeting/standup/1:1 transcript (INBOUND) and route it to the right capture: a scannable action breakdown for an ephemeral standup, or a durable memory file plus recall bead plus index row for a sync or 1:1, cross-linking the capture to related memories and tracked bead clusters. The inbound complement to the slack plugin /standup command (which GENERATES an outbound standup from the user's own activity). Use when the user says 'capture this standup', 'break down this transcript', 'capture this sync', 'capture this 1:1', 'here is the transcript', or pastes a standup/sync/1:1 transcript with capture intent. Distinct from /standup (outbound), /handoff (cold-start prompt), /bead-forge checkpoint (in-flight analysis), and bd remember (single fact)."
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

- **Generating Michael's own standup from his activity.** Use `/standup-prep` (git/PR/Jira/beads source) or the slack plugin `/standup` (Slack-messages source). Those are outbound generation; this is inbound capture.
- **A cold-start prompt for the next session.** Use `/handoff`.
- **Capturing in-flight analysis or design decisions against compaction.** Use `/bead-forge` checkpoint mode. This skill is for meeting transcripts, not conversation state.
- **A single fact.** Use `bd remember`.

## Workflow

### STEP 0: Locate the transcript (both caller paths)

- **Interactive human, no transcript in context**: ask once, "Paste the transcript." Do not proceed without it.
- **Non-interactive agent caller, no transcript in args**: use the most recent pasted transcript already in conversation context. Do not block.
- **Streamed in chunks (live/in-progress meeting fed across turns)**: the user pastes the transcript in pieces ("continuation", "not done yet", "last chunk"). Do NOT re-run the full capture per chunk. Append each chunk verbatim under `## Raw transcript`, keep ONE `PARTIAL` banner at the top, and let analysis sections accrue per segment as decisions land (dated subsections, e.g. "## Convergence (HH:MM)"). Defer finalization to the closing chunk: flip the banner to complete, drop `PARTIAL` from the bead title + index row, REFRESH the recall bead description from its chunk-1 opening-only text to the converged final state (the streaming description goes stale otherwise; if the meeting maps to a tracked epic/bead, also comment the outcomes there), and append to `log.md` once. For streaming captures, DEFER the `perl` en-dash strip to the closing chunk (run it once at finalization), do NOT strip after each chunk: `perl -i` mutates the file outside the Edit tool's read-tracking, so a per-chunk strip forces a redundant Read before the next chunk's Edit (~1 wasted Read per chunk over a long meeting). Intermediate chunks stay safe regardless: the `block-em-dash` hook auto-replaces U+2014 on each prose write, and U+2013 is cosmetic until the file is displayed (it never is mid-stream). Only U+2013 accumulates, and the single finalization strip clears it. Fallback: if any intermediate chunk Edit is ever hard-blocked on a dash, strip that one chunk and continue.
- **Truncated paste (one complete transcript cut at the 50k paste limit)**: a paste ends mid-line with a harness marker like "[Message truncated - exceeded 50,000 character limit]", or ends abruptly mid-sentence. Do NOT assume it is complete. Capture what is present (do not block on the full transcript), note in the file that it is truncated pending the remainder, finalize what you have, and THEN ask the user for the rest: the user often does not realize the paste was cut off, so do not wait silently for a follow-up that may never come. (A non-interactive agent caller cannot ask, so it notes the truncation and proceeds.) When the remainder does arrive, it may come as a second `/capture-transcript` (often labeled "second part" / "cut off from the 50k limit"); treat it as a continuation of the SAME capture, never a fresh invocation: do NOT create a second file, bead, `log.md` entry, or index row. Since you finalized the first segment, the remainder is the post-finalization case: Read the existing file with the Read tool first to satisfy the edit-guard, but a default Read of a LARGE capture file truncates at the token cap (~25k tokens) and a truncated Read does NOT satisfy the guard: the first Edit then bounces with "File has not been read yet". Read the specific target region (offset/limit around your edit anchor) so the Read actually covers the lines you will edit. This applies to ANY append to an existing large capture (a requested delta-append, not only the truncated-paste remainder). Append the remainder as a new segment under `## Raw transcript` (label the parts, e.g. "Segment 1 (truncated at paste limit)", "Segment 2 (continuation)"), refresh only the analysis sections and the recall bead description the new content changes, drop the truncation note, then re-run the `perl` dash-strip as the last write. If the remainder happens to arrive BEFORE you finalized, merge both into one capture instead. The 2026-06-12 and 2026-06-25 office-hours captures both hit this.

### STEP 1: Classify into one TYPE

Auto-detect from content; a stated type hint always overrides detection.

- **STANDUP**: team round-robin status (several people, quick updates, a TL or PM running it). Example: a Jesup standup.
- **SYNC / ORG MEETING**: broad org, strategy, or all-hands (senior voices, announcements, strategy). Example: a bi-weekly Product-Eng sync.
- **ONE-ON-ONE (1:1)**: two people, candid, often org or people content. Example: an ad-hoc 1:1.

A standup that holds a named decision, an owned open question, or a strategy/direction statement is durable content even though its form is a standup: route it through STEP 3B regardless of the STANDUP label (the 2026-05-11 <Service> standup is the precedent; it lives in `memory/` and is indexed in `meetings/README.md`). If ambiguous: state the inferred type and proceed. An interactive human may get a one-line confirm; an agent caller infers and proceeds. Never block on classification.

### STEP 2: Identity and style discipline (before writing anything)

- **Resolve every name and title against `memory/org-context.md` (the source of truth).** Transcripts garble names, and senior execs plus non-English-origin names are the highest-frequency garble points (e.g. a teammate appearing as a teammate/Haim/Jaime; Yath appearing as "Jaap"). See `bd memories correction:identity:transcript-name-disambiguation`. **Searching past a garble**: grepping the garbled spelling alone is the trap - it returns no hit even when the person IS in org-context under their real name (2026-06-23: grepped "Jaylene"/"Tyson", missed existing entries "Jailine Rodriguez" and "Thaisa Morgan"). Before marking a name tentative or "not in org-context", search by ROLE, TEAM, or ADJACENT PERSON (e.g. grep `recruiter`, the team name, or the PM who sits near them), and scan same-day sibling capture files (a name added by another capture earlier today will not be in your mental model). Only mark tentative after the role/team/adjacent search also comes up empty. If a name will not resolve, mark it tentative (e.g. `[unverified: "Jaap"?]`); never invent one. Do not embed the org chart here; org-context.md owns it and drifts.
- **Feed org deltas back (org-context is the source of truth, not just a lookup).** While resolving names, note any org-structure fact the transcript reveals that is new or changed vs `org-context.md`: a new person, promotion, role/title change, departure, or team move. Surface these in the chat deliverable (STEP 4) as a proposed `org-context.md` update naming the section, since stale org-context reintroduces the name-garble problem future captures fight. Propose, do not auto-write; the user adjudicates the org-context edit.
- **Gender-neutral always.** Name-first or singular they. Never infer pronouns from a name and never inherit pronouns from the transcript text.
- **One-man-army resourcing.** When framing action items, never assume added, SME, or extra engineering resourcing is available. See `bd memories feedback:resourcing:one-man-army`.
- **No fabrication.** Capture only facts present in the transcript. Do not invent decisions, owners, dates, or a person's role/title/team. A role inferred from surrounding context (e.g. assuming someone discussed in an engineering promo-cycle thread is an engineer) is a fabrication: attribute a role/title/team only when the transcript states it or `org-context.md` confirms it, otherwise mark it tentative or omit it. See `bd memories correction:verification:transcript-role-inference`.

### STEP 3: Route by type

#### A) STANDUP -> scannable action-item breakdown (ephemeral by default)

The default deliverable is a breakdown for Michael in chat, NOT a durable file (standups are usually ephemeral). Exception worth offering proactively: a recurring TEAM standup carrying multiple distinct cross-team threads (different owners, different workstreams) leans durable even without one hard decision, because the threads collectively are worth eyes-on. For Michael's own team standup (Jesup; captured durably most days), proactively offer the full durable capture (STEP 3B) on a harness-visibility basis, not just the chat breakdown, and name visibility as a valid trigger alongside decision content. The user still confirms; do not auto-write.

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
   bd create --type=task --priority=3 --labels=memory --title="[memory] <readable-type> YYYY-MM-DD (<who/topic>)" --description="<summary + pointer to memory/<topic-slug>-YYYY-MM-DD.md>"
   ```
   `<readable-type>` is a human label ("Product-Eng sync", "standup"), not the STEP 1 enum.
3. **Append to `log.md`** (the temporal index): `python3 ~/.claude/skills/bead-forge/log-append.py <id>`. Best-effort; it exits 0 on failure.
4. **Add an index row** to `memory/meetings/README.md`, newest-first at the top of the table. Row format: `| YYYY-MM-DD | <Topic> | [file](../<topic-slug>-YYYY-MM-DD.md) | <one-line with bead id appended> |`. The one-line cell MUST be under 150 chars (200 hard cap, `lint-memory.py`); the bead id goes at the END of that cell, not a separate column.
5. **If the meeting refines or decides on an existing tracked work cluster (a Jira epic and/or a beads epic + children), cross-link the cluster.** The recall bead + meetings index alone are NOT enough: a future cold-start agent who picks up a child bead from `bd ready`, or runs `bd memories`, will not reach this capture (the failure that forced repeated re-prompting on 2026-06-26 for the MX2-NNNNN harness cluster). Do all of:
   - **Always-loaded anchor (highest leverage, do this first):** create or update a `reference:<cluster-slug>` beads memory (`bd remember --key="reference:<slug>" "..."`) naming the Jira epic key + the beads epic + its child beads + the capture file + the recall bead + the locked and open decisions. Beads memories are injected at session start, so this is the one surface that survives a cold start; `bd search` does NOT reliably tokenize hyphenated Jira keys (e.g. `MX2-NNNNN`), so the memory, not search, is the load-bearing path.
   - **Cluster bead pointers:** `bd comment` the parent epic AND each related child bead with the capture file + recall bead + the `reference:` memory key + that bead's specific delta from the meeting. Child beads are the most common cold-start entry point and must point back to the capture.
   - **Top-index row (cluster anchors only):** if the cluster is a significant ongoing initiative a cold-start agent would seek from the top index, add ONE pointer row (not content) to `MEMORY.md` under the relevant domain section. Skip for routine captures: the meetings sub-index row is enough, and a row per meeting bloats `MEMORY.md`.
   - **Sensitivity:** if the STEP 3C gate fired, the anchor memory and all bead comments carry ONLY non-sensitive work content and reference the private file by name (beads sync via Dolt).

#### C) ONE-ON-ONE (1:1) -> durable capture

1. **Write the file** `memory/1on1-YYYY-MM-DD-<name>.md` (in `memory/` ROOT, not `memory/1on1s/`). Frontmatter as in B, with `metadata.type: 1on1-capture`.
2. **Sensitivity gate.** Set `metadata.sensitivity: private` AND add a header note ("PRIVATE. Do not surface in shared beads, Slack, or PR/Jira.") if the 1:1 hits any of: a named person plus a negative evaluation ("X is not ready", "X is struggling"); career-level, performance, or compensation content; or org-politics content naming specific individuals. Anything else defaults to non-private. The candid content stays in the LOCAL FILE ONLY.
3. Body sections: context and framing; the substantive work content (technical points, decisions, action items as a clear list); and, if private, the org/people read under a clearly labeled section.
4. **Create the recall bead** (with `--labels=memory`) and the `log.md` append, exactly as in B. The recall bead and any work-tracking bead carry ONLY non-sensitive work content and cross-reference the private file by name. If the sensitivity gate fired, the bead title uses a generic label ("[memory] 1:1 YYYY-MM-DD") WITHOUT the person's name, since bead descriptions sync via Dolt across accounts; the file reference inside the description is fine. If the 1:1 maps to a tracked work cluster, apply B step 5 cross-linking too, sensitivity-gated: the anchor memory and bead comments carry non-sensitive work content only.
5. **Add an index row** to `memory/1on1s/README.md`, newest-first. Row format: `| YYYY-MM-DD | <Name> | [1on1-YYYY-MM-DD-<name>.md](../1on1-YYYY-MM-DD-<name>.md) | <one-line> |`. Note the second column header is `With`, not `Topic`. A private one says "PRIVATE" plus a terse non-sensitive hook and the bead id; same under-150-char rule.

### STEP 4: Deliverable and gate

- Present the breakdown or summary in chat: action items for a standup; a tight summary plus a "what was captured" line for a sync or 1:1.
- Writing the capture artifacts (file plus bead plus log entry plus index row) is the requested action of the skill for SYNC and 1:1, so write them. For a 1:1 where the sensitivity gate fired, state in the chat summary that candid content was kept local (PRIVATE) so the user knows where it lives.
- **Inline any extracted IDs** (PR numbers, ticket keys, bead ids) in the chat summary as a code block. Michael copy-pastes from chat; do not bury IDs in the file only.
- **If B step 5 fired** (cluster cross-link), state in the chat summary which surfaces were linked: the `reference:` memory key, the beads commented, and any MEMORY.md row. This is the proof the capture is findable from a cold start.

### STEP 5: Index hygiene

- Keep every sub-index row under 150 chars (200 hard cap, `lint-memory.py`). The same em-dash and en-dash ban applies to the README rows you write; index rows are the highest-frequency slip surface. Before drafting the one-line cell, measure the actual prefix: `echo -n "| YYYY-MM-DD | Topic | [file](../slug.md) | " | wc -c` (substitute real values). Budget for the one-line = 200 minus that count minus 2 (closing ` |`). File slug length varies (28-46 chars typical), so the prefix spans 72-95 chars and the old "~110" guideline is unsafe for longer slugs. Safe default: keep the one-line cell under 100 chars; that fits every typical prefix with room to spare.
- Read the index README with the **Read tool** before the index-row Edit. The prefix-measure above uses `echo`/`wc -c`, and it is tempting to also `head`/`cat` the README to eyeball sibling rows, but bash reads do NOT satisfy the harness Read-before-Edit guard: the first `Edit` then bounces with "File has not been read yet". (Distinct from the post-strip "File has been modified since read" case in Hard constraints, which is about re-reading after `perl -i`; this is about Read-tool-ing the index in the first place.)
- The index holds a one-line only; depth goes in the capture file.
- Never put capture CONTENT in MEMORY.md or a README; those are indexes, not stores. A one-line POINTER row to a cluster-anchor capture (B step 5) is the only exception, and only for significant ongoing initiatives, never routine captures.

## Distinctions

| Vs | Difference |
|---|---|
| slack plugin `/standup` | Outbound generation from Michael's OWN Slack activity. This skill is inbound capture of someone else's transcript. |
| `/standup-prep` | Outbound generation of Michael's own status from his git/PR/Jira/beads activity (the spoken talk-track he brings to a standup). This skill is inbound capture of a pasted transcript. Complementary halves of a meeting: prep-before vs capture-after. |
| `/handoff` | Cold-start prompt for the NEXT session. This skill captures a meeting that already happened. |
| `/bead-forge checkpoint` | Preserves in-flight conversation analysis against compaction. This skill captures a meeting transcript. |
| `bd remember` | Stores a single fact. This skill produces a structured breakdown or a durable file plus recall bead plus log entry plus index row. |

## Anti-patterns

- Capturing a standup to a durable file by default (standups are ephemeral; durable only on decision content or request).
- Misrouting a decision-bearing standup to ephemeral output because its form is a standup (escalate to STEP 3B).
- Putting candid 1:1 people-content (or the person's name in a sensitive bead title) anywhere outside the local file.
- Index rows over the 150-char length limit, or a one-line that duplicates the file's depth.
- Writing a 1:1 or sync file into a subdir (`memory/1on1s/`, `memory/meetings/`) instead of `memory/` ROOT, which breaks the `../` index links.
- Capturing a decision that maps to a tracked bead/epic cluster without cross-linking it (B step 5): an orphaned capture that the recall bead + meetings index alone do NOT surface on a cold start. The `reference:` anchor memory + cluster bead pointers are the fix.

## Hard constraints

- For a 1:1, candid or sensitive people-content NEVER leaves the local `memory/` file. The recall bead and any work bead carry non-sensitive work content only, cross-reference the private file by name, and use a name-free title when the sensitivity gate fired (beads sync via Dolt).
- Resolve every name and title against `memory/org-context.md` before writing. Mark unresolved names tentative; never fabricate names, decisions, owners, dates, or a person's role/title/team not present in the transcript (a role inferred from surrounding context is a fabrication).
- No em-dashes (U+2014) or en-dashes (U+2013) anywhere in chat output, capture files, or index rows. Use hyphens, colons, or parentheses. The `block-em-dash` hook enforces only the U+2014 (em-dash) ban; the U+2013 (en-dash) strip is this skill's own responsibility via the perl one-liner below. The `## Raw transcript` section is the guaranteed trip point: pasted Zoom/Otter transcripts carry these dashes, so verbatim reproduction will block on the `block-em-dash` hook. After writing any capture file, run `perl -CSD -i -pe 's/\x{2014}/-/g; s/\x{2013}/-/g' <file>` to strip both in one pass, then continue. Run this strip as the LAST write to a given file in the current edit batch: `perl -i` mutates the file outside the Edit tool's read-tracking, so any subsequent Edit to that same file fails with "File has been modified since read" and forces a re-read. If new information arrives later (a name resolves, a fact lands) and you must edit a file you already stripped, re-read it first, then re-strip after.
- Gender-neutral always: name-first or singular they; never infer pronouns from a name or inherit them from the transcript.
