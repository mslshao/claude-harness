---
name: enrich
description: >
  Context loader for Jira tickets, beads, PRs, or topics. Gathers ticket details,
  related beads, codebase references, and domain knowledge into a structured
  briefing. Use when the user asks about a ticket, wants context before running
  /challenge or /consult, needs a briefing for meeting prep, or wants to understand
  what a bead or PR involves. Trigger on: "what's the context on", "brief me on",
  "enrich", "load ticket", "what do we know about", any Jira ticket ID or bead ID
  pasted without other instructions.
argument-hint: "[MX2-XXXXX | docr-XXXX | #1234 | topic]"
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
| `docr-\w+` | Bead ID | `bd show`, also fetch linked Jira if referenced |
| `#\d+` or URL containing `github.com/.*/pull/\d+` | GitHub PR | `gh pr view` |
| Everything else | Free text | Search beads and codebase by keywords |

If no argument is provided, check conversation context for a recently mentioned
ticket, bead, or PR. If none found, ask: "What should I load context for?"

## Enrichment

For tool calls, parameters, and bounds, see [sources.md](sources.md).

Launch all applicable sources **in parallel** (single message, multiple tool calls).
Not every source applies to every input - skip what doesn't make sense.

### Step 1: Fetch primary source

Per the input type table above. This always runs first because it provides the
keywords for steps 2-4.

### Steps 2-4: Run in parallel after step 1

**2. Discover related beads.**
Extract keywords from the primary source (ticket summary, bead title, PR title).
Run `bd search <keywords>`. Take top 5 results. Load each with `bd show`.

**3. Check beads memories.**
Run `bd memories <keyword>` with 1-3 terms: service name, domain, ticket ID.
Take first 10 matches.

**4. Grep codebase.**
Extract file paths or service names from the primary source. Grep for entry
points, models, settings. Read up to 8 files.

### Parallel execution

Steps 2, 3, and 4 are independent once step 1 completes. Launch all three
in a single message to minimize wall-clock time.

If the input is free text (no primary source to fetch), run all four steps
in parallel using the free text as keywords.

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
| 1 | [key fact from primary source] | Jira / Bead / PR | Confirmed |
| 2 | [related context from beads] | Bead docr-xxxx | Confirmed |
| 3 | [domain gotcha from memories] | Memory | Confirmed |
| 4 | [code pattern or dependency] | Codebase | Confirmed |
| 5 | [missing or unclear item] | (none) | Gap |

Include 5-10 findings. Each finding is one fact, attributed to its source.
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

## Boundary with /pr-intel

`/enrich` and `/pr-intel` both take a PR number as input but serve different
purposes:

- `/enrich #1234` produces **background context**: what the PR changes, related
  tickets, codebase references, domain knowledge. Useful for understanding what
  you're about to review.
- `/pr-intel #1234` produces **review analysis**: quality assessment, specialist
  findings, draft inline comments, verdict. Useful for conducting the review.

If the user asks to "review" a PR, use `/pr-intel`. If they ask "what is this
PR about" or need context before reviewing, use `/enrich`.

## Rules

- **Factual context only.** Report what you found. Do not recommend approaches,
  judge quality, or suggest next steps (except in Open Questions, where you can
  note what's missing).
- **Verify code claims.** When the primary source says "the handler does X",
  grep/read the code to confirm before including it as a finding.
- **Parallel gathering.** Launch independent sources simultaneously. The user
  is waiting; wall-clock time matters more than token efficiency.
- **Respect bounds.** 5 Jira comments, 5 bead search results, 10 memory matches,
  8 codebase files. See sources.md for the full bounds table.
- **Graceful degradation.** If a source fails, note it and continue. A partial
  briefing is better than no briefing.
- **Don't pad.** If the enrichment produces 3 findings, show 3 findings. Don't
  manufacture findings to fill a table. If the input is already well-understood
  and enrichment adds nothing, say so: "Context is minimal - this is a
  straightforward [type] with no related beads or domain gotchas."
