---
name: review
description: >
  Local self-review fan-out for uncommitted or branch-relative changes.
  Personal-tier expansion of the project /review skill: dispatches in parallel
  to up to nine review agents (code, test-quality, observability,
  silent-failure, security, devops, typescript, git-historian, bot-review)
  with conditional triggers, deduplicates overlapping findings, and presents
  a grouped severity report. Read-only and local-only; does not post to
  GitHub or fetch external context. Use before opening or pushing a PR.
  Trigger on: "review my changes", "review this branch", "self-review",
  "/review".
argument-hint: "[--staged | --all | <range>]"
---

# Review (personal tier)

Local self-review via parallel fan-out to personal-tier review agents. The
personal /review is a superset of the project /review: it inherits the four
project review agents and adds five personal-only specialists (security,
infrastructure, TypeScript, git-history regression, cross-file blast-radius)
behind conditional dispatch triggers. Read-only and local-only: no GitHub
posting, no Jira/Confluence fetch, no code modification.

## Why personal-tier expansion

The project /review covers what every engineer should see before pushing
(structural, test-quality, observability, error propagation). The personal
/review additionally surfaces specialist concerns that have historically
required a separate manual invocation (security audit, Terraform validation,
TypeScript-specific checks, regression-of-recent-fix detection, cross-file
consumer invariants). Bundling them behind conditional triggers keeps the
noise floor low while raising the ceiling on what gets caught locally.

A separate "Roster Differentiation" section at the bottom of this file
documents which agents are personal-only vs project-shared, to inform future
promotion decisions.

## When to use

Before opening or pushing a PR, when you want a second opinion on your own
diff. Different from a single-tool linter pass: fans out to multiple agents
with different priors so independent signals stack rather than echo.

Not a substitute for CI. The agents flag what a careful reviewer would; CI
verifies build, type, and test correctness. Run both.

## Input

Default scope: `git diff $(git merge-base origin/main HEAD)`. Branch-relative
diff against the merge-base with `origin/main`, including uncommitted
working-tree changes.

| Flag | Scope |
|------|-------|
| (none) | `git diff $(git merge-base origin/main HEAD)` |
| `--staged` | `git diff --cached` |
| `<range>` | `git diff <range>` |

If the diff is empty, stop and report "No changes to review against
`{scope}`."

## Process

1. **Gather diff scope.** Run the appropriate `git diff` command and capture
   the file list and full diff. If the diff exceeds 1500 lines, warn and
   proceed (large diffs dilute findings; consider splitting the review).

   Also gather `git log $(git merge-base origin/main HEAD)..HEAD --format='%h %s%n%n%b'`
   for commit messages on this branch since fork. Pass this commit log to each
   agent prompt as supplementary intent context (separate from the diff).

2. **Pre-evaluate dispatch signals** (once, before fan-out):

   | Signal | True when |
   |--------|-----------|
   | `has_test_files` | Diff contains `*_test.py`, `test_*.py`, `*.test.ts(x)`, `*.spec.ts(x)`, `conftest.py` |
   | `has_observability_signal` | Exception-class declarations added/removed/renamed; metric-emission patterns (`add_metric`, `put_metric_data`, `MetricsCollector`, `MetricsContext`, `DatadogProvider`, `DogStatsDProvider`); `*.tf` files matching `aws_cloudwatch_metric_alarm\|datadog_monitor\|datadog_dashboard\|aws_cloudwatch_log_group\|aws_lambda_function\|aws_ecs_task_definition`; new value added to a class inheriting from `StrEnum`, `Enum`, `Literal[...]` |
   | `has_error_handling_signal` | Python: added/modified `try:`, `except `, `raise `, `JSONResponse`, `HTTPException`, FastAPI exception handler patterns. TypeScript: added/modified `apiRequest`, `isHttpError`, `console\.error`, `\.catch\(`, `\.then\(`, `await fetch`, `response\.json` patterns. OR commit messages mention error handling/retry/fallback. |
   | `has_security_signal` | Changed file paths match `auth\|security\|token\|jwt\|permission\|rbac\|document\|upload\|download\|access\|audit\|secret\|credential\|patient` OR diff contains `SecretStr`, `logger\.`, `\.info\(`, `\.error\(`, `\.exception\(` on changed lines |
   | `has_terraform_files` | `*.tf`, `*.hcl`, `terragrunt.hcl`, or paths under `infra/`, `module/` |
   | `has_typescript_files` | `*.ts`, `*.tsx`, `*.mts`, `*.cts` outside `src/gen-typescript/` |
   | `has_file_history` | At least one changed file has 3+ prior PRs in the last 180 days (use `git log --since=180.days --oneline -- <file>` and count merge commits or commits referencing PR numbers; threshold met when count >= 3 on any file) |
   | `changes_public_surface` | Diff modifies a top-level `def `, `class `, exported `function`, exported `const`, `interface`, `type`, or module `__all__` declaration |
   | `structural_risk_size` | Diff > 200 lines OR > 5 files changed |
   | `has_pydantic_settings_signal` | Diff adds/modifies a class inheriting from `BaseSettings`, `pydantic_settings.BaseSettings`, or `Singleton`; OR contains `os.environ.get`, `os.environ\[`, `os.getenv\(`; OR adds/modifies a field on a class whose filename matches `*app_settings*`, `*settings*`, `*config*` |
   | `has_python_files` | Diff includes any `*.py` file outside `src/gen-python/` |

3. **Fan out in parallel.** Single message with up to nine Agent tool calls.
   Build each prompt with these elements, in order:

   a. **Code root** path (worktree or repo root).
   b. **Diff scope** as a command (`git -C <root> diff $(git -C <root> merge-base origin/main HEAD)`)
      AND the captured diff output inline (filtered per the per-agent rules in
      step 4).
   c. **Self-enrichment instruction (mandatory).** Tell the agent to read full
      contents of each changed file from disk (not just diff lines), read the
      relevant `.claude/rules/*.md`, and grep for related code paths. Findings
      must be grounded in actual code, not extrapolated from the diff.
   d. **Author Mode preamble**: "CI has not run yet. Flag everything that
      would come back from CI or a careful reviewer."
   e. **Commit log for intent context**: the captured `git log` output.
   f. **Citation requirement**: file:line on every finding.

4. **Per-agent dispatch rules:**

   - **`mx2-code-reviewer`** for structural design, naming, SOLID adherence,
     error handling strategy, code smells, project-rule compliance.
     **Always dispatch.** Filter: implementation files only (exclude tests,
     generated code, lockfiles).

   - **`test-quality-reviewer`** for behavioral test coverage: the refactor
     test, mock saturation, no-assertion tests, name-vs-assertion drift,
     missing negative paths.
     Dispatch when `has_test_files`. Filter: test files + the source files
     they test (use Grep to map test_X.py to X.py).
     Skip note: "test-quality-reviewer: skipped (no test files in diff)".

   - **`observability-reviewer`** for instrumentation gaps: exception class
     renames affecting Datadog Error Tracking monitor filters, error paths
     logged without paired metrics, ddtrace/OTel context propagation gaps
     across SNS/SQS/EventBridge boundaries, missing CloudWatch log retention,
     metric tag cardinality risks.
     Dispatch when `has_observability_signal`. Filter: files matching the
     observability sub-rules + sibling `*.tf` in the same service directory.
     Skip note: "observability-reviewer: skipped (no observability signals)".

   - **`mx2-silent-failure-hunter`** for error propagation gaps: bare/broad
     excepts that swallow errors, log-and-continue where callers depend on
     success, fallback masking, boundary cases where Python errors become
     JSON responses TypeScript code silently drops.
     Dispatch when `has_error_handling_signal`. Filter: files containing
     try/except/raise patterns + frontend-backend boundary files.
     Skip note: "mx2-silent-failure-hunter: skipped (no error-handling signals)".

   - **`mx2-security-auditor`** for PII/PHI exposure in logs and LLM data flows,
     audit trail field completeness on document operations, secret handling
     via SecretStr, error message sanitization.
     Dispatch when `has_security_signal`. Filter: auth/PII/audit/document
     files + any file touching `logger\.` or `SecretStr` patterns.
     Skip note: "mx2-security-auditor: skipped (no security-relevant signals)".

   - **`mx2-devops-build-deploy`** for Terraform/HCL correctness: missing
     variable pass-through to child modules, duplicate HCL keys (silently
     keeps last value), missing environment configs, EventBridge subscription
     completeness, terragrunt dependency injection gaps.
     Dispatch when `has_terraform_files`. Filter: `*.tf`, `*.hcl`,
     `terragrunt.hcl` files + sibling environment directories.
     Skip note: "mx2-devops-build-deploy: skipped (no infra files in diff)".

   - **`mx2-typescript-reviewer`** for type safety in TS apps, React/Next.js
     patterns, frontend-specific concerns (a11y, performance, bundle size),
     TS-specific error handling.
     Dispatch when `has_typescript_files`. Filter: TS files only (do not send
     Python diff to this agent).
     Coordination: when both `mx2-code-reviewer` and `mx2-typescript-reviewer`
     would fire on the same diff, send each only its language-relevant files.
     Skip note: "mx2-typescript-reviewer: skipped (no TS files in diff)".

   - **`mx2-git-historian`** for regression-of-recent-fix detection
     (modified lines authored within 90 days in commits referencing Jira bug
     tickets) and flip-flop pattern detection (line ranges rewritten 3+ times
     in 60 days).
     Dispatch when `structural_risk_size` AND `has_file_history`. Filter:
     line ranges of changed files only (the agent runs `git log/blame/show`
     against the worktree itself).
     Skip note: "mx2-git-historian: skipped (PR small or no file history)".

   - **`bot-review`** for cross-file consumer-invariant breakage. For each
     changed public symbol, identifies consumers via Grep and articulates the
     invariant each consumer assumes that the change weakens.
     Dispatch when `changes_public_surface`. Filter: changed public-symbol
     declarations only + full file path list (do not send full diff; the
     agent fetches consumers itself).
     Advisory-only: severity hard-capped at COMMENT/NOTE/SUGGESTION; never
     BLOCKING/CRITICAL. Findings appear in their own subsection of the
     output, not folded into the main severity buckets.
     Skip note: "bot-review: skipped (no public surface change)".

   - **`mx2-tenth-man`** for adversarial dissent: surfaces naive, dumb, or
     obvious-but-unasked questions about assumptions, scope, edge cases, and
     intent-vs-implementation drift. Designed as a safety net for fragmented
     attention; bigger diffs have more hiding spots.
     Dispatch when `structural_risk_size`. Filter: file path list + commit
     log + first 50 lines of each file's diff. The agent asks questions
     about intent; it does not need exhaustive code context.
     Advisory-only: severity vocabulary is QUESTION only; never emits
     verdicts. Findings appear in their own "Open questions" subsection of
     the output. Max 5 questions per run.
     Skip note: "mx2-tenth-man: skipped (XS/S diff)".

   - **`mx2-pydantic-reviewer`** for configuration patterns: required fields
     with empty-string defaults (silent misbehavior), cross-service
     `AppSettings` imports (architecture violation), `os.environ` patterns
     that should be Settings fields, magic strings/numbers that belong in
     Settings, missing `default_factory` on dynamic values.
     Dispatch when `has_pydantic_settings_signal`. Filter: Settings/config
     files in the diff + sibling Settings files in the same service
     directory (to detect duplicate or conflicting field declarations).
     Skip note: "mx2-pydantic-reviewer: skipped (no Settings/config signals)".

   - **`mx2-python-style`** for Google Python Style Guide + MX2 style
     overrides: 2-space indent, 108-char line length, modern type syntax
     (`X | None` not `Optional[X]`), logging conventions (percent-formatting,
     `extra` dict), import organization. Author Mode (pre-CI) only;
     duplicates CI signal otherwise.
     Dispatch when `has_python_files`. Filter: Python files only.
     Skip note: "mx2-python-style: skipped (no Python files in diff)".
     Note: this agent's findings overlap with what CI catches via pylint,
     yapf, isort, autoflake. The /review value is catching them BEFORE
     pushing to avoid the CI round-trip. If you are running /review
     post-CI for some reason, consider skipping this agent manually.

5. **Synthesize.** When all dispatched agents return:
   - Dedup overlapping findings (same file + line + theme is one entry,
     attributed to all sources that flagged it).
   - Group by severity. Use the agents' own severity tags where present;
     otherwise classify by impact.
   - Preserve every file:line citation.
   - Drop findings that another agent's read invalidates (one flags, the
     other explains why it is not a concern in this context).
   - `bot-review` findings go in their own "Advisory (cross-file)" subsection
     to preserve the COMMENT/NOTE/SUGGESTION distinction.

## Output

Plain terminal text aimed at the author reading in their own terminal. Not
GitHub-markdown-styled; no fenced draft-comment blocks, no PR summary
sections. The author decides what to fix.

```
## Self-review: {scope description}

{N} findings across {M} files.
Agents: {comma-separated list of agents that ran and their state}.

### Critical
- {file}:{line} - {one-line summary}
  Source: {agent name(s)}
  {2-3 lines of context, fix suggestion}

### Important
- ...

### Suggestion
- ...

### Advisory (cross-file)
- {file}:{line} - {one-line invariant articulation}
  Source: bot-review
  Consumer: {consumer file}:{line}
  Severity: COMMENT | NOTE | SUGGESTION

### Open questions
- {one-line question grounded in file:line or commit context}
  Source: mx2-tenth-man

### Positive
- {short callouts; cap at 3}
```

The `Agents:` line lists every agent's state: ran, skipped with reason, or
not-applicable. Omit any severity bucket with no entries. If all buckets are
empty, report "No findings; ready to push."

Severity rules:

- **Critical**: bugs, data loss risk, security exposure, behavior break.
- **Important**: patterns that will come back in CI or PR review.
- **Suggestion**: polish items the author can take or leave.
- **Advisory (cross-file)**: bot-review's consumer-invariant findings,
  severity-capped to COMMENT/NOTE/SUGGESTION.
- **Positive**: cap at 3 items.

## Namespace decision

This skill claims the unscoped `/review` slot at the personal tier. Personal-
tier skills take resolution precedence over project-tier skills with the same
`name:` frontmatter field, per CLAUDE.md's name-overlap convention. Typing
`/review` in a session with this skill loaded resolves to this personal
version; the project version remains as the cold-start baseline for
contributors who do not have the personal expansion loaded.

If the CodeRabbit plugin (or any other plugin shipping a `/review`) is also
installed, Claude Code auto-namespaces the plugin variant as
`/<plugin>:review`. The unscoped slot belongs to this skill.

## Fire-and-forget setup (optional)

Each subagent's tool calls (file reads, rule lookups, project greps, git
log/blame for git-historian) trigger a permission prompt by default. For
uninterrupted runs, pre-approve the read-only set in
`.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Grep",
      "Glob",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(git blame:*)",
      "Bash(git show:*)",
      "Bash(git status:*)"
    ]
  }
}
```

## Bounds

- **Read-only.** Does not modify code, does not post to GitHub.
- **Local-only.** Does not fetch Jira, Confluence, or remote PR state. The
  diff plus local git history is the entire context the agents see.
- **No external state.** Does not read or write task trackers or persistent
  memory.
- **Bounded fan-out.** Up to twelve review agents with conditional dispatch.
  Maximum ten verdict-emitting specialists fire on a single diff (the four
  always-or-conditional agents from project /review, plus six personal-only
  conditional agents: security, devops, typescript, git-historian, pydantic,
  python-style). Two advisory-only agents fire conditionally and produce
  non-verdict output: `bot-review` (cross-file invariant questions, fires on
  public-surface changes) and `mx2-tenth-man` (adversarial questions, fires
  on M+ diffs).

## Roster Differentiation

This section documents which agents are personal-only vs project-shared, to
inform future promotion decisions (see CLAUDE.md "Lab-to-production for
personal/project artifact pairs").

| Agent | Personal | Project | Notes |
|-------|----------|---------|-------|
| `mx2-code-reviewer` | yes | (project has `code-reviewer`) | Personal variant has skill-catalog awareness and write-capable tools per CLAUDE.md "lab-to-production" intentional divergence. |
| `test-quality-reviewer` | yes | yes (name-overlap) | Personal takes precedence via name-overlap convention. |
| `observability-reviewer` | yes | yes (name-overlap) | Personal takes precedence. Both promoted via PR #8970. |
| `mx2-silent-failure-hunter` | yes | (project has `silent-failure-hunter`) | Personal variant exists at `mx2-silent-failure-hunter`; project version landed via PR #8971 as `silent-failure-hunter` (unprefixed). |
| `mx2-security-auditor` | yes | no | Personal-only. PII/PHI exposure focus on legal-domain. Promotion candidate after soak. |
| `mx2-devops-build-deploy` | yes | no | Personal-only. Terraform/HCL specialist. Promotion candidate. |
| `mx2-typescript-reviewer` | yes | no | Personal-only. TS app specialist. Promotion candidate. |
| `mx2-git-historian` | yes | no | Personal-only. Regression-of-recent-fix detector. Higher promotion bar (false-positive sensitivity). |
| `bot-review` | yes | no | Personal-only. Cross-file blast-radius. Advisory severity contract. Promotion candidate, but advisory model needs project-tier consensus first. |
| `mx2-tenth-man` | yes | no | Personal-only. Adversarial dissent (QUESTION severity only). Designed as safety net for multi-window fragmented attention; the advisory contract makes promotion lower-risk, but the value is michael-specific and the project-tier need has not been demonstrated. |
| `mx2-pydantic-reviewer` | yes | no | Personal-only. Pydantic Settings + configuration patterns specialist. Codebase-general; promotion candidate after soak. |
| `mx2-python-style` | yes | no | Personal-only. Style enforcement (Google Python + MX2 overrides). Promotion bar is HIGH: most findings duplicate CI signal (pylint, yapf, isort, autoflake). Worth keeping at personal tier for pre-CI catch but promoting risks redundant noise. |
| `mx2-pr-precedent` | yes | no | NOT in /review (queries `gh` API, violates local-only). Used only in /pr-intel. |

Promotion criteria (informal): an agent is a candidate when (a) it has run
without false-positive churn for 30+ days at personal tier, (b) its scope is
codebase-general not michael-specific, and (c) its severity contract is clear
enough that a less-tuned operator can act on findings without context. Track
candidates via beads `docr-*` series.
