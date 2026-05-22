---
name: compound
description: "Proactively extract reusable workflow patterns from a substantial work unit that just completed, staging them as habit memories that drain into codified rules over time. Use after a PR merges, a /launch ships, a bead closes, or a multi-step investigation wraps and the work involved a non-obvious technique worth repeating. The proactive sibling to /reflect (which is reactive and correction-triggered). Trigger phrases: '/compound', 'extract patterns', 'what did we learn from that', 'capture this workflow', 'compound that', 'what was reusable here', 'pattern-capture'. Also invoke proactively at substantial-completion signals (PR merged, /launch finished, bead closed) when the conversation contains a novel approach not yet captured as a habit:* memory. Distinct from /handoff (cold-start prompt for the NEXT session) and direct `bd remember` (no synthesis, no dedup, no promotion-gate awareness). Invokes /bead-forge memory mode internally for Routes 1 and 3."
argument-hint: "[optional: short hint about what just finished, e.g. 'launch of docr-XXXX' or 'PR #YYYY merged']"
---

# Compound

Extract reusable workflow patterns from a substantial work unit, dedup against the existing habit:* corpus, and route the finding to the right durable surface (habit memory, workflow.md, or a topic file). Always present for accept before writing.

This skill is the **proactive** half of pattern capture. Its reactive sibling is `/reflect`, which fires on user corrections (CLAUDE.md Reflection Trigger). `/compound` fires after **successful** work that produced a novel technique, work where nothing went wrong, so /reflect never triggered, but where a future session would benefit from knowing what the current session figured out.

## Why this exists

The pattern-capture pipeline has a coverage gap. `/reflect` catches mistakes (correction-triggered, writes to `correction:*` memories and rule files). `/bead-forge` checkpoint mode preserves in-flight conversation context against compaction. `/handoff` produces a cold-start prompt for ONE specific next session. None of these capture: "this work just shipped, the approach was novel, and a future session would benefit from knowing what we figured out."

That gap is real. `memory/workflow.md` has documented the promotion gate ("second observed application + generalization beyond originating context") since 2026-05-13, and 9 `habit:*` bd memories have accumulated since, but each first-observation moment has been hand-noticed under multi-window operational reality. `/compound` automates the noticing.

## When to invoke

Manual only in v1. Triggers:

- User explicitly types `/compound` or asks to "extract the pattern", "capture this workflow", "what's reusable here".
- After a substantial completion signal (a draft PR was published, `/launch` returned, a bead got closed, or a multi-step investigation wrapped) AND the work surfaced a non-obvious approach not already captured as a `habit:*` memory.
- After 3+ exchanges of decision-making where the user landed on a deliberate technique (not just an outcome), and that technique would replicate to future work.

## When NOT to use

- **Every PR or bead close.** Routine work captures the pattern in the code itself; no extraction needed.
- **The work was a correction.** Use `/reflect`. /compound is for what worked; /reflect is for what failed.
- **The work is mid-flight, not done.** Use `/bead-forge` checkpoint mode to preserve the in-progress synthesis against compaction. Once the work is done, `/compound` extracts the durable pattern.
- **The next-session handoff is what is needed.** Use `/handoff`. That produces a cold-start prompt; /compound produces patterns reusable across many future sessions.
- **A specific fact, not a pattern.** Use `bd remember` directly. /compound is for techniques that generalize; a one-off fact about a service endpoint goes straight to memory without the workflow.

## Workflow

### 1. Scope detection

Determine what work unit just completed. Substantial work often produces non-git artifacts (a Confluence design doc, a Jira state change, a Slack thread where a design discussion or bugfix approach got worked through), so pull from every surface where a completion signal could live. Run these in parallel:

**Local (bash)**:

```bash
bd list --status=in_progress --json | jq -r '.[] | "\(.id) \(.title)"'
git log --since='6 hours ago' --oneline -20
gh pr list --author @me --state all --limit 5 --json number,title,state,updatedAt
```

**External (MCP)**:

- **Jira**: tickets I transitioned or commented on recently. JQL: `assignee = currentUser() AND updated >= -1d`. Tool: `mcp__atlassian__searchJiraIssuesUsingJql`. Fetch comments on hits to see what changed.
- **Confluence**: pages I edited in the last day. CQL: `contributor = currentUser() AND lastmodified > now("-1d")`. Tool: `mcp__atlassian__searchConfluenceUsingCql`. A newly-published design doc is a substantial work unit even when no PR exists.
- **Slack**: my recent messages where a technique, design, or bugfix approach got worked out (person-to-person discussions that landed somewhere worth keeping). Query: `from:me` over the last 6 hours; keyword narrowing is leaky (skip it unless results are noisy). Tool: `mcp__plugin_slack_slack__slack_search_public_and_private`. Also check threads where I posted a "here's what we landed on" wrap. **Incidents (what went wrong) are not /compound-shaped**; those go to /reflect. /compound captures what worked, not what failed.

Not every source will surface a signal, and that is fine. Empty results just narrow the candidate work unit.

Cross-reference against conversation context. If a `/launch` just shipped, the worktree path and PR URL are the anchor. If a bead just closed, `bd show <id>` carries the design notes. If a Confluence page was just published, the page URL plus its inline comments are the anchor. If a Slack thread just resolved, the thread is the anchor. If the user passed a hint in the argument, take that as the anchor and skip detection.

If signals are empty OR multiple signals surface with no clear anchor in conversation context, ask the user "What just finished?" One focused question, not a menu; do not invent a work unit to justify continuing.

**Bias-stripping**: if the user's invocation hint pre-frames the route ("this should be a workflow.md entry", "this is heavy-synthesis"), note the leaning as input but do NOT skip dedup or the socratic step. Let the gate run; convergence with the leaning is a positive signal, divergence means the leaning was wrong. Pre-loading the user's answer into the workflow defeats the gate's purpose.

### 2. Socratic questions

Ask 2-3 terse questions to surface the pattern. The technique is the gap between what the bead/PR said and what the work actually required.

- **"What did you have to figure out that was not obvious from the bead/PR?"** Surfaces undocumented insight.
- **"Is this a pattern you'd want repeated next time, or a one-off?"** Surfaces generalization; one-offs do not warrant capture.
- **"What would have made the next person doing this faster?"** Surfaces the workflow shape.

Keep questions scannable. Do not lecture; do not pre-answer. The user's answer IS the raw material.

**Confidence calibration**: if the user's answers do not surface a pattern sharper than "I just did the work" or "it was straightforward", stop the workflow. A captureable pattern names a technique, sequence, or insight that would replicate. If none of the three questions surfaces one, the work was routine; routine work does not need /compound.

**Misroute check**: if the answers reveal the pattern is correction-shaped ("we should never do X again", "X went wrong because Y", "the lesson is don't do Z"), this is `/reflect` territory, not `/compound`. Stop and surface: "this looks like a correction-shaped insight. /compound captures techniques that worked; corrections route through /reflect. Want to switch?" Do not auto-route; let the user adjudicate the surface choice.

### 3. Dedup

Before proposing, check the existing corpus at every tier. The pattern may already be codified at a higher tier than `habit:*`; the goal is to catch it whatever surface it lives on. A habit-only dedup misses patterns already promoted to workflow.md or codified as rules, and re-capture would create silent duplicates.

Before running the queries, derive 2-3 distinctive keywords from the candidate pattern (verbs and noun phrases; avoid stop-words; multi-word phrases beat single nouns). Example: for the pattern "deploy watch via /loop", `KW_TEXT="deploy watch loop"` and `KW_GREP="deploy|watch|loop"`. Set both vars before running the block; the agent must NOT run with literal placeholders.

```bash
KW_TEXT="<2-3 keywords as a space-separated phrase>"     # for domain-matcher
KW_GREP="<same keywords as a pipe-separated regex>"      # for grep -E

bd memories habit:                                                                    # habit-tier memories
bd list --label=memory --status=open --json | jq -r '.[] | "\(.id) \(.title)"'        # forge memory beads (open only; retired ones are auto-closed by the drain hook)
grep -iE "$KW_GREP" ~/.claude/projects/-workspaces-main/memory/workflow.md             # promoted patterns
grep -riE "$KW_GREP" ~/.claude/projects/-workspaces-main/memory/*.md                   # topic files
grep -riE "$KW_GREP" /workspaces/main/.claude/rules/                                   # project rules
bash /home/vscode/.claude/scratch/domain-matcher/match.sh "$KW_TEXT" | head -10        # related terminology (best-effort; skip on missing script or noise)
```

The domain-matcher surfaces prior terminology you may not have phrased the same way (calibration ~79% recall; misfires are expected, don't block on them). If the script is missing, skip that line entirely.

Adjudication on match:

- **Match in `.claude/rules/` or `workflow.md`**: pattern is already codified at a higher tier than habit. Do NOT capture as habit. Surface: "this is already in `<file:line>`. Did you mean to refine that rule via /reflect, or is this a distinct instance?" Let the user route.
- **Match in a topic file or memory-labeled bead**: surface as near-duplicate. "Closest existing capture: `<bead-id or file>`. Is this a refinement of that, or a new entry under a different key?"
- **Match in habit-tier `bd memories`, aged 30+ days without a second observation**: surface a fold option in addition to the standard three-way. "This habit has aged. Options: (a) treat as second observation (promote to workflow.md), (b) refine the existing habit, (c) capture as distinct, or (d) **fold both into a rule via /reflect** so the pattern becomes always-loaded behavior instead of dormant memory." Option (d) is the in-flow drain path; it converts two soft habits into one durable rule at capture-time.
- **Match in habit-tier `bd memories`, recent (under 30 days)**: original three-way (second observation, refinement, or distinct).
- **No match at any tier**: novel. Continue to Route.

The user adjudicates; the skill never auto-decides. Skipping any tier risks duplicating a pattern that already lives somewhere, and that erodes the discoverability of every existing surface.

### 4. Route

Three possible destinations, decided by what dedup surfaced. **Routes 1 and 3 both invoke `/bead-forge` in memory checkpoint mode** so the habit gets a real `docr-XXXX` bead ID, structured fields, automatic topic-file indexing (forge Phase 2b), and a chronological log entry (forge Phase 5). The lightweight `bd remember` key becomes a pointer to the bead, not the primary record.

| Situation | Destination | Persist mechanism |
|-----------|-------------|-------------------|
| **First observation, atomic** (single-paragraph bead body) | New `memory`-labeled bead + `habit:<topic>` key pointing to bead ID | Invoke `/bead-forge` in memory checkpoint mode with the captured pattern. After it returns the bead ID, run `bd remember --key='habit:<topic>' '<date>: <one-line summary> (see docr-XXXX)'` so future dedup queries find both surfaces. |
| **Second observation** of an existing `habit:*` (user confirms validated in a second concrete instance) | `memory/workflow.md` row citing the original bead | Edit `memory/workflow.md` Entries table; add a new row with three cells: (1) pattern title, (2) the originating bead ID (`docr-XXXX`), (3) one-line description that names both observed contexts. Use the existing rows in workflow.md as the formatting reference. Optionally `bd update <id>` on the original bead to note the second instance. |
| **Heavy synthesis** (multi-domain, multi-paragraph, generalizes a whole class of work) | New `memory`-labeled bead with long description + topic file (auto-created by forge Phase 2b) | Invoke `/bead-forge` in memory checkpoint mode with the multi-paragraph synthesis. Forge Phase 2b will check for an existing topic file under the bead's domain label; if none, create one with frontmatter and add the MEMORY.md index entry. Same `habit:<topic>` pointer key as Route 1. |

**Why /bead-forge instead of direct `bd remember`**: forge memory mode runs a self-check gate (`Phase 3`), enforces title and acceptance conventions, applies the `memory` category label, updates the per-domain index automatically (`Phase 2b`), and appends to chronological `log.md` (`Phase 5`). Doing this manually was the prior pattern; it accumulated drift (some habits had topic files, some didn't; none had bead IDs that workflow.md could cite). Routing through forge inherits the discipline.

**The existing 9 `habit:*` bd memories stay as-is.** No backfill; treat them as a legacy lightweight tier. Future habits get the forge-bead treatment.

**Habit-key convention**: use `habit:<topic>` for general patterns and `habit:<domain>:<topic>` when the topic is service-specific or surface-specific (e.g., `habit:workflow:plan-second-session-gate`, `habit:slack:save-thread-verbatim`). The colon-namespaced form scopes future dedup queries (`bd memories habit:workflow:` finds all workflow-class habits without false-matching other domains). When in doubt, namespace; flat keys are harder to dedup later.

**Domain label for the forge bead**: pick a single domain that matches an existing topic file in `~/.claude/projects/-workspaces-main/memory/` if one exists; otherwise pick a fresh one that names the surface (`launch`, `slack`, `workflow`, `pr-review`, etc.). Forge Phase 2b creates the topic file under that label if needed, so the domain choice is the steering signal for auto-indexing.

If none of the three routes feels right, the pattern probably isn't ready; say so and stop. Not every conversation yields a captureable pattern, and that is the correct outcome.

### 5. Present

Show the proposed write (full text, exact key/path) and wait for accept/reject/edit:

```
## Proposed pattern capture

**Source**: <bead-id | PR # | Jira ticket | Confluence page | Slack thread | conversation segment>
**Route**: <Route 1: forge memory bead + habit:* pointer | Route 2: workflow.md row citing original bead | Route 3: forge memory bead + auto-topic-file + habit:* pointer>
**Dedup**: <"novel, no match at any tier" | "match at <tier>: <action user chose>">

### Write

<exact persist call OR exact diff>

**Apply? (y/n/edit)**
```

On `y`: run the persist call, confirm. On `edit`: incorporate user's wording, re-present. On `n`: stop. **No silent writes.** The promotion gate is operator-controlled, not skill-controlled.

**On /bead-forge failure**: if forge fails to create the bead (DB conflict, validation reject, transient error), do NOT silently drop the capture. Surface the failure with the proposed bead body intact and offer two fallbacks:
1. Retry forge once.
2. Capture as lightweight `bd remember --key='habit:<topic>' '[REFORGE-PENDING <date>] <one-line summary>'` directly. The `[REFORGE-PENDING ...]` marker tags the entry for the SessionStart drain hook to automatically re-forge into a memory bead on a future session (via `~/.claude/hooks/reforge-pending-habits.py`). No manual follow-up needed; the hook upgrades the entry once it runs, restoring drainability.

The cost of dropping a captured pattern silently is high: the next dedup query won't find a memory that doesn't exist, and the same insight will be re-derived from scratch.

## Distinctions

| Skill | Trigger | Target | What it preserves |
|-------|---------|--------|-------------------|
| `/compound` (this skill) | Manual, after successful work | Memory bead (via /bead-forge memory mode) + `habit:*` pointer + `workflow.md` row on second observation | Reusable patterns for many future sessions |
| `/reflect` | Behavioral, on user correction matching prior `correction:*` memory | `correction:*` memory + rule files in `.claude/rules/` or skill/agent definitions | Lessons from mistakes |
| `/bead-forge` checkpoint mode (direct) | Manual or proactive, during in-flight deep analysis | Memory-labeled bead capturing conversation context | Conversation context against compaction. Note: /compound invokes this skill internally for Routes 1 and 3, but you can also invoke it directly when the work is mid-flight and not yet a captureable pattern. |
| `/handoff` | Session winding down | A copy-paste prompt for the next session | Cold-start continuity for one specific successor session |
| `bd remember` direct | Anywhere | A single `bd memory` key | A single fact, no synthesis, no dedup. Useful for the pointer key that /compound creates after a forge-bead exists; not appropriate for first-class pattern capture. |

The distinguishing question for `/compound` vs everything else: **"Is this a pattern that would help many future sessions, not just the next one or this one's debugging?"** If yes, /compound. If "just the next session", /handoff. If "this session's debrief", /bead-forge checkpoint. If "the rule was wrong", /reflect.

## Promotion gate

`memory/workflow.md` documents the promotion criterion: **second observed application + generalization beyond originating context**. Do not bypass it.

- A first observation of a pattern is a `habit:*` memory, never a direct workflow.md row.
- A workflow.md row requires user confirmation that the pattern has now been observed in a **second concrete instance**, in a **different originating context** than the habit memory recorded.
- The promotion is a user decision, not a skill decision. The skill surfaces the option; the user adjudicates whether the second observation truly generalizes.

This gate exists because workflow.md is the canonical reusable-pattern surface. Premature promotion floods it with single-instance ideas that turn out to be one-offs. The habit:* layer is the proving ground.

## Calibration soak

The first 5-10 `/compound` invocations are calibration soak. False positives (capturing a one-off that never recurs) and false negatives (stopping at the socratic step when a real pattern was there) are both expected. Trust the gate's no's during soak; the drain hook (see Drain mechanism below) handles false-positive cleanup silently in the background. Do not retune the socratic questions until you have 10+ invocations of data.

## Drain mechanism

Captures without a drain become stagnant inventory: the habit stack grows, dedup gets noisier, and codified rules never form. The drain has two surfaces, neither of which requires the user to invoke a separate skill:

1. **SessionStart auto-retire hook** (`~/.claude/hooks/auto-retire-stale-habits.sh`). Runs at most once per UTC day. For every `docr-XXXX` referenced from a `habit:*` bd memory body, the hook checks: is the bead open, created 90+ days ago, AND not cited at any higher tier (workflow.md, topic files, `.claude/rules/`, CLAUDE.md)? If all true, `bd close` it with a reason. Logs every action to `~/.claude/scratch/compound-drain-log.jsonl`. Reversible via `bd reopen <id>`. Other memory-labeled beads (cutover handoffs, audit notes, meeting prep) are EXCLUDED because they are not referenced from a `habit:*` key.

2. **In-flow folding during Step 3 dedup**. When dedup surfaces a matching habit that has aged (created > 30 days ago without a second observation), Step 3 offers a fold option in addition to the three existing adjudications: route both the existing habit and the new capture through `/reflect` to codify as a rule. This converts two soft habits into one always-loaded rule, organically draining the stack at capture-time without requiring a separate user invocation.

Promotion to workflow.md (the second-observation path) remains as Route 2 in Step 4. That is the third drain surface, and it stays user-gated as before.

Net effect: the habit stack stays small. The SessionStart retire runs silently; the in-flow fold surfaces during dedup so the user adjudicates the consolidation decision, but never needs to run a separate skill or remember to drain.

## Anti-patterns

Operational mistakes to avoid. For absolute non-negotiables, see Hard constraint below.

- **Habit-only dedup.** Checking just `bd memories habit:` misses patterns already promoted to workflow.md or codified in `.claude/rules/`. The dedup step must span every tier; see Step 3.
- **Capturing one-offs.** If the user's answer to "would you want this repeated" is no, stop. Not every conversation yields a pattern.
- **Auto-fire ambition.** v1 is manual-only. Auto-fire on /launch completion or /pr-intel post-publish was deferred: the drain hook handles stale-habit cleanup, but auto-fire would still capture trivial work as noteworthy and dilute the soak signal. Re-evaluate after manual usage produces 10+ entries and the completion-signal heuristics prove reliable.
- **Overlap with /handoff.** Do not produce cold-start prompts here. /handoff owns the next-session surface; /compound owns the many-future-sessions surface.

## Output format

Run the workflow inline. The visible artifacts are:

1. Brief scope-detection summary (one line: "Detected work unit: <thing>").
2. The 2-3 socratic questions, asked one at a time or as a numbered list, match the user's response cadence.
3. Dedup result (one line: overlap or no overlap, with the matched memory key if any).
4. The "Proposed pattern capture" block (template above) with the exact persist call or diff.
5. On accept: confirmation of the write with the resulting memory key or file path.

Do not produce a long summary. The value is in the durable artifact, not the conversation.

## Dry-run walkthrough

Scenario: A `/launch` just finished building a small personal-tier skill (single-file, ~120 lines), and during the conversation the user pointed out that subagents cannot write to `~/.claude/` because of the sandbox, so the work shipped via main-thread writes instead of the standard worktree+PR flow.

**Step 1 (scope detection)**: `gh pr list` returns nothing (no PR, this was a personal-tier deliverable). `git log` shows no commits in `/workspaces/main`. `bd list --status=in_progress` shows the bead I just claimed. Jira/Confluence/Slack queries return nothing relevant (this work was bead-tracked only, no ticket, no doc, no Slack thread). User's hint: "the /launch for the compound skill". The work unit is clear.

**Step 2 (socratic)**:
- "What did you have to figure out that was not obvious from the bead?" → "The /launch flow assumed a worktree+PR. The deliverable lives in ~/.claude/ which subagents can't write to. Had to swap to skill-creator + main-thread write."
- "Is this a pattern you'd want repeated?" → "Yes, anytime a /launch target is personal-tier, the worktree path is wrong."
- "What would have made the next person faster?" → "A check at /launch entry that asks 'is the target inside /workspaces/main or in ~/.claude/?' and routes accordingly."

**Step 3 (dedup)**: Derive keywords `KW_TEXT="launch personal-tier worktree skill-creator"` and `KW_GREP="launch|personal-tier|worktree|skill-creator"`. Run the 5-tier parallel check:
- `bd memories habit:` returns no overlap. Closest neighbor `habit:workflow:plan-second-session-gate` is unrelated.
- `bd list --label=memory --status=open` shows existing checkpoint beads (cutover, audit, meeting prep) but no forge habit beads yet (this would be the first one).
- workflow.md grep: no matches.
- topic-file grep: no matches.
- `.claude/rules/` grep: no matches (the /launch invariant is not codified anywhere).
- domain-matcher: returns nothing useful for this novel topic.

Verdict: novel at every tier. Continue to Route.

**Step 4 (route)**: First observation, atomic shape → Route 1: /bead-forge memory mode + `habit:*` pointer key.

**Step 5 (present)**:

```
## Proposed pattern capture

**Source**: docr-hnaa (/launch of compound skill)
**Route**: Route 1 (new memory bead via /bead-forge + habit:* pointer)
**Dedup**: no overlap with existing habit:* corpus

### Write (two steps)

Step A: Invoke /bead-forge in memory checkpoint mode with this content:

  Title: /launch target in ~/.claude/ requires non-worktree path
  Category: memory
  Domain: launch
  Body: When /launch target is in ~/.claude/ (not /workspaces/main), the
    standard worktree+PR flow is wrong because subagents are sandboxed
    to /workspaces/main and cannot write to ~/.claude/. Route via
    skill-creator or main-thread write instead. First observed building
    the /compound skill itself.
  Acceptance: A future /launch invocation targeting ~/.claude/ should
    route through skill-creator or main-thread write, not worktree+PR.

Step B: After forge returns the bead ID, run:

  bd remember --key='habit:launch-personal-tier-target' \
    '2026-05-20: When /launch target is in ~/.claude/, worktree+PR flow is wrong; subagents cannot write to ~/.claude/. See docr-XXXX.'

**Apply? (y/n/edit)**
```

If the user says `y`: invoke /bead-forge memory mode (which itself runs Phase 4 present + Phase 5 create, so the user sees the forged bead before persist). After the bead is created, run the `bd remember` pointer. If a second concrete instance shows up later (e.g., building a personal-tier agent via /launch), the future /compound invocation will dedup against this habit, find the bead ID, and surface Route 2 (workflow.md promotion citing the original bead).

## Hard constraint

Do not write to durable surfaces (`bd remember`, `memory/workflow.md`, `memory/<topic>.md`, `MEMORY.md`, beads via `/bead-forge`) without explicit user accept. The presented "Proposed pattern capture" block in Step 5 is the only gate; if the user says no or edits without explicit accept, the workflow stops.

Do not write to `correction:*` keys or any file under `.claude/rules/`. That surface is `/reflect`-owned. If the pattern emerged from a mistake, the correct skill is `/reflect`, not this one. If unsure, ask before persisting.

Do not bypass the workflow.md promotion gate. A first observation is always a `habit:*` (Route 1 or Route 3 via /bead-forge memory bead), never a direct workflow.md row. Promotion requires a confirmed second concrete instance and user adjudication.

The reason these are hard constraints: the durable surfaces are the canonical record across sessions. Silent writes, surface confusion with /reflect, and bypassed promotion gates accumulate over many invocations and erode the memory architecture. A skill that occasionally fails to capture is recoverable; a skill that occasionally writes the wrong thing to the wrong surface is not.
