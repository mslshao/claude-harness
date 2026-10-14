---
component: dotclaude/agents
type: directory-map
status: V0 (13 of 22 agents have entries; the 9 added on 2026-10-14 have none yet)
authored_by: Claude Opus 5
---

# WORLDMAP: Personal Agents

AI-authored commentary on each personal-tier agent in `~/.claude/agents/`. When I reach for the agent, what failure mode it prevents, how it compounds, and where it has limits. Entries follow the format documented in the top-level `WORLDMAP.md`.

The agents divide into three rough classes: thinking-partner agents (tech-lead, decision-maker, skeptic) that operate at the framing layer; structural reviewers (code-reviewer, executor, prompt-refiner) that do code-shaped work; and specialist linters (TypeScript, silent-failure, observability, test quality, module cohesion, blast-radius-reviewer, pr-precedent) that fire on narrow concerns. The boundaries between classes are not absolute; blast-radius-reviewer and pr-precedent in particular live between "linter" and "memory mechanism." The voice of each entry tries to name what makes that agent earn its keep, not just what it does.

---

```yaml
---
component: blast-radius-reviewer
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

What it prevents: code review naturally focuses on the diff in isolation. "Is this function correct? Is the test good?" The blast-radius-reviewer lens forces a different question: "What does each consumer assume that this change weakens?" The agent walks consumers of changed symbols and articulates the invariant each one depends on.

How it compounds: pairs with the code-reviewer (which evaluates the diff itself) and the pr-precedent agent (which carries forward concerns from prior PRs in the same area). Three lenses together catch overlapping failure modes that any single lens would miss.

Limits: cannot detect dynamic dependencies (reflection-based consumers, plugin-loaded code that references symbols by string). Works well for statically resolvable consumers (imports, references in well-typed code); blind to runtime dispatch.

---

```yaml
---
component: tech-lead
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
related: [skeptic, decision-maker]
---
```

When I reach for it: ambiguous problem spaces. The user paste of 6 unrelated tickets and asks "what is the shape here?" The conversation that needs three rebuttals to land on the right framing. The communication draft where the user knows the message but cannot find the words.

What it prevents: a general-purpose response to a synthesis problem produces general-purpose framing. The tech-lead's specific job is "find the shape under N sources," which it does better than a generalist because the prompt is shaped for that exact task.

Strict carve-out: NOT for evaluating reviewer feedback. The agent has a tendency to over-defend the original work when handling code-review responses. The harness has a separate guidance ("feedback-reception mode") for that case, with its own forbidden-response patterns.

How it compounds: works with the skeptic (adversarial advisor) when the tech-lead's synthesis needs an adversarial check. The combination is "find the shape, then test the shape against naive questions."

Limits: the tech-lead is the most opinionated agent in the harness. Its framings are sharp, which is the point, but they can also be wrong. The author's rule (skeptic lens for specialist subagent recommendations) applies: when user evidence contradicts the tech-lead's recommendation, the tech-lead does not win by default.

---

```yaml
---
component: decision-maker
type: agent
status: active
trigger_signals:
  - "autonomous pipeline reaches an approval gate (autopilot, launch)"
  - "binary call needed: PROCEED, ITERATE, or ESCALATE"
prevents:
  - "pipeline stalling on a call that has a defensible answer"
  - "human-in-the-loop overhead on routine quality gates"
related: [skeptic, code-reviewer]
---
```

When I reach for it: autonomous-pipeline mode where I need to decide whether to continue, iterate, or escalate to the user. Not for thinking-partner work (that is the tech-lead).

What it prevents: a pipeline that requires human approval at every gate is not autonomous. The decision-maker provides quality gating without forcing the user to adjudicate routine calls. The user gates the LAST decision (ESCALATE outcomes); the decision-maker handles the others.

How it compounds: pairs with calibration files (`calibration/decision-maker.md` and `calibration/decision-maker.lookback.md`) that capture HOW the agent makes calls. Calibration drift is reviewed periodically (the `/calibrate` skill), keeping the decision-maker's calls aligned with the author's preferred standards over time.

Limits: only as good as its calibration. New domains where calibration is thin produce uncertain decisions. The escape valve (ESCALATE) is load-bearing here; if calibration is thin AND the decision-maker tries to PROCEED anyway, the user might miss a bad call.

---

```yaml
---
component: code-reviewer
type: agent
status: active
trigger_signals:
  - "PR review work (own PR or others')"
  - "pre-commit structural review"
  - "self-review against project rules before push"
prevents:
  - "shipping code that violates project standards"
  - "missing structural anti-patterns the linter does not catch"
related: [blast-radius-reviewer, silent-failure-hunter, observability-reviewer]
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
component: task-executor
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
component: pr-precedent
type: agent
status: active
trigger_signals:
  - "PR introduces new abstractions in directories with multiple recent prior PRs"
  - "M+ size PR in a domain with active design churn"
prevents:
  - "missing concerns that already-merged peer reviewers raised in the same area"
related: [blast-radius-reviewer, code-reviewer]
---
```

When I reach for it: PR review in directories where I see multiple recent merged PRs in the file's neighborhood. The agent surfaces inline comments from those prior PRs that still apply to current diff lines, filtered against what current bot reviewers already raised.

What it prevents: each PR review is an isolated event; what one reviewer raised in PR #X may not surface in PR #Y in the same area even when the same concern applies. The agent carries forward the corpus of prior concerns and tests whether they apply now.

Output discipline: returns only the concerns that still apply AND are not already raised by current PR's bot reviewers. The dedup is the load-bearing piece; without it, the agent generates pile-on comments that erode reviewer trust.

How it compounds: pairs with blast-radius-reviewer (which evaluates the diff against consumer assumptions) and the code-reviewer (which evaluates against current rules). Three lenses across time (precedent), space (consumers), and current-state (rules).

Limits: requires gh API access to prior PR comments. Slower than other specialists because of the API round-trips. Worth the cost on PRs in churning areas; overhead on quiet directories.

---

```yaml
---
component: silent-failure-hunter
type: agent
status: active
trigger_signals:
  - "PR touches catch blocks, error handlers, or API error responses"
  - "PR adds frontend-backend integration (Python FastAPI to TypeScript Next.js)"
  - "diff modifies error propagation patterns or fallback logic"
prevents:
  - "Python exceptions becoming JSON error responses that TypeScript code silently drops"
  - "swallowed errors that produce empty arrays, default values, or 200 responses for failures"
  - "missing audit log calls on the error path"
related: [security-auditor, observability-reviewer, code-reviewer]
---
```

When I reach for it: any diff that touches error handling, especially when it crosses the Python and TypeScript boundary. The polyglot codebase's hardest failures live at the boundary: Python raises an exception, FastAPI converts it to a 500 JSON response, the TypeScript fetch call sees the response is non-2xx and returns an empty array rather than throwing. The user sees "no results" instead of an error.

What it prevents: silent data corruption. Caught-and-swallowed exceptions hide failures from users and operators. Missing audit log calls on error paths break compliance trails; a HIPAA-relevant operation that failed without a log entry is worse than the failure itself.

How it compounds: with security-auditor (checks audit fields on the calls that exist) and observability-reviewer (checks metric emission). Three lenses on the error-handling surface.

Limits: cannot detect runtime swallowing without execution. Static review catches the pattern (catch block without log, return-without-throw); the actual frequency of the swallow requires production telemetry.

---

```yaml
---
component: typescript-reviewer
type: agent
status: active
trigger_signals:
  - "PR touches src/typescript/mx2/ (Next.js web, Office add-ins, shared libraries)"
  - "TS diff evaluation pre-push"
  - "PR involves boundary code (frontend to backend integration)"
prevents:
  - "TS code shipping without the type safety MX2 expects (loose `any`, unchecked type assertions)"
  - "React/Next.js anti-patterns (uncontrolled rerenders, missing memo boundaries)"
  - "a11y or bundle-size regressions in user-facing apps"
related: [silent-failure-hunter, security-auditor, code-reviewer]
---
```

When I reach for it: any TypeScript change in the monorepo. The Python codebase has more reviewers; the TypeScript surface is thinner, so this agent is the primary structural-review lens for TS.

What it prevents: TS-specific patterns that the Python-focused reviewers would not catch. React/Next.js patterns, frontend performance concerns (bundle size, a11y, hydration), TS-specific error handling (cause chains, catch semantics).

How it compounds: routes boundary errors to silent-failure-hunter (which understands the polyglot boundary), PII concerns to security-auditor, cross-stack structural concerns to code-reviewer. The agent is the front door for TS work; it dispatches to specialists when concerns cross domains.

Limits: project-tier promotion still pending. The inline comment in the agent definition notes that project promotion is a follow-up bead; once vetted, the agent moves to project tier and gets wired into `/pr-intel` and `/consult` dispatch directly. Until then, it fires only when explicitly invoked.

---

```yaml
---
component: test-quality-reviewer
type: agent
status: active
trigger_signals:
  - "tests were just written or modified (proactive invocation)"
  - "explicit 'review tests for X' request"
  - "pre-commit gate before test files land"
prevents:
  - "tests that pass on framework mechanics instead of project behavior"
  - "mock-saturated tests where mocks outnumber real assertions"
  - "tests with names that promise behavior but assert wiring"
  - "missing negative paths and error-case coverage"
related: [test-forge (uses this agent in its feedback loop), code-reviewer]
---
```

When I reach for it: any time tests are written or modified. The harness's discipline is that tests are the specification; a test suite that does not specify what the code should do produces code that does whatever passes the tests. The reviewer catches the failure mode early.

What it prevents: a class of test that satisfies the test runner without verifying behavior. Pydantic serialization tests that assert nothing the project cares about. Mock-saturated tests where the test verifies how the code happens to call its dependencies (refactor-fragile). Tests named "test_invalid_email_raises_validation_error" that assert a mock call count.

How it compounds: feeds into test-forge as the quality gate (test-generator writes tests, test-quality-reviewer evaluates them, the loop iterates). Pairs with code-reviewer when test review surfaces a production-code design issue.

Limits: severity triage is subjective. A blocker on one project might be advisory on another, depending on the cost of the failure the test was meant to catch. The agent's calibration is currently project-specific; cross-project ports would require recalibration.

---

Calibration files (`calibration/*.md`) deserve their own commentary; they are the reflection-trigger mechanism applied to specialist agent calls. When an agent's calls drift from the author's preferred quality, the calibration file is updated with examples; the agent's prompt then references the calibration. Periodic review (the `/calibrate` skill) prevents drift accumulation.

```yaml
---
component: module-cohesion-reviewer
type: agent
status: active
trigger_signals:
  - "/pr-intel or /review fan-out where the diff touches a Python module"
  - "a PR whose description says pure move, rename, or no behavior change"
  - "a new helper landing in a module whose name does not name it"
prevents:
  - "a hand-rolled query landing next to the typed accessor that already expresses it"
  - "a behavior change smuggled into a diff described as a pure move"
  - "catch-all modules and test-only helpers accreting inside the production import graph"
related: [code-reviewer, mx2-pydantic-reviewer, test-quality-reviewer, blast-radius-reviewer]
---
```

When I reach for it: as a fan-out target whenever a diff touches Python modules, or directly when the question is one level up from the line. Not "is this function correct?" but "does this module own one nameable concern, and is it coupled to the rest of the codebase the way it should be?" This is the personal variant shadowing a project-tier agent of the same name; the delta is that its seam defers to the personal specialist roster by name, so it stays quiet inside a fan-out where those siblings are already running.

What it prevents: the defect class that single-file tooling structurally cannot see. A filename is not a defect any linter checks, and semantic duplication across files is beyond token-similarity rule sets. Its two named headline catches are a hand-rolled implementation duplicating an existing typed accessor (reusing the accessor removes both the duplicate and the untyped surface at once) and behavior smuggled into a "pure move": a dropped memoization, a key-presence check turned into `is not None`, a swapped default, in a diff whose description promised no behavior change.

The seam is the design: the agent definition spends more words on what is NOT its lane than on its question bank. Within-file structure goes to the code reviewer, Settings to the Pydantic reviewer, PII to the security auditor, error propagation to the silent-failure hunter, consumer blast radius to blast-radius-reviewer, and test files in their entirety to test-quality-reviewer (it is told not to open one, even when a test file is in the diff). Restating a sibling's finding is the failure it is tuned against, because pile-on is what erodes trust in a multi-agent report.

Advisory by construction: every finding is a question the author answers, never a verdict, and the agent is required to answer by reading or grepping anything it could verify itself before asking. It is also told to say so in one line and stop when a module is clean, rather than manufacturing questions to fill a report.

Limits: it is a Sonnet agent on a judgment-heavy lens, and the judgment it needs ("is this divergence deliberate?") depends on author intent it cannot observe. The pre-existing carve-out is a real coverage hole with a defensible reason behind it: a catch-all module the diff merely touched stays unflagged, so the worst cohesion debt in a file is invisible to the review of the change that walks right past it. And the interrogative framing cuts both ways; a genuinely wrong coupling arrives as a polite question that an author can close with "yes, intended" and no further pressure.

---

```yaml
---
component: human-lens-reviewer
type: agent
status: active
trigger_signals:
  - "an artifact is about to be handed to a person: a chat post, a page, a changelog section, a decision record, a README, a meeting brief"
  - "a review verdict or a findings report is about to go back to a human author"
  - "an agent-consumed artifact whose ambiguity could make two agents act differently"
prevents:
  - "a reader forming a different takeaway than the author intended"
  - "session-internal vocabulary (finding ids, round names, scratch paths) reaching someone who cannot resolve it"
  - "a reader approving or rejecting for the wrong reason because the page gave them a partial picture"
related: [skeptic, prompt-refiner, provenance-classifier]
---
```

When I reach for it: last, on the way out. Every other reviewer in this directory asks whether the work is right; this one asks whether the person receiving it can tell. That makes it the only reviewer whose client is not the author and not the codebase but the named reader, and it is why its dispatch is worthless without three inputs the caller usually leaves implicit: who the reader is, what they already know, and what they must do with the artifact. A dispatch that omits the reader gets a review against an inferred one, stated as inferred, because a caller that is an agent cannot answer a clarifying question and a review that refuses to run is a review that never happens.

What it prevents: two failure modes named together by the harness owner, and they are not the same defect. The first is convolution, where the reader cannot get the point in one pass: sentence nesting, undefined acronyms, an ask buried mid-paragraph, identifiers that meant something inside the session that produced them and nothing outside it. The second, and the more dangerous, is the under-contexted artifact, where the reader gets the point cleanly and still cannot judge it, because what is decided, what is a lean and what is open have been blended into one confident voice. A confused reader asks a question; a misinformed one acts.

How it compounds: it is the judgment half of a pair whose measurement half already existed. The brevity rule and its check script count words, bullets, questions and banned characters against a per-surface budget, which catches a draft that is too long but says nothing about a draft that is short and unreadable. The copy-discipline memory carries the rules about what a reader's copy may not contain. This agent reads those two rather than restating their numbers, so the budgets stay in one place, and then does the thing neither can: forms the takeaway a reader would actually form and compares it with the one the author meant.

Limits, and they are real. It is a Sonnet agent on a judgment-heavy lens, deliberately, because a reviewer that runs on every outbound artifact has to be cheap enough to actually run; the weaker tier is the point and also the exposure. It infers a reader's prior knowledge from a role, which is a guess about a person, and that guess is why its output is required to carry a never-empty could-not-determine section. It does not fact-check, so a fluent, well-shaped, wrong artifact passes it clean. And its minimal-rewrite discipline is easy to state and hard to hold: the failure mode to watch for in its output is a rewritten paragraph offered as a demonstration, which takes the pen out of the author's hand and is exactly what an advisory reviewer must not do.
