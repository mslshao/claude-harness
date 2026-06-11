---
name: review
description: >
  (personal; shadows the project-tier `review` and takes precedence) Delta vs
  the project version: twelve review agents instead of five, adding devops,
  typescript, git-historian, pydantic, python-style, bot-review, and skeptic
  lenses with conditional triggers. Local self-review fan-out for uncommitted
  or branch-relative changes: parallel dispatch, deduplicated overlapping
  findings, grouped severity report. Read-only and local-only; does not post
  to GitHub or fetch external context. Use before opening or pushing a PR.
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

## Reviewer standard

The human-reviewer authoritative source is the engineering lead's [Code Review Guide
for Humans](https://<company>.atlassian.net/wiki/spaces/PPET/pages/5684789249)
(Mar 2026). The priority order codified there is the order this skill
surfaces findings:

1. Description / intent (sent-back-quickly class)
2. Data models / types (sent-back-quickly class; downstream depends)
3. Complexity / organization / naming (call-site test, SRP)
4. Boolean / behavior-switching parameters
5. Tests (obviously correct, single behavior, not coupled to impl)
6. Correctness (trust tests; do NOT trace execution in head)
7. Static analyzer findings (SonarCloud)
8. Pragma / override review (necessary? explained? minimal?)
9. Exception design (raise the condition, not the handling)
10. Large-scale change methodology

When pre-checks (#1, #2, #10) fire, they render in a **Front Door** output
bucket above Critical. The framing is "send back to author" rather than
"iterate line-by-line": fixing these typically invalidates the downstream
review effort, so we surface them first. Pragma misuse (#8), boolean
parameters (#4), and exception design (#9) are inline-iterate findings,
not Front Door; a reviewer's explicit "send back quickly" framing applies to
description and types specifically.

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

1a. **Commit-message intent pre-check (Front Door).** Walk the captured
    commit log. The branch's commit messages are the analog of the PR
    description before the PR exists: if they fail to convey intent, the
    PR description that gets written from them will also fail a reviewer's #1
    gate.

    Flag as a Front Door finding when ANY of:
    - Subject lines are boilerplate-only (`WIP`, `fix`, `update`, `wip
      commit`, `address feedback`, `lint`, `more changes`, single-word)
      AND the branch has > 1 commit
    - All commits lack a body and the subjects are < 30 chars total
    - No subject references a Jira ticket (`MX2-\d+`) AND the diff
      touches multiple services
    - The branch is a squash candidate with > 5 noisy commits that should
      collapse before opening the PR

    Pass when: at least one commit message conveys WHY (not just WHAT),
    or the branch is a single well-described commit. This check fires
    pre-push to catch the issue before it propagates to a PR description
    that reviewers will send back.

1b. **Large-refactor methodology pre-check (Front Door).** When the diff
    is > 500 lines AND > 5 files AND the per-file changes follow a
    mechanical pattern (same edit shape repeated across files), check
    whether the commit messages or any captured branch context describe
    the methodology (the script, command, or rule applied). If absent,
    flag as a Front Door finding: large mechanical changes need a
    methodology statement so reviewers can spot-check rather than read
    every line. (a reviewer #11.)

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

3. **Fan out in parallel.** Single message with up to twelve Agent tool calls.
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
   g. **a reviewer priority order (mx2-code-reviewer only)**: append a one-line
      preamble naming the order so the agent surfaces findings in the
      reviewer-priority sequence: "Surface findings in a reviewer priority
      order: description, types, complexity / naming, boolean params,
      tests, correctness-via-tests (not in-head exec), static analyzers,
      pragmas, exception design, large-refactor methodology. Tag findings
      as front_door=true when they match types (Type System Subversion
      check) or large-refactor methodology gap; these promote to the
      Front Door bucket in synthesis."

4. **Per-agent dispatch rules.** Dispatch the triggered agents in a single
   parallel message. The compact trigger/filter map is below; the full
   per-agent filter, skip-note, coordination, and advisory-contract detail is
   in [dispatch-rules.md](dispatch-rules.md).

   | Agent | Dispatch when | Filter |
   |-------|---------------|--------|
   | `mx2-code-reviewer` | always | implementation files (exclude tests/generated/lockfiles) |
   | `test-quality-reviewer` | `has_test_files` | test files + the sources they test |
   | `observability-reviewer` | `has_observability_signal` | obs-matching files + sibling `*.tf` |
   | `mx2-silent-failure-hunter` | `has_error_handling_signal` | try/except/raise files + FE-BE boundary files |
   | `mx2-security-auditor` | `has_security_signal` | auth/PII/audit/document + `logger.`/`SecretStr` files |
   | `mx2-devops-build-deploy` | `has_terraform_files` | `*.tf`/`*.hcl`/`terragrunt.hcl` + sibling env dirs |
   | `mx2-typescript-reviewer` | `has_typescript_files` | TS files only |
   | `mx2-git-historian` | `structural_risk_size` AND `has_file_history` | changed-file line ranges |
   | `bot-review` (advisory) | `changes_public_surface` | changed public-symbol decls + full file list |
   | `mx2-skeptic` (advisory) | `structural_risk_size` | file list + commit log + first 50 diff lines/file |
   | `mx2-pydantic-reviewer` | `has_pydantic_settings_signal` | Settings/config files + sibling Settings files |
   | `mx2-python-style` | `has_python_files` | Python files only (Author Mode / pre-CI only) |

   Each non-always agent emits a skip note when its signal is absent (e.g.
   "test-quality-reviewer: skipped (no test files in diff)"). The two advisory
   agents are severity-capped and emit non-verdict output: `bot-review` to
   COMMENT/NOTE/SUGGESTION, `mx2-skeptic` to QUESTION only (max 5). Coordination:
   when both `mx2-code-reviewer` and `mx2-typescript-reviewer` fire, send each
   only its language-relevant files. `mx2-python-style` duplicates CI signal
   (pylint/yapf/isort/autoflake); its value is the pre-push catch, so skip it
   manually if running /review post-CI.

5. **SonarCloud pre-check (always; in parallel with the fan-out).** Sonar
   findings are tractable to self-remediate before pushing, so this skill
   surfaces them inline rather than waiting for the post-push gate
   roundtrip. Direct-access discipline: query the MCP first, never ask
   the user to paste from `sonarcloud.io` (see
   `correction:verification:sonarqube-access-pattern`,
   `config:sonarcloud-mcp`).

   - **If the current branch has an open PR**: call
     `mcp__sonarqube__search_sonar_issues_in_projects` with
     `projects=["mx2_docr"]`, `pullRequestId="<N>"`,
     `issueStatuses=["OPEN", "CONFIRMED"]`, AND
     `mcp__sonarqube__get_project_quality_gate_status` with
     `projectKey="mx2_docr"`, `pullRequest="<N>"`. Determine PR existence
     via `gh pr view --json number,headRefName --jq '.number' 2>/dev/null`.
   - **Leak-period scope filter (mandatory).** Filter returned issues to
     those whose `textRange.startLine` falls within the diff scope's hunks.
     Sonar's leak-period mode flags pre-existing violations in touched
     files; those are NOT this branch's responsibility. Surface a one-line
     note "N leak-period findings dropped" so the author knows the count
     differs from the gate's raw view. See
     `feedback:pr-review:sonarqube-leak-period-scope`.
   - **If no PR exists yet (pre-push) OR the MCP errors**: fall back to
     walking the local rule catalog at
     [~/.claude/projects/-workspaces-main/memory/sonarcloud-rules.md](../../projects/-workspaces-main/memory/sonarcloud-rules.md).
     For each rule with a `**Detector**` block, run it against the diff.
     This catches catalog-known rules before Sonar has scanned the branch.
   - **Surface findings** in the `Important` bucket (or `Critical` if the
     issue would block the gate AND is in-diff). Include rule code,
     file:line, the Sonar message, and one-line author-actionable
     remediation.
   - **Last-resort escape hatch**: only if the MCP errored AND the catalog
     walk turned up nothing AND the gate is still failing (per
     `gh pr checks <N>`), ask the user to paste the issue list. State the
     MCP error in the ask. Do not preempt these checks.

6. **Synthesize.** When all dispatched agents and the Sonar pre-check return:
   - Dedup overlapping findings (same file + line + theme is one entry,
     attributed to all sources that flagged it).
   - **Promote to Front Door** any finding that matches a reviewer's
     sent-back-quickly classes: description/intent gate failure (from
     step 1a), large-refactor methodology gap (from step 1b), and
     type/model smells (untyped dicts, `dict[str, Any]`, Literal-key
     dicts, `| None` on collections, `bool | None`, same model
     representing multiple states; typically surfaced by
     `mx2-code-reviewer` Design Judgment Checks). Pragma misuse,
     boolean-parameter smells, and exception-design findings stay in
     their severity buckets; a reviewer's "send back" framing applies to
     description and types specifically, not all design judgment
     findings. Front Door findings render above Critical with framing
     that signals "fix this before deeper review is worth doing."
   - Group remaining findings by severity. Use the agents' own severity
     tags where present; otherwise classify by impact.
   - Preserve every file:line citation.
   - Drop findings that another agent's read invalidates (one flags, the
     other explains why it is not a concern in this context).
   - `bot-review` findings go in their own "Advisory (cross-file)" subsection
     to preserve the COMMENT/NOTE/SUGGESTION distinction.
   - Sonar findings get attribution `Source: SonarCloud (MCP)` or
     `Source: SonarCloud (catalog detector)` so the author can see which
     path produced the signal.

7. **Write the self-review cache (for `/pr-intel --mine` dedup).** After
   presenting the report, persist the RAW per-specialist findings so a
   subsequent `/pr-intel --mine` on the same unchanged diff can reuse them
   instead of re-dispatching the overlapping roster (bead `docr-xvnr`).

   a. Compute the scope identity. The hash MUST be computed from the same
      scope the review ran against (default / `--staged` / `<range>`):

      ```
      mkdir -p ~/.claude/scratch/review-cache
      find ~/.claude/scratch/review-cache -name '*.json' -mmin +120 -delete   # prune >2h TTL
      BRANCH=$(git rev-parse --abbrev-ref HEAD)
      SLUG=$(echo "$BRANCH" | tr '/' '-')
      MB=$(git merge-base origin/main HEAD)
      HEAD_SHA=$(git rev-parse HEAD)
      # default scope; for --staged use `git diff --cached`, for <range> use that range
      DIFF_SHA=$(git diff "$MB" | grep -vE '^index ' | sha256sum | cut -d' ' -f1)
      ```

      The `grep -vE '^index '` strips the only content-derived-but-noisy line
      so a review of uncommitted changes and a `/pr-intel` of the same content
      after it is committed produce the same hash. Any real edit changes the
      body and yields a miss (correct, conservative).

   b. Write `~/.claude/scratch/review-cache/<SLUG>.json`:
      - `branch`, `merge_base_sha` (MB), `head_sha` (HEAD_SHA), `diff_sha256` (DIFF_SHA)
      - `scope_flag`: `"default"` | `"--staged"` | the range string
      - `timestamp`: ISO-8601 UTC
      - `dispatched`: list of agent names that ran
      - `skipped`: map of agent name to skip reason
      - `findings`: map of agent name to that agent's RAW structured FINDING
        list (the per-agent output, NOT the synthesized/deduped view; pr-intel
        re-synthesizes). FINDING `file:` paths are repo-relative and therefore
        portable into pr-intel's worktree-rooted synthesis.

   c. This is the ONLY state `/review` writes, and only to scratch. It never
      writes to the repo, GitHub, or task trackers. Skip the write silently if
      `~/.claude/scratch/` is not writable. If findings were applied to the
      diff after the review ran, skip the cache write entirely; the hash can
      never match and a stale-findings cache misleads more than a miss.

## Output

Plain terminal text aimed at the author reading in their own terminal. Not
GitHub-markdown-styled; no fenced draft-comment blocks, no PR summary
sections. The author decides what to fix.

```
## Self-review: {scope description}

{N} findings across {M} files.
Agents: {comma-separated list of agents that ran and their state}.

### Front Door
[Present ONLY when at least one finding from a reviewer's sent-back-quickly
classes exists: description/intent gate failure, type/model smell, or
large-refactor methodology gap. Omit entirely when empty.]

When this bucket is non-empty, the framing is "fix these before pushing or
before continuing deeper review." Type and intent issues ripple downstream;
fixing them often invalidates the downstream review.

- [intent | types | methodology] {file}:{line OR commit-msg ref} - {one-line summary}
  Source: {agent or pre-check name}
  {1-2 lines: what the smell is, what to do instead}

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
  Source: mx2-skeptic

### Positive
- {short callouts; cap at 3}
```

The `Agents:` line lists every agent's state: ran, skipped with reason, or
not-applicable. Omit any severity bucket with no entries. If all buckets are
empty, report "No findings; ready to push."

Severity rules:

- **Front Door**: a reviewer's sent-back-quickly classes (description/intent,
  type/model smell, large-refactor methodology). Render above Critical.
  Empty bucket is omitted entirely. The author should fix these before
  deeper review iteration. Pragma, boolean-param, and exception-design
  smells are inline-iterate findings; they stay in Critical/Important/
  Suggestion.
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
- **Local-first.** The diff and local git history are the entire context
  the dispatched agents see. The skill itself queries the SonarSource MCP
  when an open PR exists for the branch (see step 5); that is the one
  remote read. Does not fetch Jira, Confluence, or PR review state.
- **Local self-review cache only.** The single state write is
  `~/.claude/scratch/review-cache/<branch>.json` (raw per-specialist findings,
  for `/pr-intel --mine` dedup per bead `docr-xvnr`). Does not write task
  trackers, persistent memory, the repo, or GitHub. The Sonar MCP query is a read.
- **Bounded fan-out.** Up to twelve review agents with conditional dispatch.
  Maximum ten verdict-emitting specialists fire on a single diff (the four
  always-or-conditional agents from project /review, plus six personal-only
  conditional agents: security, devops, typescript, git-historian, pydantic,
  python-style). Two advisory-only agents fire conditionally and produce
  non-verdict output: `bot-review` (cross-file invariant questions, fires on
  public-surface changes) and `mx2-skeptic` (adversarial questions, fires
  on M+ diffs).

## Roster Differentiation

Which agents are personal-only vs project-shared, and the informal promotion
criteria, are documented in [roster.md](roster.md) to inform future promotion
decisions (see CLAUDE.md "Lab-to-production for personal/project artifact
pairs").
