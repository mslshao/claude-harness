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
page versions v3-v8 of a runbook on 2026-07-22
(`bd recall correction:workflow:confluence-refetch-before-update`).

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
   description of the change (page-history audit trail; the schema supports it).

## Delta 3: post-push verification

After the push, re-fetch the page once and confirm your edit anchor is present in the
body (a distinctive phrase from the applied change). If absent, report the failure
loudly with the page URL and current version; do not retry blindly.

## Multi-update sessions

The baseline is per-push, not per-session. After each successful push, the re-fetch
from Delta 3 becomes the new baseline. Never push from a body fetched before your own
previous push.
