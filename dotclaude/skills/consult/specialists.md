# Specialist Roster

These agents are available via the Agent tool. Each has its own agent definition with
detailed instructions; do NOT replicate their knowledge. Give them clear input and a
focused ask.

**Domain context**: Specialists can search `bd memories <keyword>` for gotchas, API config,
and patterns relevant to their analysis. Include this in specialist prompts when the domain
has known pitfalls (e.g., `bd memories botocore` for exception handling, `bd memories datadog`
for service names).

| Agent (subagent_type) | Domain | Model |
|---|---|---|
| `mx2-python-style` | Style enforcement, type annotation syntax, logging conventions | sonnet |
| `mx2-pydantic-reviewer` | Settings classes, env var management, field typing | sonnet |
| `mx2-security-auditor` | PII/PHI, auth, audit trails, encryption, compliance | sonnet |
| `mx2-code-reviewer` | Holistic review, SOLID, structural design, naming, code smells, triage (Python-scoped) | sonnet |
| `mx2-typescript-reviewer` | TS code review: type safety, React/Next.js patterns, frontend concerns, TS error handling. Sibling to mx2-code-reviewer for TS files | sonnet |
| `mx2-silent-failure-hunter` | Silent failures, error propagation, boundary errors (TS/Python) | sonnet |
| `mx2-git-historian` | Regression-of-recent-fix detection, flip-flop pattern, behavioral attribution to prior PRs | sonnet |
| `mx2-pr-precedent` | Survival filter on prior PR review comments (drops nitpicks, self-precedent, resolved threads) | sonnet |
| `mx2-devops-build-deploy` | Build failures, deployment, infra, incidents | sonnet |
| `observability-reviewer` | Datadog/CloudWatch instrumentation gaps, exception-class ET fingerprint risk, tag cardinality, ddtrace/OTel trace propagation across SNS/SQS/EventBridge | sonnet |
| `test-quality-reviewer` | Test meaningfulness, mock discipline, assertion quality | sonnet |
| `prompt-refiner` | Prompt preprocessing (headless mode only from consult) | sonnet |

## Dispatch Heuristics

- **Code change review**: `mx2-code-reviewer` (holistic triage, Python-scoped), plus any specialists
  it would route to based on what's in the diff
- **TypeScript code review**: `mx2-typescript-reviewer` when changed files include
  `src/typescript/**` or `*.ts`/`*.tsx`/`*.mts`/`*.cts` paths (excluding `src/gen-typescript/`).
  Sibling specialist to `mx2-code-reviewer`; do not dispatch both for the same file
- **New feature design**: `mx2-code-reviewer` (structure + standards), `mx2-security-auditor`
  (if it touches documents/PII), `mx2-python-style` (if generating code)
- **Test assessment**: `test-quality-reviewer`
- **Configuration change**: `mx2-pydantic-reviewer`, `mx2-security-auditor` (if secrets)
- **Ambiguous or terse input**: `prompt-refiner` (headless) to expand context before
  dispatching to other specialists
- **Cross-cutting judgment call**: Read the code yourself, synthesize without spawning
  subagents if the question is about trade-offs rather than domain analysis
- **Pipeline reuse audit**: When a plan introduces new code paths, ask every specialist:
  "Does the existing pipeline already provide this behavior?" This is a cross-cutting
  concern, not a single-specialist domain. The question applies to code structure
  (mx2-code-reviewer), error handling (mx2-silent-failure-hunter), and infrastructure
  (mx2-devops-build-deploy). Include it in specialist prompts when the plan builds
  a new path parallel to an existing pipeline.
- **Plan document (not code/diff)**: Within your domain, probe for: Pipeline Bypass
  ("does this add a new code path when the existing pipeline could serve?"), Reasoning
  Chain gaps ("do the steps actually follow from each other?"), and Scope/Completeness
  ("what production concerns - rollback, observability, migration - does this plan omit?")
- **Reviewer feedback iteration**: Do NOT dispatch to `mx2-tech-lead`. Use
  `mx2-code-reviewer` for structural evaluation, or handle directly. If relaying
  reviewer feedback, inject the Feedback Reception preamble (see CLAUDE.md dispatch #6)
- **Historical regression check**: dispatch `mx2-git-historian` when the diff modifies
  a file with 2+ merged PRs in the last 90 days AND the diff alters existing behavior
  (not pure additions). Skip when the file's `git log` shows < 2 commits in 180 days.
- **Pattern divergence check**: dispatch `mx2-pr-precedent` when the PR introduces a
  new abstraction (class, enum, factory, decorator) in a directory that already
  contains 2+ similar abstractions, OR when the file list overlaps with 3+ recent
  merged PRs in the last 180 days. Skip if all candidate prior PRs are by the same
  author as the current PR (self-precedent is meaningless).
- **Observability instrumentation review**: dispatch `observability-reviewer` when
  any of the following hold: (a) diff renames/removes a class inheriting from
  `Exception|Error|MX2Error|ApplicationError` (Datadog ET fingerprint risk via
  `@error.type:` monitor filters); (b) diff adds `add_metric|put_metric_data|
  MetricsCollector|MetricsContext|DatadogProvider|DogStatsDProvider` near a
  `raise|except|return None|return \[\]|return \{\}` in the same hunk (logs vs
  metrics gap); (c) diff modifies `*.tf` files matching `aws_cloudwatch_metric_alarm|
  datadog_monitor|datadog_dashboard` AND code files in the same PR (cross-stack
  consistency); (d) diff adds a value to a class inheriting from `StrEnum|Enum|
  Literal\[` (potential dashboard breakdown gap, QUESTION-tier). Different from
  `mx2-silent-failure-hunter` (logs/audit/error propagation) and
  `mx2-devops-build-deploy` (Terraform correctness).
- **NOT to dispatch (both git-historian and pr-precedent)**: XS PRs, test-only PRs,
  generated-code-only PRs, and rebase-artifact PRs. These specialists' value depends
  on substantive cross-PR or temporal context that does not exist for those classes.
