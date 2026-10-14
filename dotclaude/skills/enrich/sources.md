# Enrichment Sources

Shared reference for context-gathering tools and bounds. Referenced by
`/enrich` SKILL.md.

## Quick Reference

| Source | Tool | Bounds | Fallback |
|--------|------|--------|----------|
| AWS context | `mcp__aws__call_aws` | 1 service, last 1h errors | Skip if no service identifier |
| Datadog context | `mcp__datadog__*` | Last 24h hot tier | Skip if no service identifier |
| GitHub PR | `gh pr view` (CLI) | Changed files list | `gh api` for review comments |
| Codebase | Grep + Read | Max 8 files read | Skip if no references found |

## 1. Tickets: not available here

This company uses neither Jira nor Confluence (Michael, 2026-09-23 10:34 PDT), and
this machine has no ticket tools. Skip ticket hydration and say so in the briefing.

## 2. Open Chores

**Related open items (always, for any input type):**
Extract keywords from the primary source (ticket summary, PR title) and scan
`~/.claude/memory/open-chores.md` for matching lines.

**Bounds:** Note how many matching lines were found, if any.

## 3. Memory Topic Files

```bash
grep -rilE '<service-name>' ~/.claude/memory/ ~/.claude/rules/
grep -rilE '<domain-keyword>' ~/.claude/memory/ ~/.claude/rules/
grep -rilE '<ticket-id>' ~/.claude/memory/ ~/.claude/rules/
```

Run 1-3 keyword searches based on what the primary source references. Use the
service name, domain terms, and ticket ID as search terms.

**Bounds:** First 10 matches across all searches (deduplicated). Include
gotchas, corrections, and domain knowledge. Skip deployment and org memories
unless the briefing is about deployment or org topics.

## 4. AWS Context

**Conditional:** Only run if step 1 extracted a Lambda function name or ECS
service name. Skip for free-text inputs that contain no service identifier.

**Tool:** `mcp__aws__call_aws`

**Lambda function config:**
```
mcp__aws__call_aws
  service: lambda
  action: get_function_configuration
  parameters: {"FunctionName": "<function-name>"}
```

Extract: `LastModified`, `Environment.Variables` (variable **names only** - do
NOT extract variable values; env vars frequently contain secrets and must not
be logged per `.claude/rules/security.md`), `Runtime`, `MemorySize`, `Timeout`.

**Note:** `LastModified` reflects the deploy time, not the commit time. The lag
between merge and deploy can be days or weeks. Do not conflate deploy time with
code change time.

**Recent error counts (CloudWatch):**
```
mcp__aws__call_aws
  service: cloudwatch
  action: get_metric_statistics
  parameters: {
    "Namespace": "AWS/Lambda",
    "MetricName": "Errors",
    "Dimensions": [{"Name": "FunctionName", "Value": "<function-name>"}],
    "StartTime": "<1 hour ago>",
    "EndTime": "<now>",
    "Period": 3600,
    "Statistics": ["Sum"]
  }
```

**Bounds:** 1 service per enrichment. Last 1 hour of error counts only.

## 5. Datadog Context

**Conditional:** Only run if step 1 extracted a service identifier (Lambda function
name or ECS service name). Skip for free-text inputs without a service identifier.

**Tools:** `mcp__datadog__search_datadog_events`, `mcp__datadog__search_datadog_logs`,
`mcp__datadog__aggregate_spans`

**Recent error events:**
```
mcp__datadog__search_datadog_events
  query: "service:<service-name> status:error"
  timeframe: last_24h
```

**Top error patterns:**
```
mcp__datadog__search_datadog_logs
  query: "service:<service-name> status:error"
  timeframe: last_24h
```

**Bounds:** Last 24h hot tier. For any window longer than 7 days, use
`storage_tier: "flex_and_indexes"` explicitly - the default hot tier silently
drops older data.

**Gotchas - read before querying:**

1. **ECS service tag suffix.** ECS-deployed services carry an `-ecs` suffix on
   their Datadog service tag. Query `<service>-doc_chunk-ecs`, not `<service>-doc_chunk`.
   Always verify the actual service tag via `mcp__datadog__aggregate_spans` grouped
   by `service` before assuming the tag format.

2. **Hot tier retention.** Any window longer than 7 days needs
   `storage_tier: "flex_and_indexes"` explicitly set. The default hot tier silently
   drops data older than 7 days - you will get zero results with no error.

3. **Error Tracking case fingerprint drift.** Error Tracking case fingerprints
   can drift over time as stack traces evolve. A single case can accumulate
   different stack-trace fingerprints, hijacking the case across distinct error
   classes. Compare `first_seen` vs `last_seen` fingerprint hashes before trusting
   case-level "still firing" signals.

## 6. GitHub PRs

**Primary (always available):**
```bash
gh pr view <N> --json title,body,changedFiles,url,state,author,baseRefName
```

**Extract:** title, description, changed files list, state, author, base branch.

**For inline review comments** (when the briefing needs reviewer context):
```bash
gh api /repos/<company>/docr/pulls/<N>/comments \
  --jq '[.[] | {user: .user.login, path: .path, line: .line, body: .body}]'
```
Adds inline thread context (Copilot/Sentry comments live here). Also fetch
`gh pr view <N> --json comments` for issue-level bot comments (SonarQube,
PR Metrics, Vercel, Mergify) - they appear in a different endpoint.

**Bounds:** Changed files list only (not full diff). The briefing provides
context, not review analysis. For review analysis, use `/pr-intel`.

## 7. Codebase

Grep and Read based on references found in the primary source.

**PR branch not checked out (read via `git show`, not the working tree):** When the
primary source is a GitHub PR, its changed files live on the PR's head branch, NOT the
local working tree (which holds the base branch). Reading `src/.../foo.py` directly
returns "No such file or directory" for any file the PR adds or that diverged. Fetch
the head ref once, then read through it:
```bash
gh pr view <N> --json headRefName --jq '.headRefName'   # e.g. cfried/mx2-ruleseng
git fetch origin <headRefName>
git show origin/<headRefName>:<path>                     # read any changed file
```
Do NOT stand up a worktree for enrichment (that is `/pr-intel`'s job); `git show`
against the fetched ref is enough for the read-only characterization enrich does.

**File paths:** Extract `src/python/mx2/...` or similar path patterns from
ticket descriptions or PR changed files. Read those files.

**Service entry points:** If the primary source names a service, grep for:
```
Grep for "def handler" or "def lambda_handler" in src/python/mx2/<service>/
Grep for "class.*App" or "app = FastAPI" in src/python/mx2/<service>/
```

**Models and settings:** If entry points reference models or settings, read
those files to understand the data structures.

**Bounds:** Max 8 files read total. Prioritize: entry points > models >
settings > tests. Read public interfaces, not deep implementation. If more
than 8 files are relevant, note what was skipped.

## Graceful Degradation

If any source fails (MCP unreachable, CLI errors, grep finds nothing),
include a marker in the output and continue with remaining sources:

```
[UNAVAILABLE: Open Chores - no matching lines in open-chores.md for "<keywords>"]
[UNAVAILABLE: AWS - function not found or credentials unavailable]
[UNAVAILABLE: Datadog - no results returned for service "<service-name>"]
[UNAVAILABLE: Codebase - no file references found in primary source]
```

A briefing with 3 of 5 sources is more useful than no briefing. Never block
on a single source failure.
