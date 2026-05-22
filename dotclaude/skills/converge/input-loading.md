# Phase 1: Refine - Input Loading and Context Enrichment

This file holds the heavy Phase 1 reference content for `/converge`.
SKILL.md references it; do not duplicate content back into SKILL.md.

## Step 0: Load All Inputs

Detect input types in the raw invocation and load each. URLs need ID
extraction before MCP calls:

- **Jira ticket ID** (`MX2-\d+`): fetch via Atlassian MCP
  (`getJiraIssue`). Pull description, AC, comments.
- **Bead ID** (`docr-\w+`): run `bd show <id>` to load description,
  notes, dependencies.
- **Slack URL** (`https://*.slack.com/archives/<CHANNEL>/p<TS>` or
  `/archives/<CHANNEL>/<TS>`): extract the channel ID and message
  timestamp from the URL path, then call
  `slack_read_thread(channel=<CHANNEL>, thread_ts=<TS>)`. For pasted
  thread excerpts (no URL), use the text as-is.
- **Confluence URL**
  (`*.atlassian.net/wiki/spaces/<SPACE>/pages/<PAGE_ID>/<slug>`):
  extract the numeric `<PAGE_ID>` from the URL path, then call
  `getConfluencePage(pageId=<PAGE_ID>)`. For pasted page bodies, use
  the text as-is.
- **PR reference** (`#\d+` or `gh pr` URL): fetch via `gh pr view`.
- **Conversation transcript** (multi-line text with timestamp markers
  or speaker labels): parse to extract problem framing and prior
  attempts; ignore turn-by-turn chatter.
- **Free-text rough idea**: most common. Pass through.

### Mixed-Input Precedence

When two sources disagree about problem framing, resolve in this
precedence order:

**inline text > Slack/transcript > Confluence > Jira/PR > bead notes**

Rationale: more recent/conversational inputs better reflect current
user intent. Surface the disagreement in Phase 5 "Open Assumptions"
so the user can correct if the precedence was wrong for their case.

### Bias-Detection (INPUT_MODE Classification)

`/converge` takes ONE approach as input by design, so we do NOT fully
strip the user's solution-thinking the way `/ideate` does. BUT we DO
detect whether the input is:

- **Problem-framed**: "we need to handle X better" / "users are hitting
  Y" / "MX2-NNNNN says we should figure out Z". The plan space is wide
  open.
- **Mechanism-prescribed**: "add a Redshift query that does X" / "build
  a Fulfillment service" / "use approach Y to solve Z". The user has
  committed to a mechanism.

Mechanism-prescribed inputs trigger ENHANCED scrutiny in Phase 3
(Challenge + Consult) on whether the prescribed mechanism is the RIGHT
mechanism. If the specialists recommend a different mechanism, the
convergence delta categorization (see Phase 4) should reflect a
MAJOR_REVISIONS or SCRAPPED_AND_REBUILT outcome rather than minor
tweaks. This is the canonical Fulfillment-vs-Coverage failure mode:
user prescribed a noun ("Fulfillment service") that should have been
a feature of an existing noun ("Coverage"), and convergence dutifully
refined the wrong noun without flagging the prescription.

Capture the input's framing mode as `INPUT_MODE: problem-framed` or
`INPUT_MODE: mechanism-prescribed` in the refined scope so Phase 3
subagents and Phase 4.6 gate know what to scrutinize.

## Step 1: Pre-load Domain Context

Best-effort, not a gate. Before extracting intent, surface existing
terminology from bead memories so Phase 2 enters with prior decisions
in hand. Run the domain-matcher to infer domain keywords from the
rough input:

```bash
bash /home/vscode/.claude/scratch/domain-matcher/match.sh "<user input>" \
  | cut -d: -f1 | head -10
```

For each matched keyword, run `bd memories <keyword>` and skim the top
5 results. If the input names a known service (e.g., `<service>`, `folio`,
`salesforce`, `metadata_updater`) or a path under
`src/python/mx2/<service>/`, also read the service-level `CLAUDE.md`
when one exists.

**Quality bar.** Best-effort context loader, not a gate. The matcher's
calibration is ~79% recall / ~82% precision (n=18 baseline); misfires
are expected. If the matcher returns no results, returns tokens that
look like noise, or fails to run, skip pre-load and continue. A
misfire must NOT block convergence.

Fold pre-loaded results into the refined scope under a
`Loaded context:` heading listing matched keywords, the bead-memory
entries surfaced, and any service-level `CLAUDE.md` excerpts read.
Phase 2 cites this section when checking for terminology collisions.

## Step 2: Extract Intent

Identify the core goal, implicit context (check conversation history,
git state, active beads), and scope signals from the loaded inputs.

## Step 3: Gather Context

Use tools. `git status` / `git diff` for current work state. Grep the
codebase if the idea mentions functionality by name. Read CLAUDE.md
for project rules.

### Sibling-Bead Sweep (Mandatory, Not Optional)

Always run `bd list --status=in_progress`. For EVERY returned bead
whose title or description contains a domain keyword from the input OR
any of architecture/decision/converge/Path/refactor, run
`bd show <id>` and capture the ratified-decision section into the
`Loaded context:` heading from step 1.

These are not "in-flight work I might collide with"; they are the
RATIFIED ARCHITECTURAL DECISIONS that supersede any plan formed fresh.
The Epic-first check from CLAUDE.md is necessary but not sufficient:
parent-only checks miss sibling beads under different epics in the
same domain. The decision-bearing bead often lives in a sibling epic,
not the nominal-parent epic of the current ticket.

**Recurrence note**: 2026-05-19 <service>-self-containment session
converged through six wrong directions because docr-b7xa's ratified
Path B decision (in a sibling epic MX2-NNNNN, not the nominal-parent
MX2-NNNNN) was never loaded. The decision lived in the bead
description, not in `bd remember`, so `bd memories <keyword>` did not
surface it. `bd list --status=in_progress` + `bd show` is the only
path that catches this class.

## Step 4: Enrich (when references detected)

If the input mentions a Jira ticket (`MX2-\d+`), bead ID (`docr-\w+`),
or PR number (`#\d+`), the Step 0 input loading should have already
fetched them. Additionally:

- Run `bd search <keywords>` from the ticket/bead title (top 5 results)
- Run `bd memories <keyword>` with service name or domain (top 10
  matches)
- Fold all results into the refined scope as structured context

This replaces the need for a manual `/enrich` call before `/converge`.

## Step 5: Expand Specificity

Name files, functions, patterns, and constraints. Include context the
LLM needs that the user takes for granted.

## Output

Phase 1 produces an internal "refined scope" document with:

- Refined problem statement (1-3 sentences with constraints surfaced)
- `Loaded context:` heading with matched keywords + bead memories +
  service-level CLAUDE.md excerpts + ratified architectural decisions
  from sibling-bead sweep
- `INPUT_MODE:` classification (`problem-framed` or
  `mechanism-prescribed`)

Not shown to user. Phase 2 (Scope & Decompose) consumes this directly.
