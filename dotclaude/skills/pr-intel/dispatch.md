# Specialist Dispatch

## Dispatch Triggers

When pre-loaded context is available, triggers are pre-evaluated in
`<pr-context section="dispatch-signals">`. Use the boolean signals directly:

| Signal | Triggers |
|--------|----------|
| `has_try_except_raise: true` OR `structural_risk_size: true` | Structural risks |
| `has_security_patterns: true` OR `security_files` non-empty | Security & compliance |
| `has_test_files: true` | Test quality |
| `has_terraform_files: true` | Infrastructure review |
| `has_typescript_files: true` | TypeScript review |
| `structural_risk_size: true` AND `has_file_history: true` | Git history regression |
| `structural_risk_size: true` AND `has_pattern_precedent: true` | Prior PR precedent |
| `has_observability_signal: true` | Observability instrumentation review |
| `changes_public_surface: true` OR `has_pattern_precedent: true` | Cross-file blast-radius |
| `structural_risk_size: true` | Adversarial dissent |
| `has_pydantic_settings_signal: true` | Pydantic Settings review |

The descriptions below document what each trigger checks (for reference and
fallback mode). When dispatch-signals are available, use the booleans above.

**Structural risks** → `mx2-code-reviewer` + `mx2-silent-failure-hunter`
Trigger: diff > 200 lines OR > 5 files changed OR diff contains `try`/`except`/`raise`

**Security & compliance** → `mx2-security-auditor`
Trigger: changed files match `auth|security|token|jwt|permission|rbac|document|upload|
download|access|audit|secret|credential|patient` OR diff contains `SecretStr|logger\.|
\.info\(|\.error\(|\.exception\(`

**Test quality** → `test-quality-reviewer`
Trigger: PR includes files matching `*_test.py|test_*|conftest.py`

**Infrastructure review** → `mx2-devops-build-deploy`
Trigger: changed files match `*.tf|*.hcl|terragrunt.hcl` OR paths contain `infra/|module/`

**TypeScript review** → `mx2-typescript-reviewer`
Trigger: `has_typescript_files: true` (changed files include `*.ts|*.tsx|*.mts|*.cts` outside `src/gen-typescript/`)
Filter: scope diff to TS files only when prompting; the agent does not need Python diff.
Coordination: when both `mx2-code-reviewer` and `mx2-typescript-reviewer` would fire, send each only its language-relevant files; do not dispatch both on the same file.

**Git history regression** → `mx2-git-historian`
Trigger: `structural_risk_size: true` AND `has_file_history: true` (M+ PRs touching files with 3+ prior PRs in 180 days)
Filter: line ranges of changed files only. The agent runs git log/blame/show against the worktree.

**Prior PR precedent** → `mx2-pr-precedent`
Trigger: `structural_risk_size: true` AND `has_pattern_precedent: true` (M+ PRs introducing new public symbols in directories with 2+ recent prior PRs)
Filter: file path list only. The agent queries `gh` API server-side; no diff content is needed in the prompt.

**Cross-file blast-radius** → `bot-review`
Trigger: `changes_public_surface: true` OR `has_pattern_precedent: true`. The agent identifies consumers of changed public symbols and articulates the invariant each consumer assumes that the change weakens. Advisory only (severities limited to COMMENT/NOTE/SUGGESTION; never BLOCKING/CRITICAL). Filter: changed public-symbol declarations only + full file path list (the agent fetches consumers itself via Grep/Read on the worktree). Different from `mx2-pr-precedent` (prior-PR comments on same files), `mx2-code-reviewer` (line-level structural), and `mx2-silent-failure-hunter` (error propagation boundaries).

**Observability instrumentation review** → `observability-reviewer`
Trigger: `has_observability_signal: true`. The signal is true when ANY of the following hold:
- Diff renames or removes a class inheriting from `Exception|Error|MX2Error|ApplicationError` (Datadog ET fingerprint risk: monitors at `infra/module/datadog_api_monitors/monitors.tf` filter on `@error.type:`)
- Diff contains `add_metric|put_metric_data|MetricsCollector|MetricsContext|DatadogProvider|DogStatsDProvider` AND a `raise|except|return None|return \[\]|return \{\}` in the same hunk (potential logs-without-metrics gap)
- Diff modifies `*.tf` files matching `aws_cloudwatch_metric_alarm|datadog_monitor|datadog_dashboard` AND non-test code files in the same PR (cross-stack consistency)
- Diff adds a new value to a class inheriting from `StrEnum|Enum|Literal\[` (potential dashboard breakdown gap, QUESTION-tier)

The four sub-rules are disjunctive. A single broad regex over-triggers (every new enum/exception dispatches) AND under-triggers (removing a `log.error` line that an alert depends on stays invisible). Conjunctive sub-rules narrow correctly.

**Pydantic Settings review** → `mx2-pydantic-reviewer`
Trigger: `has_pydantic_settings_signal: true`. The signal is true when ANY of the following hold:
- Diff adds or modifies a class inheriting from `BaseSettings`, `pydantic_settings.BaseSettings`, or `Singleton`
- Diff contains `os.environ.get`, `os.environ\[`, or `os.getenv\(` on changed lines (often a candidate for migration to Settings)
- Diff adds or modifies a field on a class whose filename matches `*app_settings*`, `*settings*`, or `*config*` AND the class body contains `model_config` or `SettingsConfigDict`

Focuses on configuration-management patterns: required fields with empty-string defaults (silent misbehavior), cross-service `AppSettings` imports (architecture violation per `architecture.md`), missing `__table_name__()` cross-service patterns, and `os.environ` usage that should be a Settings field. Different from `mx2-code-reviewer` (general structural review) and `mx2-security-auditor` (secrets handling).

**Adversarial dissent** → `mx2-tenth-man`
Trigger: `structural_risk_size: true` (M+ PR: > 200 lines OR > 5 files). Surfaces naive-but-unasked questions about scope, assumptions, and risk that other specialists miss because they are focused on their own domain. Advisory only; severity vocabulary limited to QUESTION (never BLOCKING/CRITICAL/COMMENT). Findings appear in their own subsection of the synthesis report under "Open questions", not folded into the main severity buckets. Designed as a safety net for fragmented attention (multi-window operational reality).

Different from `bot-review` (cross-file consumer-invariant articulation; both are advisory but tenth-man asks "what did you not consider" while bot-review asks "what does X consumer assume that breaks"). Different from `mx2-code-reviewer` (structural verdicts) and `mx2-silent-failure-hunter` (error-propagation verdicts) which produce judgments rather than questions.

**Inline IaC analysis** → `checkov` (tool call, not subagent)
Trigger: `has_terraform: true` AND at least one net-new `*.tf` file exists.
Fires on ALL sizes (including XS), unlike specialist dispatch. It's a bounded tool
call (5-10s per file), so the cost-vs-signal ratio works even on small PRs.
Runs alongside the specialist agents (same parallel batch). See [checkov.md](checkov.md)
for invocation, suppression list, severity mapping, and integration into synthesis.
Findings flow through pr-intel's standard FINDING format and severity triage.
Skip on rebase-artifact PRs (all tf files are stale per Merge Base Freshness).

**NOT to dispatch** (specialist agents above, NOT checkov): XS/S PRs, test-only PRs, generated-code-only PRs, and rebase-artifact PRs (where Merge Base Freshness shows the diff is entirely stale content).

## Context Optimization

Do NOT send the full diff to every specialist. Filter by relevance:
- **All specialists**: exclude files flagged `already_on_main` by Merge Base Freshness
- **Security auditor**: only auth/PII/audit/document files + PR description
- **Test reviewer**: only test files + the source files they test
- **mx2-code-reviewer**: only implementation files (non-test, non-config)
- **mx2-silent-failure-hunter**: only files containing try/except/raise patterns
- **mx2-devops-build-deploy**: only Terraform/HCL/terragrunt files + infra directory changes
- **mx2-git-historian**: line ranges of changed files only (the agent runs git log/blame for context)
- **mx2-pr-precedent**: file path list only (the agent queries gh API server-side; no diff content needed)
- **observability-reviewer**: only files matching the observability sub-rules above (exception-class diffs, metric-emission hunks, observability `*.tf` files, enum/Literal additions) PLUS any sibling `*.tf` in the same service directory PLUS the PR description (for alert references)
- **bot-review**: changed public-symbol declarations only (lines matching the `changes_public_surface` regex from `SKILL.md` Dispatch Signals) PLUS the full file path list. Mirrors `mx2-pr-precedent`'s "file path list only" filter shape, NOT the full diff. The agent fetches consumers itself via Grep/Read on the worktree; sending the full diff saturates context on the M+ PRs the agent is most useful for.
- **mx2-tenth-man**: PR description + file path list + summarized diff overview (first 50 lines of each file's diff). The agent asks questions about intent and assumptions; it does not need exhaustive code context. Sending the full diff saturates without improving question quality. Include the Jira ticket AC if available.
- **mx2-pydantic-reviewer**: only files matching the pydantic_settings sub-rules above (Settings class diffs, os.environ patterns, *settings* / *config* filename diffs) PLUS sibling settings files in the same service directory (to detect duplicate field declarations or cross-service `AppSettings` import attempts).

## Specialist Prompt Preamble

Every specialist prompt begins with:

```
REPO STATE: The PR's HEAD commit (<headRefOid short>) is checked out in a temporary
worktree at <WORKTREE_DIR>. Use this path as the root for all Read, Grep, and Glob
operations. Git read commands (log, blame, show, diff) are encouraged via
`git -C "$WORKTREE_DIR" ...`. Do NOT run git checkout, reset, rebase, commit, or
any state-modifying command.

SCOPE: The diff below shows what changed in PR #<number>. Use it to identify what to review.

STATIC ANALYSIS CONTEXT: This repo runs CI checks (pylint, mypy, flake8, bandit, yapf,
isort, autoflake, SonarCloud, Datadog SAST/SCA/Secrets, GitHub Copilot). Focus on
design judgment that automated tools cannot catch. Do not flag style, formatting, or
type issues unless they indicate a deeper design problem or CI has not yet passed.

VERIFICATION: You have read access to the full codebase at the PR's HEAD commit via
Grep, Glob, and Read tools. Use <WORKTREE_DIR> as the path root (not /workspaces/main).
For every finding, verify your claim against the actual codebase before reporting it:
- Before claiming "X is untested" -> grep <WORKTREE_DIR>/tests/ for the function name
- Before claiming "X doesn't handle Y" -> read the full function, not just the diff hunk
- Before claiming "callers expect Y" -> grep for call sites
Do not fabricate cross-references from your own knowledge.

EVIDENCE CATEGORIES (use one per finding):
- VERIFIED: You confirmed by reading/searching the codebase at the PR commit. State what you checked.
- DIFF-VISIBLE: Apparent from the diff but wider context could change the picture.
- QUESTION: Plausible concern you couldn't confirm. Frame as a question.

TONE: Frame findings as observations, not verdicts. Use "this appears to" or "this may"
for DIFF-VISIBLE findings. Use "confirmed that" only for VERIFIED findings where you
read the code. QUESTION findings are already interrogative. Do not use absolute language
("this is wrong", "this will break") unless you have VERIFIED evidence of a concrete bug.
```

When Jira ticket context is available, append this to the preamble:

```
TICKET CONTEXT: This PR implements <ticket key> (<ticket summary>).

Acceptance Criteria from the ticket:
<ticket AC, verbatim from Jira>

When evaluating the code, check whether it satisfies these criteria. If you notice
the implementation diverges from a criterion (handles a broader or narrower scope,
skips a condition the AC specifies, or implements different behavior), flag it as a
finding with evidence category VERIFIED and note the specific deviation. Deviations
are not automatically bugs - they may be intentional - but they should be surfaced.
```

## Specialist-Specific Prompts

### mx2-code-reviewer
```
<scope preamble>

Review implementation files from PR #<number> for structural risks:
SOLID violations, naming, error handling patterns, code smells.
Return findings in structured FINDING format with evidence categories.
Use Grep/Read to verify structural claims against the full file, not just
the diff hunk. Focus on production impact and maintenance risk.

PR context: <body>

Files changed (diff):
<filtered implementation diff>
```

### mx2-silent-failure-hunter
```
<scope preamble>

Review error handling in PR #<number>. For each silent failure or overly
broad catch block, return structured FINDING format with evidence categories.
Use Grep to check call sites before claiming error propagation issues.
Use Read to see the full function context, not just the diff hunk.
If the PR touches both Python and TypeScript files, check the boundary
error handling between them.

Files changed (diff):
<files containing try/except/raise>
```

### mx2-security-auditor
```
<scope preamble>

Audit PR #<number> for security and compliance. Legal document processing
platform: PII, audit trails, and document access controls are critical.
Return structured FINDING format with evidence categories.
Use Grep to verify whether audit logging exists before claiming it is missing.
If clean, provide positive confirmation of what was reviewed.

PR context: <body>

Files changed (diff):
<filtered auth/PII/audit files>
```

### test-quality-reviewer
```
<scope preamble>

Assess test quality in PR #<number>. Do tests verify domain behavior or
just exercise framework mechanics? Return structured FINDING format with
evidence categories. Use Grep/Read to examine the source files under test
in the codebase, not just the diff excerpt.

Source files under test (diff):
<filtered source diff>

Test files (diff):
<filtered test diff>
```

### mx2-devops-build-deploy
```
<scope preamble>

Review infrastructure changes in PR #<number> for Terraform/HCL correctness.
Check for: missing variable pass-through to child modules, duplicate HCL keys
(silently keeps last value), missing environment configs (CD but no beta/prod),
EventBridge subscription completeness, and terragrunt dependency injection gaps.
Return structured FINDING format with evidence categories. Use Read to examine
child module variables.tf when checking pass-through. Use Glob to verify
environment config completeness across infra/{service}/ directories.

Files changed (diff):
<filtered terraform/hcl/terragrunt diff>
```

### mx2-git-historian
```
<scope preamble>

For changed lines in PR #<number>, detect:
1. Regression-of-recent-fix: lines authored within 90 days in commits referencing
   Jira bug tickets (MX2-NNNN with type=Bug) or containing [bug]/[fix]/regression/hotfix
2. Flip-flop pattern: line ranges rewritten 3+ times in the last 60 days

Apply the hard false-positive filters from your agent definition. Do NOT detect
silent reverts (Ghost Diffs check in /pr-intel/SKILL.md owns that). Do NOT report
generic "recent author" findings without a behavioral concern.

Cite introducing commit SHA, PR #, author, date, and a verbatim excerpt of the
commit message body for every finding.

Files changed (line ranges):
<changed file paths and line ranges>
```

### mx2-pr-precedent
```
<scope preamble>

For each modified file in PR #<number>, query gh for the 3 most recent merged PRs
that touched the file (last 180 days). For each, fetch inline review comments and
apply the survival filter from your agent definition:
- Drop self-precedent (same author as current PR)
- Drop comments < 50 chars (LGTM, emojis, nits)
- Drop if shared filename only (require shared symbol references)
- Drop if the same concern already appears in current PR's bot comments (provided below)
- Drop if pattern not present in current diff (verify via Read)

Surface only survivors. Cite source PR, comment URL, reviewer, and a verbatim
excerpt for every finding.

Current PR bot comments (for dedup):
<list of bot comments from current PR's inline review comments>

Files modified:
<file path list>
```

### observability-reviewer
```
<scope preamble>

Review observability instrumentation in PR #<number>. Detect: exception class
renames/removals affecting Datadog Error Tracking monitors keyed on @error.type
(grep infra/**/*.tf to verify); error/skip paths in instrumented services that
emit logs but no metrics (provider detection: MetricsCollector for CloudWatch,
DatadogProvider/DogStatsDProvider for Datadog); metric tag/dimension cardinality
risk on high-volume metrics; ddtrace/OTel context propagation gaps across
SNS/SQS/EventBridge boundaries; new Lambda/ECS without CloudWatch log retention.
Demote to QUESTION-tier any finding requiring Datadog/CloudWatch UI access
(dashboard breakdowns, alert applicability, log-filter impact).

Return findings in structured FINDING format with evidence categories. Use Grep
to verify exception-class references against infra/ Terraform; use Read to
confirm trace propagation calls at queue boundaries. Do NOT flag log-only
silent failures (route to mx2-silent-failure-hunter); do NOT review Terraform
correctness (route to mx2-devops-build-deploy).

PR context: <body>

Files changed (filtered to observability triggers + sibling *.tf):
<filtered diff>
```

### bot-review
```
<scope preamble>

Review cross-file blast-radius in PR #<number>. For each changed public symbol in the
filtered diff below, identify consumers via Grep on <code_root>, Read each consumer's
call site, and articulate the invariant the consumer assumes that the change weakens.
Apply the verbatim three-citation gate from your agent definition: every finding cites
(a) changed-symbol line, (b) consumer line, (c) invariant articulation. Drop findings
missing any of the three.

Severity vocabulary is hard-constrained to COMMENT/NOTE/SUGGESTION; do NOT emit
BLOCKING or CRITICAL. Filter "consumer references this" noise; only surface "consumer
assumes X that this change weakens." Do NOT flag line-level structural concerns (route
to mx2-code-reviewer), prior-PR comment recurrences (route to mx2-pr-precedent), or
silent-error-propagation (route to mx2-silent-failure-hunter).

Use FINDING format from your agent definition (changed_symbol_file/line/excerpt,
consumer_file/line/excerpt, invariant, severity, evidence, verification,
recommended_check). If no findings survive the three-citation gate, output a single
no-findings line.

PR context: <body>

Changed public-symbol declarations (filtered):
<filtered diff: lines matching changes_public_surface regex>

Full file path list:
<file paths from the PR>
```


### mx2-pydantic-reviewer
```
<scope preamble>

Review Pydantic Settings classes and configuration patterns in PR #<number>
against MX2 conventions (`.claude/rules/architecture.md` Configuration
Management section). Focus on:

- Required fields declared with `= ""` or other empty defaults (silent
  misbehavior at runtime; should be required with no default for fail-fast)
- Cross-service `AppSettings` imports (architecture violation: see
  `architecture.md` "Cross-service isolation")
- Cross-service DynamoDB access without a standalone dyntastic model
  pointing at the local service's `AppSettings`
- `os.environ.get` patterns that should be migrated to Settings fields
- Magic strings or numbers that should be Settings fields
- Missing `default_factory` on dynamic values (timestamps, UUIDs) where a
  module-level default would evaluate at import time

Use Read to inspect the full Settings file and Grep to find call sites
before flagging. Use Glob to detect sibling Settings files in the service
directory that might have duplicate or conflicting field declarations.

Return findings in structured FINDING format with evidence categories.
Do NOT flag general type safety (route to mx2-code-reviewer), secrets/PII
handling (route to mx2-security-auditor), or architectural trade-offs at the
service-design level (route to mx2-tech-lead manually if needed).

PR context: <body>

Files changed (filtered to Settings/config patterns):
<filtered diff>
```

### mx2-tenth-man
```
<scope preamble>

Surface naive, dumb, or obvious-but-unasked questions about PR #<number>. You
are NOT a code reviewer; you do not verify correctness or flag bugs. Other
specialists own those verdicts. Your job is to ask the questions a fresh pair
of eyes would ask that the author or other reviewers might have skipped past
because they were too close to the problem.

Examples of question shapes you should produce (not exhaustive):
- "Did anyone confirm that X is actually true?" (assumption surfacing)
- "What happens if Y occurs and we're not handling it here?" (edge case)
- "Why is this in this PR rather than a follow-up?" (scope)
- "Is the bead/Jira AC actually satisfied, or just partially?" (intent vs implementation)
- "Has anyone checked whether this regresses the case from MX2-NNNN?" (history)

Constraints:
- Severity vocabulary is QUESTION only. Do NOT emit BLOCKING, CRITICAL,
  DISCUSSION, MINOR, NOTE, COMMENT, SUGGESTION, or any verdict tag.
- Maximum 5 questions. If you have more, prioritize the ones most likely to
  expose a real risk.
- Frame as a question, not a statement. "Has anyone checked X?" not "X is
  broken."
- Each question cites at least one file:line or PR description excerpt so the
  reader can ground the question in evidence.
- Do NOT repeat questions already raised by other specialists or in PR
  comments (provided below for dedup). If your question is a sharper version
  of an existing finding, drop it.

Existing specialist findings and PR comments (for dedup):
<list of findings from prior specialists in this pr-intel run + PR comments>

PR context: <body>
Jira AC (if available): <ticket AC>

PR overview (summarized diff):
<first 50 lines of each file's diff>
```


## Structured Finding Format

Each specialist returns findings in this format:

```
FINDING:
  file: <path>
  location: <function or class containing the code>
  code: <verbatim quote of the relevant line(s) from the diff or codebase>
  evidence: VERIFIED | DIFF-VISIBLE | QUESTION
  verification: <what you checked (VERIFIED), or what the reviewer should check>
  issue: <one-line summary>
  impact: <what breaks, what's at risk, what degrades>
  severity: BLOCKING | DISCUSSION | MINOR
  note_to_reviewer: <optional: caveats, confidence level, what you couldn't check>
```
