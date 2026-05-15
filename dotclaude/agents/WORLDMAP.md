---
component: dotclaude/agents
type: directory-map
status: V0 partial sweep (10 of 21 agents have entries)
authored_by: Claude Opus 4.7
---

# WORLDMAP: Personal Agents

AI-authored commentary on each personal-tier agent in `~/.claude/agents/`. When I reach for the agent, what failure mode it prevents, how it compounds, and where it has limits. Entries follow the format documented in the top-level `WORLDMAP.md`.

V0 covers the highest-leverage agents. The remaining ~11 are mostly specialist linters (mx2-pydantic-reviewer, mx2-typescript-reviewer, mx2-python-style, mx2-security-auditor, mx2-silent-failure-hunter, mx2-devops-build-deploy, mx2-git-historian, mx2-pr-precedent, observability-reviewer, test-quality-reviewer) where the entries are mechanical: each fires on a specific concern (Pydantic, TypeScript, Python style, security, error handling, devops, git history, prior PR comments, observability, test quality), and my "when I reach for it" is "the diff touches that concern." Detailed entries for these will be added in follow-up sweep work.

---

```yaml
---
component: bot-review
type: agent
status: active
trigger_signals:
  - "PR diff changes public symbol signatures (exports, type defs, class signatures)"
  - "PR introduces a new public API surface"
  - "M+ size PR touching files with multiple consumers"
prevents:
  - "evaluating a diff in isolation when the actual blast radius is downstream"
  - "missing 'this signature change weakens an invariant a consumer assumes'"
related: [pr-precedent, code-reviewer]
---
```

When I reach for it: PR review work, specifically when the diff is making something publicly visible (new function exported, new type defined, signature change to a shared utility). I do not run it on every PR review; about 1 in 5 PRs touches a public symbol in a way that warrants the blast-radius lens.

What it prevents: code review naturally focuses on the diff in isolation. "Is this function correct? Is the test good?" The bot-review lens forces a different question: "What does each consumer assume that this change weakens?" The agent walks consumers of changed symbols and articulates the invariant each one depends on.

How it compounds: pairs with the code-reviewer (which evaluates the diff itself) and the pr-precedent agent (which carries forward concerns from prior PRs in the same area). Three lenses together catch overlapping failure modes that any single lens would miss.

Limits: cannot detect dynamic dependencies (reflection-based consumers, plugin-loaded code that references symbols by string). Works well for statically resolvable consumers (imports, references in well-typed code); blind to runtime dispatch.

---

```yaml
---
component: mx2-tech-lead
type: agent
status: active
trigger_signals:
  - "user asks 'what should we do about X' or 'how should I approach Y'"
  - "user pastes multiple unrelated sources (tickets, Confluence, Slack, code) and wants a coherent read"
  - "user needs to articulate something they understand intuitively but cannot put into words"
prevents:
  - "shallow synthesis from incomplete context"
  - "premature solutioning before the problem is framed"
  - "user's intuition lost in the gap between 'I know it' and 'I can write it down'"
related: [tenth-man, decision-maker]
---
```

When I reach for it: ambiguous problem spaces. The user paste of 6 unrelated tickets and asks "what is the shape here?" The conversation that needs three rebuttals to land on the right framing. The communication draft where the user knows the message but cannot find the words.

What it prevents: a general-purpose response to a synthesis problem produces general-purpose framing. The tech-lead's specific job is "find the shape under N sources," which it does better than a generalist because the prompt is shaped for that exact task.

Strict carve-out: NOT for evaluating reviewer feedback. The agent has a tendency to over-defend the original work when handling code-review responses. The harness has a separate guidance ("feedback-reception mode") for that case, with its own forbidden-response patterns.

How it compounds: works with the tenth-man (adversarial advisor) when the tech-lead's synthesis needs an adversarial check. The combination is "find the shape, then test the shape against naive questions."

Limits: the tech-lead is the most opinionated agent in the harness. Its framings are sharp, which is the point, but they can also be wrong. The author's rule (skeptic lens for specialist subagent recommendations) applies: when user evidence contradicts the tech-lead's recommendation, the tech-lead does not win by default.

---

```yaml
---
component: mx2-decision-maker
type: agent
status: active
trigger_signals:
  - "autonomous pipeline reaches an approval gate (autopilot, launch)"
  - "binary call needed: PROCEED, ITERATE, or ESCALATE"
prevents:
  - "pipeline stalling on a call that has a defensible answer"
  - "human-in-the-loop overhead on routine quality gates"
related: [tenth-man, code-reviewer]
---
```

When I reach for it: autonomous-pipeline mode where I need to decide whether to continue, iterate, or escalate to the user. Not for thinking-partner work (that is the tech-lead).

What it prevents: a pipeline that requires human approval at every gate is not autonomous. The decision-maker provides quality gating without forcing the user to adjudicate routine calls. The user gates the LAST decision (ESCALATE outcomes); the decision-maker handles the others.

How it compounds: pairs with calibration files (`calibration/decision-maker.md` and `calibration/decision-maker.lookback.md`) that capture HOW the agent makes calls. Calibration drift is reviewed periodically (the `/calibrate` skill), keeping the decision-maker's calls aligned with the author's preferred standards over time.

Limits: only as good as its calibration. New domains where calibration is thin produce uncertain decisions. The escape valve (ESCALATE) is load-bearing here; if calibration is thin AND the decision-maker tries to PROCEED anyway, the user might miss a bad call.

---

```yaml
---
component: mx2-tenth-man
type: agent
status: active
trigger_signals:
  - "high-blast-radius decision in an autonomous pipeline"
  - "user shows signs of fragmented attention (multi-window operational reality)"
  - "plan rests on assumptions about external state"
prevents:
  - "reflexive accept of an output that warrants scrutiny"
  - "buried risks in autonomous-pipeline outputs"
related: [decision-maker, challenge]
---
```

When I reach for it: autonomous-pipeline outputs that the user might reflexively accept. The tenth-man's job is to ask the naive, dumb, or obvious-but-unasked question that a careful reader would notice but a sampling reader might miss.

What it prevents: the multi-window operational reality means the user is sometimes scanning rather than reading. An adversarial advisor surfaces the question that the user did not ask but should have. The cost is one extra model call; the value is catching a load-bearing detail before it ships.

Strictly advisory. The tenth-man does not block; it raises questions. The user decides. This separation is intentional: the harness rule says "agents advise, the user decides."

How it compounds: paired with `decision-maker` (which makes binary calls) and `challenge` (which surfaces assumptions). All three are skeptic-lens tools in different roles.

Limits: false positives erode the user's trust in the tenth-man. The author has calibrated the prompt to reduce noise; calibration drift here is a known concern. The `calibrate` skill handles the periodic recalibration.

---

```yaml
---
component: mx2-code-reviewer
type: agent
status: active
trigger_signals:
  - "PR review work (own PR or others')"
  - "pre-commit structural review"
  - "self-review against project rules before push"
prevents:
  - "shipping code that violates project standards"
  - "missing structural anti-patterns the linter does not catch"
related: [bot-review, silent-failure-hunter, observability-reviewer]
---
```

When I reach for it: a diff exists and the user wants a structural review against the project's rules. The agent is the workhorse of PR review work; it fires on most reviews.

What it prevents: linters catch syntactic and shallow semantic issues. The code-reviewer catches design-judgment issues that require understanding the project's architecture: missing audit logging, log-and-reraise patterns, models reaching up into services, defensive validation against impossible states.

How it compounds: serves as the default in `/review` and `/pr-intel` skill dispatch. Other specialists (security, observability, silent-failure, test quality) layer on for specific concerns. The code-reviewer is the baseline pass.

Author Mode: when invoked pre-CI with the explicit "flag everything" context, the agent reports style, types, lint, naming, and design issues. The mode shift catches what would otherwise fail CI; this is the prophylactic use of the agent before a push.

Limits: the agent's quality is bounded by the project rules it loads. A project with thin rules produces thin reviews. The harness's project-tier rules directory is what gives this agent its depth in MX2 specifically.

---

```yaml
---
component: mx2-executor
type: agent
status: active
trigger_signals:
  - "bounded implementation task with known root cause"
  - "pattern-matching change against well-known conventions"
  - "single-file fix where acceptance criteria are clear"
prevents:
  - "strong-model token spend on mechanical work"
  - "the main conversation getting bogged down in implementation detail"
related: [code-reviewer (review-step)]
---
```

When I reach for it: well-scoped implementation tasks where I (the main conversation) understand what needs to happen, the change is mechanical, and the diff will be small. Dispatch to the executor (a Sonnet agent) with precise instructions; review the returned diff before committing.

What it prevents: a strong-model main conversation spending tokens on edits a smaller model could handle. The pattern is the load-bearing piece of the cost-via-delegation discipline.

Carve-out for PR iterations: when resolving bot feedback on already-pushed PRs and the fix is single-file and under 20 lines, do the edit directly instead of dispatching. Implementer dispatch overhead (200-400 seconds) exceeds direct-edit cost (30 seconds) for mechanical fixes.

How it compounds: the dispatch + review pattern means I retain quality oversight while reducing main-conversation token spend. Net cost is lower than pure-strong-model with same quality outcomes.

Limits: Sonnet quality varies by task. For multi-file refactors, ambiguous spec, or codebase exploration, the executor produces worse results than direct work. The trigger conditions are tight precisely because Sonnet self-assessment is unreliable.

---

```yaml
---
component: prompt-refiner
type: agent
status: active
trigger_signals:
  - "user prompt is brief and the dispatch target needs more context"
  - "I am about to dispatch to a specialist subagent"
  - "the conversation is mid-flow and the next dispatch needs a self-contained prompt"
prevents:
  - "subagents guessing at intent because the dispatch prompt was thin"
  - "round-trips lost to subagent clarification questions"
related: [refine (the skill version), launch-implementer (uses refiner output)]
---
```

When I reach for it: the user gave a terse prompt that I need to expand before dispatching to a subagent. The refiner reads the conversation context, fills gaps, and produces a self-contained prompt the subagent can act on without asking me for more.

What it prevents: a subagent invoked with "do X" without context will either guess or ask. Either way the round-trip cost is significant. The refiner front-loads the context so the subagent goes straight to work.

Used in headless mode (no human-readable refinement output) when invoked as part of dispatch automation. Used in interactive mode (`/refine` skill) when the user wants to see the refined version before sending.

How it compounds: most useful inside automation skills (`/launch`, `/pr-intel`, `/converge`) where the dispatch chain is several layers deep and each layer needs a self-contained prompt for the next.

Limits: the refiner can over-expand a prompt. A prompt that grew from 20 words to 200 words is harder for the subagent to act on than a 50-word focused prompt. Calibration matters; the agent's prompt template caps expansion length.

---

```yaml
---
component: observability-reviewer
type: agent
status: active
trigger_signals:
  - "PR touches metric emission, span instrumentation, or logging"
  - "PR adds or modifies a Datadog monitor"
  - "Lambda or ECS configuration change that affects observability scope"
prevents:
  - "shipping code with insufficient instrumentation to diagnose later"
  - "silent metric tag cardinality explosions"
  - "Datadog Error Tracking monitor filters keyed on renamed exception classes breaking silently"
related: [silent-failure-hunter, devops-build-deploy]
---
```

When I reach for it: diffs that touch instrumentation. The agent is mechanical in dispatch (the diff signals are clear), but its findings are often the highest-leverage finding on the PR because observability gaps are usually only noticed after a production incident.

What it prevents: a class of failure that hides for weeks until something breaks and the runbook says "check the dashboard" and the dashboard has no data because instrumentation was never added.

Dual-lens (Datadog provider stack + CloudWatch via MetricsCollector) reflects the codebase's reality. New code uses one stack; older code uses the other. Reviews catch when new code uses the wrong stack for its position in the codebase.

Limits: cannot evaluate runtime tag cardinality without sample data. The agent flags POTENTIAL high-cardinality patterns (user-id as a tag); confirming requires production-side investigation.

---

```yaml
---
component: launch-flex / launch-implementer / launch-tester
type: agent
status: active
trigger_signals:
  - "/launch skill is in execution phase"
  - "spawned by the launch orchestrator with a specific role"
prevents:
  - "main-conversation context bloat during multi-phase implementation work"
  - "subagent role drift (a subagent doing both code AND tests poorly)"
related: [/launch skill, mx2-code-reviewer (review steps), test-quality-reviewer]
---
```

When I reach for them: never directly. These are spawned by the `/launch` skill in execution phase. Each one has a focused role:

- `launch-implementer`: writes production code in a shared worktree, follows plan acceptance criteria, checks in via the standup protocol.
- `launch-tester`: writes tests in the same worktree, follows TDD principles, checks in via the same standup protocol.
- `launch-flex`: catch-all role that adapts to whatever the launch plan needs (infrastructure, migration, security, documentation).

The standup protocol (in `_shared/launch-protocol.md`) is what coordinates them. They post status updates to the orchestrator; the orchestrator decides phase transitions.

What it prevents: a single agent trying to write code AND tests AND infrastructure AND docs produces worse outputs in each domain than role-specific agents. The separation enforces focus.

How it compounds: with the orchestrator (`/launch` skill) which sequences phases and reviews handoffs. The orchestrator is the agent that holds the plan in context; the implementers operate against the plan without holding the whole context.

Limits: only as good as the plan. A vague plan produces vague implementation. The launch skill itself enforces plan quality (convergence phase before execution), which is the upstream check on agent quality.

---

```yaml
---
component: mx2-pr-precedent
type: agent
status: active
trigger_signals:
  - "PR introduces new abstractions in directories with multiple recent prior PRs"
  - "M+ size PR in a domain with active design churn"
prevents:
  - "missing concerns that already-merged peer reviewers raised in the same area"
related: [bot-review, code-reviewer]
---
```

When I reach for it: PR review in directories where I see multiple recent merged PRs in the file's neighborhood. The agent surfaces inline comments from those prior PRs that still apply to current diff lines, filtered against what current bot reviewers already raised.

What it prevents: each PR review is an isolated event; what one reviewer raised in PR #X may not surface in PR #Y in the same area even when the same concern applies. The agent carries forward the corpus of prior concerns and tests whether they apply now.

Output discipline: returns only the concerns that still apply AND are not already raised by current PR's bot reviewers. The dedup is the load-bearing piece; without it, the agent generates pile-on comments that erode reviewer trust.

How it compounds: pairs with bot-review (which evaluates the diff against consumer assumptions) and the code-reviewer (which evaluates against current rules). Three lenses across time (precedent), space (consumers), and current-state (rules).

Limits: requires gh API access to prior PR comments. Slower than other specialists because of the API round-trips. Worth the cost on PRs in churning areas; overhead on quiet directories.

---

The remaining ~11 agents follow the pattern of "specialist fires on a specific signal, produces findings in its domain." Entries for these will be added in the follow-up WORLDMAP sweep.

Calibration files (`calibration/*.md`) deserve their own commentary; they are the reflection-trigger mechanism applied to specialist agent calls. When an agent's calls drift from the author's preferred quality, the calibration file is updated with examples; the agent's prompt then references the calibration. Periodic review (the `/calibrate` skill) prevents drift accumulation.
