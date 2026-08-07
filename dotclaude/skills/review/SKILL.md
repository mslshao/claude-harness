---
name: review
description: >
  (personal; shadows the project-tier `review` and takes precedence) Delta vs
  the project version: thirteen review agents instead of six, adding devops,
  typescript, git-historian, pydantic, python-style, bot-review, and skeptic
  lenses with conditional triggers. Local self-review fan-out for uncommitted
  or branch-relative changes: parallel dispatch, deduplicated overlapping
  findings, grouped severity report. Read-only and local-only; does not post
  to GitHub or fetch external context. Use before opening or pushing a PR.
  Trigger on: "review my changes", "review this branch", "self-review",
  "/review".
argument-hint: "[--staged | <range>]"
---

# Review (personal tier)

Local self-review via parallel fan-out to personal-tier review agents. The
personal /review is a superset of the project /review: it inherits the six
project review agents (code-reviewer, test-quality-reviewer, observability-reviewer,
silent-failure-hunter, mx2-security-auditor, module-cohesion-reviewer) and adds
seven personal-only specialists (devops, TypeScript, git-history regression,
pydantic, python-style, cross-file blast-radius, skeptic) behind conditional
dispatch triggers. Read-only and local-only: no GitHub
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

The human-reviewer authoritative source is the engineering lead's Code Review Guide
for Humans (an internal Confluence page, Mar 2026). The priority order codified
there is the order this skill surfaces findings:

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
not Front Door; the engineering lead's explicit "send back quickly" framing
applies to description and types specifically.

This skill adds ONE Front Door class that is not from the engineering lead's guide:
**capability duplication** (step 2a), sourced from `architecture.md` Reuse
Across Boundaries. It is kept attributionally separate rather than appended
to the list above, which is someone else's document.

## Input

Default scope: `git diff $(git merge-base origin/main HEAD)`. Branch-relative
diff against the merge-base with `origin/main`, including uncommitted
working-tree changes.

| Flag | Scope |
|------|-------|
| (none) | `git diff $(git merge-base origin/main HEAD)` |
| `--staged` | `git diff --cached` |
| `<range>` | `git diff <range>` |

If the diff is genuinely empty (the merge-base resolved and there are no
changes since it), stop and report "No changes to review against
`{scope}`." Do NOT report empty output as "no changes" when the base failed
to resolve: that is the shallow-clone false-clean the step 1 guard catches,
so FAIL LOUD per that guard instead.

## Process

1. **Gather diff scope.** Run the appropriate `git diff` command and capture
   the file list and full diff. If the diff exceeds 1500 lines, warn and
   proceed (large diffs dilute findings; consider splitting the review).

   **Shallow-clone merge-base guard (load-bearing).** The default scope (and
   any scope that resolves the base with `git merge-base origin/main HEAD`)
   can silently under-scope on a shallow clone. The codespace checkout IS a
   shallow clone (`git rev-parse --is-shallow-repository` returns true), where
   `git merge-base origin/main HEAD` may be unresolvable. When it is,
   `git diff $(git merge-base origin/main HEAD)` collapses to a bare
   `git diff` (working-tree-only) and reports a false "clean" on a
   high-consequence check. Resolve the base once up front; if it comes back
   empty, FAIL LOUD: stop and tell the user the merge-base is unreachable on
   this shallow clone, advising `git fetch --unshallow` or an explicit
   `<range>`. Do NOT auto-fetch (a network op crosses the local-only bound),
   and never silently narrow scope. Capture `git rev-parse --short HEAD` and
   put the HEAD SHA in the `{scope description}` so the reviewed commit is
   unambiguous.

   Also gather `git log $(git merge-base origin/main HEAD)..HEAD --format='%h %s%n%n%b'`
   for commit messages on this branch since fork. Pass this commit log to each
   agent prompt as supplementary intent context (separate from the diff).

1a. **Commit-message intent pre-check (Front Door).** Walk the captured
    commit log. The branch's commit messages are the analog of the PR
    description before the PR exists: if they fail to convey intent, the
    PR description that gets written from them will also fail the engineering
    lead's #1 gate.

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
    every line. (The engineering lead's guide, #11.)

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
   | `has_python_module_change` | A `src/python/**/*.py` file is added, deleted, or renamed, OR added lines declare a net-new top-level `def `/`class ` (column-0 on a `+` line). Test-only Python changes (`*_test.py`, `test_*`, `conftest.py`) alone do not set it unless production/test-only mixing is the concern |
   | `adds_capability` | Added lines introduce a NEW outbound capability rather than extending an existing one. Any of: an HTTP call (`requests.`, `httpx.`, `urllib.request`, `aiohttp`, `fetch(`); a subprocess invocation (`subprocess.`, `os.system`, `shell=True`); a queue or topic publish (`publish(`, `send_message(`, `put_events(`); a new route declaration (`@app.`, `@router.`, `APIRouter(`); a new CLI entry point (`argparse`, `click.`, a new `__main__` block); a system-package or image install (`apt-get install`, a Dockerfile `RUN` adding a binary); or a new raw SQL or warehouse query string. Test-only files alone do not set it |

2a. **Active reuse-search (capability-collision pre-check).** Fires when
    `adds_capability`. The question here is not "is the new code correct?"
    but "should this code exist at all, or does something in the monorepo
    already own this capability?" That is `architecture.md` Reuse Across
    Boundaries, specifically its "If no boundary exists, build one; don't
    duplicate" bullet.

    **Run the search yourself; do NOT delegate it to the fan-out.** The
    mandatory self-enrichment instruction in step 3c already tells every
    agent to grep for related code paths, and on the <service>
    `/metadata/refresh` duplication (2026-07-24, `docr-5obvn`) it did not
    fire even with `module-cohesion-reviewer` dispatched. The incumbent was
    `src/python/mx2/<service>/api/routers/doc_metadata_refresh.py`, mounted at
    `<service>/api/fastapi.py:23`, publishing the same SNS topic. An instruction
    that has been tried and missed is not a mechanism; the search has to be
    deterministic and owned here.

    Derive 2-4 search terms per introduced capability from the CAPABILITY,
    not from the new code's naming (the author's names are precisely what
    will not match the incumbent's):
    - the external endpoint, host, or binary being reached
      (`api.anthropic.com`, `superset`, `soffice`)
    - the shared-library symbol that would wrap it (`init_llm`,
      `RedshiftCalls`, `DocumentStore`)
    - the domain verb plus object (`publish refresh`, `convert docx`)

    Use BARE symbols as terms, never `class X` or `def X` anchors. The
    incumbent is often re-exported from a package `__init__.py` or declared
    in a differently-named submodule (`mx2.redshift_calls.RedshiftCalls`
    lives in `calls.py`), so a declaration-anchored term misses the call
    sites that prove the capability is already owned.

    Then, from the code root, run BOTH passes. Source first, because
    documentation hits otherwise crowd out the declaration (measured on the
    `/metadata/refresh` replay: 16 of the first 40 hits were markdown, and
    at a 12-line cap the source hit fell off the list entirely):

    ```
    # pass 1, source: what already implements this
    git grep -n -i -E "<term1>|<term2>" -- 'src/python/mx2/**/*.py' \
      'src/typescript/mx2/**/*.ts' 'libs/**/*.py' \
      ':(exclude)**/*_test.py' ':(exclude)**/test_*.py' \
      ':(exclude)**/conftest.py' | head -25

    # pass 2, docs: which service CLAIMS to own it (often the clearest statement)
    git grep -n -i -E "<term1>|<term2>" -- '**/*.md' | head -15
    ```

    Test files are excluded by git pathspec, NOT by piping through
    `grep -v`. `git grep` emits `path:line:content`, so a content-matching
    filter drops real source lines whose code happens to contain the filter
    text: `grep -vE 'test_'` discards `litify_docs__Latest_Version__c` and
    `_resolve_latest_version_id`, exactly the identifier shapes a capability
    search targets. A trailing-colon anchor narrows that but does not close
    it, since content can contain a colon too.

    Keep pass 2. On the `/metadata/refresh` replay the single clearest
    ownership statement was in `<service>/api/CLAUDE.md`, naming the router,
    the topic, and the "don't cross-wire them" boundary, which no source
    hit stated as plainly.

    Record ONE of two outcomes per capability. Both are mandatory output;
    silence is not an allowed third state:

    - **Candidate owner found**: name it as `file:line`, state what it
      already does, and carry it into the report as a Front Door finding
      (step 6). Also pass it into the `mx2-code-reviewer` and
      `module-cohesion-reviewer` prompts as evidence, so their reads start
      from the incumbent rather than from the new code.
    - **No owner found**: record the literal terms tried, as
      `reuse-search: searched <terms>, no existing owner found`. This
      renders on the `Agents:` header line. A search whose terms are not
      stated is indistinguishable from a search that never ran.

    Do not resolve the finding. Whether to delete the new code, call the
    incumbent, or add a boundary to the incumbent is the author's call;
    this step exists to make sure the question is asked BEFORE the diff
    gets refined into a better version of the wrong thing.

3. **Fan out in parallel.** Single message with up to thirteen Agent tool calls.
   Build each prompt with these elements, in order:

   a. **Code root** path (worktree or repo root).
   b. **Diff scope** as a command (`git -C <root> diff $(git -C <root> merge-base origin/main HEAD)`)
      AND the captured diff output inline (filtered per the per-agent rules in
      step 4).
   c. **Self-enrichment instruction (mandatory).** Tell the agent to read full
      contents of each changed file from disk (not just diff lines), read the
      relevant `.claude/rules/*.md`, and grep for related code paths. Findings
      must be grounded in actual code, not extrapolated from the diff.
      **Not-checked-out-branch caveat**: this disk-read instruction assumes the
      working tree IS the review target (HEAD is the branch). When the scope is a
      `<range>` against a branch that is only fetched (e.g. reviewing a PR branch
      from `main`), on-disk reads return the BASE, not the branch, so agents emit
      base-relative false positives (observed PR #10611: a Settings field flagged
      as "added but unconsumed" because the agent read main, where the consumer
      did not yet exist). Fix: either (a) instruct each agent to read the branch's
      blobs via `git show <headref>:<path>` (pass `<headref>` in the prompt), or
      (b) check the branch into a worktree first so the working tree matches the
      review target.
   d. **Author Mode preamble**: "CI has not run yet. Flag everything that
      would come back from CI or a careful reviewer."
   d2. **Read-only reminder (every agent)**: "You are a reviewer: report
      findings; never modify the working tree, even to demonstrate a fix.
      Fixes go through a separate fix pass the orchestrator verifies."
      (Reviewer tool rosters are already read-only; this line covers resumed
      or re-purposed sessions where roster enforcement can lapse: a 2026-07
      pilot had a resumed reviewer apply its own findings unattributed.)
   e. **Commit log for intent context**: the captured `git log` output.
   f. **Citation requirement**: file:line on every finding.
   g. **Engineering lead's priority order (mx2-code-reviewer only)**: append a
      one-line preamble naming the order so the agent surfaces findings in the
      reviewer-priority sequence: "Surface findings in the engineering lead's
      priority order: description, types, complexity / naming, boolean params,
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
   | `module-cohesion-reviewer` (advisory) | `has_python_module_change` | implementation `.py` files + full file list |

   Each non-always agent emits a skip note when its signal is absent (e.g.
   "test-quality-reviewer: skipped (no test files in diff)"). The three advisory
   agents are severity-capped and emit non-verdict output: `bot-review` to
   COMMENT/NOTE/SUGGESTION, `mx2-skeptic` to QUESTION only (report all real
   questions ranked by blast radius, soft ceiling ~10), and
   `module-cohesion-reviewer` to QUESTION/SUGGESTION/COMMENT (every finding an
   author-facing question, never BLOCKING/CRITICAL).

   **Reuse-finding exemption to that cap.** A finding that an existing
   endpoint, service, or shared-library symbol ALREADY owns the capability
   this diff adds is not subject to the advisory cap; it promotes to Front
   Door per step 6, whichever agent surfaced it. The cap exists so cohesion
   questions do not read as verdicts, but a reuse violation held at QUESTION
   severity is what lets it be answered with a local refactor (leaf-module
   extraction) instead of deletion. That is how the <service>
   `/metadata/refresh` duplication survived converge, a 13-lens `/review`,
   two independent post-launch reviews, and `/pr-intel --mine`.

   Coordination:
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
   - **Promote to Front Door** any finding that matches the engineering
     lead's sent-back-quickly classes: description/intent gate failure (from
     step 1a), large-refactor methodology gap (from step 1b), and
     type/model smells (untyped dicts, `dict[str, Any]`, Literal-key
     dicts, `| None` on collections, `bool | None`, same model
     representing multiple states; typically surfaced by
     `mx2-code-reviewer` Design Judgment Checks). **Also promote
     capability duplication** (from step 2a, or from any agent that
     independently names an existing owner): a change that reimplements
     what an existing endpoint or shared symbol already provides is the
     strongest send-back class there is, because refining it wastes the
     entire downstream review. This one class is sourced from
     `architecture.md` Reuse Across Boundaries, not from the engineering
     lead's guide. Pragma misuse,
     boolean-parameter smells, and exception-design findings stay in
     their severity buckets; the engineering lead's "send back" framing applies to
     description and types specifically, not all design judgment
     findings. Front Door findings render above Critical with framing
     that signals "fix this before deeper review is worth doing."
   - Group remaining findings by severity. Use the agents' own severity
     tags where present; otherwise classify by impact.
   - Preserve every file:line citation.
   - Drop findings that another agent's read invalidates (one flags, the
     other explains why it is not a concern in this context). This is the
     only legitimate drop: another agent disproved it.
   - **Demote (never drop) to Open questions** any finding that cannot be
     verified against the local diff plus the checked-out repo. A self-review
     sees only local state, so a finding reaching past the local diff plus
     repo is unproven here, not disproven, and demotes rather than blocks.
     (Typically you authored the change and can resolve the question
     directly.) Demote when a finding: (a) assumes state outside the diff and
     local repo (a cross-PR interaction, remote or deploy state, another open
     PR, anything unverifiable locally); (b) is a cross-service ripple whose
     in-repo consumer was NOT grep-confirmed (grep-confirm-or-demote: a grep
     miss demotes it, it does not disprove the ripple); or (c) is a
     provenance/intent question ("why does this exist?", "was this
     deliberate?"). This operationalizes the `code-review.md` False Positive
     Triage rule (a "callers may depend on X" claim with no named caller is
     speculative) as a demote, not a silent drop. The thirteen-agent fan-out
     produces more of this traffic than a six-agent one, so the demote path
     carries more here than it does at the project tier it came from.
   - **A reuse finding does not demote.** A step-2a finding names an in-repo
     incumbent at `file:line` produced by a grep that ran, so it is
     grep-confirmed by construction and belongs in Front Door. This exception
     is load-bearing: capability duplication is the one class whose whole
     value is asking whether the change should exist, and a version of it
     parked in Open questions gets answered with a local refactor instead of
     a deletion. Never let trigger (b) above swallow it.
   - `bot-review` findings go in their own "Advisory (cross-file)" subsection
     to preserve the COMMENT/NOTE/SUGGESTION distinction.
   - `module-cohesion-reviewer` findings render in "Open questions" (every
     finding is an author-facing question); a finding the agent tags SUGGESTION
     or COMMENT (an actionable cohesion fix such as a duplicated typed accessor)
     may instead surface in Suggestion so it is not skimmed past. Exception:
     a finding naming an existing owner for a capability this diff adds
     promotes to Front Door regardless of the tag the agent gave it.
   - **Reuse-search state always renders**, even when it found nothing. Put
     the negative on the `Agents:` line with its search terms. Never drop it
     as "no finding"; an omitted negative is how a lens silently stops
     running.
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
[Present ONLY when at least one send-back-quickly finding exists:
description/intent gate failure, type/model smell, large-refactor
methodology gap, or capability duplication. Omit entirely when empty.]

When this bucket is non-empty, the framing is "fix these before pushing or
before continuing deeper review." Type and intent issues ripple downstream;
fixing them often invalidates the downstream review.

- [intent | types | methodology | reuse] {file}:{line OR commit-msg ref} - {one-line summary}
  Source: {agent or pre-check name}
  {1-2 lines: what the smell is, what to do instead}
  [reuse findings only] Existing owner: {file}:{line} - {what it already does}
  [reuse findings only] Searched: {the literal grep terms used}

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
  Source: mx2-skeptic | module-cohesion-reviewer
- {file}:{line, or n/a if the claim has no local anchor} - {the demoted claim}
  Source: {agent name(s)}
  Why demoted: {outside local scope | consumer not grep-confirmed | provenance/intent}

### Positive
- {short callouts; cap at 3}
```

The `Agents:` line lists every agent's state: ran, skipped with reason, or
not-applicable. It also carries the step-2a reuse-search state: either
`reuse-search: searched <terms>, no existing owner found`, or
`reuse-search: 1 candidate owner (see Front Door)`, or
`reuse-search: skipped (no new capability in diff)`. Omit any severity
bucket with no entries. If all buckets are empty, report "No findings;
ready to push."

Severity rules:

- **Front Door**: the engineering lead's sent-back-quickly classes (description/intent,
  type/model smell, large-refactor methodology) plus capability duplication
  (step 2a). Render above Critical. Empty bucket is omitted entirely. The
  author should fix these before deeper review iteration. Pragma,
  boolean-param, and exception-design smells are inline-iterate findings;
  they stay in Critical/Important/Suggestion. A reuse finding is never
  downgraded to advisory, even when the agent that surfaced it is
  advisory-capped (see step 4).
- **Critical**: bugs, data loss risk, security exposure, behavior break.
- **Important**: patterns that will come back in CI or PR review.
- **Suggestion**: polish items the author can take or leave.
- **Advisory (cross-file)**: bot-review's consumer-invariant findings,
  severity-capped to COMMENT/NOTE/SUGGESTION.
- **Open questions**: two populations, both author-facing. Questions from
  `mx2-skeptic` and `module-cohesion-reviewer` (their native output), plus
  findings DEMOTED from a severity tier because they cannot be verified
  against the local diff plus repo (out-of-local-scope, consumer not
  grep-confirmed, or provenance/intent). Demoted, not dropped. A reuse
  finding never lands here; it belongs in Front Door.
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
- **Bounded fan-out.** Up to thirteen review agents with conditional dispatch.
  Maximum ten verdict-emitting specialists fire on a single diff (five of the
  six always-or-conditional agents from project /review, mx2-security-auditor
  included and the advisory module-cohesion-reviewer excluded,
  plus five personal-only conditional agents: devops, typescript, git-historian,
  pydantic, python-style). Three advisory-only agents fire conditionally and produce
  non-verdict output: `bot-review` (cross-file invariant questions, fires on
  public-surface changes), `mx2-skeptic` (adversarial questions, fires
  on M+ diffs), and `module-cohesion-reviewer` (cross-file cohesion and coupling
  questions, fires on Python-module changes).

## Roster Differentiation

Which agents are personal-only vs project-shared, and the informal promotion
criteria, are documented in [roster.md](roster.md) to inform future promotion
decisions (see CLAUDE.md "Lab-to-production for personal/project artifact
pairs").
