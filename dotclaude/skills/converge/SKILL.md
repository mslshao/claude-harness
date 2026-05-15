---
name: converge
description: >
  End-to-end planning pipeline that chains refine, forge, challenge, consult,
  and synthesize into a single invocation. Produces a converged, stress-tested
  PLAN (no code written) and only creates beads after human approval. Use when
  the user has a rough idea and wants a production-quality plan without manually
  orchestrating each skill. For hands-off implementation from a well-scoped
  ticket (plan + code + PR), use /launch instead.
argument-hint: "[rough idea, feature description, or bead reference]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "WebFetch"]
---

# Converge

Orchestrate the full planning pipeline: refine a rough idea, decompose it into
a plan, stress-test assumptions, get specialist review, synthesize findings, and
present the converged result for signoff. The user sees one thing: the final plan.

## Why This Exists

Without this skill, the user manually invokes /refine, /bead-forge, /challenge,
/consult, and /synthesize in sequence, passing context between each. They review
intermediate output they don't care about. This skill runs the full pipeline
internally and presents only the converged result.

## Input

One of:
- A rough idea or feature description (text)
- A bead reference (`bd show <id>` output or bead ID)
- A source file or Jira ticket to plan around
- A mix of the above

## Pipeline Overview

```
rough idea
    |
    v
[Phase 1: Refine]          Internal. Expand context, clarify scope.
    |
    v
[Phase 2: Scope & Decompose]  Internal. Analyze codebase, find seams, draft plan.
    |
    +--------+--------+
    |                 |
    v                 v
[Phase 3a:         [Phase 3b:
 Challenge]         Consult]    Parallel via Agent tool.
    |                 |
    +--------+--------+
             |
             v
[Phase 4: Synthesize]       Merge findings, modify plan.
             |
             v
[Phase 5: Present]          First thing the user sees.
             |
       [user approval]
             |
             v
[Phase 6: Create]           Beads created, optional gate.
```

Phases 1-4 are INTERNAL. Do not show intermediate output to the user. Phase 5
is the first visible output.

## Process

### Phase 1: Refine (internal)

Apply the refine protocol to expand the rough input into a well-specified scope:

1. **Pre-load domain context** (best-effort, not a gate): Before extracting
   intent, surface existing terminology from bead memories so Phase 2 enters
   with prior decisions in hand. Run the domain-matcher to infer domain
   keywords from the rough input:

   ```bash
   bash /home/vscode/.claude/scratch/domain-matcher/match.sh "<user input>" \
     | cut -d: -f1 | head -10
   ```

   For each matched keyword, run `bd memories <keyword>` and skim the top
   5 results. If the input names a known service (e.g., `<service>`, `folio`,
   `salesforce`, `metadata_updater`) or a path under
   `src/python/mx2/<service>/`, also read the service-level `CLAUDE.md` when
   one exists.

   **Quality bar.** This is a best-effort context loader, not a gate. The
   matcher's calibration is ~79% recall / ~82% precision (n=18 baseline);
   misfires are expected. If the matcher returns no results, returns
   tokens that look like noise, or fails to run, skip pre-load and
   continue with step 2. A misfire must NOT block convergence.

   Fold pre-loaded results into the refined scope under a `Loaded context:`
   heading listing matched keywords, the bead-memory entries surfaced, and
   any service-level `CLAUDE.md` excerpts read. Phase 2 cites this section
   when checking for terminology collisions.

2. **Extract intent**: Core goal, implicit context (check conversation history,
   git state, active beads), scope signals.
3. **Gather context**: Use tools. `git status`/`git diff` for current work state.
   `bd ready`/`bd list --status=in_progress` for tracked work. Grep the codebase
   if the idea mentions functionality by name. Read CLAUDE.md for project rules.
4. **Enrich** (when references detected): If the input mentions a Jira ticket
   (`MX2-\d+`), bead ID (`docr-\w+`), or PR number (`#\d+`), run the enrich
   protocol inline (not as a separate skill invocation):
   - Fetch the Jira ticket via Atlassian MCP (AC, description, status)
   - Run `bd search <keywords>` from the ticket/bead title (top 5 results)
   - Run `bd memories <keyword>` with service name or domain (top 10 matches)
   - Fold all results into the refined scope as structured context
   Skip if no identifiers detected. This replaces the need for a manual
   `/enrich` call before `/converge`.
5. **Expand specificity**: Name files, functions, patterns, and constraints.
   Include context the LLM needs that the user takes for granted.

Output: an internal "refined scope" document. Not shown to user.

### Phase 2: Scope & Decompose (internal)

Using the refined scope, perform the core bead-forge analysis:

1. **Understand scope**: Read source files mentioned. Search the MX2 codebase for
   existing patterns. Identify natural seams.

   **Infrastructure pull-up**: Before scoping to the named service, check whether
   the prompt touches a cross-cutting concern (observability, worker lifecycle,
   error handling, queueing). If so, search for shared base classes and
   infrastructure modules that all services in that domain inherit from or
   depend on. A fix at the base class often outweighs N individual service fixes.
   Concretely: if the prompt mentions "pipeline", "worker", "processing", or any
   named ECS/Lambda service, check `mx2.worker.worker`, `mx2.sqs.*`, `mx2.telemetry.*`,
   and any shared Lambda handler patterns before deciding where changes belong.
   Also read relevant Terraform/infrastructure config (e.g., Lambda module env vars)
   to verify what is already configured in production - do not assume a capability
   is missing without checking infra.

2. **Pipeline reuse gate** _(this is the Pipeline Bypass assumption category from
   `challenge/assumption-taxonomy.md` - same check, authoritative definition there)_:
   Before designing any new code path, check whether the
   existing pipeline already provides the needed behavior. Ask: "What happens if
   we just send one message through the normal path?" New paths mean new bugs and
   new contracts to maintain. The existing path is tested. If reuse works, the plan
   should leverage it even if it involves a small overhead (e.g., one redundant
   Lambda invocation that early-exits). This check has the highest ROI of any
   single review question.
3. **Codebase collision check**: Search for existing code that overlaps. Note where
   new code must stay separate and why.
4. **Terminology-collision check**: Cross-reference each new concept the plan
   introduces (new bead title, new function name, new module name, new domain
   noun) against the `Loaded context:` section from Phase 1. If a name in the
   plan collides with an existing term defined in bead memory or service docs,
   surface to the user: "You named this X, but bead memories define X as Y.
   Are you proposing to extend Y or introduce something orthogonal?" If
   orthogonal, propose a sub-term (e.g., `Pitched X`, `Unattached X`) so the
   plan does not silently overload an existing concept.

   Skip if Phase 1 pre-load was empty or skipped. Surface the collision in the
   Phase 5 "Open Assumptions" section if the user has not adjudicated by the
   time Phase 5 fires.
5. **Decompose**: Break into work items with:
   - Title (imperative, scoped)
   - Description (what and why)
   - Acceptance criteria (observable outcomes)
   - Design notes (approach, patterns to follow, codebase references)
   - Dependencies (what blocks what)
6. **Category assignment**: Each item gets a bead category label
   (task/memory/decision/discovery/review).

Apply the granularity check from bead-forge: each item should be completable in
one focused session. If an item is too large, decompose further.

Output: an internal "draft plan" - the work items, their dependencies, and the
dependency graph. Not shown to user yet.

### Phase 3: Stress Test (parallel, internal)

Launch two parallel subagents via the Agent tool. Both receive the draft plan.

**CRITICAL: Launch both in a single message. Do not serialize.**

#### Phase 3a: Challenge (subagent)

Prompt the subagent with the draft plan and instruct it to:

1. Extract assumptions using the challenge taxonomy triggers:
   - "We'll use..." / "We should..." (approach assumptions)
   - "The existing..." / "There's already..." (codebase state)
   - "This will..." / "This should..." (outcome assumptions)
   - References to code not Read in this conversation (codebase)
   - What's NOT mentioned (scope/completeness)
2. Apply the relevance gate: "If wrong, does the plan change?" Drop irrelevant
   assumptions. Target 3-7.
3. Score on fragility (SOLID/SOFT/FRAGILE) and impact (HIGH/LOW).
4. For FRAGILE assumptions: gather evidence via tools. Record searches and findings.
5. Produce a modification table: what needs to change based on evidence.

Include in the subagent prompt: "Search `bd memories` for domain-specific gotchas
relevant to this plan. Read source files to verify codebase assumptions."

#### Phase 3b: Consult (subagent)

Prompt the subagent to act as a tech lead coordinator. Provide the draft plan and
instruct it to:

1. Determine relevant specialists from the roster (see consult/specialists.md).
   Not every plan needs every specialist. Match specialists to concerns in the plan.
2. Spawn specialist subagents in parallel. Each specialist gets:
   - The relevant plan items (not the full plan if only some items are relevant)
   - A focused question (what specifically to evaluate)
   - Author Mode preamble: "CI has not run yet. Flag everything: style, types,
     lint, naming, and design issues."
3. Synthesize specialist outputs: themes, contradictions, gaps.
4. Triage findings: Fix now / Fix next / Defer / Won't fix.

Include in the subagent prompt: "Focus on design-level concerns, not
implementation details. The plan hasn't been built yet. For each plan item
in your domain, probe for: Pipeline Bypass (does this add a new code path
when the existing pipeline could serve?), Reasoning Chain gaps (do the steps
actually follow from each other?), and Scope/Completeness (what production
concerns - rollback, observability, migration - does this plan omit?)."

### Phase 4: Synthesize (internal)

When both Phase 3 subagents return, merge their findings:

1. **Gather**: Collect challenge modifications and consult findings.
2. **Connect**: Find themes across both. Where do challenge and consult agree?
   Where do they contradict?
3. **Deduplicate**: Multiple sources may flag the same issue. Merge.
4. **Apply to plan**: Modify the draft plan based on findings:
   - INVALIDATED assumptions: remove or revise affected plan items
   - Specialist concerns rated "Fix now": incorporate into plan items
   - Gaps identified by either source: add items or acceptance criteria
   - Contradictions: make the judgment call, note the trade-off. For FRAGILE+HIGH
     contradictions, use the decision record format from `consult/report-format.md`
5. **Capture what changed**: Record a brief "convergence delta" listing what
   the challenge and consult phases changed about the original plan.

Output: the converged plan (modified work items + convergence delta).

### Phase 4.5: Tenth-Man Lens (adversarial post-synthesis pass)

After Phase 4 produces the converged plan, dispatch `mx2-tenth-man` (via Agent
tool, `subagent_type: mx2-tenth-man`) with the converged plan as input. The
tenth-man asks naive, dumb, or obvious-but-unasked questions designed to surface
risks the consensus consult and challenge passes assumed away. Output is
advisory-only, never blocks; format is the agent's standard `🔻` prefix block.

The tenth-man commentary appears in the Phase 5 output as a `## Tenth-Man Lens`
section AFTER the Convergence Delta and BEFORE the Work Items, so the user sees
adversarial dissent before reading the recommended plan. If the agent returns
`🔻 No concerns from this lens`, omit the section entirely.

This is the lowest-traffic surface for tenth-man and the calibration starting
point. Calibration data accumulates here before tenth-man expands to autopilot
ESCALATE and decision-maker borderline calls. If the tenth-man dispatch fails
(agent missing, calibration file unreadable, transient error), proceed without
it; do not block convergence on advisory tooling. Note the failure in the
Phase 5 output as a one-line "Tenth-Man Lens unavailable: <reason>" so the
user knows the adversarial pass did not run.

### Phase 5: Present

This is the **first output the user sees**. Format:

> **Deliverable adaptation.** The format below assumes the deliverable is a
> set of work items. When the deliverable is a communication artifact (PR
> comment, decision doc, briefing, Slack draft), replace the "Work Items"
> section with the draft artifact ready to copy/post. The Convergence Delta,
> Open Assumptions, and Checkpoint Recommendation still apply unchanged. The
> Phase 6 "Create" step is replaced by user signoff to send/post.

```markdown
## Converged Plan: [topic, 3-8 words]

### Summary
[2-5 sentences: what this plan accomplishes, how many work items, key design decisions]

### Convergence Delta
> [What changed during stress-testing. 2-4 bullet points showing the
> most significant modifications from challenge/consult. This tells the
> user their plan was actually tested, not rubber-stamped.]

### Work Items

[For each item, in dependency order:]

#### [N]. [Title]
**Type**: [task/feature/bug/decision/discovery]
**Priority**: [P0-P4]
**Depends on**: [item numbers or "none"]

[Description: 2-4 sentences. What and why.]

**Acceptance criteria:**
- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

**Design notes:** [Approach, patterns, codebase references. 1-3 sentences.]

---

### Dependency Graph
[ASCII representation showing execution order and parallelism]

### Open Assumptions
[Any FRAGILE/UNVERIFIABLE assumptions the user should confirm. Omit if none.]

---

**Approve this plan?** Reply "yes" to create beads (with optional human gate
on implementation), or provide feedback to revise.
```

### Phase 6: Create (on approval)

When the user approves:

1. Create beads via `bd create` for each work item. Use `--title`, `--description`,
   `--type`, `--priority`. Include acceptance criteria and design notes in the
   description.
2. Wire dependencies via `bd dep add`.
3. If the plan has 3+ implementation items, ask: "Add a signoff gate? This blocks
   implementation beads in `bd ready` until you explicitly resolve the gate."
   If yes, create a gate bead with `--type=task --title="Signoff: [plan topic]"`
   and make implementation items depend on it.
4. Present the created bead IDs and the dependency graph.

If the user provides feedback instead of approving, revise the plan and re-present
(Phase 5 again). Do not loop more than twice - if the user has extensive changes,
suggest they provide the feedback and you'll run `/bead-forge` with the converged
context directly.

## Checkpoint Protocol

If this skill produces findings that would be lost to compaction (especially the
convergence delta and rejected alternatives), include a Checkpoint Recommendation
block in the Phase 5 output:

```
## Checkpoint Recommendation
Category: decision
Domain: [relevant domain]
Title: "PLAN DECISION: [topic] - converged approach with rationale"
Context to preserve:
- [Key design decision and why]
- [Rejected alternative and why rejected]
- [Assumption that was invalidated and what replaced it]
Rationale: convergence analysis produced decisions that inform implementation
```

The main agent should persist this via `/bead-forge checkpoint` if the plan is
approved.

## Rules

- **No intermediate output.** Phases 1-4 are invisible to the user. If a phase
  fails (e.g., can't reach codebase), note it in Phase 5 presentation rather
  than asking mid-pipeline.
- **Parallel is mandatory.** Challenge and consult MUST run in parallel via
  separate Agent tool calls in the same message. Serializing them defeats the
  purpose.
- **Beads are created last.** Do not create beads during Phases 1-4. The whole
  point is convergence before commitment.
- **Don't rubber-stamp.** If challenge finds nothing and consult has no concerns,
  that's fine - but the convergence delta should honestly say "no significant
  changes" rather than fabricating modifications.
- **Scope guard.** If the refined input is too large for a single converge pass
  (10+ work items likely), say so in Phase 5 and suggest breaking into
  sub-features that each get their own converge pass.
