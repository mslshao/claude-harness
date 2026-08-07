# Specialist Dispatch

In `--mine` mode, the Review-Cache Reuse step (see
[dispatch-mechanics.md](dispatch-mechanics.md)) may have already
populated findings for the overlapping roster from a recent `/review` run on an
unchanged diff (bead `docr-xvnr`). When that happens, only `mx2-pr-precedent`
dispatches here; the reused findings flow into Synthesis as if the agents had
just returned. The triggers below still apply on a cache MISS or in default mode.

## Provenance Classification

Each specialist's findings carry a default provenance classification (`speed-amplified`
or `bot-surfaced`) consumed by `synthesis.md` step 5d. The classification determines
whether the posted inline comment opens with an attribution prefix (bot-surfaced) or
uses Michael's voice directly (speed-amplified). The full classifier table lives in
`synthesis.md` step 5d; specialists do NOT classify their own findings, the synthesizer
does it from source + verification-path signals. Override at synthesis time when a
specific finding's verification path contradicts the default.

## Dispatch Triggers

When pre-loaded context is available, triggers are pre-evaluated in
`<pr-context section="dispatch-signals">`. Use the boolean signals directly:

| Signal | Triggers |
|--------|----------|
| `has_try_except_raise: true` OR `structural_risk_size: true` | Structural risks |
| `has_security_patterns: true` OR `security_files` non-empty | Security & compliance |
| `has_test_files: true` | Test quality |
| `has_terraform: true` | Infrastructure review |
| `has_ci_workflow_change: true` | CI/CD workflow security review |
| `has_typescript_files: true` | TypeScript review |
| `structural_risk_size: true` AND `has_file_history: true` | Git history regression |
| `structural_risk_size: true` AND `has_pattern_precedent: true` | Prior PR precedent |
| `has_observability_signal: true` | Observability instrumentation review |
| `changes_public_surface: true` OR `has_pattern_precedent: true` | Cross-file blast-radius |
| `structural_risk_size: true` | Adversarial dissent |
| `has_pydantic_settings_signal: true` | Pydantic Settings review |
| `adds_capability: true` | Active Reuse-Search (orchestrator step, ALL sizes; section below, not a specialist) |

The descriptions below document what each trigger checks (for reference and
fallback mode). When dispatch-signals are available, use the booleans above.

## Active Reuse-Search (orchestrator-owned, runs BEFORE the fan-out)

Fires when `adds_capability` (SKILL.md Dispatch Signals). Runs at ALL sizes,
including XS/S renders that dispatch no specialists; it is an orchestrator
step, not a specialist. The question is not "is the new code correct?" but
"should this code exist at all, or does something in the monorepo already
own this capability?" That is `architecture.md` Reuse Across Boundaries,
specifically its "If no boundary exists, build one; don't duplicate" bullet.
Cross-author review is where this matters most: there is no bead or design
context to fall back on, so if the orchestrator does not run the search,
nobody does (PR #10807, 2026-07-24: both reuse gaps surfaced only on a
second pass, after the author was asked the why-not-how question).

**Run the search yourself; do NOT delegate it to the specialists.** The
per-agent self-enrichment instruction already tells every agent to grep for
related code paths, and on the <service> `/metadata/refresh` duplication
(2026-07-24, docr-5obvn) it did not fire even with
`module-cohesion-reviewer` dispatched. An instruction that has been tried
and missed is not a mechanism; the search has to be deterministic and owned
here.

Derive 2-4 search terms per introduced capability from the CAPABILITY, not
from the new code's naming (the author's names are precisely what will not
match the incumbent's):
- the external endpoint, host, or binary being reached
  (`api.anthropic.com`, `superset`, `soffice`)
- the shared-library symbol that would wrap it (`init_llm`,
  `RedshiftCalls`, `DocumentStore`)
- the domain verb plus object (`publish refresh`, `convert docx`)

Use BARE symbols as terms, never `class X` or `def X` anchors: the
incumbent is often re-exported from a package `__init__.py` or declared in
a differently-named submodule (`mx2.redshift_calls.RedshiftCalls` lives in
`calls.py`), so a declaration-anchored term misses the call sites that
prove the capability is already owned.

From the PR worktree root, run BOTH passes, source first (documentation
hits otherwise crowd out the declaration):

```
# pass 1, source: what already implements this
git grep -n -i -E "<term1>|<term2>" -- 'src/python/mx2/**/*.py' \
  'src/typescript/mx2/**/*.ts' 'libs/**/*.py' \
  ':(exclude)**/*_test.py' ':(exclude)**/test_*.py' \
  ':(exclude)**/conftest.py' | head -25

# pass 2, docs: which service CLAIMS to own it (often the clearest statement)
git grep -n -i -E "<term1>|<term2>" -- '**/*.md' | head -15
```

Test files are excluded by git pathspec, NOT by piping through `grep -v`:
`git grep` emits `path:line:content`, so a content-matching filter drops
real source lines whose code happens to contain the filter text
(`grep -vE 'test_'` discards `litify_docs__Latest_Version__c`, exactly the
identifier shape a capability search targets).

Record ONE of two outcomes per capability; both are mandatory output, and
silence is not an allowed third state (the outcome renders on the header
`reuse-search:` line, output-formats.md):

- **Candidate owner found**: name it as `file:line`, state what it already
  does, and carry it into synthesis step 7b as a capability-duplication
  Front Door finding. Pass the incumbent into the `mx2-code-reviewer` and
  `module-cohesion-reviewer` prompts as evidence, appending: "Does an
  existing endpoint, service, or shared-library symbol already own this
  capability? Answer with a `file:line` for the incumbent, or state that
  you searched and found none. Do NOT answer by proposing a cleaner local
  structure for the new code; extracting it into a tidier module is not an
  answer to whether it should exist."
- **No owner found**: record the literal terms tried, rendered as
  `reuse-search: searched <terms>, no existing owner found`. A search
  whose terms are not stated is indistinguishable from a search that never
  ran.

Do not resolve the finding. Whether to delete the new code, call the
incumbent, or add a boundary to the incumbent is the author's call; this
step exists to make sure the question is asked BEFORE the diff gets
refined into a better version of the wrong thing.

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

**CI/CD workflow security review** → `mx2-devops-build-deploy`
Trigger: `has_ci_workflow_change: true` (changed files match `.github/workflows/*.ya?ml`). Use the CI-workflow prompt variant (see the `mx2-devops-build-deploy` prompt below), NOT the Terraform prompt.

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

**Adversarial dissent** → `mx2-skeptic`
Trigger: `structural_risk_size: true` (M+ PR: > 200 lines OR > 5 files). Surfaces naive-but-unasked questions about scope, assumptions, and risk that other specialists miss because they are focused on their own domain. Advisory only; severity vocabulary limited to QUESTION (never BLOCKING/CRITICAL/COMMENT). Findings appear in their own subsection of the synthesis report under "Open questions", not folded into the main severity buckets. Designed as a safety net for fragmented attention (multi-window operational reality).

Different from `bot-review` (cross-file consumer-invariant articulation; both are advisory but skeptic asks "what did you not consider" while bot-review asks "what does X consumer assume that breaks"). Different from `mx2-code-reviewer` (structural verdicts) and `mx2-silent-failure-hunter` (error-propagation verdicts) which produce judgments rather than questions.

**Module cohesion & coupling** → `module-cohesion-reviewer`
Trigger: `has_python_module_change: true` (subject to the standard M+ specialist size gate; not dispatched on XS/S). Cross-file cohesion and coupling lens: which concern a module owns, name-vs-contents, production vs test-only helper separation, a hand-rolled query duplicating a typed accessor a shared module already exposes, cross-service reach-in past a published boundary, and dependency-direction violations. Resolves to the personal-tier variant (shadows the project agent), whose seam defers to the other specialists in this roster by name. Advisory only; every finding is an author-facing question, severity vocabulary limited to QUESTION/SUGGESTION/COMMENT (never BLOCKING/CRITICAL). Different from `mx2-code-reviewer` (within-file SRP), `bot-review` (consumer-invariant blast-radius across call sites), and `mx2-pydantic-reviewer` (Settings patterns): this agent owns the module-and-import-graph layer those do not. If skipped, note "module-cohesion-reviewer: skipped (no Python module changes)" in the output header. When `adds_capability` fired, append the Active Reuse-Search results and its cross-service reuse question (section above) to this agent's prompt AND to `mx2-code-reviewer`'s.

**Inline IaC analysis** → `checkov` (tool call, not subagent)
Trigger: `has_terraform: true` AND (at least one net-new `*.tf` file exists OR `has_new_tf_resource`: a modified `.tf` added a `resource`/`module`/`data` block). The range-overlap filter (checkov.md) scopes modified-file findings to the added block, so pre-existing resources are not re-flagged.
Fires on ALL sizes (including XS), unlike specialist dispatch. It's a bounded tool
call (5-10s per file), so the cost-vs-signal ratio works even on small PRs.
Runs alongside the specialist agents (same parallel batch). See [checkov.md](checkov.md)
for invocation, suppression list, severity mapping, and integration into synthesis.
Findings flow through pr-intel's standard FINDING format and severity triage.
Skip on rebase-artifact PRs (all tf files are stale per Merge Base Freshness).

**NOT to dispatch** (specialist agents above, NOT checkov): XS/S PRs, test-only PRs, generated-code-only PRs, and rebase-artifact PRs (where Merge Base Freshness shows the diff is entirely stale content).

**Non-code diffs still get a review, just a different lens.** For a docs-only, rules-file, markdown, or config-only diff the code-focused specialist fan-out has no surface, so "no dispatch" does NOT mean "no review." The review reduces to three checks the fan-out cannot do: (1) **claim accuracy**: verify every cited example, file path, dependency, and command in the added text actually exists AND demonstrates the stated pattern (read the referenced file, grep the dep, run the command); a doc that names a canonical example is only correct if that example uses the pattern the doc prescribes. (2) **placement and consistency**: the addition sits under the right heading and does not contradict or silently duplicate a nearby line. (3) **AC vs ticket**. This IS the review for such a PR; do not substitute a padded code fan-out and do not skip. (PR #10669, 2026-07-17: a 1-line `python-testing.md` bullet whose review was entirely (1), verifying `sf_sync_client_test.py` used the `responses` fixture param and asserted on `responses.calls`.)

**Attributing off-roster findings in a non-code review.** These reviews often lean on an agent outside the specialist roster, most often `claude-code-guide` for Claude Code skill/hook/memory/frontmatter semantics. Attribute its findings like any tool: open the inline lede with `My `claude-code-guide` consult flagged ...` or `Flagged by `claude-code-guide`: ...` (both pass `check_review_attribution.py`; a natural-language lede such as "Checked the docs:" does not, and gets rewritten at /post-review time). Set the provenance-classifier `source` to the agent actually consulted, never a specialist that never ran. Findings from cross-artifact synthesis (comparing the diff against sibling files) use the `Cross-file analysis surfaced ...` lede. (PR #10970, 2026-07-24: three claude-code-guide / synthesis ledes drafted in natural language had to be rewritten at the /post-review attribution check.)

## Context Optimization

Do NOT send the full diff to every specialist. Filter by relevance:
- **All specialists**: exclude files flagged `already_on_main` by Merge Base Freshness
- **Security auditor**: only auth/PII/audit/document files + PR description
- **Test reviewer**: only test files + the source files they test
- **mx2-code-reviewer**: only implementation files (non-test, non-config)
- **mx2-silent-failure-hunter**: only files containing try/except/raise patterns
- **mx2-devops-build-deploy**: only Terraform/HCL/terragrunt files, infra directory changes, or `.github/workflows/*.ya?ml`
- **mx2-git-historian**: line ranges of changed files only (the agent runs git log/blame for context)
- **mx2-pr-precedent**: file path list only (the agent queries gh API server-side; no diff content needed)
- **observability-reviewer**: only files matching the observability sub-rules above (exception-class diffs, metric-emission hunks, observability `*.tf` files, enum/Literal additions) PLUS any sibling `*.tf` in the same service directory PLUS the PR description (for alert references)
- **bot-review**: changed public-symbol declarations only (lines matching the `changes_public_surface` regex from `SKILL.md` Dispatch Signals) PLUS the full file path list. Mirrors `mx2-pr-precedent`'s "file path list only" filter shape, NOT the full diff. The agent fetches consumers itself via Grep/Read on the worktree; sending the full diff saturates context on the M+ PRs the agent is most useful for.
- **mx2-skeptic**: PR description + file path list + summarized diff overview (first 50 lines of each file's diff). The agent asks questions about intent and assumptions; it does not need exhaustive code context. Sending the full diff saturates without improving question quality. Include the Jira ticket AC if available.
- **mx2-pydantic-reviewer**: only files matching the pydantic_settings sub-rules above (Settings class diffs, os.environ patterns, *settings* / *config* filename diffs) PLUS sibling settings files in the same service directory (to detect duplicate field declarations or cross-service `AppSettings` import attempts).
- **module-cohesion-reviewer**: changed implementation `.py` files (non-test) PLUS the full file path list of the changeset. The agent reads whole modules and greps the worktree itself to confirm cohesion and duplication, so it needs the path map more than the full diff. Exclude test-only files unless production/test-only mixing is the concern.

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
isort, autoflake, SonarCloud, Datadog SAST/SCA/Secrets, GitHub Copilot). Weight your
attention toward design judgment those tools cannot catch, but report every real finding
you have. If one is style, formatting, or type-level, tag it `CI-catchable: <tool>` and
report it anyway; the synthesis pass drops the ones CI is genuinely covering on these
lines and keeps the rest. Do not withhold a finding because a tool might catch it.

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

READ-ONLY: You are a reviewer. Report findings; never modify the working tree, the
branch, or the PR, even to demonstrate a fix. Fixes go through a separate fix pass the
orchestrator verifies. (Covers resumed/re-purposed sessions where tool-roster
enforcement can lapse; a 2026-07 pilot had a resumed reviewer apply its own findings.)
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

Surface findings in the engineering lead's priority order (Code Review Guide for Humans,
an internal Confluence page):
1. Description / intent (already checked at Phase 0; surface only if you see
   intent drift between description and diff)
2. Data models / types (Type System Subversion check: untyped dicts as
   record stand-ins, `dict[str, Any]`, model representing multiple
   independent concepts, None-Abuse on collections)
3. Complexity / organization / naming (call-site test, SRP)
4. Boolean / behavior-switching parameters
5. Tests (delegate to test-quality-reviewer if dispatched; flag missing
   coverage on new branches)
6. Correctness via tests, NOT in-head execution (if tests missing, flag the
   gap; do not trace control flow to convince yourself it works)
7. Static analyzer findings (SonarCloud + Datadog code analysis pre-checks ride on this; Sentry static patterns ride in mx2-code-reviewer)
8. Pragma / override justification (Pragma Justification check)
9. Exception design (raise the condition, not the handling)
10. Large-refactor methodology (was the methodology stated?)

Tag findings as `front_door: true` when they match item 2 (type/model
smells) or item 10 (large-refactor methodology gap). Front Door findings
shift the review recommendation to Comment with back-to-author framing
(synthesis.md step 7b and Recommendation Table).

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

PROBE: module-level initialization paths for new external dependencies.
When a PR introduces a new client/SDK/secret-fetch at module scope (e.g.,
`_client = SomeSDK(...)` or `_settings = get_secret_value(...)` at the top
of a Lambda handler module), check explicitly:
- Is the init wrapped in try/except, or does a cold-start failure of the
  external dependency kill every invocation on the worker until the container
  recycles?
- Is there a no-op fallback for "dependency unavailable, keep processing,"
  or is the dependency a hard requirement?
- Does the init path run BEFORE any feature-flag / `_should_enable_X` check,
  such that the flag can't disable the failure surface it gates?

PROBE: new external-dependency calls inside retry loops. When a PR adds a
retry/fallback loop around an external call, check whether OTHER new external
calls in the same function (e.g., prompt fetch, config fetch, credential
refresh) are inside or outside the retry. A common defect shape is "retry
covers the OpenAI call but not the prompt fetch that happens one line above
the loop" - the new dependency's failure mode bypasses the safety net the PR
believes it has.

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

PROBE: symmetric-path coverage. When the source contains two or more
structurally identical methods (e.g., parallel LLM call sites with the same
retry shape, parallel handlers for related entity types, parallel mapping
functions), and a test exists for one path, check whether the symmetric test
exists for the other. Asymmetric coverage is a common defect shape: one
function gets a retry-exhaustion test because the author hit the failure
once, the symmetric function ships untested. Cite both function names and
whether each has coverage.

PROBE: positive-assertion of new wiring. When the PR's headline change is
"wire X into Y" (new tracer, new client, new instrumentation), check whether
ANY test asserts the wiring was exercised. A test that passes whether or
not the new `with X(...)` block is present does not verify the change. The
no-op fixture pattern (NoOpTracerProvider, null clients) correctly runs the
production code path but does NOT, by itself, prove the wiring is reached;
that requires an explicit `verify(mock, called).method(...)` or equivalent
assertion at the wiring boundary.

Source files under test (diff):
<filtered source diff>

Test files (diff):
<filtered test diff>
```

### mx2-devops-build-deploy
```
<scope preamble>

When the changed files are `.github/workflows/*.ya?ml` (`has_ci_workflow_change`), review for WORKFLOW SECURITY, not Terraform: untrusted-trigger / secret-exposure surface (which events run with secrets; is untrusted PR-head checkout possible on them), `author_association`/actor gating, `GITHUB_TOKEN` permission scope and `id-token` usage, `concurrency` semantics, unpinned `uses:` SHAs on secret-bearing steps, and operational foot-guns (missing `timeout-minutes`). Skip the Terraform/HCL checks that follow.

Review infrastructure changes in PR #<number> for Terraform/HCL correctness.
Check for: missing variable pass-through to child modules, duplicate HCL keys
(silently keeps last value), missing environment configs (CD but no beta/prod),
EventBridge subscription completeness, and terragrunt dependency injection gaps.
Resolve every hardcoded external reference in the diff (endpoint/DNS URL, ARN,
account ID, secret ARN, API gateway ID) to the account/env it actually targets:
grep infra for per-env existence (infra/{service}/{env}) and the account IDs in
the env terragrunt files, and use Datadog span aws_account/env tags where reachable.
Confirm it matches the env being deployed. A non-prod env pointing at a prod
endpoint, or a per-env module inheriting a shared-account default it cannot reach
cross-account, is BLOCKING. Sweep sibling fields of the same kind (every
*_dns_name, every *_secret_arn) before concluding, not just the one that caught
your eye.
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

Retrieve everything via `gh api` / `gh pr list` / `gh pr view` (server-side); you have
no worktree and need no local checkout. Do NOT run `gh pr checkout`, `git checkout`, or
`git branch` (create or delete): a local branch op violates the read-only mandate and
trips the destructive-command guard (observed PR #10714, 2026-07-20: the agent
`gh pr checkout`'d then `git branch -D`'d the PR branch and triggered a security warning).

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

PROBE: reference-implementation comparison. When the PR introduces a new
instrumentation pattern (LLM span wiring, tracer init, metric emission for a
service that previously had none), locate the closest sibling implementation
in the codebase via Grep on the SDK/library imports and compare the call shape
end-to-end. Specifically check: are context manager handles captured and
populated (`as handle:` then `handle.set_attributes(...)`), is
`suppress_instrumentation()` wrapping SDK calls that would otherwise be
double-captured by ddtrace + the new tracer, are attribute keys consistent
with the reference impl. Divergence from the reference pattern is a
DIFF-VISIBLE finding worth surfacing even when the diff alone looks correct.

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

### mx2-skeptic
```
<scope preamble>

Surface naive, dumb, or obvious-but-unasked questions about PR #<number>. You
are NOT a code reviewer; you do not verify correctness or flag bugs. Other
specialists own those verdicts. Your job is to ask the questions a fresh pair
of eyes would ask that the author or other reviewers might have skipped past
because they were too close to the problem.

Examples of question shapes you should produce (not exhaustive):
- "Does the runtime, platform, framework, or an existing service already provide this,
  so the mechanism this PR builds should not exist at all?" (necessity / goal-fit; e.g.
  a hand-rolled client that duplicates a Lambda extension, sidecar, managed feature, or
  published boundary). This is the HIGHEST-VALUE question you can ask: interrogate
  whether a net-new mechanism needs to exist BEFORE anyone reviews how it is built, and
  anchor on the PR's stated goal to ask whether the diff is the simplest path to it.
  When it applies, prioritize it above the shapes below.
- "Did anyone confirm that X is actually true?" (assumption surfacing)
- "What happens if Y occurs and we're not handling it here?" (edge case)
- "Why is this in this PR rather than a follow-up?" (scope)
- "Is the bead/Jira AC actually satisfied, or just partially?" (intent vs implementation)
- "Has anyone checked whether this regresses the case from MX2-NNNN?" (history)

Constraints:
- Severity vocabulary is QUESTION only. Do NOT emit BLOCKING, CRITICAL,
  DISCUSSION, MINOR, NOTE, COMMENT, SUGGESTION, or any verdict tag.
- Report every real question you have, ordered highest-blast-radius first. Do
  NOT drop a genuine question to hit a count: synthesis filters and ranks in a
  separate pass downstream, and a suppressed question is lost, not deferred.
  Soft ceiling ~10; past that, keep ranking rather than truncating. This is a
  recall instruction, not license to pad: the "do not manufacture concerns"
  rule below still binds.
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


### module-cohesion-reviewer
```
<scope preamble>

Review PR #<number> for cross-file module cohesion and coupling. You judge the
module-and-import-graph layer, NOT within-file structure. Emit author-facing
questions, never verdicts.

Yours: which concern a module owns, name-vs-contents, catch-all modules, production
and test-only helpers sharing an import graph, a hand-rolled query duplicating a typed
accessor a shared module already exposes, cross-service reach-in past a published
boundary, dependency-direction violations.

Not yours (other specialists in this run own them; do not restate): within-file SRP
and call-site readability (`mx2-code-reviewer`), Settings and config
(`mx2-pydantic-reviewer`), PII and secrets (`mx2-security-auditor`), test
meaningfulness (`test-quality-reviewer`), error propagation
(`mx2-silent-failure-hunter`), consumer-invariant blast-radius (`bot-review`).
Anything a single-file linter (Sonar, Copilot, pylint, mypy) catches is not yours.

Verify before asking: read the full module, grep for the accessor you claim is
duplicated, read the import you claim reaches across a boundary. A question you could
answer by reading is one you should have answered.

Constraints:
- Severity vocabulary: QUESTION, SUGGESTION, COMMENT only. Never BLOCKING/CRITICAL.
- Each finding cites the rule it rests on (code-style Naming & Organization,
  `exemplars.md`, or `architecture.md`) and what you read or grepped.
- Do NOT repeat findings from the specialists above or from existing PR comments
  (provided below for dedup). If your finding is a sharper version of one of theirs,
  drop it.

Existing specialist findings and PR comments (for dedup):
<list of findings from prior specialists in this pr-intel run + PR comments>

PR context: <body>

Files changed (filtered to implementation .py) + full path list:
<filtered diff + path map>
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
