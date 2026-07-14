# Enrichment Sources

Shared reference for context-gathering tools and bounds. Referenced by
`/enrich` SKILL.md and `/pr-intel` SKILL.md (Section 1, Jira hydration).

## Quick Reference

| Source | Tool | Bounds | Fallback |
|--------|------|--------|----------|
| Jira ticket | Atlassian MCP `mcp__atlassian__getJiraIssue` | Last 5 comments | Large-ticket extraction script |
| Bead | `bd show` + `bd search` | Top 5 search results | Skip if bd unavailable |
| Beads memories | `bd memories` | First 10 matches | Skip if no matches |
| AWS context | `mcp__aws__call_aws` | 1 service, last 1h errors | Skip if no service identifier |
| Datadog context | `mcp__datadog__*` | Last 24h hot tier | Skip if no service identifier |
| GitHub PR | `gh pr view` (CLI) | Changed files list | `gh api` for review comments |
| Codebase | Grep + Read | Max 8 files read | Skip if no references found |

## 1. Jira Tickets

```
mcp__atlassian__getJiraIssue
  cloudId: <your-atlassian-cloud-id>
  issueIdOrKey: MX2-XXXXX
  fields: ["summary", "status", "assignee", "priority", "description", "customfield_11220", "comment", "issuelinks"]
  responseContentFormat: markdown
```

**Extract:** summary, status, assignee, priority, linked tickets (`issuelinks`),
last 5 comments. Read BOTH `customfield_11220` and `description`; both render
in the Jira UI as of ~2026-04-30. Per project convention (see
[/workspaces/main/.claude/commands/jira.md](/workspaces/main/.claude/commands/jira.md),
MX2-NNNNN): non-Salesforce issue types put canonical content in `description`
with `customfield_11220` blanked to empty ADF; Salesforce-specific issue types
mirror the same content in both fields. Use whichever field has content; if
both are populated, prefer `description` for non-SF types and either for SF
types (they should match).

**Linked-issue sweep (when `issuelinks` is non-empty):** for each linked issue
(relates to / blocks / is blocked by), fetch status plus the most recent 2-3
comments (same `getJiraIssue` call, fields `["summary", "status", "comment"]`).
If a linked issue's findings contradict or supersede the target ticket's latest
framing, surface a flagged **CONTRADICTION** line at the top of the briefing,
citing both sources (ticket + comment date each). Rationale: MX2-NNNNN sat
blocked ~6 weeks re-asserting a hypothesis its "relates to" sibling MX2-NNNNN
had falsified in comments on 2026-05-19; the falsification was invisible from
the target ticket alone. **Bounds:** max 3 linked issues, most recently updated
first; note the count if more exist.

**ADF parsing for `customfield_11220`:** This field always returns ADF JSON
regardless of `responseContentFormat`. Extract plain text using the recursive
`extract_text` helper from the large-ticket script below (lines 45-52): walk
`content` arrays, collect every `text` string, join with spaces.

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

## 2. Beads

**Primary source (when input is a bead ID):**
```bash
bd show <id>
```
Extract: title, description, acceptance criteria, design notes, dependencies,
comments. If the bead references a Jira ticket (in title or description),
also fetch that ticket via Jira source above.

**Related beads (always, for any input type):**
```bash
bd search <keywords-from-primary-source>
```
Take the top 5 results. For each, run `bd show <id>` to load context. Prioritize:
- Beads with status `in_progress` or `open` (active work)
- Beads with category labels: `memory`, `decision`, `discovery` (context-rich)
- Beads that share dependency chains with the primary source

**Bounds:** Top 5 search results. If more exist, note the count in the briefing
("15 related beads found, showing top 5").

## 3. Beads Memories

```bash
bd memories <service-name>
bd memories <domain-keyword>
bd memories <ticket-id>
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
gh api /repos/lawfirm/main/pulls/<N>/comments \
  --jq '[.[] | {user: .user.login, path: .path, line: .line, body: .body}]'
```
Adds inline thread context (Copilot/Sentry comments live here). Also fetch
`gh pr view <N> --json comments` for issue-level bot comments (SonarQube,
PR Metrics, Vercel, Mergify) - they appear in a different endpoint.

**Bounds:** Changed files list only (not full diff). The briefing provides
context, not review analysis. For review analysis, use `/pr-intel`.

## 7. Codebase

Grep and Read based on references found in the primary source.

**File paths:** Extract `src/python/mx2/...` or similar path patterns from
ticket descriptions, bead design notes, or PR changed files. Read those files.

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

If any source fails (MCP unreachable, `bd` command errors, CLI errors, grep finds nothing),
include a marker in the output and continue with remaining sources:

```
[UNAVAILABLE: Jira - MCP returned error: <brief message>]
[UNAVAILABLE: Beads - bd search returned no results for "<keywords>"]
[UNAVAILABLE: AWS - function not found or credentials unavailable]
[UNAVAILABLE: Datadog - no results returned for service "<service-name>"]
[UNAVAILABLE: Codebase - no file references found in primary source]
```

A briefing with 3 of 5 sources is more useful than no briefing. Never block
on a single source failure.
