---
component: dotclaude/skills
type: directory-map
status: V0 complete (all 32 skills have entries)
authored_by: Claude Opus 5
---

# WORLDMAP: Personal Skills

AI-authored commentary on each personal-tier skill in `~/.claude/skills/`. When I invoke the skill, what failure mode it prevents, how it compounds, and where it has limits. Entries follow the format documented in the top-level `WORLDMAP.md`.

Skills fall into four loose buckets: planning / decomposition (converge, bead-forge, ideate, refine, synthesize, challenge, consult, enrich), execution and review (launch, campaign, pr-intel, review, cold-review, post-review, babysit-pr, overwatch, test-forge, autopilot), investigation and memory (investigate, handoff, reflect, compound, calibrate, snapshot-system-prompt, recall, bd-related, capture-transcript), and tactical chores (audit-worktrees, codility-review, doc-sweep, standup-prep, skill-catalog). The boundaries blur (autopilot is execution but also planning; reflect is memory but also rule-enforcement; overwatch watches rather than executes); the buckets are reading aids, not strict taxonomy.

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
related: [converge (uses challenge as a phase), skeptic (adversarial sibling)]
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
related: [converge, launch, decision-maker, skeptic]
---
```

When I reach for this: well-scoped work where the gating decisions are routine and the decision-maker agent's calibration covers the call space. Two modes: `plan` (converge only, output = beads) and `build` (converge + launch, output = draft PR).

What it prevents: the failure mode where well-scoped work waits hours or days because the user wasn't around to approve a routine gate. The decision-maker handles the routine calls; the user gates only ESCALATE outcomes.

How it compounds: with decision-maker (quality gate at each checkpoint) and skeptic (adversarial advisor on borderline calls). The decision-maker makes calls; the skeptic surfaces what the decision-maker might have missed.

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

```yaml
---
component: compound
type: skill
status: active
trigger_signals:
  - "substantial-completion signal (PR merged, /launch shipped, bead closed) AND the work surfaced a novel technique not yet captured as a habit:* memory"
  - "user explicitly says 'extract the pattern', 'capture this workflow', 'what's reusable here', '/compound'"
  - "3+ exchanges where the user landed on a deliberate technique, not just an outcome"
prevents:
  - "novel approaches lost between session compactions because nothing wrote them to memory"
  - "first-observation insights that never reach workflow.md or topic files because hand-noticing is unreliable under multi-window operational reality"
related: [reflect, bead-forge, handoff, workflow.md memory file]
---
```

When I reach for this: after work that worked. The proactive sibling of `/reflect`. Reflect fires on user corrections (something went wrong); compound fires on novel-but-quiet successes (nothing went wrong, but the approach is worth replicating). Without the proactive variant, only failures shape the harness; successes evaporate.

What it prevents: the gap between `/reflect`, `/bead-forge` checkpoint mode, and `/handoff`. Reflect catches mistakes. Checkpoint preserves in-flight conversation context. Handoff produces a cold-start prompt for one specific next session. None of these capture "this work just shipped, the approach was novel, a future session would benefit from knowing what we figured out." Compound is the missing routing primitive.

How it compounds: with `workflow.md` (the second-observation promotion gate; compound writes first-observation habits there) and `bead-forge` (compound invokes forge's memory checkpoint mode internally for Routes 1 and 3, so habits get a real bead ID, structured fields, and chronological log entry). The skill is built on top of existing primitives, not in parallel to them.

Limits: requires human judgment at the present-for-accept gate. The user reviews each candidate pattern before it lands as a habit memory; the skill does not write to durable surfaces unilaterally. Throughput is bounded by the human review step; the design choice favors precision over volume.

```yaml
---
component: ideate
type: skill
status: active
trigger_signals:
  - "user says 'what are my options for X', 'brainstorm Y', 'tradeoffs between X and Y', 'which approach should I take'"
  - "problem statement before any specific approach is on the table"
  - "/ideate explicit invocation, often with a Jira ticket, bead, Slack thread, Confluence draft, or transcript as input"
prevents:
  - "jumping into /converge on the first plausible approach without considering N alternatives"
  - "rejected alternatives lost (only the winning approach gets stress-tested; rivals evaporate after the decision)"
  - "missing the upstream-of-converge gap in the planning pipeline"
related: [converge, consult, challenge]
---
```

When I reach for this: the user has a problem but does not yet know which of N approaches to pursue. `/converge` starts from a refined approach and stress-tests it; `/consult` is multi-specialist review on the SAME code; `/challenge` is adversarial assumption extraction on an EXISTING plan. None of those answer "I have a problem, I do not yet know what to do." Ideate is that upstream entry point.

What it prevents: the single-approach trap. When the agent jumps to the first plausible approach, the rejected alternatives are not just lost; they were never considered. The structured ideate pass forces divergent generation, ranking, and a skeptic pass before handing the winner to `/converge`. The rejected alternatives are preserved in the output for later reference (a later session may find the rejected option was actually right under changed constraints).

How it compounds: with `converge` (the downstream stress-test on the chosen approach), `consult` (specialists weigh in on borderline rankings during ideate's evaluative phase), and `challenge` (adversarial pressure on the winner's assumptions inside ideate's skeptic pass). The four skills compose into a planning pipeline: ideate (divergent) → converge (stress-test the winner) → launch (build it) → babysit-pr (watch the rollout).

Limits: the ranked-approach output is the artifact; the user decides whether to accept the recommended winner. The decision-maker iterate gate at the end of ideate flags low-confidence calls for escalation, but the human still owns the final approach choice. Ideate is a structured thinker, not a decider.

---

```yaml
---
component: recall
type: skill
status: active
trigger_signals:
  - "user references past work without a current-session referent ('the thing with X', 'what we discussed about Y')"
  - "vague pronouns ('that bug', 'the doc') with no in-session antecedent"
  - "cold-start session where the user assumes context this session does not have"
prevents:
  - "answering from thin context when the real answer lives in another session's beads, memories, or topic files"
  - "fabricating a plausible-but-wrong referent for a vague reference"
  - "deep-reading the wrong artifact because the search was single-corpus (beads only, or memories only)"
related: [enrich, bd-related, investigate]
---
```

When I reach for this: the user references work I have no current-session memory of. Phrases like "what we landed on for X", "remind me about Y", or a bare named entity that was never introduced this turn. The skill runs a breadth-first search across all three persistent corpora (beads titles + descriptions, memory keys + values, topic files) in parallel and returns one-line previews with IDs and recency, then stops; the agent decides which hits warrant a deep read.

What it prevents: the failure mode where a vague back-reference gets answered from the shallow current context, producing a confident-but-wrong answer because the actual decision lives in a closed bead from three sessions ago. The BFS-only discipline is the safeguard against the opposite failure too: pulling full content for every hit blows the context budget before the right artifact is even identified. Recall surfaces the map; DFS into the territory is a separate, agent-initiated step.

How it compounds: with `enrich` (recall finds the ID when it is unknown; enrich loads full context once the ID is known, so recall feeds enrich) and with `bd-related` (recall calls `bd_related.py` for the memory-graph leg of its parallel search). It is the consumer-side complement to the producer-side `bd-recency-surface` hook: the hook surfaces what is in the corpus at write time, recall queries it at read time.

Limits: coverage is bounded by what the search corpora hold. There is no comment-search flag, so bead comments are invisible to recall; and the `--status all` requirement is load-bearing precisely because the target work usually lives in closed beads that `bd` excludes by default. When recall returns nothing and the user is certain the info exists, the escape valve is the external surfaces (Slack, Jira, Confluence) the skill names explicitly.

---

```yaml
---
component: bd-related
type: skill
status: active
user_invokable: false
trigger_signals:
  - "about to write a plan / review / fix in a known domain AND the load-time preload hook has not fired for this task"
  - "user names a topic, bead, or memory key and wider corpus context is wanted before responding"
  - "a subagent's findings need cross-checking against prior correction memories in the same domain"
prevents:
  - "forming a response in a domain without seeing the prior corrections that govern it"
  - "missing a ratified decision living in a sibling bead under a different epic"
  - "the load-time preload hook being the only graph walk, when it did not cover the mid-conversation domain shift"
related: [recall, enrich]
---
```

When I reach for this: never via the user (`user_invokable: false`); it is a model-only subroutine. I invoke it when entering a domain mid-conversation that the most recent /enrich, /converge, or /pr-intel did not cover, or when I want the wider neighborhood of a seed (memory key, bead ID, or free-text keyword) before forming a response. It walks the personal memory graph: matches, bridges (co-mentioned cross-tree neighbors), and namespace siblings/cousins.

What it prevents: the specific failure the harness keeps relitigating, where the ratified decision lives in a sibling bead under a different epic and a parent-only check misses it. The walker surfaces those cross-tree neighbors (the `bridge` kind ranks first for exactly this reason) so a review or plan does not proceed in ignorance of a correction or decision that already governs the case. It is the deliberate, on-demand graph walk that backstops the load-time `preload-sibling-beads.sh` hook when that hook did not fire for the current task.

How it compounds: it is the graph engine underneath `recall` (recall calls `bd_related.py` for its memory-graph leg) and a precursor to `enrich` (the walker names what is relevant; enrich loads it). Three layers of context retrieval at different granularities: the load-time hook (automatic, allowlist-gated), bd-related (on-demand, model-invoked), and recall (user-facing, multi-corpus).

Limits: output is informational, not directive: a surfaced neighbor does not mean the user wants action on it, and treating it as a to-do list is the misread to avoid. Quality also depends on the namespace index and bridges file being fresh; both regenerate in under two seconds, but a stale graph (corpus changed substantially since the last build) silently undercovers.

---

```yaml
---
component: capture-transcript
type: skill
status: active
trigger_signals:
  - "user pastes a standup / sync / 1:1 transcript with capture intent ('capture this standup', 'here is the transcript')"
  - "explicit /capture-transcript invocation, optionally with a standup | sync | 1:1 hint"
  - "a meeting transcript streamed in chunks across turns ('continuation', 'last chunk')"
prevents:
  - "high-value transcript signal lost to compaction because nothing wrote it to a durable file"
  - "each capture re-deriving the two-tier memory conventions and slipping on identity, sensitivity, or length discipline"
  - "candid 1:1 people-content leaking into Dolt-synced beads or shared surfaces"
related: [handoff, bead-forge, recall]
---
```

When I reach for this: a meeting, standup, or 1:1 transcript is pasted with capture intent. The skill is the INBOUND complement to the slack plugin's `/standup` (which generates an OUTBOUND status from the author's own activity). It classifies the transcript into one type, then routes: an ephemeral scannable action breakdown for a standup, or a durable `memory/` file plus recall bead plus log entry plus index row for a sync or 1:1.

What it prevents: pasted transcripts are high-value and high-loss; they carry decisions and org signals but arrive garbled (names mangled by transcription) and evaporate at compaction. The two-tier architecture has exact conventions for where each capture lands, and without a skill every capture re-derives them and slips on one of the three disciplines: identity (resolve names against org-context, mark unresolved ones tentative, never fabricate), sensitivity (a 1:1's candid people-content stays in the local file, never in a Dolt-synced bead title), and length (index rows under the lint cap). It encodes all three once.

How it compounds: it shares the durable-capture machinery with `bead-forge` (the recall bead, the `log-append.py` chronological entry) and is the meeting-transcript-shaped sibling of the other capture primitives. `/handoff` produces a cold-start prompt for the next session; `/bead-forge` checkpoint preserves in-flight conversation analysis; `bd remember` stores one fact; this skill captures a meeting that already happened. Its durable output then becomes discoverable through `recall`.

Limits: classification and routing are only as good as the transcript and the org-context source of truth. A name that will not resolve gets marked tentative rather than guessed, and a misrouted decision-bearing standup (sent to ephemeral output because its form is a standup) is the named anti-pattern the skill guards against but still depends on the model recognizing the decision content. The chunked-streaming path adds a finalization discipline (one PARTIAL banner, defer the log append to the closing chunk) that a careless re-run per chunk would violate.

---

```yaml
---
component: campaign
type: skill
status: active
trigger_signals:
  - "an epic already decomposed into PR-sized node beads that are each bypass-shaped"
  - "user says 'run the campaign for <epic>', 'execute the epic unattended', 'walk-away build the stack'"
  - "bare re-invocation after a halt, an abandon, or a context-budget rollover (the resume path)"
prevents:
  - "an unattended runner improvising on a malformed node bead instead of stopping"
  - "double-firing a node whose inner /launch is still live after a session died mid-node"
  - "a downstream PR stacking on a failed or silently stale base"
related: [launch, converge, ideate, audit-worktrees]
---
```

When I reach for this: never for a single ticket, and never to plan. One human `/converge` happens BEFORE this skill enters the picture. Campaign owns only the epic layer (node ordering, stack bases, cursor durability, halt and abandon semantics, the run report) and hands every node to `/launch` inline with `--gate=agent`. It adds no judgment about WHAT to build.

What it prevents: the incoherence failure of a walk-away runner filling in a gap. A node bead reading "implement the design" would fall through launch's pre-converged bypass into a full UNATTENDED re-converge, which is a plan nobody reviewed becoming code nobody asked for. The construction gate is the last attended moment in the run, and it fails loudly listing every deficient bead rather than proceeding. The second class is duplicate work on resume: node status is always re-derived from the node bead's own event log, never trusted from the cursor cache, so an `in_flight` node holding a live launch lock is waited on rather than re-driven.

How it compounds: with `/launch` (the per-node engine, including its own review fan-out and draft-PR finalization) and with `audit-worktrees` (the cleanup pass for the orphans a halted chain leaves behind). Failure is a whole-chain halt, not a per-node skip: every open PR in the chain gets a status comment, including the green upstream ones, because a green parent merged mid-halt would strand the rest.

Limits: sequential nodes only in v1, since worktree and branch naming is second-resolution and collides under concurrency. It never merges, never flips a draft ready, and never performs terminal ticket transitions. "Walk away" is bounded by the machine: a codespace that sleeps during a CI wait kills the poll, and recovery is a manual bare re-invocation. The mid-run merge case is a deliberate loud halt rather than an autonomous fix, because a lease push needs a human verb that round. And the skill gates itself on a drill suite (`docr-k8l6y`) that had to be green before its first real epic, which is the honest read: this was not trusted on arrival.

---

```yaml
---
component: cold-review
type: skill
status: active
trigger_signals:
  - "a consequential change is finished and this session wrote both the code and every review of it"
  - "user says 'cold review', 'external review prompt', 'hand this to a fresh session'"
  - "a review came back and its findings need to cross back to the implementing session"
prevents:
  - "same-session review inheriting the author's framing, so review misses stay correlated with author blind spots"
  - "diff-anchored review missing the reuse and sibling-path-parity classes that live outside the hunks"
  - "review findings dying at the boundary, since the implementing session never sees the review"
related: [review, pr-intel, post-review, handoff]
---
```

When I reach for this: after finishing a consequential change, in place of another `/review` plus `/pr-intel --mine` cycle. The skill PRODUCES a prompt; it does not run the review. Running it here, even by spawning a subagent, reintroduces the exact bias it exists to remove, because this session would be authoring the reviewer's prompt.

What it prevents: two failures that are easy to conflate, and only one of them is about who reviews. Framing correlation is the WHO: multi-agent fan-outs give subagents fresh context windows, but the implementing session writes their prompts, and a 7-lens same-session pass missed or killed 8 findings that a human peer and a bot both caught (2026-07-24). Diff-anchoring is the HOW, and three independent retros found it the larger cause: on one PR, 5 or 6 of 9 substantive human findings were sibling-path parity divergences, a class no diff-anchored lens owns because the sibling code is unchanged and often in another package. That is why the emitted artifact carries four fixed contextual reaches (reuse search, sibling-path parity, reference resolution, invariant pinning) as template rather than advice.

The operational rules in it are scar tissue, not polish: pin the head SHA and read and grep through it (a working-tree grep answers the reference-resolution question against the wrong branch and reports a rename as incomplete); fetch before diffing, or a stale local base reports 33 files for a 3-file PR; and check whether the acceptance criteria were amended after implementation, because an AC list carrying the author's own verification results is author framing wearing a requirement's clothes.

How it compounds: it is the author-side third of the review surface (`/review` is same-session and local, `/pr-intel` is someone else's PR). The hand-back template is the half that is easy to overlook: the implementing session cannot see the review, so the per-round FIX REQUEST block is the only thing that crosses, and its ALREADY VERIFIED section is what keeps round N+1 from re-running the reviewer's work.

Limits: the decorrelation half is explicitly unproven and under evaluation (bd `docr-qc87r`); only the diff-anchoring half rests on measured evidence today. Nothing enforces the handoff either. The skill can emit a perfect prompt and the user can paste it into a subagent of the authoring session, which buys the contextual reaches and none of the decorrelation, and the output will look identical.

---

```yaml
---
component: overwatch
type: skill
status: active
trigger_signals:
  - "'watch my work queue', 'tell me when something needs my attention' asked as a STANDING request"
  - "user is heads-down and does not want to break focus to poll beads, PRs, and tickets"
  - "a bare /overwatch arriving from its own scheduled wakeup"
prevents:
  - "hand-polling three sources every hour to answer 'what should I pick up next'"
  - "a watcher that is itself a notification source (noisy no-op cycles)"
  - "a source that errored being read as a source that was quiet"
related: [babysit-pr, standup-prep, launch]
---
```

When I reach for this: standing requests only. "What is ready right now" is `bd ready`; overwatch is for the case where the polling itself is the toil. It runs a self-paced wakeup loop over beads, PRs, and tickets, surfaces only deltas (a bead newly unblocked, a review newly requested, an in-progress item going stale), and keeps all state as one JSON blob in a tracking bead so any wakeup can cold-start.

What it prevents: the obvious answer is manual polling, but the more interesting one is the failure of watchers generally, which is that they become noise. A cycle with no deltas and every source healthy prints nothing at all, so silence carries information. Two smaller disciplines back that up: a source's failure is its exit code and never an empty stdout (so an outage is never mistaken for a quiet queue), and state is persisted AFTER output, so a crash re-alerts rather than marking an alert seen that the user never received. Duplicate over drop, deliberately.

How it compounds: it is the read-only counterpart to `babysit-pr` (single PR, mutating, window-bounded) and the forward-looking counterpart to `standup-prep` (backward-looking, one-shot). It also inverts babysit-pr's state mechanism on purpose: a fixed-size blob replacing the bead's notes each cycle, because babysit-pr's append-only comment log is fine across a handful of cycles and unbounded in a standing loop.

Limits: the skill names its own tradeoffs, and they are real. Coverage is in-session only: both scheduling primitives fire only while the REPL is alive, so a codespace that sleeps on idle kills the loop, and there is no server-side mechanism in v1. Output is chat-only, which is the sharpest limit, because a delta can land in one of five concurrent windows and go unseen, and by construction the user does not notice a miss on a channel they are not watching. Lose the tracking bead and the loop re-baselines from scratch for one silent cycle rather than reconstructing what it knew.

---

```yaml
---
component: standup-prep
type: skill
status: active
trigger_signals:
  - "'prep my standup', 'verbal standup', 'what did I do yesterday / Friday', 'what did I ship'"
  - "post-PTO catch-up across several days (`--days N`)"
  - "a bare 'help me with standup' when recent context is code, PR, and ticket work"
prevents:
  - "work misfiled onto the wrong day because the sources are UTC-stamped and the day is local"
  - "a Slack sweep that reads public-only or page one and silently drops most of the day"
  - "bot comments posted under the user's token being reported as review activity"
related: [capture-transcript, overwatch, handoff]
---
```

When I reach for this: the user wants a spoken talk-track built from their own activity for a past day. Outbound generation, gathered across git, authored and reviewed PRs, PR and issue comments, tickets, Confluence, beads, and Slack. Read-only; it never posts or mutates.

What it prevents: three concrete, observed errors. The day boundary is first and the skill treats it as load-bearing: the local UTC offset is derived mechanically from the user's own commit stamps and every source is re-binned against it, because hand-computing a date or a day of week is exactly where the wrong day creeps in. Second is the truncated sweep: a public-only Slack search returned 1 message where private plus DMs returned 109 across 6 pages, and stopping at page one drops the start of the day (descending sort puts the morning last), so the output must state how many pages were read. Third is overclaiming: stack-management and merge-activity comments the bot posts under the user's token are filtered out, and the exclusion is flagged rather than done silently.

How it compounds: the inbound complement is `capture-transcript` (what others said in a meeting that already happened); the Slack plugin's `/standup` is the lighter Slack-only path when a postable channel message is all that is wanted. `overwatch` covers the forward-looking half of the same question.

Limits: a good part of this file is a vendor-quirk ledger, and quirks expire. Bare dates in Confluence search evaluate in UTC while ticket search uses the profile timezone; the Slack tool's `after`/`before` parameters are epoch seconds rather than dates; a contributor filter returns pages the user ever touched, not pages they touched that day. Each is verified and each is true only until the vendor changes it, and nothing here detects when that happens. The Confluence last-modified value comes back as a friendly string ("yesterday at 6:23 PM") that cannot support exact gating at all, so that source is accepted approximately by design. Default scope is the current repo; multi-repo weeks need an explicit loop.

---

```yaml
---
component: doc-sweep
type: skill
status: active
trigger_signals:
  - "monthly cadence on one specific Confluence page series"
  - "after a batch of agent, skill, or rule additions that the pages document"
  - "a prior review left findings unapplied"
prevents:
  - "documentation describing a harness that no longer exists (inventory and model-lineup drift)"
  - "editing a page from memory of what it said rather than from a fresh fetch"
  - "a fix applied against a stale claim about what an enforcement hook actually blocks"
related: [handoff, compound]
---
```

When I reach for this: maintenance of one named Confluence series, on a monthly-ish cadence or after harness changes that the pages describe. Verify-then-fix in two workflows: parallel read-only agents check each page and fact-check external product claims, then per-page fix agents apply exact-substring edits, publish, and re-fetch to confirm.

What it prevents: the drift classes that a docs corpus about fast-moving tooling accumulates by default (agent and command inventories going stale, third-party product claims rotting on roughly a monthly cycle, mechanical schema slips). More specific to this skill's shape: it prevents the fix pass from becoming its own source of damage. Edits are exact substrings against a freshly fetched body with an occurrence-count guard, the fetch aborts on version drift, and every replacement is verified by re-fetch.

Two habits worth naming because they are unusual: the skill distrusts its own reviewers (a proposed "schema drift" finding is checked against the ratified schema first, after a reviewer flagged a deliberate special case as drift), and it reads enforcement claims from the hook source rather than a memory paraphrase (a stale memory claim about a hook degraded a fix once).

How it compounds: with the page-format memory file, which is both its input and its output. Each sweep writes back a convergence-history entry and an updated held-items list, so the next sweep starts from what the last one could not close.

Limits: narrow by construction, and it says so. One page series, one author, one space, personal-tier with no promotion path (the machinery reaches into personal memory files and hooks). Items owned by someone outside the loop are never fixed unilaterally, so a sweep can finish "converged" with known drift still standing. Cadence is a recurring bead check rather than cron because the codespace sleeps, which means in practice the sweep runs when someone remembers it. And it accepts a documented class of round-trip noise (trailing-space widening, bold-link normalization) rather than chasing it.
