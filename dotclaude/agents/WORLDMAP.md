---
component: dotclaude/agents
type: directory-map
status: V0 complete (22 agents covered by 20 entries; one combined entry for the launch-flex/implementer/tester trio)
authored_by: Claude Opus 4.7
---

# WORLDMAP: Personal Agents

AI-authored commentary on each personal-tier agent in `~/.claude/agents/`. When I reach for the agent, what failure mode it prevents, how it compounds, and where it has limits. Entries follow the format documented in the top-level `WORLDMAP.md`.

The agents divide into three rough classes: thinking-partner agents (tech-lead, decision-maker, tenth-man) that operate at the framing layer; structural reviewers (code-reviewer, executor, prompt-refiner, the launch-* trio) that do code-shaped work; and specialist linters (Pydantic, TypeScript, Python style, security, silent-failure, devops, git history, observability, test quality, bot-review, pr-precedent) that fire on narrow concerns. The boundaries between classes are not absolute; bot-review and pr-precedent in particular live between "linter" and "memory mechanism." The voice of each entry tries to name what makes that agent earn its keep, not just what it does.

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

```yaml
---
component: mx2-pydantic-reviewer
type: agent
status: active
trigger_signals:
  - "PR creates or modifies a Pydantic Settings class"
  - "PR converts os.environ / os.getenv calls to typed configuration"
  - "configuration audit on a service before deploy"
prevents:
  - "configuration that bypasses Settings and reads env vars directly"
  - "Settings classes growing service factory methods (violating the dumb-container rule)"
  - "instance-import patterns that break test override of configuration"
related: [code-reviewer, security-auditor]
---
```

When I reach for it: a diff touches Settings classes or config code. The signals are sharp (Settings imports, `os.environ` calls, `AppSettings` class declarations), so dispatch is mechanical.

What it prevents: configuration drift away from the project's Pydantic Settings convention. Direct env var access bypasses the type system and the singleton accessor pattern; methods on Settings classes turn config containers into service factories. Both compound over time as other code copies the pattern.

How it compounds: pairs with code-reviewer (general type safety) and security-auditor (secrets in Settings). Three lenses cover what one would miss.

Limits: scope is narrow by design. Will not flag generic typing issues, missing audit logs, or auth gaps; those route to other agents. The narrowness is the strength; over-broad reviewers produce diluted findings.

---

```yaml
---
component: mx2-python-style
type: agent
status: active
trigger_signals:
  - "Python code review (mine or others') against MX2 style"
  - "pre-CI self-check on a Python diff"
  - "explicit invocation when CI flagged style failures"
prevents:
  - "CI failures on style issues that could have been caught locally"
  - "drift from Google + MX2 conventions (indent width, line length, modern type syntax)"
  - "deferred imports, f-string log calls, typing.Any usage"
related: [code-reviewer, pydantic-reviewer]
---
```

When I reach for it: Python file review work, especially pre-push. The agent is fast (Sonnet, narrow scope) and catches the class of issues CI would otherwise reject. Pre-push invocation saves a CI round-trip.

What it prevents: style and lint failures landing in CI, which costs at least one round-trip (CI run, fix, push, CI again). Every avoided round-trip pays for the agent invocation many times over.

How it compounds: chained with code-reviewer for full-spectrum review. The style agent fires on narrow concerns; the code-reviewer fires on structural concerns. Together they cover both axes.

Limits: enforces existing rules, does not propose new ones. When project rules update, the agent needs the new rules loaded before it can flag drift. The reflection-trigger discipline handles the rules-update path.

---

```yaml
---
component: mx2-security-auditor
type: agent
status: active
trigger_signals:
  - "diff touches PII/PHI handling (Pydantic models, log calls, LLM data flows)"
  - "audit trail field completeness review on a service"
  - "change to document access, matter-scoped queries, or authentication context"
prevents:
  - "secrets and PII leaking through logs, error messages, or LLM prompts"
  - "audit trails missing required HIPAA / legal-compliance fields"
  - "matter-scoped access controls violated by a new query path"
related: [silent-failure-hunter, code-reviewer]
---
```

When I reach for it: any change in the document-handling pipeline or auth context. Legal-domain code carries a higher security bar than general application code; attorney-client privilege and chain-of-custody requirements turn ordinary data leaks into legal-grade compliance events.

What it prevents: a class of failure where PII or document content ends up somewhere it shouldn't (log file, exception message, LLM prompt context, error response payload). Each leak surface has different mitigations; the agent walks all of them.

Strict carve-out: does NOT detect missing audit log CALLS (that is silent-failure-hunter's job); does NOT review JWT or RBAC structure (that is code-reviewer's job). The narrowness avoids overlap with other specialists.

How it compounds: pairs with silent-failure-hunter (finds where audit logging should happen but doesn't) and code-reviewer (evaluates auth structures). The three together cover the security stack.

Limits: cannot evaluate runtime data flows without sample data. Static review catches "this field type allows PII to be logged" but not "in production, this field always contains PII." For dynamic concerns, production-side investigation is required.

---

```yaml
---
component: mx2-silent-failure-hunter
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
component: mx2-devops-build-deploy
type: agent
status: active
trigger_signals:
  - "pants build failures (lockfile, BUILD file, target resolution)"
  - "Terraform / Terragrunt issues (provisioning, state, drift)"
  - "Lambda / ECR / ECS deployment failures or CI/CD workflow debugging"
  - "AWS security config review (IAM, S3, KMS, API Gateway)"
prevents:
  - "build/deploy diagnosis without MX2-specific convention knowledge"
  - "CI/CD debugging that requires repeated reproduction in the wrong environment"
  - "AWS security misconfigurations that pass technical review but violate MX2 conventions"
related: [code-reviewer, security-auditor]
---
```

When I reach for it: anything in the build, deploy, or infra layer. The agent carries the MX2-specific conventions that aren't in any public docs (pants gotchas, the Terragrunt structure, the IAM patterns for legal-data services). General DevOps knowledge does not get you to the MX2 fix; the agent is the bridge.

What it prevents: long debugging cycles that come from applying generic build/infra fixes to MX2-specific patterns. Pants is not just pip; Terragrunt is not just Terraform. The MX2 conventions exist because they encode legal-data security and audit requirements; bypassing them silently breaks compliance.

How it compounds: with security-auditor when the AWS config review touches data-at-rest or in-flight protection. With code-reviewer when the build issue traces back to a Python module structure problem.

Limits: this agent has Edit and Write tools (unusual for a Sonnet specialist) because devops work often requires modifying Terraform or BUILD files inline. The author chose to trust the agent here; the tradeoff is that the agent can do more damage if miscalibrated. Worth watching the change pattern.

---

```yaml
---
component: mx2-git-historian
type: agent
status: active
trigger_signals:
  - "/pr-intel on an M+ PR touching files with recent history"
  - "PR changes lines that were last modified within 60-90 days"
  - "explicit invocation when 'is this a regression?' is the question"
prevents:
  - "regressing a recently-shipped bug fix without noticing"
  - "missing the flip-flop pattern (lines rewritten 3+ times in 60 days)"
related: [pr-precedent, code-reviewer]
---
```

When I reach for it: PR review on files with active churn. The signals are narrow by design (lines authored within 90 days in bug-fix commits, or lines rewritten 3+ times in 60 days). Generic "this file changed recently" findings would overlap with code-reviewer's structural review and produce noise; the historian's narrowness is the load-bearing constraint.

What it prevents: a specific failure where a fix lands, gets superseded by an unrelated change, and the regression goes unnoticed because the reviewer of the unrelated change had no reason to look at the prior fix's commit message. The historian carries the prior commit's context forward into the current review.

How it compounds: with pr-precedent (which surfaces inline review comments from prior PRs in the same area). The historian looks at commit history; pr-precedent looks at review-comment history. Two different memory mechanisms cover related failure modes.

Limits: false positives are possible on files with naturally high churn (config files, test scaffolding). The narrow trigger condition reduces this but does not eliminate it. The reviewer's job is to discard noise; the historian's job is to surface candidates.

---

```yaml
---
component: mx2-typescript-reviewer
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
component: provenance-classifier
type: agent
status: active
trigger_signals:
  - "/pr-intel synthesis step 5d batch dispatch with the full findings list"
  - "any finding's verification path needs the speed-amplified vs bot-surfaced split classified"
prevents:
  - "misclassifying bot-surfaced findings as speed-amplified when their verification path needed live state, multi-page synthesis, or cross-file blast radius the reviewer could not have sustained at speed"
  - "the classifier-vs-voice decoupling failure that emerged on three PRs where SonarCloud-sourced findings were uniformly misclassified despite the comment text opening with explicit Sonar attribution"
related: [pr-intel, post-review, bot-review]
---
```

When I reach for it: never directly; the classifier is invoked in batch by `/pr-intel` synthesis (step 5d) with the full findings list, and returns one classification per finding plus a one-sentence rationale. The synthesizer wires the classification into the finding briefing, the audit line in the Review Recommendation header, and the audit field counts written to bd memory by `/post-review`.

What it prevents: speed-amplified vs bot-surfaced is the wrong split to make from the comment text. The verification path is the load-bearing signal: if the path required querying production state, cross-referencing N source files, or reading a long external doc, no human reviewer would have sustained the work at PR-review speed, regardless of how the comment reads. Decoupling the classifier from the voice/rendering layer makes the audit signal a property of the work, not the prose.

How it compounds: with `pr-intel` (the upstream skill that produces the findings) and `post-review` (the downstream skill that posts and records the audit counts). The agent is a narrow stage in the pipeline; the harness is shaped to make narrow stages composable.

Limits: classification quality is bounded by the finding's metadata. If the synthesizer hands the classifier a finding without verification-path evidence, the agent has to infer from the rendered comment text, which is exactly the failure mode the agent exists to prevent. Synthesizer discipline (passing the full verification context, not just the comment) is the upstream guard.
