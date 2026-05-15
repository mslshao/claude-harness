# Two-Tier Memory Doctrine

The harness uses two distinct memory tiers with different storage, access patterns, and content shape. The split exists because every persistent fact would either bloat the prompt (if everything were a flash card) or sit unread (if everything were a topic file). Two tiers gives a working separation.

## Tier 1: Flash-card memories

Implementation in this author's setup: beads memory store (`bd remember --key=... "<fact>"`).

Properties:

- **Always loaded** at session start via startup hook.
- Short facts (1-3 sentences): gotchas, API config, tool quirks, voice preferences.
- Shared across sessions and (in the beads-backed implementation) across machines via Dolt-backed sync.
- Searched by keyword (`bd memories <keyword>`).
- Default for new facts; use this tier unless the item needs depth.

## Tier 2: Topic files

Implementation: markdown files in a memory directory (e.g., `~/.claude/projects/<project>/memory/`).

Properties:

- **On-demand**: read via the file-read tool when entering a domain.
- Detailed context: investigation logs, architecture notes, design rationale, review snapshots.
- Referenced by Tier 1 entries where applicable (a flash-card says "see topic file for depth").
- Indexed by a top-level `MEMORY.md` (the index, not a memory itself).

## No duplication between tiers

If a fact is a Tier 1 memory, do not repeat it in a Tier 2 topic file. Topic files add context and depth around Tier 1 memories, not copies.

## What goes in each tier

**Tier 1 (flash cards):**

- API quirks ("don't pass region_name= to boto3.client")
- Voice preferences ("no em-dashes in any output")
- Tool gotchas ("the X CLI requires --json flag in non-interactive shells")
- Identity facts ("user X is at company Y, role Z")
- Recurring corrections ("don't mock the database in integration tests")

**Tier 2 (topic files):**

- Architecture snapshots (system geography at a point in time)
- Investigation logs (root-cause analyses with citations)
- People hints (per-person feedback-reception notes for review work)
- 1:1 notes
- Org context snapshots (reporting lines, ownership)
- Multi-page reading material (skills documentation, learning resources)

## What does NOT go in either tier

Some content is ephemeral and belongs in scratch directories or session-local state, not persistent memory:

- In-progress work state (use a task tracker for this)
- Temporary investigation findings (use scratch files; promote to memory only when they prove durable)
- Current-session conversation context (the conversation IS this; persisting it duplicates)

## Dating convention

Topic files follow one of three dating patterns:

- **Point-in-time snapshots** (review activity, pre-milestone state captures): dated filename `<topic>-YYYY-MM-DD.md`, no updates. A later snapshot is a new file.
- **Living topic files** (org context, project state, evolving doctrine): add `last_modified: YYYY-MM-DD` to the frontmatter on each substantive edit. Do NOT bulk-backfill; apply forward the first time each file is edited.
- **Skill/agent/CLAUDE.md files**: no in-file date; version control history is the source of truth for when they were last edited.

## Override note

When the AI tool's own auto-memory system claims to be "the memory system" and the harness's two-tier architecture also claims to be the memory system, they coexist via this doctrine: the tool's auto-memory becomes Tier 1 (flash cards), the harness's topic-file convention becomes Tier 2 (depth). They are complements, not competitors.

## Why this exists

A single-tier "everything is a flash card" approach fails when facts have varying depths. A 3-paragraph investigation log does not fit in a 1-sentence flash card; cramming it produces unreadable flash cards. A single-tier "everything is a topic file" approach fails because nothing gets read at session start; the daily-needed facts sit in files the agent never opens.

Two tiers with disciplined splitting (flash cards for breadth, topic files for depth) get both behaviors at the cost of a routing decision when writing new memory.

## Where it has limits

- The doctrine requires the author to maintain the index (Tier 2's `MEMORY.md`). Stale indices defeat the on-demand pattern. The author must update the index when adding or removing topic files.
- Cross-machine sync for Tier 2 is harder than Tier 1 in many backends. The Dolt-backed beads setup syncs Tier 1 across machines automatically; topic files require manual or separate-tool sync.
