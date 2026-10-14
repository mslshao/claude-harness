---
description: (personal; shadows the project-tier confluence command) Delta: mandatory pre-push re-fetch/version-check gate on every update, concurrent-edit rebase instead of clobber, versionMessage on writes. Create or update a Confluence page.
allowed-tools: mcp__atlassian__searchConfluenceUsingCql, mcp__atlassian__getConfluencePage, mcp__atlassian__createConfluencePage, mcp__atlassian__updateConfluencePage, mcp__atlassian__getConfluenceSpaces
---

# Confluence Page (personal override)

Base flow: Read and follow the project command at
[/workspaces/main/.claude/commands/confluence.md](/workspaces/main/.claude/commands/confluence.md)
(usage, config, create mode, update mode, notes, CQL escaping). Do not duplicate it;
this file carries ONLY the personal-tier delta below, which overrides the project
command's update-mode steps 2 and 6 where they conflict.

Why this override exists: `updateConfluencePage` is last-write-wins with NO
expected-version parameter (verified against the tool schema 2026-07-23). A push built
on a stale fetch silently clobbers every edit made since that fetch; this destroyed
page versions v3-v8 of a runbook on 2026-07-22.

## Delta 1: record a baseline at fetch time (extends project Update step 2)

When fetching current content with `getConfluencePage`, record from the response:
- `baseline_version` = the version number (`version.number` or equivalent field on the
  response object; inspect the object rather than assuming the exact path)
- `baseline_body` = the fetched body text

If no version field exists on the response, keep `baseline_body` alone; the gate below
falls back to body comparison.

## Delta 2: the pre-push gate (replaces project Update step 6's bare push)

Immediately before EVERY `updateConfluencePage` call, no exceptions (agent path,
interactive path, `--replace`, retries, and every iteration of a multi-edit session):

1. Re-call `getConfluencePage` for the page (same contentFormat).
2. Compare: fresh version vs `baseline_version` (fallback: fresh body vs `baseline_body`).
3. **Unchanged**: push the prepared body.
4. **Changed** (someone or something edited the page after your fetch): do NOT push the
   prepared body; it was built on a stale base and would clobber the concurrent edits.
   Instead:
   a. Diff `baseline_body` vs the fresh body to see what the concurrent edit changed.
   b. Re-apply YOUR intended edits onto the FRESH body (targeted patch; preserve the
      concurrent changes).
   c. If your edit and the concurrent edit touch the same region: interactive path,
      show both versions and ask; agent path, stop and report the conflict with both
      texts rather than guessing. `--replace` + version-changed is ALWAYS this case
      (the whole page is the region): full replacement of a page that just moved is
      exactly the clobber this gate exists to prevent.
   d. Set `baseline_version`/`baseline_body` to the fresh values and push the re-applied
      body.
   e. Note the concurrent edit in your output ("page moved v<N> -> v<M> during editing;
      edits re-applied onto the fresh body").
5. On every `updateConfluencePage` call, pass `versionMessage` with a one-line
   description of the change (page-history audit trail; the schema supports it). When
   the push re-applies your edits onto a concurrent session's fresh body (step 4), say
   so in the versionMessage and name the base you merged onto; that line is what makes
   the other session's reconciliation instant (proven both directions on 2026-08-20).

## Delta 2b: body must be literal text, never a shell expression

`updateConfluencePage`/`createConfluencePage` are MCP tool calls, not Bash. A `body` value
written as `$(cat file)` or any other shell-substitution syntax does NOT get expanded; it is
pushed verbatim as the page content. This corrupted a live page for about a minute on
2026-08-19 before Delta 3 caught it.

Before every push, confirm the `body` argument is the actual composed text (typically already
in context from a prior Read/Write), never a command string. If the content came from a file,
read it into context first and inline it; do not shell out to fetch it inside the tool call.

## Delta 3: post-push verification

After the push, re-fetch the page once and confirm your edit anchor is present in the
body (a distinctive phrase from the applied change). If absent, report the failure
loudly with the page URL and current version; do not retry blindly.

Same-session repeat pushes may satisfy Delta 3 from the push response instead of a
fresh fetch: pass `includeBody: true` on `updateConfluencePage`; when the response
shows `version.number == baseline + 1` AND the echoed body contains the edit anchor,
that echo IS the server's stored content: record it as the new baseline. Delta 2
(fresh fetch immediately before every push) is UNCHANGED and unconditional; this trims
only the third leg, one full-body fetch per push. Large bodies overflow the echo to a
tool-results file (see `memory/atlassian-mcp.md`); json-load that file rather than
skipping the check. (Added 2026-08-12 after nine full-body round-trips in one day on
the <service> cutover status/endgame page pair.)

## Delta 4: quantitative claims carry their method

Any rate, count, or denominator written to a page must carry its method inline (the
tool/query plus measurement timestamp) or cite where the method is recorded. A bare
"measured <date>" is not a method. 2026-08-20: two same-day /text 500-rate figures
(5/~1,065 and 5/~1,475) landed on sibling cutover pages with no recorded method; they
disagreed only because of filter and window drift, and a third session had to re-measure
and supersede both. The figure with a recorded method is the one that survives.

## Multi-update sessions

The baseline is per-push, not per-session. After each successful push, the verification
body from Delta 3 (the post-push re-fetch, or the `includeBody` echo on repeat pushes)
becomes the new baseline. Never push from a body fetched before your own previous push.
