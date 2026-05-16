---
name: review
description: >
  Local self-review fan-out for uncommitted or branch-relative changes.
  Dispatches in parallel to project review agents (code-reviewer for
  structural/style/design, test-quality-reviewer for behavioral test
  quality, observability-reviewer for instrumentation gaps,
  silent-failure-hunter for error propagation gaps), deduplicates
  overlapping findings, and presents a grouped severity report. Read-only
  and local-only; does not post to GitHub or fetch external context. Use
  before opening or pushing a PR. Trigger on: "review my changes", "review
  this branch", "self-review", "/review".
argument-hint: "[--staged | --all | <range>]"
---

# Review

Local self-review via parallel fan-out to project review agents. Surfaces
what CI and a careful reviewer would flag, before either has run. Read-only
and local-only: this skill does not post to GitHub, does not fetch Jira or
Confluence, does not modify code.

## When to use

Before opening or pushing a PR, when you want a second opinion on your own
diff. Different from a single-tool linter pass: fans out to multiple agents
with different priors so independent signals stack rather than echo.
Repeated runs of one tool against the same diff produce correlated output,
not independent signal.

Not a substitute for CI. The agents flag what would come back from a careful
reviewer; CI verifies build, type, and test correctness. Run both.

## Input

Default scope: `git diff $(git merge-base origin/main HEAD)` - branch-relative diff against the merge-base with `origin/main`, including uncommitted working-tree changes. Using the merge-base avoids surfacing main's progress since branch point.

| Flag | Scope |
|------|-------|
| (none) | `git diff $(git merge-base origin/main HEAD)` |
| `--staged` | `git diff --cached` (cached only) |
| `<range>` | `git diff <range>` for an explicit ref or commit range |

If the diff is empty, stop and report "No changes to review against
`{scope}`." If the working tree has uncommitted changes when scope is the
default, include them; the default is "everything since main, committed or
not."

## Process

1. **Gather diff scope.** Run the appropriate `git diff` command and capture
   the file list and full diff. If the diff exceeds 1500 lines, warn the
   user and proceed (large diffs dilute findings; consider splitting the
   review).

   Also gather `git log $(git merge-base origin/main HEAD)..HEAD --format='%h %s%n%n%b'`
   for commit messages on this branch since fork. Pass this commit log to each agent
   prompt as supplementary intent context (separate from the diff). May be empty for
   branches with no commits-since-fork (e.g., uncommitted-only review).

2. **Fan out in parallel.** Single message with up to four Agent tool
   calls. Build each agent's prompt with these elements, in order:

   a. **Code root** path (the worktree or repo root the agent operates on).
   b. **Diff scope** as a command (`git -C <root> diff $(git -C <root> merge-base origin/main HEAD)` or the
      flag-equivalent) AND the captured diff output inline.
   c. **Self-enrichment instruction (mandatory).** Tell the agent to ground
      itself before opining: read the full current contents of each
      changed file from disk (not just the diff lines), read the relevant
      `.claude/rules/*.md` for the file types it is reviewing, and grep
      for the most-related existing code paths in the project. The agent
      must not produce findings on details it has not read. This pre-empts
      the common failure mode where an agent extrapolates from the diff
      alone and hallucinates project conventions, missing imports, or
      surrounding code structure that the diff does not show.
   d. **Author Mode preamble**: "CI has not run yet. Flag everything that
      would come back from CI or a careful reviewer."
   e. **Commit log for intent context**: the captured `git log` output (subject + body
      for each commit on this branch). Provides intent context the diff alone doesn't
      show. May be empty.
   f. **Citation requirement**: file:line on every finding.

   Targets:

   - **`code-reviewer`** for structural review, design quality, naming,
     SOLID adherence, error handling, code smells, and project-rule
     compliance from `.claude/rules/`. Always dispatch.
   - **`test-quality-reviewer`** for behavioral test coverage: the refactor
     test, mock saturation, no-assertion tests, name-vs-assertion drift,
     missing negative paths. Dispatch only when the diff contains test
     files (path matches `*_test.py`, `test_*.py`, `*.test.ts`, `*.test.tsx`,
     `*.spec.ts`, `*.spec.tsx`, `conftest.py`). If skipped, note "test-quality-reviewer:
     skipped (no test files in diff)" in the output header.
   - **`observability-reviewer`** for instrumentation gaps: exception class
     renames that break Datadog Error Tracking monitor filters, error paths
     logged without paired metrics, ddtrace/OTel context propagation gaps
     across SNS/SQS/EventBridge boundaries, missing CloudWatch log retention
     on new Lambda/ECS services, and metric tag/dimension cardinality risks.
     Dispatch only when the diff contains observability-relevant signals.
     The diff matches if ANY of:
     - A class declaration matching `class .*Exception|class .*Error|class .*\(MX2Error\)|class .*\(ApplicationError\)` is added, removed, or renamed
     - The diff contains `add_metric|put_metric_data|MetricsCollector|MetricsContext|DatadogProvider|DogStatsDProvider`
     - A `*.tf` file is touched and contains `aws_cloudwatch_metric_alarm|datadog_monitor|datadog_dashboard|aws_cloudwatch_log_group|aws_lambda_function|aws_ecs_task_definition`
     - A new value is added to a class inheriting from `StrEnum`, `Enum`, or `Literal[...]`

     If skipped, note "observability-reviewer: skipped (no observability-relevant
     signals in diff)" in the output header.
   - **`silent-failure-hunter`** for error propagation gaps in MX2's polyglot
     codebase: bare/broad excepts that swallow errors, log-and-continue patterns
     where callers depend on success, missing audit trail presence on document
     operations, fallback masking that hides meaningful failures, and
     boundary-failure cases where Python errors become JSON responses that
     TypeScript code silently drops. Dispatch only when the diff contains
     error-handling-relevant signals. The diff matches if ANY of:
     - Python: added/modified `try:`, `except `, or `raise ` lines
     - Python: added/modified `JSONResponse`, `HTTPException`, or FastAPI exception handler patterns
     - TypeScript: added/modified `apiRequest`, `isHttpError`, `console\.error`, `\.catch\(`, `\.then\(`, `await fetch`, or `response\.json` patterns
     - The PR description explicitly mentions error handling, retry logic, or fallback behavior

     If skipped, note "silent-failure-hunter: skipped (no error-handling
     signals in diff)" in the output header.

3. **Synthesize.** When all dispatched agents return:
   - Dedup overlapping findings (same file + line + theme is one entry,
     attributed to all sources that flagged it).
   - Group by severity. Use the agents' own severity tags where present;
     otherwise classify by impact.
   - Preserve every file:line citation.
   - Drop findings that another agent's read invalidates (one flags, the
     other explains why it is not a concern in this context).

## Output

Plain terminal text aimed at the author reading in their own terminal. Not
GitHub-markdown-styled; no fenced draft-comment blocks, no PR summary
sections. The author decides what to fix; this skill does not draft replies.

```
## Self-review: {scope description}

{N} findings across {M} files.
Agents: code-reviewer, test-quality-reviewer, observability-reviewer, silent-failure-hunter.

### Critical
- {file}:{line} - {one-line summary}
  Source: {agent name(s)}
  {2-3 lines of context, fix suggestion}

### Important
- ...

### Suggestion
- ...

### Positive
- {short callouts of what is working; cap at 3 items}
```

If `test-quality-reviewer` was skipped, replace its name in the `Agents:`
line with `test-quality-reviewer (skipped: no test files)`. Similarly for
`observability-reviewer` when no observability-relevant signals are in the
diff: `observability-reviewer (skipped: no observability signals)`. Similarly for
`silent-failure-hunter` when no error-handling signals are in the diff:
`silent-failure-hunter (skipped: no error-handling signals)`. List
only the agents that actually ran (or ran-and-skipped) with their state.

Severity rules:

- **Critical**: bugs, data loss risk, security exposure, behavior break
- **Important**: patterns that will come back in CI or PR review
- **Suggestion**: polish items the author can take or leave
- **Positive**: cap at 3 items

Omit any severity bucket with no entries. If all four buckets are empty,
report "No findings; ready to push."

## Namespace decision

This skill claims the unscoped `/review` slash. Claude Code ships a
built-in `/review` ("Review a pull request") alongside `/init` and
`/security-review`. Project-level skills shadow the built-in when names
collide, verified empirically when this skill landed; typing `/review` in
a session that has this skill loaded resolves to this skill.

If the CodeRabbit plugin (or any other plugin shipping a `/review`) is
also installed, Claude Code auto-namespaces the plugin variant as
`/<plugin>:review`. Multiple variants coexist; the unscoped slot belongs
to this skill.

## Fire-and-forget setup (optional)

Each subagent's tool calls (file reads, rule lookups, project greps) trigger
a permission prompt by default; the self-enrichment step adds more of them.
For uninterrupted runs, pre-approve the read-only set in
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
      "Bash(git show:*)",
      "Bash(git status:*)"
    ]
  }
}
```

Skip if you prefer to inspect each tool call before approval. The git
allowlist is read-only by design; any non-allowlisted command (writes,
mutations, network calls) still prompts.

## Bounds

- **Read-only.** Does not modify code, does not post to GitHub.
- **Local-only.** Does not fetch Jira, Confluence, or remote PR state. The
  diff is the entire context the agents see.
- **No external state.** Does not read or write task trackers, persistent memory, or DynamoDB.
- **Bounded fan-out.** Up to four project-tier review agents
  (`code-reviewer`, `test-quality-reviewer`, `observability-reviewer`, `silent-failure-hunter`),
  with conditional dispatch on the latter three. No general specialist
  routing matrix, no cascade. If a diff warrants security review, run the
  security audit pass separately.
