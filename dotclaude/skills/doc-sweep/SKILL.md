---
name: doc-sweep
description: "Consistency-and-freshness sweep for the AI Coding Tools Confluence series (hub 5640257537 + children, PPET space). Verify-then-fix in two workflows: parallel per-page verify agents check open findings and staleness classes against LIVE pages, external fact-check agents verify third-party product claims, then per-page fix agents apply exact-substring edits with publish and re-fetch verification. Use monthly, after major harness changes (new project agents/skills/rules), or when a review left unapplied findings. Trigger: 'doc sweep', 'sweep the AI docs', 'AI tooling docs drift', '/doc-sweep'. Personal-tier only."
argument-hint: "[optional focus: inventory | external-claims | schema | path to a findings file]"
---

# Doc Sweep

Keep the AI Coding Tools Confluence series consistent and current. Two-workflow shape,
proven 2026-07-02 (47/47 edits, 0 failures) and 2026-06-09 (fix-pass 10/10 pages).

## 0. Preconditions (read before dispatching anything)

1. `~/.claude/projects/-workspaces-main/memory/ai-coding-tools-page-format.md`: the page
   registry (IDs + tracks), header/footer schema, conventions, held items, and the
   convergence-history log. This file is the sweep's input AND its output.
2. `~/.claude/projects/-workspaces-main/memory/atlassian-mcp.md`: Confluence tool quirks.
3. Enforcement surfaces are read from SOURCE, never from memory paraphrase: the banned
   shared-page vocab list is the regex in `~/.claude/hooks/block-personal-tier-vocab.sh`
   (grep it fresh each sweep; a stale memory claim about this hook degraded a fix on
   2026-07-02, `bd memories correction:verification:enforcement-claims-cite-source`).

## 1. Build the work-list

Collect candidate items from every lane that has historically produced drift:

- **Held items** in the format memory (tooling-owner blocks stay held; note them).
- **Unapplied findings** from prior review artifacts (e.g. scratch digests under
  `~/.claude/scratch/ai-kt-*`); prior findings JSON may split across
  `findings`/`verified`/`subjective` keys: prefer `findings`+`verified` when
  `findings` is non-empty, else `subjective`+`verified` (dedup lesson, 2026-07-02).
- **Inventory drift**: hub appendix agent/command lists vs the repo
  (`/workspaces/main/.claude/agents|commands|skills`, `bin/check_claude_inventory.py`
  output, repo `CLAUDE.md` tables).
- **External product claims**: model lineup, Cursor rules mechanisms, Copilot
  feature/availability claims (org fact: local Copilot disabled 2026-07,
  `bd memories decision:copilot-chat-local-disabled-2026-07`), tool-feature assertions.
  These rot on roughly a monthly cadence.
- **Mechanical classes**: phantom links (bare `Word.md` auto-linkified to
  `http://Word.md`; fix by backticking), header/footer schema conformance, `## N.`
  numbering, `> 💡 **Bold lead**:` callout shape, em-dash ban.

## 2. Verify workflow (read-only)

Dispatch via the Workflow tool: one agent per page + one agent per external claim.

- Page agent inputs: pageId, cloudId `<your-atlassian-cloud-id>`, the page's
  candidate items, and the conventions block (below). Output schema per finding:
  `{section, stillApplies, recommend: apply|skip|needs-owner|needs-verification,
  evidence, find, replace}` plus current page `version`.
- External agents: WebSearch/WebFetch fact-checks returning
  `{verdict: supported|refuted|unclear, evidence, recommendation}` with source URLs.
- Conventions block for every prompt: no em-dash (U+2014); `**Term**: body` colon
  connector; callouts `> 💡 **Bold lead**: ...`; filenames backticked; sections
  `## N. Title`; second-person direct voice; no personal-tier vocab (quote the hook
  regex verbatim in the prompt).

## 3. Orchestrator triage (non-delegable)

- Personally read every proposed find/replace. Enforce: find matches exactly once on
  the page, or carries `replaceAll: true` + `expectedOccurrences`.
- Resolve `needs-verification` items with the external agents' verdicts; refuted
  citations get removed/softened, not left.
- Check reviewer "schema-drift" claims against the RATIFIED schema in the format
  memory before accepting them; the ratified special cases win (a reviewer flagged
  the First Week redirect callout as drift on 2026-06-09; the schema documents it as
  deliberate).
- Anything requiring an external owner stays held and gets re-confirmed, not fixed.

## 4. Fix workflow (one agent per page with accepted edits)

Each fix agent, sequentially per page:

1. Fetch page as markdown; abort with `version-drift` if version != expected.
2. Save body to scratchpad `page-<id>-before.md`; apply edits with a deterministic
   python exact-substring script (no regex, no retyping; occurrence-count guard);
   write `page-<id>-after.md`. Suffix helper scripts with the pageId (parallel agents
   share the scratchpad).
3. Publish the FULL new body (markdown) with a dated version message; re-fetch and
   verify every replace landed and version incremented.
4. Guards: no em-dash introduced; length delta equals the net replacement size.
5. Return `{pageId, status, versionBefore, versionAfter, applied, failed, notes}`.

Benign Confluence round-trip artifacts to ignore, not chase: hard-break trailing
spaces widening on each round-trip (6->8->10), bold-link normalization
(`**PR [#x](u)**` -> `**PR** [**#x**](u)`), bare-domain auto-linking.

## 5. Wrap-up (durable capture)

- Update the format memory: convergence-history entry (date, edits, pages, notables)
  and the held-items list (re-confirmed / newly held / cleared).
- `bd comments add docr-jxh7 "<one-paragraph sweep summary>"`.
- If the sweep found systemic drift a structural fix would prevent, propose it
  (that is how the repo CLAUDE.md CI inventory check came to exist).

## Cadence

Monthly, via a recurring bead check (not cron: codespaces sleep). Also run after: a
batch of project agent/skill/rule additions, a model-lineup change, or an org tooling
decision (e.g. a tool being enabled/disabled) that the pages reference.

## Hard constraints

- Verify before fix, always; never edit from memory of what a page said.
- Publishing uses exact-substring replacement on freshly-fetched bodies only.
- Held items with named owners are never fixed unilaterally.
- Personal-tier skill: do not promote to the project tier (single-author docs; the
  sweep machinery references personal memory files and hooks).
