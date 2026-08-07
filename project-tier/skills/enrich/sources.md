---
allowed-tools:
  - mcp__atlassian__getJiraIssue
  - mcp__aws__call_aws
  - mcp__datadog__search_datadog_events
  - mcp__datadog__search_datadog_logs
  - mcp__datadog__aggregate_spans
  - Bash(gh pr view:*)
  - Bash(gh api:*)
  - Grep
  - Read
---

# Enrichment Sources

Shared reference for context-gathering tools and bounds. Referenced by
`/enrich` SKILL.md.

## Quick Reference

| Source | Tool | Bounds | Fallback |
|--------|------|--------|----------|
| Jira ticket | Atlassian MCP `mcp__atlassian__getJiraIssue` | Last 5 comments | Large-ticket extraction script |
| AWS context | `mcp__aws__call_aws` | 1 service, last 1h errors | Skip if no service identifier |
| Datadog context | `mcp__datadog__*` | Last 24h hot tier | Skip if no service identifier |
| GitHub PR | `gh pr view` (CLI) | Changed files list | `gh api` for review comments |
| Codebase | Grep + Read | Max 8 files read | Skip if no references found |

## 1. Jira Tickets

```
mcp__atlassian__getJiraIssue
  cloudId: <atlassian-cloud-id>
  issueIdOrKey: MX2-XXXXX
  fields: ["summary", "status", "assignee", "priority", "description", "customfield_11220", "comment", "issuelinks"]
  responseContentFormat: markdown
```

**Extract:** summary, status, assignee, priority, linked tickets (`issuelinks`),
last 5 comments. Prefer `customfield_11220` (SF Description) over the standard
`description` field - it is what humans see in the Jira UI, and `description`
is null for most MX2 tickets.

**ADF parsing for `customfield_11220`:** This field always returns ADF JSON
regardless of `responseContentFormat`. Extract plain text using the recursive
`extract_text` helper from the large-ticket script below: walk `content` arrays,
collect every `text` string, join with spaces.

**Bounds:** Last 5 comments only. Older comments rarely contain actionable context
for a briefing. If needed, the user can ask for more.

**Large ticket handling:** When `getJiraIssue` output exceeds token limits, it
gets saved to a temp file. Extract fields with:

```bash
cat <saved-file> | python3 -c "
import json, sys
data = json.load(sys.stdin)
text = data[0]['text'] if isinstance(data, list) else data['text']
parsed = json.loads(text)
print('Summary:', parsed['fields']['summary'])
print('Status:', parsed['fields']['status']['name'])
print('Assignee:', parsed['fields'].get('assignee', {}).get('displayName', 'Unassigned'))
comments = parsed.get('fields', {}).get('comment', {}).get('comments', [])
for c in comments[-5:]:
    def extract_text(node):
        if isinstance(node, str): return node
        texts = []
        if 'text' in node: texts.append(node['text'])
        for child in node.get('content', []): texts.append(extract_text(child))
        return ' '.join(texts)
    print(f'{c[\"author\"][\"displayName\"]} ({c[\"created\"]}):')
    print(extract_text(c['body']))
    print('---')
"
```

## 2. AWS Context

**Conditional:** Only run if step 1 extracted a Lambda function name or ECS
service name. Skip for free-text inputs that contain no service identifier.

**Tool:** `mcp__aws__call_aws`

**Lambda function config:**
```
mcp__aws__call_aws
  cli_command: "aws lambda get-function-configuration --function-name <function-name>"
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
  cli_command: "aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Errors --dimensions Name=FunctionName,Value=<function-name> --start-time <1-hour-ago-ISO8601> --end-time <now-ISO8601> --period 3600 --statistics Sum"
```

**Bounds:** 1 service per enrichment. Last 1 hour of error counts only.

## 3. Datadog Context

**Conditional:** Only run if step 1 extracted a service identifier (Lambda function
name or ECS service name). Skip for free-text inputs without a service identifier.

**Tools:** `mcp__datadog__search_datadog_events`, `mcp__datadog__search_datadog_logs`,
`mcp__datadog__aggregate_spans`

**Recent error events:**
```
mcp__datadog__search_datadog_events
  query: "service:<service-name> status:error"
  from: "now-1d"
  to: "now"
```

**Top error patterns:**
```
mcp__datadog__search_datadog_logs
  query: "service:<service-name> status:error"
  from: "now-1d"
  to: "now"
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

## 4. GitHub PRs

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
context, not review analysis.

## 5. Codebase

Grep and Read based on references found in the primary source.

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
[UNAVAILABLE: Jira - MCP returned error: <brief message>]
[UNAVAILABLE: AWS - function not found or credentials unavailable]
[UNAVAILABLE: Datadog - no results returned for service "<service-name>"]
[UNAVAILABLE: Codebase - no file references found in primary source]
```

A briefing with 3 of 5 sources is more useful than no briefing. Never block
on a single source failure.
