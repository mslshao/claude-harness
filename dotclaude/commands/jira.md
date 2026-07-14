---
description: (personal; shadows the project-tier `jira` command and takes precedence) Delta: adds batch mode (multiple tickets from a draft file) on top of single interactive creation. Create one or more Jira tickets (single interactive, or batch from a draft file)
allowed-tools: Bash(git:*), mcp__atlassian__atlassianUserInfo, mcp__atlassian__getAccessibleAtlassianResources, mcp__atlassian__createJiraIssue, mcp__atlassian__editJiraIssue, mcp__atlassian__getIssueLinkTypes, mcp__atlassian__createIssueLink
---

# Create Jira Ticket(s)

Personal-tier override of the project `/jira` skill. Mirrors the single-ticket interactive flow, adds a batch mode for filing related ticket sets in parallel.

Run as:
- `/jira` : infer ticket content from the current branch
- `/jira <description>` : single ticket from the provided description
- `/jira batch <draft-path>` : multi-ticket batch from a YAML draft file (NEW in personal tier)

Branch context (git log, diff stats) is always collected in parallel and used to supplement ticket creation, regardless of mode.

## Pre-flight: pre-check stakeholder-facing text

Before drafting ANY ticket body for human review, pre-check the draft through:

```bash
echo "$DRAFT_BODY" | /home/vscode/.claude/scratch/scripts/check-stakeholder-text.sh
```

Non-zero exit means em-dashes (banned per CLAUDE.md Writing Style) or personal-tier vocab (bead, bd CLI, /personal-skill, docr-* IDs) are present. Fix BEFORE presenting the draft so the user sees clean content, and BEFORE submitting so the PreToolUse hooks do not block mid-batch.

This pre-check is the earlier guardrail; `block-em-dash.sh` and `block-personal-tier-vocab.sh` are the last-resort backstop.

## Steps (single-ticket mode: no `batch` arg)

### 1. Understand the work

If `$ARGUMENTS` is non-empty AND the first token is not `batch`, use the description as the primary basis for the ticket. Interpret in context of the current conversation.

If `$ARGUMENTS` is empty, infer from the current branch. Run in parallel:
- `git branch --show-current`
- `git log main...HEAD --oneline`
- `git diff main...HEAD --stat`

Always collect branch context (per PR #9340 clarification). When `$ARGUMENTS` is provided, branch context supplements; when absent, branch context is the sole input.

Check for an existing ticket ID in branch name or commits (pattern `MX2-\d+`). If found, stop, no new ticket needed.

### 2. Resolve API dependencies (parallel)

- `mcp__atlassian__atlassianUserInfo` for current user's account ID
- `mcp__atlassian__getAccessibleAtlassianResources` for cloudId

### 3. Draft the ticket

Draft:
- **Summary**: one concise sentence
- **Description**: 2 to 4 sentences covering what and why
- **Issue type**: default Task; Bug if clearly a fix; Story for new service or feature
- **Project**: MX2
- **Assignee**: current user by default
- **Component (owning scrum team)**: REQUIRED for board visibility. Infer the owning team from the work's domain and the current conversation; default to the user's team (Jesup) when unclear. The MX2 Sprint board filters on Components, so a ticket with none does not appear on the board.
- **Label (domain)**: the domain label (e.g. `<service>`), also board-filtered. Infer from the work's domain; ask only if genuinely ambiguous.

See the "Board visibility" section of `memory/jira.md` for the rule and the verified component ids per team.

**Attribution**: every drafted description ends with the paragraph `Generated using the Claude Code /jira skill.`

**Pre-check the draft body** with check-stakeholder-text.sh before presenting.

Show to user. Confirm or edit before creating.

### 4. Create

Use `mcp__atlassian__createJiraIssue` with the cloudId. ADF format for `description`:

```json
{
  "type": "doc",
  "version": 1,
  "content": [
    { "type": "paragraph", "content": [{ "type": "text", "text": "..." }] },
    { "type": "paragraph", "content": [{ "type": "text", "text": "Generated using the Claude Code /jira skill." }] }
  ]
}
```

**customfield_11220**:
- Salesforce issue types (`Bug - Salesforce`, `Story - Salesforce`): mirror the attributed ADF doc from `description`
- All other types (Task, Story, Bug): empty ADF doc `{ "type": "doc", "version": 1, "content": [] }`. Do not omit; Jira fills a verbose placeholder otherwise.

Set `assignee_account_id` to current user's account ID.

**Label + Components (board visibility, required).** `createJiraIssue` drops `labels` on essentially every create and never sets `components` from the draft. Do NOT rely on passing `labels` in the create payload (it will not stick); ALWAYS issue a follow-up `editJiraIssue {"labels": [<domain label>], "components": [{"id": "<team component id>"}], "customfield_11220": <empty ADF>}` as a mandatory second step (component ids per the "Board visibility" section of `memory/jira.md`; Jesup=11049). Treat this as unconditional, not verify-then-maybe-reapply. Skipping it leaves the ticket off the Sprint board.

### 5. Output

Print the created ticket ID. If created from current branch, suggest renaming to include the ticket ID for `/pr` pickup.

## Steps (batch mode: `/jira batch <draft-path>`)

### 1. Read the draft file

The draft is a YAML file at `<draft-path>` with the following shape:

```yaml
parent: MX2-NNNNN              # optional: shared parent epic for all tickets
tickets:
  - summary: "Phase 1: Foo"
    description: |
      Multi-line markdown description body.
    issue_type: Task            # optional; default Task
    parent: MX2-XXXXX           # optional per-ticket override
    priority: Medium            # optional; default Medium
    component: Jesup            # owning scrum team (board visibility); default Jesup if omitted
    label: <service>               # domain label (board visibility)
    links:                      # optional outgoing Blocks links to other tickets
      blocks:
        - phase_2_id            # symbolic reference resolved after creation
                                # OR a literal MX2-NNNNN to link to existing tickets
    id_ref: phase_1_id          # optional symbolic ID for cross-references
```

Symbolic IDs (`phase_1_id`) are resolved after all tickets are created so blocks-links can reference siblings created in the same batch.

### 2. Validate all draft bodies through the pre-check

For each ticket in the draft:

```bash
echo "$summary"$'\n'"$description" | /home/vscode/.claude/scratch/scripts/check-stakeholder-text.sh
```

If ANY ticket fails the pre-check, surface ALL failures to the user, do NOT proceed. The batch should be clean before any MCP call.

### 3. Resolve cloudId + account ID once (shared across batch)

Same parallel calls as single-ticket mode. Cached for the batch.

### 4. Confirm the batch with the user

Show the full list (summary + first line of description per ticket) plus the link graph. Ask for confirm before filing.

### 5. Create tickets in parallel

Issue all `createJiraIssue` calls in ONE message with multiple tool blocks. Capture the returned MX2-NNNNN keys, mapping each symbolic `id_ref` to its real key.

**Per-ticket fields preserved** (see `memory/jira.md` "Editing tickets" section): assignee, parent, customfield_11220 (empty ADF for non-SF types or mirrored for SF types), priority.

**Board-visibility fields (batch).** After the parallel creates, set each ticket's domain Label and owning-team Component (from the draft's `label` / `component`, defaulting Component to Jesup) via follow-up `editJiraIssue` calls in one parallel message, since `createJiraIssue` drops labels and does not set components. Verify on read-back. Per the "Board visibility" section of `memory/jira.md`.

### 6. File issue links in parallel

After all tickets are created, file all Blocks links in ONE message with multiple `createIssueLink` calls. Resolve symbolic IDs to real keys.

Per tool schema:
- `inwardIssue` = blocker
- `outwardIssue` = blocked

When ticket A blocks ticket B, pass `inwardIssue: A_key, outwardIssue: B_key, type: "Blocks"`.

### 7. Verify and report

Run a single JQL: `parent = <parent-epic> AND key in (created keys)` to confirm all landed. Print the final mapping table (symbolic ID, MX2 key, summary, blocks-relationships).

## When to use batch mode

- A ratified design (Confluence, RFC, design doc) lands with a phase or milestone table; populate the epic from it
- A series of dependent work items needs to be filed at once
- The single-ticket flow would require N round-trips

When you only need 1 or 2 tickets, single-ticket mode is faster.

## Editing existing tickets

Before any `editJiraIssue` call, load `memory/jira.md` and follow the "Editing tickets: fields to preserve" table. Missing fields are nulled by the MCP, not preserved.

Pre-check edited bodies through `check-stakeholder-text.sh` the same way as creates.

## Notes

- Never invent or guess a ticket ID; only use IDs returned by the API
- Always confirm drafts with the user before creating
- If MCP is unavailable, surface the draft so the user can create manually
