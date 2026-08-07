---
name: recall
description: "BFS-first cross-corpus search for information another session produced. Use when the user references past work without a current-session referent ('what we discussed about X', 'remind me about Y', 'the thing with Z', vague pronouns following a session gap, named entities not introduced this turn), AND at cold start when the user pastes a SESSION HANDOFF prompt (from /handoff): run with the handoff's 'Run /recall <seeds>' line, or derive 2-4 seeds from its CONTEXT section if it predates seed lines. Searches beads (titles via bd search, descriptions via a bd list | jq pass), memories (keys + values), and topic files in ~/.claude/projects/-workspaces-main/memory/. Returns ranked one-line previews with IDs and recency; agent DFSs into specific hits as needed. Consumer-side complement to the producer-side bd-recency-surface hook."
argument-hint: "<2-4 seeds: keywords, bead IDs, memory keys>"
---

# /recall

BFS-first discovery across all persistent artifacts. Returns one-line previews per hit; agent reads previews, decides what to dig into.

## When to use

Trigger when the user prompt suggests past-session work:

- "the thing with X" / "what we discussed about X" / "did we already X"
- "remind me about X" / "you mentioned X"
- Named entities (a person, project, ticket) referenced without current-session context
- Vague pronouns ("that bug", "the doc") with no in-session referent
- Cold-start sessions where the user assumes context that this session does not have
- A pasted SESSION HANDOFF prompt (produced by /handoff) at session start: use its
  "Run /recall <seeds>" line verbatim; if the handoff predates seed lines, derive
  2-4 seeds from its CONTEXT and IN-FLIGHT STATE sections. The handoff prose is
  lossy compression of the prior session; the recall pass surfaces the sibling
  beads, memories, and topic files it compressed away. Run it before substantive
  work, alongside the handoff's own first actions.

Do NOT trigger when:
- The query has a clear current-session referent (just answer from context)
- The user has provided a specific bead/memory/file path (just read it directly)
- The work is operational (use `bd ready`, `bd list`, etc.)

## Process

### Phase 1: Parse query into search seeds

Extract from the user's prompt:
- **Topic keywords**: free-text terms that might match bead titles, memory keys, topic file names.
- **Named entities**: people (a teammate's first name, last name, or GitHub handle), projects (dyn2red, <service>, folio), tickets (MX2-N), beads (docr-XXXX).
- **Time hints**: "yesterday", "last week", "earlier" suggest a time-narrowed window.

If the query is too vague to extract seeds, ask ONE clarifying question; otherwise proceed with the best-guess seed.

### Phase 2: Parallel BFS across artifact types

Run these in parallel where independent. All return BFS-shape output (ID/path + 1-line preview + recency), NOT full content:

1. **Memory keys + bridges** (via `bd_related.py`):
   ```bash
   python3 ~/.claude/scratch/scripts/memory-graph/bd_related.py "<seed>" --limit 10
   ```
   Returns: memory keys (matches + bridges + siblings + cousins), topic file paths.

   **Split underscore- and hyphen-joined seeds into space-separated tokens before calling.**
   The walker scores on whole word tokens, so an identifier-shaped seed silently returns
   `(no neighbors)` even when the corpus holds a directly relevant memory. Measured 2026-08-06:
   `require_full_window` returned nothing while `require full window` reached
   `gotcha:datadog-new-monitor-registration-lag`, and `MX2-NNNNN` returned nothing while the
   plain-word seeds in the same query worked. Pass BOTH forms when the seed is an identifier
   (a terraform attribute, metric name, ticket key, function name, env var). This is the same
   whole-token matching behaviour documented for `search_datadog_monitors` in
   `memory/datadog-query-gotchas.md` Gotcha 9.

   A genuine `(no neighbors)` is still possible and is not a failure: `clamp` returns nothing in
   both forms because no memory keys on it. Treat an empty result as "not in the graph", not as
   "the walker is broken", but only after trying the split form. Never let an empty walker result
   stand as the answer on its own; steps 2 and 3 below are independent and regularly hit where
   the walker misses (they did for every seed in the 2026-08-06 run).

2. **Bead titles + descriptions**:
   ```bash
   bd search "<seed>" --status all 2>/dev/null | head -20
   bd list --status=all -n 100000 --json 2>/dev/null | jq -r '.[] | select((.description // "") | test("<seed>"; "i")) | "\(.id) \(.title)"' | head -20
   ```
   Two separate passes: `bd search` matches titles; the `bd list | jq` pass is
   a TRUE description search (do NOT use `bd search --desc-contains`, which
   ANDs with the title query and returns a strict subset of the title pass).
   `-n 100000` is mandatory: `bd list` silently caps at 50 rows without it,
   which made this pass a silent no-op against a ~1300-bead corpus
   (root-caused 2026-08-06; two same-session empty results looked like
   "no matches").
   `--status all` is mandatory on both: recall's purpose is finding work other
   sessions produced, which predominantly lives in CLOSED beads that bd
   excludes by default. There is no comment-search flag, so comments are not
   covered.
   Returns: bead IDs with titles.

3. **Topic file contents** (grep, last-modified sort):
   ```bash
   grep -l -i -F "<seed>" ~/.claude/projects/-workspaces-main/memory/*.md 2>/dev/null \
     | xargs -I{} sh -c 'echo "$(stat -c %Y "{}") {}"' \
     | sort -rn \
     | head -10 \
     | awk '{print $2}'
   ```
   Returns: topic file paths, recency-sorted.

4. **Recent bead activity** (if time hint present): filter on bead updated
   timestamps (bead list JSON does not carry comment timestamps):
   ```bash
   bd list --status=all -n 100000 --json 2>/dev/null | jq -r '.[] | select(.updated_at >= "<window-start-ISO>") | "\(.updated_at) \(.id) \(.title)"' | sort -r | head -20
   ```

### Phase 3: Merge and rank

Combine results into a unified list, deduplicating cross-artifact matches (a bead and its associated memory key both surfacing for the same query). Rank by:
- Recency (recently-updated entities first)
- Exact-match weight (substring hits in titles/keys score higher than body text)
- Cross-source confirmation (an entity appearing in multiple artifact types scores higher)

### Phase 4: Present (BFS only)

Output as scannable groups:

```markdown
## Recall: <query>

### Beads (N hits)
- **docr-XXXX** (status, last touched YYYY-MM-DD): one-line title or description excerpt
- ...

### Memories (N hits)
- `namespace:key`: one-line value preview
- ...

### Topic Files (N hits)
- `memory/<filename>.md`: one-line excerpt or summary
- ...

### Bridges / related entities
- (cross-references via bd_related walker)

---
_BFS layer only. Run `bd show <id>` / `bd memories <key>` / Read `<path>` to DFS into any hit. Limit deep reads to entities that warrant it; cumulative context budget grows fast._
```

### Phase 5: Hand off to DFS judgment

Stop here. The agent (or user) decides which previews warrant a deeper read. Do NOT auto-fetch full bead content, full memory values, or full topic file contents. That's DFS; the agent triggers it based on the BFS surface.

## Rules

- **BFS only**: each hit is one line. NO full content fetch in this skill. Deep reads are the next step, agent-initiated.
- **Parallel where possible**: artifact-type searches don't depend on each other; run them in a single batched message of tool calls.
- **Empty results are valid**: if no hits, say so plainly. Do not invent context. Suggest alternative seed terms or `bd list --status=open` for broader scan.
- **Recency is signal**: surface most recently touched entities first; that's usually what the user is referencing.
- **Cross-reference, don't duplicate**: if a bead and a memory key both match, surface both but note the relationship ("docr-XXXX is the bead; coaching:foo is the memory key associated with it").
- **No speculation**: do not interpret what the user "must mean" beyond what their prompt suggests. The recall surface is raw; interpretation happens after.

## Distinct from related skills

- **vs `/enrich`**: enrich loads context for a SPECIFIC ticket/PR/bead given the ID. recall finds candidates when the ID is unknown.
- **vs `bd memories <keyword>`**: that's a single artifact-type search. recall crosses beads + memories + topic files.
- **vs producer-side `bd-recency-surface` hook**: that surfaces what's already in the corpus at the moment of writing. recall is the read-side query primitive.
- **vs `/investigate`**: investigate is for root-cause debugging of production errors. recall is for finding past discussions.

## When to escalate

If the recall surface returns nothing relevant and the user is sure the info exists:
- Suggest checking Slack (search via slack MCP), Jira (searchJiraIssuesUsingJql), or Confluence (searchConfluenceUsingCql).
- Suggest broadening the seed (more terms, less specific).
- Last resort: ask the user for any specific entity ID they remember (bead, PR, ticket).
