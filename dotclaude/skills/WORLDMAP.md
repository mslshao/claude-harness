---
component: dotclaude/skills
type: directory-map
status: V0 complete (all 22 skills have entries)
authored_by: Claude Opus 4.7
---

# WORLDMAP: Personal Skills

AI-authored commentary on each personal-tier skill in `~/.claude/skills/`. When I invoke the skill, what failure mode it prevents, how it compounds, and where it has limits. Entries follow the format documented in the top-level `WORLDMAP.md`.

Skills fall into four loose buckets: planning / decomposition (converge, bead-forge, refine, synthesize, challenge, consult, enrich), execution and review (launch, pr-intel, review, post-review, babysit-pr, test-forge, autopilot), investigation and memory (investigate, handoff, reflect, calibrate, snapshot-system-prompt), and tactical chores (audit-worktrees, codility-review, skill-catalog). The boundaries blur (autopilot is execution but also planning; reflect is memory but also rule-enforcement); the buckets are reading aids, not strict taxonomy.

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

```yaml
---
component: autopilot
type: skill
status: active
trigger_signals:
  - "user wants to 'kick off and walk away' on a planned or implementable task"
  - "task is well-scoped enough that human approval at every gate is overhead"
  - "explicit /autopilot invocation"
prevents:
  - "long-running work blocked on human availability at routine approval gates"
  - "decision-quality drop when the user must gate decisions they lack context for"
related: [converge, launch, decision-maker, tenth-man]
---
```

When I reach for this: well-scoped work where the gating decisions are routine and the decision-maker agent's calibration covers the call space. Two modes: `plan` (converge only, output = beads) and `build` (converge + launch, output = draft PR).

What it prevents: the failure mode where well-scoped work waits hours or days because the user wasn't around to approve a routine gate. The decision-maker handles the routine calls; the user gates only ESCALATE outcomes.

How it compounds: with decision-maker (quality gate at each checkpoint) and tenth-man (adversarial advisor on borderline calls). The decision-maker makes calls; the tenth-man surfaces what the decision-maker might have missed.

Limits: only as good as the decision-maker's calibration. Domains where calibration is thin produce uncertain decisions; the ESCALATE escape valve is load-bearing. The author's discipline: invoke autopilot in well-calibrated domains, prefer `/launch` with human gates in newer domains.

---

```yaml
---
component: review
type: skill
status: active
trigger_signals:
  - "user says 'review my changes', 'review this branch', 'self-review'"
  - "/review invocation pre-PR or pre-push"
  - "after writing a non-trivial diff that needs structural + specialist coverage"
prevents:
  - "shipping with style/test/security/observability gaps that specialists would catch"
  - "manual specialist invocation skipping a specialist that should have fired"
  - "serial specialist invocation costing main-conversation context"
related: [pr-intel, consult, code-reviewer, test-quality-reviewer, observability-reviewer, silent-failure-hunter]
---
```

When I reach for this: pre-PR or pre-push self-review on local changes. Personal-tier expansion of the project `/review` skill; dispatches in parallel to up to nine review agents (code, test-quality, observability, silent-failure, security, devops, typescript, git-historian, bot-review) with conditional triggers, deduplicates findings, presents a grouped severity report.

What it prevents: the failure mode where the user knows they should run reviewers but doesn't because manually picking which to invoke is friction. Auto-dispatch with conditional triggers removes the friction; the user runs `/review` and gets full coverage.

How it compounds: with `pr-intel` (review for self vs. review for others) and with `consult` (multi-specialist analysis in a forked context). All three are entry points to specialist coverage; the choice depends on what stage of work it is.

Limits: read-only and local-only. Does not post to GitHub, does not fetch external context (Jira, Datadog). For PR-aware review with external context, `pr-intel` is the right entry point. The skill is intentionally scoped for fast local feedback.

---

```yaml
---
component: post-review
type: skill
status: active
trigger_signals:
  - "user says 'post review', 'post these comments', 'submit review'"
  - "after a /pr-intel run when user signals readiness to post"
prevents:
  - "manual conversion of pr-intel output into inline GitHub review comments"
  - "comment metadata drift (file path, line number, side mismatches)"
  - "non-atomic reviews (some comments posted, the rest dropped on a network error)"
related: [pr-intel]
---
```

When I reach for this: `pr-intel` just produced a structured review and the user signals readiness to post. The skill takes the output and submits it as an atomic GitHub review (all comments land or none do).

What it prevents: the lossy step of manually copy-pasting pr-intel output into GitHub. Inline comments require file path, position, and side metadata; that mapping is error-prone by hand. The skill automates it.

How it compounds: with `pr-intel` (produces the structured output) and with `babysit-pr` (handles ongoing PR iteration after the initial review). The three skills cover the review-loop lifecycle.

Limits: requires `pr-intel` output in the expected format. Free-form review notes don't fit; the skill is shaped for the structured output specifically. Manual posts via `gh` CLI handle the free-form case.

---

```yaml
---
component: investigate
type: skill
status: active
trigger_signals:
  - "user pastes a production error, stack trace, or Lambda failure"
  - "phrases like 'what's causing this', 'prod issue', 'why is X failing'"
  - "silent regression where 'this started after [commit/deploy]'"
prevents:
  - "proposing fixes before understanding the failure (the Iron Law in debugging.md)"
  - "investigation that skips operational verification (just reading code)"
  - "single 'root cause' framing when multiple factors contribute"
related: [bead-forge (fix planning), consult (multi-specialist review)]
---
```

When I reach for this: any production error investigation. The skill ends at a structured investigation document that names contributing factors and the leading hypothesis; it does not propose fixes. The separation is intentional; fix proposals before investigation completes are guessing.

What it prevents: the most common debugging failure mode is jumping to a fix that pattern-matches the error message instead of tracing backward through the call path. The skill enforces the trace-backward discipline by structuring its phases.

How it compounds: feeds into `bead-forge` (when the investigation produces actionable fix items) or `/consult` (when multiple specialists need to weigh in on the diagnosis). Investigation is the prerequisite step; the skill is the entry point.

Limits: investigation quality is bounded by available evidence. CloudWatch logs missing, no Datadog signal, no reproduction case; the skill produces what it can with what's available. The author's discipline: name the evidence gaps explicitly, do not infer beyond them.

---

```yaml
---
component: refine
type: skill
status: active
trigger_signals:
  - "user invokes /refine on a rough prompt"
  - "phrases like 'improve my prompt', 'shape this into a prompt'"
  - "terse user input where the next dispatch needs more context"
prevents:
  - "subagents guessing intent when the prompt was thin"
  - "round-trips to clarify intent inside an agent dispatch"
related: [prompt-refiner (the agent version), converge (uses refine as a phase)]
---
```

When I reach for this: interactive prompt refinement. The user provides a rough prompt and wants help shaping it before invocation. The skill uses the full conversation history and tool access (codebase grep, file reads) to fill context.

What it prevents: terse prompts producing shallow responses. The skill front-loads context so the eventual dispatch has what it needs.

How it compounds: with the `prompt-refiner` agent (which does the same thing in headless mode inside automation skills). The skill is the interactive variant; the agent is the auto-dispatch variant. Different entry points, same function.

Limits: over-refinement can dilute the prompt. A prompt that grew from 20 words to 200 words is harder for the eventual agent to act on than a 50-word focused prompt. The skill's prompt template caps expansion; review the output before sending.

---

```yaml
---
component: synthesize
type: skill
status: active
trigger_signals:
  - "user has N disparate inputs and needs a single coherent artifact"
  - "ticket + doc + Slack thread + analysis result need merging"
  - "/synthesize invocation, often with 'from conversation' arg"
prevents:
  - "the synthesizing step being implicit and shallow (summary instead of structure)"
  - "opinion leakage in synthesis (the skill explicitly does NOT recommend or opine)"
related: [enrich (loads sources), converge (uses synthesis as a phase)]
---
```

When I reach for this: multiple sources need merging into one artifact. The discipline is no opinions, no recommendations; pure structure. Synthesis is structuring and connecting, not commenting.

What it prevents: the failure mode where synthesis becomes editorial. A summary that includes the author's take is not synthesis; it's commentary. The discipline matters because synthesized artifacts are often handoff input to other agents or other people; opinion leakage corrupts downstream work.

How it compounds: with `enrich` (which loads the sources) and with `converge` (which uses synthesis as a phase before challenge). Three-step pattern: enrich → synthesize → opinions land in challenge or downstream skills.

Limits: discipline is the constraint. A model that defaults to opinions has to be steered toward pure structure. The skill's prompt makes this explicit; the user verifies the output respects the no-opinion rule before passing it downstream.

---

```yaml
---
component: calibrate
type: skill
status: active
trigger_signals:
  - "SessionStart hook nudges about unmerged calibration entries"
  - "autopilot run surfaced a 'Calibration Drift' block"
  - "periodic review of accumulated calibration drift"
prevents:
  - "the calibration channel becoming write-only (subagents emit entries that nothing merges)"
  - "calibration files freezing in time while agent behavior drifts"
related: [decision-maker, reflect]
---
```

When I reach for this: the SessionStart hook tells me unmerged calibration entries exist. The skill reads `bd memories calibration:<agent>:*`, presents each entry with the current calibration file state, lets the user keep/merge/reject per entry. On merge it writes to the agent's calibration file and the audit log, then deletes the source memory key.

What it prevents: a frozen calibration system. Subagents (mx2-decision-maker today, others later) cannot write directly to their calibration files (the subagent sandbox restricts writes to the project workspace). Without this skill, the calibration channel is unidirectional: subagents emit drift, nothing reads it, nothing merges it. The skill is what makes calibration a learning loop.

How it compounds: with `decision-maker` (which emits drift entries) and `reflect` (which fires on corrections to update structural rules). Three feedback mechanisms for three scales of change: per-decision (calibration), per-rule (reflect), per-component (manual edit).

Limits: requires human judgment at the gate. The user reviews each entry; this is intentional (the calibration affects agent behavior across all future sessions) but bounds throughput. Bulk review of many entries is tedious; the workflow is designed for periodic review.

---

```yaml
---
component: snapshot-system-prompt
type: skill
status: active
trigger_signals:
  - "version-drift SessionStart hook nudges about Claude Code version mismatch"
  - "user installs a new Claude Code version and wants drift visibility"
  - "explicit /snapshot-system-prompt invocation"
prevents:
  - "Claude Code releases changing my behavior without the author noticing"
  - "harness rules silently shadowed by newer system-prompt content"
related: [reflect]
---
```

When I reach for this: the version-drift hook tells me the current Claude Code version no longer matches the latest snapshot. The skill captures the current system prompt's behavioral sections to a versioned snapshot file, then diffs against the most recent prior snapshot.

What it prevents: silent behavior drift when Claude Code updates. The system prompt changes between releases; some changes are additive, some shadow harness rules, some change default behaviors that the harness assumed. Without visibility, the author finds out about the change when something goes wrong.

How it compounds: with the version-drift SessionStart hook (which detects the version change) and with the `milestone:` memory entries (which mark which version any given snapshot corresponds to). Three layers of version awareness: hook, snapshot, memory.

Limits: snapshot quality is bounded by what the model can introspect about its own system prompt. Hidden directives or platform-level changes that don't surface in the prompt are invisible to this skill.

---

```yaml
---
component: test-forge
type: skill
status: active
context: fork
trigger_signals:
  - "user says 'forge tests', 'generate tests', 'create tests for this module'"
  - "test coverage gap that needs new tests"
prevents:
  - "tests that go through the motions (framework mechanics over behavior)"
  - "shipping test-generator output without quality review"
related: [test-quality-reviewer]
---
```

When I reach for this: a module needs new tests. The skill runs the `test-generator` agent (writes tests) and feeds the output through `test-quality-reviewer` (evaluates quality) in a loop, up to 3 iterations or until the reviewer is satisfied.

What it prevents: test-generator output landing without a quality gate. Generation-only patterns produce tests that pass on framework mechanics; the reviewer's job is to flag those, and the loop's job is to iterate until the tests verify behavior.

How it compounds: with `test-quality-reviewer` (the gate) and with the broader TDD discipline (write the test first, watch it fail, then implement). Test-forge is the agentic version of the discipline; an agent writes the tests, another agent verifies them.

Limits: 3-iteration cap. If 3 cycles don't produce satisfactory tests, the skill returns what it has and surfaces the unresolved concerns. Sometimes the issue is the module is poorly testable (no clean seams, deep mocks required); the test-forge loop will not fix that.

---

```yaml
---
component: audit-worktrees
type: skill
status: active
trigger_signals:
  - "/audit-worktrees explicit invocation"
  - "user mentions 'clean up worktrees', 'stale branches'"
  - "worktree count grows past comfort threshold (operational signal)"
prevents:
  - "/launch and /autopilot worktrees accumulating after their parent agents exit"
  - "disk usage and git-config bloat in heavy launch/autopilot use"
  - "orphaned branches that confuse later automation"
related: [launch, autopilot]
---
```

When I reach for this: explicit user request, or when worktree count is growing during heavy `/launch` + `/autopilot` work. The skill produces a deletion plan with verification evidence per branch, then confirms before deleting (unless `--auto` and count is bounded).

What it prevents: heavy launch and autopilot use produces orphans: agents that crashed before cleaning up, `/pr-intel` staging worktrees authored by previous sessions, merged-and-shipped branches that no longer need a worktree. Worktree-create-log and worktree-remove-log hooks handle the happy path; this skill handles the sad path.

How it compounds: with the worktree hooks (which handle clean termination) and with `/launch` + `/autopilot` themselves (which create the worktrees). The skill is the cleanup pass that closes the loop.

Limits: verification per-branch requires API calls (PR state, merge state). Auditing many worktrees is slow. The `--auto` path bounds blast radius (deletion count cap) but the user should review the deletion plan when invoking interactively.

---

```yaml
---
component: codility-review
type: skill
status: active
trigger_signals:
  - "user pastes a Codility submission with timeline + Cody transcript + code"
  - "explicit /codility-review invocation"
  - "candidate evaluation for the Legal Document Management API assessment"
prevents:
  - "inconsistent candidate evaluation across the team"
  - "missing the authorship-authenticity gate when level-calibration looks good"
related: []
---
```

When I reach for this: a candidate's Codility submission needs evaluation. The skill runs a two-pass rubric. Pass 1 is the authorship authenticity gate (did the candidate author this, or did Cody / another AI?). Pass 2 is level calibration (which engineering level does this match?) and runs only if Pass 1 clears.

What it prevents: the failure mode where level-calibration looks correct but authorship is suspect. Without the explicit Pass 1 gate, a strong submission produced by AI assistance might pass calibration into a level the candidate cannot actually perform at.

How it compounds: standalone skill, used per-submission. The output (per-row scored Pass 1 read + level recommendation + optional draft recruiter reply) is the artifact that goes into the candidate file.

Limits: the rubric is project-specific (Legal Document Management API assessment) and the calibration is local to this hiring loop. Cross-org or cross-role uses would need different rubrics. The skill is narrow by design.

---

```yaml
---
component: skill-catalog
type: skill
status: active
user_invokable: false
trigger_signals:
  - "agent needs escalation awareness ('should I recommend a skill here?')"
  - "automatic preload into agents that need to know what's available"
prevents:
  - "agents giving help that another skill would do better"
  - "skill recommendations that don't match available skills"
related: [all skills]
---
```

When I reach for this: never directly; the catalog is loaded automatically into agents that need escalation awareness. The user never invokes it (`user_invokable: false`).

What it prevents: an agent producing a full response to a problem that a different skill is specialized to handle. The catalog gives the agent the option to say "this would benefit from `/skill-name`; it provides [specific value]" instead of doing the whole job badly.

How it compounds: with every skill in the catalog. The catalog is the index; each entry includes the trigger condition and the value-add. An agent reading the catalog can route the user to the right skill.

Limits: the catalog is curated by the author; new skills require manual entry. Skill auto-discovery would solve this but introduces drift (a catalog claiming a skill that has since been deleted is worse than a manually-curated one). Manual curation is the author's tradeoff.
