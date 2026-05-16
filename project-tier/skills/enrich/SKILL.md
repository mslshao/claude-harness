---
name: enrich
description: >
  Context loader for Jira tickets, PRs, or topics. Gathers ticket details,
  codebase references, AWS service state, Datadog error signals, and domain
  knowledge into a structured briefing. Use when asked about a ticket, needing
  context before running analysis, preparing for a meeting, or understanding
  what a PR involves. Trigger on: "what's the context on", "brief me on",
  "enrich", "load ticket", "what do we know about", any Jira ticket ID or PR
  number pasted without other instructions.
argument-hint: "[MX2-XXXXX | #1234 | topic]"
---

# Enrich

Gather context from multiple sources and produce a structured briefing. This skill
collects facts - it does not recommend, plan, or judge.

## Input

Parse the invocation (`/enrich $ARGUMENTS`) to detect the identifier type:

| Pattern | Type | Action |
|---------|------|--------|
| `MX2-\d+` or `MANDM-\d+` | Jira ticket | Fetch via Atlassian MCP |
| URL containing `atlassian.net/browse/` | Jira URL | Extract ticket ID, fetch via MCP |
| `#\d+` or URL containing `github.com/.*/pull/\d+` | GitHub PR | `gh pr view` |
| Everything else | Free text | Search codebase by keywords |

If no argument is provided, check conversation context for a recently mentioned
ticket or PR. If none found, ask: "What should I load context for?"

## Enrichment

For tool calls, parameters, and bounds, see [sources.md](sources.md).

Launch all applicable sources **in parallel** (single message, multiple tool calls).
Not every source applies to every input - skip what doesn't make sense.

### Step 1: Fetch primary source

Per the input type table above. This always runs first because it provides the
keywords and service identifiers for steps 2-4.

### Steps 2-4: Run in parallel after step 1

**2. AWS context.**
If step 1 extracted a Lambda function name or ECS service name, fetch service
config and recent error counts via `mcp__aws__call_aws`. Skip if no service
identifier was found in the primary source.

**3. Datadog context.**
If step 1 extracted a service identifier, query recent error events and top
error patterns via the `mcp__datadog__*` family. Skip if no service identifier
was found in the primary source.

**4. Grep codebase.**
Extract file paths or service names from the primary source. Grep for entry
points, models, settings. Read up to 8 files.

### Parallel execution

Steps 2, 3, and 4 are independent once step 1 completes. Launch all three
in a single message to minimize wall-clock time.

If the input is free text (no primary source to fetch), codebase search (step 4)
always runs using the free text as keywords. AWS (step 2) and Datadog (step 3)
only run if a service identifier can be inferred from the free text. If no
service identifier exists, only codebase search runs.

## Output

Present a Context Briefing to the user. Format:

```markdown
## Context Briefing: [topic, 3-8 words]

### Summary
[2-5 sentences: what this is about, current status, key context the user
needs to know. Include ticket status, assignee, and priority if from Jira.]

### Findings

| # | Finding | Source | Status |
|---|---------|--------|--------|
| 1 | [key fact from primary source] | Jira / PR | Confirmed |
| 2 | [AWS service state or recent errors] | AWS | Confirmed |
| 3 | [Datadog error pattern or quiet signal] | Datadog | Confirmed |
| 4 | [code pattern or dependency] | Codebase | Confirmed |
| 5 | [missing or unclear item] | (none) | Gap |

Aim for up to 5-10 findings when available. Each finding is one fact, attributed to its source.
Mark items that couldn't be verified as "Gap."

### Codebase References
[Files read with 1-line summary of what each contains. Entry points, models,
settings. Only include if codebase was searched.]

### Open Questions
[Unresolved items surfaced during enrichment. Missing context, unclear
requirements, suggested next actions. If no open questions, omit this section.]
```

If a source was unavailable, include the `[UNAVAILABLE: ...]` marker from
sources.md in the Summary section, not as a separate section.

## Rules

- **Factual context only.** Report what you found. Do not recommend approaches,
  judge quality, or suggest next steps (except in Open Questions, where you can
  note what's missing).
- **Verify code claims.** When the primary source says "the handler does X",
  grep/read the code to confirm before including it as a finding.
- **Parallel gathering.** Launch independent sources simultaneously. The user
  is waiting; wall-clock time matters more than token efficiency.
- **Respect bounds.** 5 Jira comments, 8 codebase files, 1 AWS service,
  24h Datadog window. See sources.md for the full bounds table.
- **Graceful degradation.** If a source fails, note it and continue. A partial
  briefing is better than no briefing.
- **Don't pad.** If the enrichment produces 3 findings, show 3 findings. Don't
  manufacture findings to fill a table. If the input is already well-understood
  and enrichment adds nothing, say so: "Context is minimal - this is a
  straightforward [type] with no related domain gotchas."
