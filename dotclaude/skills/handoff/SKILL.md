---
name: handoff
description: End-of-session ritual. Audits personal configs (CLAUDE.md, hooks, agents, skills, memory files) against this session's learnings, then produces a copy-paste-ready cold-start handoff prompt for the next session. Use when the session is winding down, when the user says "audit configs", "handoff prompt", "handoff for new session", "/handoff", or when the user pastes a long audit-style prompt from notepad. Replaces ad-hoc invocations of prompt-refiner for handoff generation (prompt-refiner shapes rough input into precise prompts; it does not synthesize session context, which is why prior handoff prompts were sparse).
argument-hint: "[--audit-only | --prompt-only | --both (default)]"
---

# Handoff

End-of-session two-phase ritual.

**Phase 1**: audit personal configs against this session's learnings; apply trivial alignment fixes; propose substantive changes for user sign-off.

**Phase 2**: synthesize session context into a self-contained cold-start handoff prompt the user can paste into a new conversation.

Default mode runs both. Use `--audit-only` if leaving the session window open. Use `--prompt-only` if the audit was already done and only the handoff is needed.

## When to invoke

- User pastes a long audit-style prompt asking to review configs against session learnings.
- User asks for a "handoff prompt", "cold-start prompt", "handoff for new session", "what to tell the next session".
- Session is winding down on a substantive topic and the user is about to close.
- User explicitly types `/handoff`.

Do NOT route handoff prompt generation through `prompt-refiner`. That agent shapes rough user input into precise prompts; it does not walk multi-turn conversation context or query in-flight state across surfaces. Using it for handoffs produces compact, generic prompts that miss the session's actual deltas.

## Phase 1: Audit

Walk these categories. For each, identify (a) what this session changed in understanding, (b) what's actionable in the personal config, (c) the cost (trivial / proposes-for-signoff / not-worth-doing).

### Category 1: Communication style

- Corrections received this session (`bd memories correction:*:*` saved today)
- Calibration shifts (user clarified what a phrase means, or how to interpret something)
- Voice/register feedback (terse-vs-thorough, audience handling, formatting prefs)
- Recurring slips caught by structural enforcement (em-dash hook fires, em-dash chat-output slips)

Targets to check: `~/.claude/CLAUDE.md`, `~/.claude/projects/-workspaces-main/memory/feedback_*.md`, `~/.claude/projects/-workspaces-main/memory/pr-template.md`.

### Category 2: Workflow mechanics

- Verb-authorization patterns (what did/didn't get blocked by the auto-mode classifier, and was that the right call)
- Gating wins/misses (a safety mechanism fired when expected, or missed when it should have)
- Multi-window operational reality (any pattern that suggested attention fragmentation)
- Loop/wakeup patterns that surfaced in this session (was there ad-hoc work that should be codified)

Targets to check: `~/.claude/CLAUDE.md` Response Behavior, hook configs in `~/.claude/settings.json`, ScheduleWakeup usage patterns.

### Category 3: Mechanism alignment

- Hooks (`~/.claude/hooks/*.sh`) that diverged from a project rule during this session
- Agents (`~/.claude/agents/*.md`) with thresholds, names, or routing rules that drifted from project tier
- Personal/project skill pairs that fell out of sync after a session-level decision (e.g., threshold change at project tier without matching personal-tier update)

Targets to check: anywhere a numeric threshold, agent name, or routing rule appears in personal tier that ALSO appears in `/workspaces/main/.claude/rules/` or `/workspaces/main/.claude/agents/`.

### Category 4: Skill/agent gaps

- Patterns that recurred during the session without a dedicated tool (ad-hoc loops, ad-hoc synthesis steps, ad-hoc context loading)
- Agents that got dispatched for the wrong job (prompt-refiner for handoffs is the canonical case)
- Skills that the user invoked manually when an existing skill should have triggered automatically

Targets to check: `~/.claude/skills/`, `~/.claude/agents/`, the harness skill catalog.

### Application gate

For each finding:

- **Trivial alignment** (rule already exists, just needs a value tweak): apply directly, note it in the audit output.
- **New rule or substantive edit**: propose to the user; do NOT auto-apply.
- **Out-of-scope** (would warrant its own conversation): note as a follow-up bead candidate; do not act.

Save new correction memories via `bd remember --key="correction:<domain>:<topic>"`. Cite the umbrella memory if one exists (per the Reflection Trigger convergence rule).

## Phase 2: Cold-Start Handoff Prompt

### Step 1: Gather state across surfaces, in parallel

The handoff is only as fresh as its inputs. Do not synthesize from conversation context alone: that misses adjacent work the user owns that lives in beads, Slack, Jira, or Confluence but never got mentioned this session. Pull from every surface where in-flight state could live.

```bash
# Beads: in-flight tasks, today's corrections
bd list --status=in_progress --json | jq -r '.[] | "\(.id) \(.title)"'
bd memories correction: 2>/dev/null | grep "$(date -u +%Y-%m-%d)"

# GitHub: authored + review-requested + recent self-activity
gh pr list --author @me --state open --json number,title,isDraft,mergeStateStatus,reviewDecision
gh pr list --search "is:open review-requested:@me" --json number,title,author

# Worktrees
git -C /workspaces/main worktree list

# Any active ScheduleWakeup loops (no direct query; check conversation state)
```

For Slack, Jira, Confluence: use the MCP tools (`mcp__plugin_slack_slack__slack_search_public_and_private`, `mcp__atlassian__searchJiraIssuesUsingJql`, `mcp__atlassian__getConfluencePage`). Targeted queries, not exhaustive sweeps:

- **Slack: recent self-authored standups + open threads waiting on me.** `from:me` over last 7 days catches standup updates whose claims may have rotted (a PR I said was "open" may have merged, a design doc I said was "in progress" may have shipped). Also `to:me` and `is:thread` to find threads I haven't replied to.
- **Jira: tickets assigned to me, not yet Done.** `assignee = currentUser() AND status NOT IN (Done, Closed, Resolved, Cancelled)`. For tickets the session referenced explicitly, fetch the latest comment thread to confirm no new info landed after my last interaction.
- **Confluence: design docs referenced in recent standups.** If a Slack standup or bead points to a `<company>.atlassian.net/wiki/spaces/.../pages/<id>/...` URL, fetch the page to confirm status (DRAFT vs PUBLISHED vs ARCHIVED) and whether any new inline comments need response.

### Step 2: Cross-reference for adjacent context

This is the step that makes the handoff complete. The session you just had focused on a topic (call it T). The handoff's job is not to summarize T; it is to make sure the NEXT session knows EVERY in-flight thing the user owns, whether or not T touched it.

For each item surfaced in Step 1, ask:

- **Does it appear in the current session's working memory?** If yes, the focus already covers it.
- **If no, would it be lost without the handoff?** A bead that's been in-progress for two weeks with no movement IS in-flight, even if nothing happened this session. A design doc whose state changed since the last standup IS adjacent. A Jira ticket with a new comment from a stakeholder IS adjacent.

Pull every "no but yes-to-lose" item into the handoff's **ADJACENT IN-FLIGHT WORK** section (see template). Do not pad with cold beads or stale tickets that genuinely require no action.

### Step 3: Synthesize into the template

Substitute placeholders; drop sections that genuinely don't apply (do NOT include empty sections as boilerplate).

### Cold-start template

```
SESSION HANDOFF: [topic, 3-8 words]

CONTEXT
[2-4 sentences: what we worked on, the load-bearing decisions, and where we left off. Lead with the most recent piece of substance, not chronology.]

IN-FLIGHT STATE
- Active beads:
  - docr-XXXX: [title] (status: in_progress, [one-line note])
- Open PRs (authored):
  - #XXXX [title] (draft | published, [state: in CI / awaiting review / merged])
- Open PRs (review-requested):
  - #XXXX [title] (from <author>, [my read so far if any])
- Active worktrees (outside main checkout):
  - <path> (<branch>, <purpose>)

CALIBRATION SHIFTS THIS SESSION
[List corrections saved THIS session, one line each with the rule body, not just the key.]
- correction:<domain>:<topic>: <one-line rule body>, not just the key

SUGGESTED FIRST ACTIONS
- Run `bd ready` to surface unblocked work
- Read `bd show <bead-id>` for the active item
- [Any domain-specific pointer that matters for the next move]

NOTABLE FILES TOUCHED OR EDITED THIS SESSION
[Only files meaningfully changed THIS session, not a directory listing.]
- <path>: <one-line description of the change>

OPEN ASKS WAITING FOR ME
[Anything where the next move is mine and would be lost without re-deriving.]
- [item]

ADJACENT IN-FLIGHT WORK (not session focus, surfaced via cross-reference)
[Items owned by me in beads/Slack/Jira/Confluence that the current session did NOT
touch, but where the next session would otherwise lose context. Each item: one line
naming the artifact and current state. Drop this whole section if nothing surfaced.]
- [bead-id | jira-key | confluence-page-id | slack-thread-link]: <state, one line>
```

Wrap the template in a fenced code block in the output so the user can copy-paste cleanly.

## Principles

- **Audit fixes apply to the CURRENT session.** Handoff prompt is for the NEXT.
- **Cross-surface freshness is not optional.** Beads, GitHub, Slack, Jira, Confluence are all sources of in-flight state. The handoff is incomplete if it only reflects the conversation. Pull from every surface; cross-reference for adjacent work; surface anything that would be lost.
- **Don't pad.** If a section has nothing to say, drop it. A boilerplate-heavy handoff buries the actual deltas. The cross-surface rule above produces ADDITIONS only when genuine adjacent work exists; cold beads and stale tickets get dropped.
- **Reference durable artifacts.** Beads, PR numbers, commit SHAs, Jira keys, Confluence page IDs, memory keys. The next session fetches fresh state from these; the handoff just points the way.
- **Test the prompt.** Read your own output as if you were a cold-start agent: would you know what to do next? If you'd ask "what's the active topic" or "where did we leave off", the prompt failed.
- **Substantive over comprehensive.** A 15-line handoff that names the active topic, the in-flight PR, and the one calibration shift that matters is better than a 60-line dump of every bead in the repo.
- **No personal-tier paths in shared-artifact-bound output.** The handoff prompt itself stays local (user pastes it into their own new session), but if the user is going to paste it into anything shared, scrub bead IDs and personal paths first.

## Anti-patterns

- Routing through `prompt-refiner`. That agent does not synthesize session context.
- Generating audit findings that "should be done at some point" without a clear gate (trivial-apply, propose, or defer).
- Listing every bead in `bd list` rather than only in-flight items.
- Emitting calibration shifts as memory keys without their body (the next session can't look them up if the key is wrong; include the rule itself).
- Adding boilerplate like "remember to be helpful" or "follow the rules" to the handoff. The next session already has CLAUDE.md.
- Synthesizing from conversation context only. Beads, Slack, Jira, and Confluence all hold in-flight state the conversation may not have surfaced. Skipping the cross-surface gather (Step 1) and cross-reference (Step 2) produces a handoff that LOOKS complete but silently drops adjacent work; the next session re-derives it the hard way.

## Output format

Run Phase 1, then Phase 2 (unless mode flag scopes one out).

Phase 1 output: structured audit with category headers, applied changes, and proposed changes.

Phase 2 output: a single fenced code block containing the cold-start handoff prompt, ready to copy.

End with a one-line summary of what was applied automatically and what's awaiting user sign-off.
