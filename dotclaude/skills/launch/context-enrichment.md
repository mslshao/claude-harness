# Context Enrichment Protocol

Phase 1 of `/launch`. Transforms a Jira ticket (or bead/free text) into a
structured implementation brief suitable as input to the converge pipeline.

## Input Parsing

Detect the identifier type from the raw `/launch` arguments:

| Pattern | Type | Action |
|---------|------|--------|
| `MX2-\d+` | Jira ticket | Fetch via Atlassian MCP |
| `docr-\w+` | Bead ID | `bd show <id>`, extract linked Jira if present |
| URL matching `atlassian.net/browse` | Jira URL | Extract ticket ID, fetch via MCP |
| URL matching `slack.com/archives/` | Slack thread URL | Extract `<CHANNEL>` and message `<TS>` from URL path, then `slack_read_thread(channel=<CHANNEL>, thread_ts=<TS>)` |
| URL matching `atlassian.net/wiki/spaces/` | Confluence page URL | Extract `<PAGE_ID>` from `/pages/<PAGE_ID>/<slug>`, then `getConfluencePage(pageId=<PAGE_ID>)`. Common when the ticket points at a design doc. |
| `#\d+` or `gh pr` URL | PR reference | Fetch via `gh pr view` |
| Multi-line text with timestamp markers or speaker labels | Conversation transcript | Parse for problem framing; ignore turn-by-turn chatter |
| Everything else | Free text | Pass directly to prompt-refiner |

Mixed inputs are allowed. A `/launch` invocation can combine a Jira ticket
ID + a Slack URL + inline text; all are loaded and folded into the brief.

### Mixed-Input Precedence

When two sources disagree about problem framing (e.g., the Jira ticket
frames the ticket as a bug and a linked Slack thread frames it as a
design decision), resolve in this precedence order:

**inline text > Slack/transcript > Confluence > Jira/PR > bead notes**

Rationale: more recent/conversational inputs better reflect current
user intent. Surface the disagreement in the Phase 4 "Open Assumptions"
section so the user can correct if the precedence was wrong for their
case. The convergence delta narrative should explicitly note which
source was authoritative for the framing.

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
MX2-NNNNN): non-SF tickets carry content in `description` with
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

### 5. Classify INPUT_MODE (bias-detection)

After gathering all inputs, classify the request as one of:

- **`problem-framed`**: the input describes a problem to solve without
  committing to a mechanism. Example: "users are hitting X", "we need a
  better way to handle Y", "MX2-NNNNN says we should figure out Z". The
  implementation space is wide open.
- **`mechanism-prescribed`**: the input commits to a specific mechanism
  to build. Example: "add a Redshift query for X", "create a Fulfillment
  service to handle Y", "use approach Z to solve W". The user (or ticket
  author) has prescribed the noun before the planning pipeline has
  evaluated whether the noun fits.

Jira tickets routinely prescribe mechanisms ("Build a new Lambda for
X", "Add SQS queue Y"). The implementation pipeline must NOT
rubber-stamp the prescription; the canonical failure mode (the
Fulfillment-vs-Coverage class) is real commits and a real PR built on a
mechanism that should have been a feature of an existing noun, not a
new noun.

Capture `INPUT_MODE: problem-framed` or `INPUT_MODE: mechanism-prescribed`
in the implementation brief so Phase 3 challenge + consult subagents and
Phase 3.6 decision-maker gate receive it as input. Mechanism-prescribed
inputs trigger ENHANCED scrutiny:
- Phase 3 challenge: treat the prescribed mechanism as an explicit
  assumption to verify on first-principles grounds.
- Phase 3 consult: evaluate whether the prescribed mechanism is the
  right tool, not just whether it can be built.
- Phase 3.6 gate: if specialists rubber-stamped the prescription
  (DELTA_CATEGORY = CONFIRMED on a non-trivial mechanism-prescribed
  ticket), fire ITERATE with WEAK_DIMENSION = mechanism.

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

    --- SLACK / CONFLUENCE / TRANSCRIPT ---
    <thread excerpts, draft doc framing, conversation context if provided>

    --- CODEBASE CONTEXT ---
    <key file summaries, existing patterns, service structure>

    --- DOMAIN GOTCHAS ---
    <relevant beads memories>
```

## Output

The implementation brief (200-400 words) plus the `INPUT_MODE`
classification is passed to Phase 2 as the seed for the planning
pipeline. Not shown to the user.

Final structure of Phase 1 output:
```
INPUT_MODE: <problem-framed | mechanism-prescribed>

<implementation brief, 200-400 words>

LOADED_CONTEXT:
- Jira ticket: <key facts>
- Related beads: <list>
- Domain gotchas: <list>
- Source files read: <list>
```

If the brief is too vague (prompt-refiner couldn't extract clear scope
from the gathered context), stop and ask the user one focused question
to clarify. Do not proceed with an ambiguous brief - the plan quality
depends on it.

## Bead Acquisition + Stage Event Write

After producing the implementation brief, acquire the launch bead (see
[durable-state.md](durable-state.md) §Bead Acquisition) and write the
first `[LAUNCH_STAGE ...]` entry. This is the durability boundary: all
subsequent phases write stage events on completion.

```bash
# Acquire bead (existing logic from durable-state.md)
# ... results in $LAUNCH_BEAD_ID

# Stamp schema version
bd update "$LAUNCH_BEAD_ID" --set-metadata launch_skill_version=v1

# Write first stage entry
if [ "$BRIEF_SIZE" -lt 2048 ]; then
  # Inline brief
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=enrich round=0 status=loaded input_mode=$INPUT_MODE ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
else
  # Brief to scratch
  mkdir -p "$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID"
  BRIEF_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/enrich-0.md"
  echo "$BRIEF_CONTENT" > "$BRIEF_PATH"
  bd update "$LAUNCH_BEAD_ID" --append-notes \
    "[LAUNCH_STAGE stage=enrich round=0 status=loaded input_mode=$INPUT_MODE path=$BRIEF_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
fi
```

After this point, the orchestrator hands off to Phase 2 (decompose) in
[plan-pipeline.md](plan-pipeline.md).
