---
name: bd-related
description: Walk the memory graph from a seed (memory key, bead ID, or free-text keyword) to surface related beads, memories, and topic files. Subroutine for model use only - not user-facing. Invoke when entering a domain mid-conversation, when you need wider context than the load-time preload-sibling-beads hook surfaced, or when a subagent's findings need cross-checking against prior corrections in the same domain. Read-only.
user-invokable: false
---

# /bd-related

Model-invocable subroutine over the personal memory graph (beads
memories + topic files + bd-memory bridges). Wraps the walker built in
Phase 1 of the memory-graph work (bead `docr-q48e`, memory key
`memory-graph-phase1`).

## When to invoke

Trigger proactively when ANY apply:

- About to write a plan / review / fix touching a known domain
  (<service>, folio, doc_v3, cqc, salesforce, etc.) AND the load-time
  hook has not already fired for this task.
- User names a topic, bead, or memory key; you want to see what else
  in the corpus relates BEFORE forming a response.
- A subagent reports findings and you want to check whether a prior
  correction memory governs this case.
- Entering a domain mid-conversation that the most recent
  /enrich /converge /pr-intel etc. did not cover.

Do NOT invoke for:
- Direct lookup ("find memories about X"); use `bd memories <kw>`.
- Bead inspection; use `bd show <id>`.
- Memory inspection; use `bd memories <key>`.

## Invocation

```bash
python3 ~/.claude/scratch/scripts/memory-graph/bd_related.py "<seed>" [--limit N] [--json]
```

Seed shapes (auto-detected):
- Memory key with `:`: `decision:cross-service-isolation:<service>-self-containment`
- Bead ID: `docr-b7xa`
- Free-text keyword(s): `<service> self-containment` (multi-token scored)

Default limit 10. Use `--json` to pipe into a follow-up step.

## Output shape

Each result line: `[<kind>] <target> via <provenance>`.

| Kind | What it is | Action |
|------|------------|--------|
| `match` | Direct substring match against memory key or topic-file path | Inspect with `bd memories <key>` or `Read <path>` |
| `bridge` | Co-mentioned with the seed on a MEMORY.md / topic-file / bd-memory line | Highest-information cross-tree neighbor; investigate first |
| `sibling` | Same namespace prefix one level up | Other entries in same sub-domain |
| `cousin` | Same namespace prefix two levels up | Other entries in same parent domain |

Emission order: top-3 matches first, then bridges, then namespace
walk, then remaining matches. The walker stops at `--limit`.

## Cold-start orientation

If just spawned and you have no context: this is a personal
knowledge-graph walker over ~1000 beads memories + ~145 topic files in
`~/.claude/projects/-workspaces-main/memory/`. Phase 1 shipped
2026-05-22. Output is informational, not directive: a surfaced
neighbor does not mean the user wants action taken on it.

## Regenerating the graph

If `~/.claude/scratch/graph/namespace_index.json` or `bridges.jsonl`
look stale (over 24h old or the corpus has changed substantially):

```bash
python3 ~/.claude/scratch/scripts/memory-graph/build_namespace_index.py
python3 ~/.claude/scratch/scripts/memory-graph/extract_bridges.py
```

Each script runs in under 2 seconds on the current corpus.

## Related

- Bead `docr-q48e` (Phase 1) and `docr-v4jj` (Phase 1.5: this skill +
  hook extension + observability).
- Memory `memory-graph-phase1`: full infrastructure pointer.
- Hook `~/.claude/hooks/preload-sibling-beads.sh`: auto-fires on a
  curated allowlist of personal-tier information-gathering skills.
