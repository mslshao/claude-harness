---
name: review
description: >
  Local self-review fan-out for uncommitted or branch-relative changes.
  Dispatches in parallel to project review agents (code-reviewer for
  structural/style/design, test-quality-reviewer for behavioral test
  quality, observability-reviewer for instrumentation gaps,
  silent-failure-hunter for error propagation gaps, mx2-security-auditor
  for PII/PHI exposure and HIPAA audit-trail field completeness,
  module-cohesion-reviewer for cross-file module cohesion and coupling),
  deduplicates overlapping findings, and presents a grouped severity
  report. Read-only and local-only; does not post to GitHub or fetch
  external context. Use before opening or pushing a PR. Trigger on:
  "review my changes", "review this branch", "self-review", "/review",
  and natural-language siblings when the request refers to code or
  working-tree changes: "give me feedback on", "look at my code",
  "thoughts on this change", "critique", "anything I'm missing", "what
  did I forget", "check my code", "check this change", "any gaps". An
  already-active conversation topic (a ticket, design, or document under
  discussion) is the referent; answer about that, do not probe past it.
  Only when no referent exists in the request or the conversation, probe
  with `git status` and `git diff`; modified or untracked files or a
  non-empty branch-relative diff count as the working-tree referent, so
  proceed with the review rather than answering conversationally.
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

If the diff is genuinely empty (the merge-base resolved and there are no
changes since it), stop and report "No changes to review against `{scope}`."
Do NOT report empty output as "no changes" when the base failed to resolve:
that is the shallow-clone false-clean the step 1 guard catches, so FAIL LOUD
per that guard instead. If the working tree has uncommitted changes when scope
is the default, include them; the default is "everything since main, committed
or not."

## Process

1. **Gather diff scope.** Run the appropriate `git diff` command and capture
   the file list and full diff. If the diff exceeds 1500 lines, warn the
   user and proceed (large diffs dilute findings; consider splitting the
   review).

   **Shallow-clone merge-base guard (load-bearing).** The default scope (and
   any scope that resolves the base with `git merge-base origin/main HEAD`)
   can silently under-scope on a shallow clone. The codespace checkout is a
   shallow clone (`git rev-parse --is-shallow-repository` returns true), where
   `git merge-base origin/main HEAD` may be unresolvable. When it is,
   `git diff $(git merge-base origin/main HEAD)` collapses to a bare `git diff`
   (working-tree-only) and reports a false "clean" on a high-consequence
   check. Resolve the base once up front; if it comes back empty, FAIL LOUD:
   stop and tell the user the merge-base is unreachable on this shallow clone,
   advising `git fetch --unshallow` or an explicit `<range>`. Do NOT auto-fetch
   (a network op crosses the local-only bound), and never silently narrow
   scope. Capture `git rev-parse --short HEAD` and put the HEAD SHA in the
   `{scope description}` so the reviewed commit is unambiguous.

   Also gather `git log $(git merge-base origin/main HEAD)..HEAD --format='%h %s%n%n%b'`
   for commit messages on this branch since fork. Pass this commit log to each agent
   prompt as supplementary intent context (separate from the diff). May be empty for
   branches with no commits-since-fork (e.g., uncommitted-only review).

1a. **Active reuse-search (capability-collision pre-check).** Run this
    before the fan-out, and only when the diff introduces a NEW outbound
    capability rather than extending an existing one. Treat the capability
    signal as met when added lines contain any of: an HTTP call
    (`requests.`, `httpx.`, `urllib.request`, `aiohttp`, `fetch(`); a
    subprocess invocation (`subprocess.`, `os.system`, `shell=True`); a
    queue or topic publish (`publish(`, `send_message(`, `put_events(`); a
    new route declaration (`@app.`, `@router.`, `APIRouter(`); a new CLI
    entry point (`argparse`, `click.`, a new `__main__` block); a
    system-package or image install (`apt-get install`, a Dockerfile `RUN`
    adding a binary); or a new raw SQL or warehouse query string.
    Test-only files alone do not meet it.

    The question this step asks is not "is the new code correct?" but
    "should this code exist at all, or does something in the monorepo
    already own this capability?" That is the Reuse Across Boundaries rule
    in `.claude/rules/architecture.md`, specifically its "If no boundary
    exists, build one; don't duplicate" bullet. Every other lens in this
    skill evaluates the mechanism the author chose; this one evaluates
    whether the mechanism needed choosing.

    **Run the search here; do not delegate it to the fan-out.** The
    self-enrichment instruction in step 2c already asks every agent to grep
    for related code paths, and that is not sufficient: on a real
    duplication of the `/metadata/refresh` publish path, the fan-out ran
    with `module-cohesion-reviewer` dispatched and the question still went
    unasked, because an advisory cohesion lens answers "how should this new
    code be organized?" rather than "should it exist?" The search has to be
    deterministic and owned by the orchestrator.

    Derive 2-4 search terms per introduced capability from the CAPABILITY,
    not from the new code's naming (the author's names are precisely what
    will not match the incumbent's): the external endpoint, host, or binary
    being reached; the shared-library symbol that would wrap it; the domain
    verb plus object. Use BARE symbols, never `class X` or `def X` anchors,
    because the incumbent is often re-exported from a package `__init__.py`
    or declared in a differently-named submodule
    (`mx2.redshift_calls.RedshiftCalls` lives in `calls.py`), so a
    declaration-anchored term misses the call sites that prove the
    capability is already owned.

    Run both passes, source first. Documentation hits otherwise crowd out
    the declaration: on the `/metadata/refresh` replay, 16 of the first 40
    hits were markdown, and at a 12-line cap the source hit fell off the
    list entirely.

    ```
    # pass 1, source: what already implements this
    git grep -n -i -E "<term1>|<term2>" -- 'src/python/mx2/**/*.py' \
      'src/typescript/mx2/**/*.ts' 'libs/**/*.py' \
      ':(exclude)**/*_test.py' ':(exclude)**/test_*.py' \
      ':(exclude)**/conftest.py' | head -25

    # pass 2, docs: which service CLAIMS to own it
    git grep -n -i -E "<term1>|<term2>" -- '**/*.md' | head -15
    ```

    Test files are excluded by git pathspec, NOT by piping through
    `grep -v`. `git grep` emits `path:line:content`, so a content-matching
    filter drops real source lines whose code happens to contain the
    filter text: `grep -vE 'test_'` discards
    `litify_docs__Latest_Version__c` and `_resolve_latest_version_id`,
    which are exactly the identifier shapes a capability search targets.
    Anchoring the filter with a trailing colon narrows that but does not
    close it, since content can contain a colon too. The pathspec filters
    by file inside git and never inspects content.

    Keep pass 2. On that same replay the clearest ownership statement was in
    `src/python/mx2/<service>/api/CLAUDE.md`, naming the router, the topic, and
    the boundary between them more plainly than any source hit did.

    Record ONE of two outcomes per capability. Both are mandatory output;
    silence is not an allowed third state:

    - **Candidate owner found**: name it as `file:line`, state what it
      already does, and surface it in `Critical` (see step 3). Also pass it
      into the `code-reviewer` and `module-cohesion-reviewer` prompts as
      evidence, so their reads start from the incumbent rather than from the
      new code.
    - **No owner found**: record the literal terms tried, as
      `reuse-search: searched <terms>, no existing owner found`, on the
      `Agents:` line. A search whose terms are not stated is
      indistinguishable from a search that never ran.

    Do not resolve the finding. Whether to delete the new code, call the
    incumbent, or add a boundary to the incumbent is the author's call; this
    step exists so the question is asked before the diff gets refined into a
    better version of the wrong thing.

    Skip note when the signal is absent:
    `reuse-search: skipped (no new capability in diff)`.

2. **Fan out in parallel.** Single message with up to six Agent tool
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
   e. **Read-only reminder (every agent)**: "You are a reviewer: report
      findings; never modify the working tree, even to demonstrate a fix.
      Fixes go through a separate fix pass the orchestrator verifies."
      (The review agents' tool rosters are already read-only; this line
      hardens against a resumed or re-purposed session where roster
      enforcement can lapse and a reviewer applies its own findings.)
   f. **Commit log for intent context**: the captured `git log` output (subject + body
      for each commit on this branch). Provides intent context the diff alone doesn't
      show. May be empty.
   g. **Citation requirement**: file:line on every finding.

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
     - Commit messages mention error handling, retry logic, or fallback behavior

     If skipped, note "silent-failure-hunter: skipped (no error-handling
     signals in diff)" in the output header.
   - **`mx2-security-auditor`** for PII/PHI exposure (field types, log calls,
     LLM data flows) and HIPAA audit-trail field completeness on existing log
     calls. Dispatch only when the diff contains security-relevant signals.
     The diff matches if ANY of:
     - The diff contains `audit_log|AuditLog|audit_document|SecretStr|secret_str`
     - The diff contains `llm|openai|anthropic|prompt|chat_completion|get_llm_document_resp`
     - A file under `src/python/mx2/audit/`, `src/python/mx2/auth/`, `libs/audit/`, or `libs/auth/` is touched
     - A Pydantic model field is added with a name matching `ssn|dob|date_of_birth|patient_name|provider_name|medical_record_number|social_security|client_name|api_key|password|token|secret`
     - Commit messages mention PII, PHI, HIPAA, audit logging, or LLM data flows

     If skipped, note "mx2-security-auditor: skipped (no security-relevant
     signals in diff)" in the output header.
   - **`module-cohesion-reviewer`** for cross-file module cohesion and coupling:
     which concern owns a module, whether its name matches its contents, production
     vs test-only helper separation, a hand-rolled query duplicating a typed accessor
     a shared module already provides, cross-service reach-in past a published
     boundary, leaf-layer modules importing from a higher layer, behavior smuggled
     into a "pure move", scope-creep beyond the one concern, and raw dicts where a
     typed model belongs. It interrogates against the cohesion rule (`code-style.md`
     Naming & Organization) and the catalog (`exemplars.md`) and emits author-facing
     questions, not verdicts. Dispatch only when the diff touches a Python module (any
     `src/python/**/*.py` added, deleted, renamed, or with a net-new top-level function
     or class). If skipped, note "module-cohesion-reviewer: skipped (no Python module
     changes)" in the output header.

     When step 1a fired, append its results to this agent's prompt as
     evidence and ask the cross-service form of the question explicitly:
     "Does an existing endpoint, service, or shared-library symbol already
     own this capability? Answer with a `file:line` for the incumbent, or
     state that you searched and found none. Do NOT answer by proposing a
     cleaner local structure for the new code; extracting it into a tidier
     module is not an answer to whether it should exist." Without that last
     clause the agent reliably answers the module-local question instead.

3. **Synthesize.** When all dispatched agents return:
   - Dedup overlapping findings (same file + line + theme is one entry,
     attributed to all sources that flagged it).
   - Group by severity. Use the agents' own severity tags where present;
     otherwise classify by impact.
   - Preserve every file:line citation.
   - Drop findings that another agent's read invalidates (one flags, the
     other explains why it is not a concern in this context).
   - **Demote (never drop) to Open Questions** any finding that cannot be
     verified against the local diff plus the checked-out repo. A self-review
     sees only local state, so a finding that reaches past the local diff plus
     repo is unproven here, not disproven, and demotes rather than blocks.
     (Typically the runner authored the change and can resolve the question
     directly.) Demote when a finding:
     (a) assumes state outside the diff and local repo (a cross-PR
     interaction, remote or deploy state, another open PR, anything
     unverifiable locally); (b) is a cross-service ripple whose in-repo
     consumer was NOT grep-confirmed (grep-confirm-or-demote: a grep miss
     demotes it, it does not disprove the ripple); or (c) is a
     provenance/intent question ("why does this exist?", "was this
     deliberate?"). This operationalizes the `code-review.md` False Positive
     Triage rule (a "callers may depend on X" claim with no named caller is
     speculative) as a demote, not a silent drop.
   - **A reuse finding does not demote.** A step-1a finding names an
     in-repo incumbent at `file:line` produced by a grep that ran, so it is
     grep-confirmed by construction and belongs in `Critical`, not in Open
     Questions. This exception is load-bearing: capability duplication is
     the one finding class whose whole value is asking whether the change
     should exist, and a version of it parked in Open Questions gets
     answered with a local refactor instead of a deletion. Route it to
     `Critical` whichever agent surfaced it, including when the surfacing
     agent is advisory-capped.
   - **Reuse-search state always renders**, even when it found nothing. Put
     the negative on the `Agents:` line with its search terms. Never drop it
     as "no finding"; an omitted negative is how a lens silently stops
     running.

## Output

Plain terminal text aimed at the author reading in their own terminal. Not
GitHub-markdown-styled; no fenced draft-comment blocks, no PR summary
sections. The author decides what to fix; this skill does not draft replies.

```
## Self-review: {scope description}

{N} findings across {M} files.
Agents: code-reviewer, test-quality-reviewer, observability-reviewer, silent-failure-hunter, mx2-security-auditor, module-cohesion-reviewer.

### Critical
- {file}:{line} - {one-line summary}
  Source: {agent name(s)}
  {2-3 lines of context, fix suggestion}

### Important
- ...

### Suggestion
- ...

### Open Questions
- {file}:{line, or n/a if the claim has no local anchor} - {the question or unverifiable claim}
  Source: {agent name(s)}
  Why demoted: {outside local scope | consumer not grep-confirmed | provenance/intent}

### Positive
- {short callouts of what is working; cap at 3 items}
```

If `test-quality-reviewer` was skipped, replace its name in the `Agents:`
line with `test-quality-reviewer (skipped: no test files)`. Similarly for
`observability-reviewer` when no observability-relevant signals are in the
diff: `observability-reviewer (skipped: no observability signals)`. Similarly for
`silent-failure-hunter` when no error-handling signals are in the diff:
`silent-failure-hunter (skipped: no error-handling signals)`. Similarly for
`mx2-security-auditor` when no security-relevant signals are in the diff:
`mx2-security-auditor (skipped: no security signals)`. Similarly for
`module-cohesion-reviewer` when no Python module changes are in the diff:
`module-cohesion-reviewer (skipped: no Python module changes)`. List
only the agents that actually ran (or ran-and-skipped) with their state.

The `Agents:` line also carries the step-1a reuse-search state, which is not
an agent but follows the same show-your-state rule: either
`reuse-search: searched <terms>, no existing owner found`, or
`reuse-search: 1 candidate owner (see Critical)`, or
`reuse-search: skipped (no new capability in diff)`.

Severity rules:

- **Critical**: bugs, data loss risk, security exposure, behavior break, and
  capability duplication (a step-1a finding naming an existing owner). The
  last one is not a bug in the usual sense; it is here because refining code
  that should not exist wastes the entire downstream review, so the author
  needs it before anything else in the report.
- **Important**: patterns that will come back in CI or PR review
- **Suggestion**: polish items the author can take or leave
- **Open Questions**: findings demoted from a severity tier because they
  cannot be verified against the local diff plus repo (out-of-local-scope,
  consumer not grep-confirmed, or a provenance/intent question). Demoted, not
  dropped: surfaced for the author, who holds the context to resolve them.
- **Positive**: cap at 3 items

Omit any bucket with no entries. If Critical, Important, Suggestion, and
Open Questions are all empty, report "No findings; ready to push." (the
Positive bucket, if any, still renders above that line).

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

The trigger-phrase overlap with the `code-reviewer` agent ("check my
code", "thoughts on this change", "anything I'm missing", "any gaps") is
intentional: when a phrase matches both surfaces, dispatch resolves to
this skill and the request gets the full fan-out. Invoke `code-reviewer`
directly only when the structural lens alone is wanted, per that agent's
own description.

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
- **Bounded fan-out.** Up to six project-tier review agents
  (`code-reviewer`, `test-quality-reviewer`, `observability-reviewer`,
  `silent-failure-hunter`, `mx2-security-auditor`, `module-cohesion-reviewer`),
  with conditional dispatch on the latter five. No general specialist routing
  matrix, no cascade.
