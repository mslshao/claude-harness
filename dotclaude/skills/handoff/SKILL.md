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

Gather in-flight state across surfaces, in parallel:

```bash
# In-flight beads
bd list --status=in_progress --json | jq -r '.[] | "\(.id) \(.title)"'

# Open PRs I authored
gh pr list --author @me --state open --json number,title,isDraft,url --jq '.[] | "\(.number) \(.title) (draft=\(.isDraft))"'

# Open PRs awaiting my review
gh pr list --review-requested @me --state open --json number,title,url

# Active worktrees
git -C /workspaces/main worktree list

# Corrections saved this session (today's date in UTC)
bd memories correction: 2>/dev/null | grep "$(date -u +%Y-%m-%d)"

# Any active ScheduleWakeup loops (note: cannot query directly; check conversation state)
```

Synthesize into the template below. Substitute placeholders; drop sections that genuinely don't apply (do NOT include empty sections as boilerplate).

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
```

Wrap the template in a fenced code block in the output so the user can copy-paste cleanly.

## Principles

- **Audit fixes apply to the CURRENT session.** Handoff prompt is for the NEXT.
- **Don't pad.** If a section has nothing to say, drop it. A boilerplate-heavy handoff buries the actual deltas.
- **Reference durable artifacts.** Beads, PR numbers, commit SHAs, memory keys. The next session fetches fresh state from these; the handoff just points the way.
- **Test the prompt.** Read your own output as if you were a cold-start agent: would you know what to do next? If you'd ask "what's the active topic" or "where did we leave off", the prompt failed.
- **Substantive over comprehensive.** A 15-line handoff that names the active topic, the in-flight PR, and the one calibration shift that matters is better than a 60-line dump of every bead in the repo.
- **No personal-tier paths in shared-artifact-bound output.** The handoff prompt itself stays local (user pastes it into their own new session), but if the user is going to paste it into anything shared, scrub bead IDs and personal paths first.

## Anti-patterns

- Routing through `prompt-refiner`. That agent does not synthesize session context.
- Generating audit findings that "should be done at some point" without a clear gate (trivial-apply, propose, or defer).
- Listing every bead in `bd list` rather than only in-flight items.
- Emitting calibration shifts as memory keys without their body (the next session can't look them up if the key is wrong; include the rule itself).
- Adding boilerplate like "remember to be helpful" or "follow the rules" to the handoff. The next session already has CLAUDE.md.

## Output format

Run Phase 1, then Phase 2 (unless mode flag scopes one out).

Phase 1 output: structured audit with category headers, applied changes, and proposed changes.

Phase 2 output: a single fenced code block containing the cold-start handoff prompt, ready to copy.

End with a one-line summary of what was applied automatically and what's awaiting user sign-off.
