---
component: dotclaude/skills
type: directory-map
status: V0 partial sweep (11 of 22 skills have entries)
authored_by: Claude Opus 4.7
---

# WORLDMAP: Personal Skills

AI-authored commentary on each personal-tier skill in `~/.claude/skills/`. When I invoke the skill, what failure mode it prevents, how it compounds, and where it has limits. Entries follow the format documented in the top-level `WORLDMAP.md`.

V0 covers the highest-leverage skills. The remaining 11 are mostly tactical (audit-worktrees, calibrate, codility-review, post-review, refine, skill-catalog, snapshot-system-prompt, synthesize, test-forge, autopilot, review) where the entry shape is mechanical: each fires on a specific user request, produces a defined output. Detailed entries for these will be added in follow-up sweep work.

---

```yaml
---
component: babysit-pr
type: skill
status: active
trigger_signals:
  - "user announces stepping away from open draft PR"
  - "user wants merge during off-hours"
  - "draft PR has active reviewer activity user cannot actively track"
prevents:
  - "bot-comment noise consuming human reviewer mindshare before they look"
  - "force-push sequencing errors when fixing PRs across multiple bot rounds"
  - "user re-loading PR state context every time they check"
origin:
  pattern: "the author repeatedly told me to ScheduleWakeup and watch for reviewers, then auto-edit the PR with appropriate responses. The behavior crystallized into a skill after enough one-off invocations made the pattern obvious."
  mechanism_evolution:
    - "ScheduleWakeup primitive watches at paced cadence"
    - "classifier sorts comments: bot vs human, mechanical vs substantive"
    - "mechanical bot suggestions auto-remediated via pre-staged worktree + force-push"
    - "substantive human feedback escalated to user, not auto-handled"
related: [launch, post-review, handoff]
---
```

When I reach for this: explicit user signal of stepping away ("watch this PR", "babysit", "I am OOO"). I do not auto-invoke it; it requires the user's directive because the auto-force-push posture is high-trust and should not be assumed.

What it prevents: the user comes back to a PR where bots have piled on mechanical suggestions (single-line ellipsis-to-pass, add a constant, rename a var) and the human reviewer has not looked yet because the bot noise pushed them off. By the time the user returns, three rounds of low-value bot churn have happened. With /babysit-pr, the user returns to a clean PR with the mechanical noise resolved and only the substantive human feedback waiting for them.

How it compounds: pairs with `launch` (which produces the draft PR) and `post-review` (which posts reviews atomically). The three skills cover the PR lifecycle from idea to merge-ready without the user manually orchestrating each round.

The subtle why: the user runs up to 5 Claude Code windows simultaneously. /babysit-pr lets one of them be the PR-watching loop while the others run other work. Without it, the user has to either (a) manually poll the PR (attention cost), (b) wait until they are available to address bot feedback (latency cost), or (c) skip review entirely (quality cost). The skill picks the (d) path that did not exist before.

---

```yaml
---
component: handoff
type: skill
status: active
trigger_signals:
  - "context window approaching limits"
  - "user signals 'audit configs' or 'wrap up'"
  - "long session with accumulated non-trivial state not yet in beads"
prevents:
  - "loss of WIP-state context that native compact cannot preserve reliably"
  - "next session restarting from cold with no awareness of in-flight decisions"
  - "compaction deciding what to keep based on recency, not load-bearing-ness"
origin:
  pattern: "designed against the failure mode of native Claude Code compaction losing important state. The native behavior summarizes by recency. /handoff lets the agent decide what is actually load-bearing for the next session, which is a different and more accurate filter."
  mechanism:
    - "audit personal configs (CLAUDE.md, hooks, agents, skills, memory) for unmerged learnings from this session"
    - "produce cold-start handoff prompt for the next session to paste in"
related: [bead-forge, skill-catalog]
---
```

When I reach for this: end-of-session signals (the user says "wrap up", "handoff for new session", or context-window pressure hits ~30%). I also reach for it proactively when the conversation has accumulated 3+ exchanges of design/decision content not yet checkpointed.

What it prevents: the failure mode where native compact summarizes a long session and the summary keeps recent-but-shallow content (the last tool result, the latest message) while dropping deep-but-older content (the design call made 50 turns ago that everything since has built on). The user has hit this before, hence the skill exists.

How it compounds: works with `bead-forge` (which persists task-shaped context to durable storage) but covers different ground. `bead-forge` is for things that should outlive the session as task state. `handoff` is for things that should arrive in the next session as conversation state. Two different decay properties, two different durability mechanisms.

The subtle why: native compact delegates "what matters" to Claude Code's compaction heuristic, which is opaque and recency-biased. `/handoff` puts the agent that just did the work in charge of deciding what to bring forward. The agent has full visibility into which decisions were load-bearing, which artifacts are referenced going forward, which beads need claim-state updated. The compaction heuristic does not have any of that. Replacing model judgment with text-based heuristics is exactly the kind of move this harness exists to oppose.

---

```yaml
---
component: converge
type: skill
status: active
trigger_signals:
  - "rough idea or feature description that needs both decomposition AND stress-testing"
  - "medium-to-large feature where the user would otherwise invoke 3+ skills manually"
  - "feature with unclear scope where assumptions need challenging"
prevents:
  - "decomposed plans that have not been challenged"
  - "challenged plans that have not been decomposed"
  - "manual orchestration of refine + forge + challenge + consult + synthesize chain"
related: [refine, bead-forge, challenge, consult, synthesize]
---
```

When I reach for this: the user has a rough idea and wants both quality decomposition AND assumption stress-testing in one invocation. Manually chaining the constituent skills would take 4-5 sequential dispatches; converge does it as one chained call.

What it prevents: a decomposition that has not been challenged ships plans with fragile assumptions baked in. A challenge pass that has not been decomposed surfaces concerns but does not produce actionable work items. Converge enforces "both" as the default for medium-to-large feature work.

How it compounds: feeds into `launch` (which builds against a converged plan) and `bead-forge` (which persists the plan as work items). The convergence output is the input to either downstream skill, depending on whether the user wants hands-off implementation (launch) or just decomposed work items (forge alone).

Limits: convergence is expensive. For small features (a one-file fix, a single-PR bug fix), the overhead exceeds the value; just use `bead-forge` alone or write the work item directly. The trigger condition (medium-to-large feature) gates this correctly most of the time.

---

```yaml
---
component: launch
type: skill
status: active
trigger_signals:
  - "well-scoped ticket ready for hands-off implementation"
  - "user wants 'fire and forget' from a clear specification"
  - "implementation work that should produce a draft PR without further input"
prevents:
  - "context bloat in main conversation during multi-phase implementation"
  - "the user being a bottleneck in routine implementation cycles"
related: [converge (produces the plan launch executes against), babysit-pr (handles the PR after launch publishes it)]
---
```

When I reach for this: the user has a clear ticket (or a converged plan) and wants implementation without further conversation. The skill enriches context, converges a plan, gets approval, dispatches an agent team in a shared worktree, and produces a draft PR.

What it prevents: implementation work consuming the user's attention when the work is well-scoped and pattern-matching. The agent team handles the cycle; the user reviews the PR.

Cold-start resume: `/launch <bead-id>` resumes a prior execution from the last verified checkpoint without re-running completed phases. Important for long-running multi-day work where the codespace might restart between sessions.

Before publishing the PR, the skill runs structured self-review (PR-intel in `--mine` mode) for AC compliance, CI status, specialist dispatch, pre-submission checklist. Per-phase reviews catch issues within each phase but miss integration bugs between phases. The pre-PR consolidated review catches these.

How it compounds: pairs with `converge` (upstream, produces the plan) and `babysit-pr` (downstream, handles the PR after publish). The three skills together cover the full lifecycle.

Limits: only as good as the plan. A vague plan produces vague implementation. The skill enforces plan quality before execution but cannot fix a fundamentally unclear request. Also, multi-PR work requires multiple launch invocations; the skill is single-PR-shaped.

---

```yaml
---
component: pr-intel
type: skill
status: active
trigger_signals:
  - "reviewing someone else's PR (default mode)"
  - "self-review before publishing own PR (`--mine`)"
  - "triage of any PR (`--quick`)"
  - "user pastes a PR URL or number"
prevents:
  - "ad-hoc PR reviews that miss specialist concerns"
  - "self-review missing AC compliance, CI status, or pre-submission checks"
  - "review pile-on (raising concerns bot reviewers already raised)"
related: [code-reviewer, bot-review, silent-failure-hunter, observability-reviewer, security-auditor, pr-precedent]
---
```

When I reach for this: any PR review work. The skill is the workhorse of the harness's PR review surface. Roughly 1 in 3 sessions involves a PR-intel invocation.

What it prevents: ad-hoc PR review produces inconsistent output (different lens applied each time, different specialists invoked or not invoked). The skill standardizes the lens: pre-flight checklist, specialist dispatch based on diff signals, synthesis, draft review comments. Output is briefing-formatted, ready to paste as a GitHub review (via `/post-review`).

Self-review mode (`--mine`): different output shape. Instead of "what concerns should I raise as a reviewer," it produces "what should I fix before pushing." Different audience, different framing.

How it compounds: with `post-review` (posts the briefing's draft comments as an atomic GitHub review), with `babysit-pr` (handles the PR after publish), with `enrich` (loads Jira/Confluence context the briefing references).

Limits: per-revision delta detection only works if a prior review memory exists. First-round reviews start cold. The skill's verification step catches some false positives (specialist claims that depend on production state the agent has not verified) but not all.

---

```yaml
---
component: bead-forge
type: skill
status: active
trigger_signals:
  - "plan approved, work needs decomposition into tracker items"
  - "conversation has 3+ exchanges of accumulated design/decision content not in tracker"
  - "checkpoint trigger: deep analysis or discussion before compaction would lose it"
prevents:
  - "decisions lost to compaction"
  - "decomposed work items that need 2-3 rounds of refinement before they are workable"
  - "single-bead requests that should be multi-bead epics"
related: [converge (uses forge for decomposition), handoff (companion durability mechanism)]
---
```

When I reach for this: two modes. (1) Task decomposition: a plan is converged, work needs to be split into tracker items with acceptance criteria, design notes, dependency graph. (2) Memory checkpoint: the conversation has accumulated decisions that would be lost to compaction; persist them now.

What it prevents: cold-start agents picking up work mid-stream that have no context about what was decided and why. Tracker items written without forge quality are skeletons that need re-refinement. Forge front-loads the quality.

The two-mode split matters because checkpoint mode is a fast-path (no codebase exploration needed; the conversation context is the input) while decomposition mode is the full process (codebase scoping, collision checks, challenge gate, self-check).

How it compounds: with `handoff` (which handles conversation-state preservation; forge handles work-state preservation). Forge for things that should be tasks; handoff for things that should be conversation context.

Limits: relies on the user (or an agent's checkpoint recommendation) to fire. Forge does not auto-detect "this deserves checkpointing"; it has explicit triggers in CLAUDE.md but those still require the model to recognize the trigger and act on it. Misses are common in fast-moving conversations.

---

```yaml
---
component: reflect
type: skill
status: active
trigger_signals:
  - "two-strike correction pattern fires (current correction matches prior memory key)"
  - "user explicitly invokes /reflect"
prevents:
  - "repeated corrections on the same topic without rule update"
  - "umbrella memory bloating with dated tally entries instead of structural enforcement"
related: [bead-forge (for memory checkpointing), correction-discipline patterns]
---
```

When I reach for this: a correction fires AND a prior memory entry exists on the same topic within ~30 days. The skill reads the target artifact (an agent definition, a CLAUDE.md section, a skill body), checks whether the rule is already covered, and proposes a single targeted edit if coverage is missing.

What it prevents: the failure mode where corrections accumulate as dated entries (`correction:style:em-dash-2026-04-15`, `correction:style:em-dash-2026-04-22`, `correction:style:em-dash-2026-05-01`) without the underlying artifact being updated. The dated entries are tallies; tallies are not corrective. The skill enforces the umbrella-plus-enforcement discipline by deciding whether a fix is needed and shipping it.

Convergence: when the skill concludes "no edit needed" AND an umbrella memory plus structural enforcement (hook, linter) are already in place, future corrections on the same topic stop tallying. The umbrella is sufficient.

How it compounds: with the reflection-trigger discipline in CLAUDE.md (which fires the skill) and with the hooks (which provide the structural enforcement the umbrella refers to).

Limits: only as good as the model's recognition of trigger conditions. A correction that does not register as a "correction" (the model interprets it as a clarification) does not fire the reflect skill. The trigger sensitivity is calibrated; over-sensitive fires too often, under-sensitive misses real corrections.

---

```yaml
---
component: challenge
type: skill
status: active
trigger_signals:
  - "plan rests on assumptions about external state (resource existence, schema shape, API behavior)"
  - "user wants assumption stress-test before committing to a plan"
  - "/converge phase 4.5 (built-in challenge gate)"
prevents:
  - "plans that proceed on fragile assumptions"
  - "implementation work blocked by an assumption that turns out wrong"
related: [converge (uses challenge as a phase), tenth-man (adversarial sibling)]
---
```

When I reach for this: a plan exists, it makes claims about what's true outside the plan (a resource exists, a schema is shaped this way, an API behaves like that). The skill extracts those claims, scores their fragility, and stress-tests them against codebase evidence and domain constraints.

What it prevents: the highest-fragility category in implementation work is "assumptions about what exists." A plan that says "we'll write to the X table" silently assumes X exists; if it does not, implementation hits the wall at line 1. Challenge surfaces this before line 1.

How it compounds: invoked inside `/converge` as phase 4.5 (before convergence ships the plan to the user). Also invoked standalone for spot-checks.

Limits: challenge can flag assumptions that are correct AND load-bearing AND not worth questioning. The discipline is to challenge the high-fragility ones, not all of them. Calibration matters; over-eager challenge produces noise.

---

```yaml
---
component: consult
type: skill
status: active
trigger_signals:
  - "2+ specialists need to weigh in on the same code"
  - "cross-cutting findings (security + style + structure)"
  - "context window is too deep for serial subagent spawning"
prevents:
  - "serial specialist dispatches bloating main conversation context"
  - "specialists missing each other's findings (each sees only its own slice)"
related: [pr-intel (uses consult for multi-specialist work), large-task agent review]
---
```

When I reach for this: multiple specialist lenses are needed on the same code. The skill runs in a forked context, parallelizes the specialists, synthesizes a unified report.

What it prevents: invoking 4 specialists serially in the main conversation costs 4x the context. Consult runs in a fork so the main conversation gets only the synthesized report.

Implementation caveat: the `/consult` skill runs in a forked context where the Agent tool is unavailable. "Multi-lens" is one-mind synthesis (one model holding multiple specialist prompts in sequence, summarizing across). For true multi-specialist independent reads, dispatch Agent tool directly from main with `run_in_background=true`.

How it compounds: invoked inside `/pr-intel` when the PR triggers multiple specialist concerns. Also invoked standalone for large-task agent review.

Limits: forked-context limitation (above) means consult is not quite the same as parallel specialist dispatch. For high-stakes review work, parallel-Agent-from-main is the stronger pattern even though it costs main-conversation context.

---

```yaml
---
component: enrich
type: skill
status: active
trigger_signals:
  - "user pastes a Jira ticket ID or PR number"
  - "user asks 'what's the context on X' or 'brief me on Y'"
  - "preparing for a meeting or downstream skill invocation"
prevents:
  - "running analysis skills without the upstream context that informs them"
  - "missing design-doc context when reviewing implementation"
related: [pr-intel (consumes enrich output), converge (consumes enrich output)]
---
```

When I reach for this: any time the user references a Jira ticket, Confluence page, PR, or topic that needs external context loaded. The skill gathers ticket details, codebase references, AWS service state, Datadog signals, and domain knowledge into a structured briefing.

What it prevents: invoking analysis skills (pr-intel, converge, challenge) without enrich first produces analysis that misses upstream context. Enrich is the prerequisite step for most analysis work.

How it compounds: feeds into downstream skills as their input context. Enrich + pr-intel produces better reviews than pr-intel alone. Enrich + converge produces better plans than converge alone.

Limits: source coverage is bounded by available MCPs (Atlassian for Jira/Confluence, GitHub for PRs, AWS for service state, Datadog for signals). New external sources require new enrich source modules. The skill is extensible but each new source is real work.

---

The remaining 11 skills follow the pattern of "skill fires on a specific user request, produces a defined output." Entries for these will be added in the follow-up WORLDMAP sweep:

- `audit-worktrees` (worktree cleanup)
- `autopilot` (autonomous pipeline)
- `calibrate` (calibration drift review)
- `codility-review` (Codility submission rubric)
- `investigate` (production error investigation)
- `post-review` (post pr-intel output as GitHub review)
- `refine` (interactive prompt refinement)
- `review` (local self-review fan-out)
- `skill-catalog` (skill discovery for escalation awareness)
- `snapshot-system-prompt` (Claude Code version drift)
- `synthesize` (combine N inputs into structured output)
- `test-forge` (TDD test generation)
