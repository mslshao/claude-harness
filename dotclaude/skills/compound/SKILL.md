---
name: compound
description: "Improvement loop: scan a just-completed work unit for session friction signals (blocked tool calls, redo edits, manual user actions a skill could automate, round-trip confirms), generate concrete buildable improvements grounded in those signals, and build the change directly (with present-and-confirm gate) or dispatch a build subagent. Falls back to habit-memory capture only when no buildable improvement exists. Use after a PR merges, a /launch ships, a bead closes, a multi-step investigation wraps, or a substantial work unit just shipped. The proactive sibling to /reflect (correction-triggered). Trigger phrases: '/compound', 'extract patterns', 'what did we learn from that', 'identify improvements', 'capture this workflow', 'compound that', 'what was friction here', 'pattern-capture'. Distinct from /handoff (cold-start prompt for the NEXT session) and direct `bd remember` (no synthesis, no dedup, no build path)."
argument-hint: "[optional: short hint about what just finished, e.g. 'launch of docr-XXXX' or 'PR #YYYY merged' or 'early' if mid-session]"
---

# Compound

Improvement loop: identify concrete buildable changes that would reduce future friction, then build them. The previous version of this skill captured generic patterns into habit memories that drained slowly; the new version drives toward an actual edit on a real surface (hook, skill, agent, rule file, settings.json, memory section). Habit-memory capture remains as a fallback when no buildable improvement exists, so soft-signal patterns are not lost.

This skill is the **proactive** half of pattern capture. Its reactive sibling is `/reflect`, which fires on user corrections (CLAUDE.md Reflection Trigger). `/compound` fires after work where things went smoothly enough that /reflect did not trigger, but where friction signals from the session reveal a specific improvement the next instance would benefit from.

## Why this exists

The pattern-capture pipeline had a coverage gap. `/reflect` catches mistakes (correction-triggered, writes to `correction:*` memories and rule files). `/bead-forge` checkpoint mode preserves in-flight conversation context against compaction. `/handoff` produces a cold-start prompt for ONE specific next session.

The previous `/compound` tried to fill the rest of the gap with three static socratic questions ("what was non-obvious?", "would you repeat it?", "what would speed it up?"). In practice this produced habit memories that captured "something" without a goal, drained into workflow.md slowly, and rarely changed behavior. The promotion gate worked; the input signal did not.

The new shape: scan the session transcript for actual friction signals, ground every improvement candidate in a specific observed event, and drive toward a buildable edit. The corpus of habit memories still exists as a fallback, but the primary output is a concrete artifact change.

## When to invoke

Manual only in v1. Triggers:

- User explicitly types `/compound` or asks "identify improvements", "what was friction here", "extract the pattern", "what's reusable".
- After a substantial completion signal (draft PR published, `/launch` returned, bead closed, multi-step investigation wrapped) AND the session contains observable friction (hook fires, redo edits, manual user actions, round-trip confirms).
- After a multi-exchange session where the user deliberately landed on a non-obvious technique that would replicate.

The "early" arg signals the work is mid-flight but the current sub-unit just shipped; that is a valid invocation point.

## When NOT to use

- **Every PR or bead close.** Routine work without friction signals has nothing to compound.
- **The work was a correction.** Use `/reflect`. /compound captures what worked or what could work better; /reflect captures what failed and codifies the avoidance.
- **The next-session handoff is what is needed.** Use `/handoff`. /handoff produces a cold-start prompt for one specific successor; /compound produces edits to durable surfaces that affect many future sessions.
- **A specific fact, not a pattern or improvement.** Use `bd remember` directly.
- **Mid-flight checkpoint of conversation context.** Use `/bead-forge` in memory checkpoint mode. /compound is for shipped work, not in-progress analysis.

## Workflow

### 1. Scope detection

Determine what work unit just completed. Pull from every surface where a completion signal could live. Run these in parallel:

**Local (bash)**:

```bash
bd list --status=in_progress --json | jq -r '.[] | "\(.id) \(.title)"'
git log --since='6 hours ago' --oneline -20
gh pr list --author @me --state all --limit 5 --json number,title,state,updatedAt
```

**External (MCP)**:

- **Jira**: tickets I created, edited, or commented on recently. JQL: `assignee = currentUser() AND updated >= -1d`. Tool: `mcp__atlassian__searchJiraIssuesUsingJql`.
- **Confluence**: pages I edited in the last day. CQL: `contributor = currentUser() AND lastmodified > now("-1d")`. Tool: `mcp__atlassian__searchConfluenceUsingCql`.
- **Slack**: my recent messages where a technique, design, or bugfix approach got worked out. Query: `from:me` over the last 6 hours. Tool: `mcp__plugin_slack_slack__slack_search_public_and_private`.

Cross-reference against conversation context. If the user passed an anchor in the argument hint, take it and skip detection.

If signals are empty OR multiple candidate work units surface with no clear anchor, ask ONE focused question: "What just finished?" Do not invent a work unit.

### 2. Friction scan (REPLACES the previous static socratic questions)

Inspect the session transcript for observable friction signals. These are the ground truth for the improvement candidates that follow. Look for:

| Signal class | What to look for | Buildable shape |
|---|---|---|
| **Hook fire** | A PreToolUse hook blocked a tool call; I re-issued with a fix. Look for "BLOCKED:" stderr in tool results, Stop hook feedback messages. | Pre-output check earlier in the flow (a lint script invoked before the tool call); or a wordlist consolidation; or a skill update that teaches me the rule before drafting. |
| **Redo edit** | I edited a file, then immediately edited it again to fix something I should have gotten right the first time. Look for two Edits to the same file path within a few turns. | A linter, a template, or a skill section that teaches the gotcha. |
| **Field-nulling gotcha** | An MCP edit operation cleared a field I did not intend to clear (assignee, parent, link, custom field). Visible as a follow-up "fix the field" call after the main edit. | Documented "preserve" list in the relevant memory file or skill; optional MCP wrapper that auto-includes the preservation set. |
| **Manual user action** | The user said "go verify", "I updated the doc, check it", "I'll handle X", "go check that I did this right". | Automation: do the verification automatically, or make the next-step a skill action. |
| **Round-trip confirm** | I asked the user to confirm something I could have predicted from conversation context (e.g., "should I use the same convention?", "is this the right naming?"). | Add the convention to the relevant memory file or skill so the next instance does not have to ask. |
| **Tool retry** | A tool call failed, I retried with a fix. Look for error responses followed by a corrected call. | Validate the input shape before calling; or document the schema gotcha. |
| **Recurring memory hit** | Same `correction:*` or `habit:*` memory referenced multiple times in the session. | Promote the memory: codify as a rule (if correction), promote to workflow.md (if habit with 2nd observation). |
| **Skill gap** | I worked around a missing skill capability (e.g., batched calls manually because the skill is single-item). | Extend the skill; or mirror as a personal-tier override that adds the capability. |
| **Manual cross-reference** | I built a cross-link by hand (Jira issue links, design-doc-to-ticket map, parent-child structure). | Automate as part of the originating skill (e.g., file Blocks links when creating sibling tickets). |

For each signal observed, name it specifically: cite the turn or tool call where it appeared, what the round-trip cost was, what the buildable fix is. The output of step 2 is a list of grounded candidates, not generic questions.

**Empty signal case**: if the scan finds no friction signals OR all signals are duplicates of existing rules/memories, the session was routine and no improvement is captureable. Stop the workflow, OR fall through to step 5b (habit-memory fallback) if conversation context surfaces a pattern worth recording as a soft signal.

**Misroute check**: if the signal is correction-shaped (user explicitly corrected something the agent did wrong) and the umbrella memory already exists with structural enforcement (hook, linter, gate), do NOT compound it. The hook is the enforcement; tallying another instance is not a corrective action. This mirrors CLAUDE.md Reflection Trigger Step 5.

### 3. Triage and dedup

For each candidate from step 2, score on two axes:

- **Build feasibility**: how big is the edit? One-line hook tweak, paragraph addition to a memory file, new section in a skill, new skill, new agent. Small surfaces (< ~30 lines) can be built directly; larger surfaces dispatch a build subagent.
- **Blast radius**: personal-tier (hook, skill, memory) vs. project-tier (`.claude/rules/`, project skill, CLAUDE.md). Personal-tier changes ship without review; project-tier go through the lab-to-production promotion path.

Then dedup at every tier so we do not double-write or duplicate existing coverage. Derive 2-3 distinctive keywords per candidate; set both vars before running:

```bash
KW_TEXT="<2-3 keywords as a space-separated phrase>"
KW_GREP="<same keywords as a pipe-separated regex>"

bd memories habit:                                                                    # habit-tier
bd memories correction:                                                                # correction-tier (recurring slips)
bd list --label=memory --status=open --json | jq -r '.[] | "\(.id) \(.title)"'        # forge memory beads
grep -iE "$KW_GREP" ~/.claude/projects/-workspaces-main/memory/workflow.md
grep -riE "$KW_GREP" ~/.claude/projects/-workspaces-main/memory/*.md
grep -riE "$KW_GREP" /workspaces/main/.claude/rules/
grep -riE "$KW_GREP" /workspaces/main/CLAUDE.md ~/.claude/CLAUDE.md
# When the candidate's likely destination is a skill/agent/hook, ALSO grep that
# artifact's whole directory: prior coverage often lives in a SUB-FILE the
# memory/rules greps above never touch (missed post-review/post-hooks.md on 2026-06-22).
grep -riE "$KW_GREP" ~/.claude/skills/<dest-skill>/ ~/.claude/agents/<dest-agent>.md 2>/dev/null
bash /home/vscode/.claude/scratch/domain-matcher/match.sh "$KW_TEXT" | head -10        # optional related terminology
```

Adjudication on match:

- **Match in `.claude/rules/` or CLAUDE.md**: the rule exists. If the friction shows the rule is being violated by another path, the build target is a NEW enforcement layer (hook, lint, gate), NOT another memory. Surface: "rule exists at `<file:line>`; build a structural enforcement that catches the same violation at a different point in the flow."
- **Match in `workflow.md`**: pattern is codified. If the candidate is a refinement or extension, edit the workflow.md row. If it is a distinct surface, file separately.
- **Match in topic file or memory bead**: surface as near-duplicate. Offer: refine, extend, or distinct entry.
- **Match in habit-tier `bd memories`, aged 30+ days**: this is a second observation. Two options: (a) promote to workflow.md row citing the original bead, OR (b) fold both into a rule via /reflect so the pattern becomes always-loaded behavior. Option (b) is the in-flow drain path.
- **Match in habit-tier `bd memories`, recent (<30 days)**: refine or extend; do not create a new sibling.
- **No match anywhere**: novel. Continue to Route.

### 4. Route to surface

The improvement determines its own destination. Match the friction shape to the right artifact:

| Friction shape | Destination | Notes |
|---|---|---|
| PreToolUse hook fires for stakeholder-facing text | A pre-output lint script (callable, not a hook) at `~/.claude/scratch/scripts/` or similar. Hook stays as backstop. | Single source of truth on the wordlist between hook and pre-check. |
| Recurring MCP-edit gotcha (field nulled, link missed) | New section in the relevant memory file (`memory/jira.md`, `memory/github-api.md`, etc.) | Reference the section from the relevant `/jira` or `/pr` skill so future invocations load the gotcha. |
| Skill missing a capability the work needed | Mirror as personal-tier override (`~/.claude/skills/<skill>/SKILL.md`) with the addition; project version stays untouched (use `~/.claude/commands/<name>.md` only when the project artifact is itself a command). | Name-overlap convention from CLAUDE.md. |
| Recurring convention question I had to ask | Section addition to the topic file or skill so the next instance does not ask. | Update MEMORY.md index if a new topic file is created. |
| Project-wide rule violation pattern | Hand off: propose the rule edit and route the landing through `/reflect` conventions (worktree + PR) | Rule files are `/reflect`-owned per the Hard constraint below; `/compound` proposes, never writes `.claude/rules/` directly. |
| Automation that could replace a manual user step | New skill, hook, or agent. | Larger build; dispatch a subagent unless the surface is tiny. |
| No buildable improvement, but the work surfaced a pattern worth recording as soft signal | Step 5b fallback: habit-memory bead via /bead-forge memory mode. | Same as the previous /compound primary path. |

The user adjudicates the destination if multiple are plausible. The skill never auto-decides between surfaces.

### 5. Build

For each candidate that passed dedup, propose the concrete edit:

- **Small surface (under ~30 lines)**: present the exact file write or edit diff. On accept, apply directly.
- **Medium surface (30-150 lines, single file)**: present a sketch. On accept, write the full content via Write tool. Re-present the diff if the result deviates from sketch.
- **Large surface (multi-file, new skill, new agent)**: route to `/launch` (worktree agent team) with explicit acceptance criteria; reserve `mx2-executor` for a fully-specified few-file build outside a PR iteration. Present the resulting diff before commit.

**Present format**:

```
## Proposed improvement [<n> of <total>]

**Source signal**: <citation of friction signal from step 2: turn number, tool call, what blocked>
**Destination**: <file path, hook name, or skill name>
**Build size**: <S/M/L>
**Dedup**: <novel | refines existing match at <path>>

### Edit

<exact diff, file content, or subagent prompt>

**Apply? (y/n/edit/skip)**
```

On `y`: apply. On `edit`: incorporate user wording, re-present. On `skip`: move to next candidate without writing. On `n`: stop the workflow.

When multiple candidates exist, present them sequentially (not bundled) so the user can accept some and skip others. The cost of presenting separately is small; the cost of an all-or-nothing decision is friction.

### 5b. Habit-memory fallback

When no buildable improvement exists at the end of step 4 OR all candidates were skipped, AND the session surfaced a pattern worth recording, fall through to the previous /compound primary path:

- Invoke `/bead-forge` in memory checkpoint mode with the pattern as a memory-labeled bead.
- After forge returns the bead ID, run `bd remember --key='habit:<topic>' '<date>: <one-line summary> (see docr-XXXX)'`.
- Forge Phase 2b auto-creates the topic file under the bead's domain label if needed.
- Forge Phase 5 appends to chronological log.md.

The fallback exists so soft-signal patterns are not lost when the friction-scan finds nothing buildable. The promotion gate (second observation, workflow.md row) still applies.

On `/bead-forge` failure: capture as lightweight `bd remember --key='habit:<topic>' '[REFORGE-PENDING <date>] <one-line summary>'`. The SessionStart drain hook upgrades the entry on a future session.

## Distinctions

| Skill | Trigger | Primary output | Fallback output |
|---|---|---|---|
| `/compound` (this skill) | Manual, after successful work with observable friction signals | Concrete edit to a durable surface (hook, skill, memory, rule) | Habit-memory bead via /bead-forge |
| `/reflect` | Behavioral, on user correction matching prior `correction:*` memory | `correction:*` memory + rule files in `.claude/rules/` | (none; correction always produces an edit) |
| `/bead-forge` checkpoint mode (direct) | Manual or proactive, during in-flight deep analysis | Memory-labeled bead capturing conversation context | (none; this IS the capture) |
| `/handoff` | Session winding down | A copy-paste cold-start prompt for the NEXT session | (none) |
| `bd remember` direct | Anywhere | A single `bd memory` key | (none; lightweight, no synthesis) |

The distinguishing question for `/compound` vs everything else: **"What buildable change would reduce friction in a future instance of work like this?"** If a buildable answer exists, /compound builds it. If only a soft-signal pattern emerges, fall back to habit memory. If the answer is "the rule was wrong", route to /reflect.

## Promotion gate (unchanged from previous version)

`memory/workflow.md` documents the promotion criterion for habit-tier entries: **second observed application + generalization beyond originating context**. /compound does NOT bypass this for fallback habit-memory captures.

A first observation of a soft-signal pattern is a `habit:*` memory, never a direct workflow.md row. A workflow.md row requires user confirmation of a second concrete instance, in a different originating context.

The new build-route candidates (steps 4 and 5) do NOT go through this gate. Building a hook, skill, or memory section is the improvement itself; no two-observation rule applies. The gate exists for the habit-tier soft-signal layer, which the new flow uses only as fallback.

## Calibration soak

First 10 invocations of the new shape are calibration soak. Expected modes:

- **False positive on friction signals**: scan flags noise that does not generalize. User skips the candidate; no harm, signal cost is low.
- **False negative on friction signals**: scan misses a real signal the user would have caught. The /reflect path remains as backstop (the user's next session will surface it as a correction).
- **Wrong surface routing**: the build lands in the wrong artifact. Easy to move post-hoc; the durable surfaces are designed to be edited.

Do not retune the scan heuristics until 10+ invocations of data are in. The drain hook handles stale habit-memory cleanup silently in the background.

## Drain mechanism (unchanged)

Habit-tier captures from step 5b without a drain become stagnant inventory. Two drain surfaces, both unchanged from the previous version:

1. **SessionStart auto-retire hook** (`~/.claude/hooks/auto-retire-stale-habits.sh`). Runs at most once per UTC day. Closes `habit:*`-referenced beads aged 90+ days without higher-tier citation.
2. **In-flow folding during step 3 dedup**. When dedup surfaces an aged habit match, offer the fold-to-rule option in addition to refine/distinct.

The new flow generates fewer habit-memory entries because the primary route is buildable changes, so drain pressure is lower than the previous version.

## Anti-patterns

- **Generic questions instead of grounded signals.** The new flow REQUIRES citing the specific tool call, turn number, or hook fire that motivates each candidate. No "what was non-obvious?" prompts.
- **Building without dedup.** Step 3 is non-skippable. Building on top of existing coverage produces silent duplicates.
- **Bundled accept gate.** Present candidates sequentially. All-or-nothing forces the user to accept low-value items to get high-value ones.
- **Auto-routing between surfaces.** If multiple destinations are plausible, the user adjudicates. The skill never picks for the user.
- **Skipping the fallback when no buildable improvement exists.** A soft-signal pattern with no concrete build target is still worth recording as habit memory, so the dedup query catches it next time.
- **Auto-fire on /launch completion.** v1 stays manual-only. Auto-fire would scan every completion and dilute the signal.

## Output format

Run the workflow inline. Visible artifacts:

1. Scope-detection summary (one line: "Detected work unit: <thing>").
2. Friction scan output (a table or numbered list of grounded candidates with citations).
3. Dedup result for each candidate (one line per: novel, near-dup at `<path>`, or fold-candidate).
4. Sequential "Proposed improvement" blocks with exact edit + accept gate.
5. On each accept: confirmation of the write with the resulting file path or memory key.
6. On final candidate: brief end-of-session summary (1-2 sentences) of what was built.

Do not produce a long summary. The value is in the edits, not the conversation.

## Hard constraint

Do not write to durable surfaces (hooks, skills, memory files, rule files, settings.json, bead memory keys) without explicit user accept. Each "Proposed improvement" block is the gate; no silent writes.

Do not write to `correction:*` keys or any file under `.claude/rules/`. Both surfaces are `/reflect`-owned. If the friction signal is correction-shaped (user explicitly corrected the agent), the correct skill is `/reflect`, not this one.

Do not bypass the workflow.md promotion gate for fallback habit-memory captures (step 5b). A first observation is always a `habit:*`, never a direct workflow.md row.

Do not auto-fire. v1 is manual-only.

The reason these are hard constraints: the durable surfaces are the canonical record across sessions. Silent writes, surface confusion with /reflect, and bypassed gates accumulate and erode the memory architecture.
