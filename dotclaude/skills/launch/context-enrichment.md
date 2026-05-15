# Context Enrichment Protocol

Phase 1 of `/launch`. Transforms a Jira ticket (or bead/free text) into a
structured implementation brief suitable as input to the converge pipeline.

## Input Parsing

Detect the identifier type from the raw `/launch` arguments:

| Pattern | Type | Action |
|---------|------|--------|
| `MX2-\d+` | Jira ticket | Fetch via Atlassian MCP |
| `docr-\w+` | Bead ID | `bd show <id>`, extract linked Jira if present |
| URL matching `atlassian.net` | Jira URL | Extract ticket ID, fetch via MCP |
| Everything else | Free text | Pass directly to prompt-refiner |

## Enrichment Steps

Run as many of these in parallel as possible.

### 1. Fetch primary source

**Jira ticket:**
```
mcp__atlassian__getJiraIssue
  cloudId: <your-atlassian-cloud-id>
  issueIdOrKey: MX2-XXXXX
  fields: ["summary", "status", "assignee", "priority", "description", "customfield_11220", "comment", "issuelinks"]
  responseContentFormat: markdown
```
Extract: summary, linked tickets (`issuelinks`), assignee, status, comments
(last 5). Read BOTH `customfield_11220` and `description`; both render in the
Jira UI as of ~2026-04-30. Per project convention
([/workspaces/main/.claude/commands/jira.md](/workspaces/main/.claude/commands/jira.md),
<jira-ticket>): non-SF tickets carry content in `description` with
`customfield_11220` blanked to empty ADF; SF-specific tickets mirror content
in both fields. Use whichever has content. `customfield_11220` returns ADF
JSON; extract plain text by recursively collecting `text` fields from `content`
nodes.

**Bead:**
```bash
bd show <id>
```
Extract: title, description, acceptance criteria, design notes, dependencies,
comments. If the bead references a Jira ticket (in title or description),
also fetch that ticket.

### 2. Discover related beads

```bash
bd search <ticket-id-or-title-keywords>
```

For each related bead found, run `bd show <id>` to load design decisions and
prior analysis. Look for:
- Memory beads (category: memory) with relevant domain labels
- Decision beads (category: decision) that constrain the approach
- Prior task beads that touched the same code paths

### 3. Read relevant source files

Extract file paths from:
- Jira ticket description and comments (look for `src/python/mx2/...` patterns)
- Related bead design notes
- If the ticket mentions a service name, grep for its entry point:
  ```
  Grep for "def handler" or "class.*Service" in src/python/mx2/<service>/
  ```

Read the key files (entry points, models, settings) to understand the existing
code structure. Do not read exhaustively - focus on the public interfaces and
patterns the implementation will need to follow.

### 4. Check beads memories for domain gotchas

```bash
bd memories <service-name>
bd memories <domain-keyword>
```

Include any relevant gotchas in the implementation brief (e.g., "botocore
exception hierarchy requires catching ClientError, not specific exceptions").

## Prompt-Refiner Dispatch

After gathering all context, dispatch `prompt-refiner` in headless mode to
produce the implementation brief:

```
Agent tool:
  subagent_type: prompt-refiner
  prompt: |
    headless

    Transform the following gathered context into a 200-400 word implementation
    brief. The brief will be used as input to a planning pipeline that produces
    work items with acceptance criteria. Focus on:

    1. What needs to be built (scope)
    2. Why (business/technical motivation)
    3. Key constraints (existing patterns to follow, dependencies, gotchas)
    4. What files/modules are involved
    5. What the acceptance criteria should verify

    Do NOT include implementation details or code. The planning pipeline will
    determine the approach.

    --- JIRA TICKET ---
    <ticket summary, description, acceptance criteria>

    --- RELATED BEADS ---
    <bead titles, design notes, decisions>

    --- CODEBASE CONTEXT ---
    <key file summaries, existing patterns, service structure>

    --- DOMAIN GOTCHAS ---
    <relevant beads memories>
```

## Output

The implementation brief (200-400 words) is passed to Phase 2 as the seed
for the converge pipeline. It is not shown to the user.

If the brief is too vague (prompt-refiner couldn't extract clear scope from
the gathered context), stop and ask the user one focused question to clarify.
Do not proceed with an ambiguous brief - the plan quality depends on it.
