# PR Context (series, service, migration)

This file documents three context-gathering checks that run after PR metadata
hydration but before specialist dispatch. Each surfaces facts the reviewer needs
to evaluate design decisions in context.

1. **PR Series Context**: sibling PRs in the same Jira ticket; prevents false
   orphan-export findings.
2. **Service Context**: CLAUDE.md / README orientation for the service the PR
   touches; gives external reviewers enough background.
3. **Migration State**: load operational state for in-flight migrations before
   forming review concerns. Permanent as of 2026-07-02 (2026-07-01 audit:
   revisit never ran, check in active use).

## PR Series Context

When a Jira ticket was hydrated, check for sibling PRs that form a multi-PR delivery.
This prevents false "orphan export" findings when one PR introduces code that a sibling
consumes.

**Trigger detection** (any of these):
- `gh pr list --search "<ticket-key>" --state open` returns >1 PR (including this one)
- PR description contains series language: "part N", "PR X of Y", or numbered references

**Skip condition**: No Jira ticket found AND no series language in description.

**Tier 1 (always when multi-PR detected):**
1. Fetch file lists for each sibling PR:
   ```bash
   gh pr list --search "<ticket-key>" --state open --json number,title,headRefName,files
   ```
2. Identify overlapping file paths between this PR and each sibling.
3. Record: `{number, title, overlapping_files}` per sibling.

**Tier 2 (only when Tier 1 finds overlapping files):**
1. For each new export in THIS PR (function, type, interface on `+` lines), grep
   sibling diffs for references:
   ```bash
   gh pr diff <sibling-number> | grep -c "<export-name>"
   ```
2. Classify exports as **referenced** (at least one sibling mentions it) or
   **unreferenced** (no sibling references it).
3. Cap: if >5 siblings, limit Tier 2 to the 5 with the most file overlap.

Store as `series_context`:
- `sibling_prs`: list of `{number, title, overlapping_files}`
- `orphan_exports`: new exports with 0 references in sibling PRs
- `consumed_exports`: new exports referenced by at least one sibling

**Downstream effects:**
- **Specialist preamble**: append series context so specialists don't flag consumed
  exports as unused
- **Synthesis**: orphan exports become design review surface questions ("What consumes
  `mapServerJobToLocal`? Not found in sibling PRs #8201, #8202, #8203."), not blocking
  findings
- **Draft Review Summary**: note the series relationship

## Service Context

Orient the reviewer to the system this PR modifies. From the changed file paths,
identify the service or package root (e.g., `src/python/mx2/dyn2red/` or
`src/python/mx2/folio/page/`). Then scan for contextual docs, in priority order:

1. **CLAUDE.md** in the service directory or nearest parent with one
2. **README.md** in the service directory
3. **Folio-style CLAUDE.md** in `src/python/mx2/folio/` (for folio subpackages)

If found, read the file and extract a brief orientation for the reviewer:
- What does this service/pipeline do (1-2 sentences)
- Key dependencies (DynamoDB tables, S3 buckets, upstream/downstream services)
- Known gotchas or design constraints
- Links to Confluence design docs or Datadog dashboards

Present this as a **Service Context** block at the top of the output, before Scope.
Keep it to 3-5 lines. The goal is to give an external reviewer enough context to
evaluate design decisions without having to read the entire service codebase.

If no contextual docs are found, note the absence ("No CLAUDE.md or README found
for this service") and infer what you can from the diff, PR description, and Jira
ticket. This is a degraded mode, not a failure.

For PRs spanning multiple services, include context for each.

## Migration State (when PR touches an in-flight migration)

> Permanent as of 2026-07-02 (2026-07-01 audit: revisit never ran, check in active use).

If the PR's title, body, or linked Jira epic chain references an active
migration (signals: tokens like "migration", "cutover", "v3", "matters",
"backfill"; Jira ticket whose epic is a migration epic; PR title prefix that
matches a known migration code-path rename), load the migration's operational
state from beads memory **before forming review concerns**:

```bash
bd memories <migration-name>            # e.g., doc_v3, dyn2red, folio-ocr
bd memories cutover                     # cross-migration general state
```

Surface in the briefing's Service Context block:
- Cutover status (planned / in flight / complete; date if known)
- Backfill status (pending / in flight / complete; date if known)
- Steady-state milestone (PR that closed the cutover bridge, if any)
- Whether dual-read / dual-write fallback was retained or removed in the
  ratified design
- Pointer to the canonical state page or runbook

**Why this matters**: a migration PR's diff and description are point-in-time
artifacts. They do not tell you whether the alias has flipped, whether the
backfill has run, or whether sibling consumers have already cut over. Without
this state, review concerns about "sequencing risk" or "missing fallback" can
be fully invalidated by facts already in beads memory. This is the same
authoritative-state principle as the deploy-list rule in `~/.claude/CLAUDE.md`
("Operational scope questions require authoritative-state verification"),
applied to PR review.

If no migration signal is detected in the PR, skip this section.
