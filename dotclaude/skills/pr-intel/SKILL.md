---
name: pr-intel
description: Actionable PR intelligence briefing with specialist-backed analysis and draft review comments ready to post. Use when the user asks to review a PR in any phrasing - "review a PR", "analyze PR", "PR intel", "look at PR #123", "check this PR", "thoughts on #456", "can you go through this PR" - or needs a structured briefing before reviewing. Also triggers for self-review with --mine flag when user says "review my PR", "check my changes before I submit".
argument-hint: "[pr-number] [--mine] [--quick] [--once] [free-text review context]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "WebFetch", "Skill"]
---

# PR Intel

Produce an actionable PR intelligence briefing for a human reviewer. Gather context,
dispatch specialist agents for deep analysis, synthesize findings, and present draft
review comments the reviewer can directly use on GitHub.

## Reviewer Context

Raw invocation: `/pr-intel $ARGUMENTS`

Parse the raw invocation above to extract:
1. **PR number**: first numeric token (e.g., `7640`), or a GitHub PR URL
2. **Mode flags**:
   - **neither (default)**: full analysis, one-shot briefing. The dead multi-phase `@claude` verify loop is retired (PR #9888 removed the self-hosted bot). An unverified falsifiable or cross-system assertion is contained as an UNVERIFIED-ASSERTION finding (synthesis.md "Unverified-Assertion Containment + Cross-System Investigation"), never a posted bot question.
   - **`--once`**: identical to default (both are one-shot now). Retained as an explicit alias for callers that previously used it to opt out of the post-and-wait loop.
   - **`--mine`** (self-review): one-shot. An unverified falsifiable or cross-system claim surfaces as a pre-submission item to check (Verdict "Needs work first"), not a bot question.
   - **`--quick`** (triage only): one-shot, no specialist dispatch, no loop.
3. **Reviewer context**: everything else is free-text instructions from the reviewer.
   Use this to steer your analysis focus, specialist prompts, and output framing.
   It takes priority over default analysis behavior.

If no PR number is found, auto-detect from the current branch:
```bash
gh pr view --json number --jq '.number'
```
If that also fails, stop and ask the user for a PR number.

## Reading Paths (conditional, by mode and title-prefix size)

The PR title's automated size prefix (XS/S/M/L/XL/2XL/3XL, stamped by Graphite/GitHub tooling) is the CANONICAL size for routing below; it is the same complexity signal a human reviewer sees. Infer from additions+deletions ONLY when no prefix exists (same fallback as Size Classification). Do not substitute independent complexity judgment for the prefix (2026-06-09 directive, bd docr-pnx9).

This SKILL.md is always read in full. Sub-files load per the table; skipping a "Skip (sanctioned)" file on a matching run is correct behavior, not a shortcut.

| Mode / size | Read | Skip (sanctioned) |
|---|---|---|
| every run | [output-formats.md](output-formats.md) (the output contract; never skippable, any mode, any size) | |
| `--quick` | nothing further | all other sub-files |
| default / `--once` / `--mine`, XS-S | [prior-reviews.md](prior-reviews.md) (if prior rounds exist), [compliance-checks.md](compliance-checks.md) (if Jira ticket or CI failures), [provenance-classification.md](provenance-classification.md), [bot-reactions.md](bot-reactions.md) (default mode only) | [dispatch.md](dispatch.md) (no specialist dispatch at XS/S, EXCEPT `has_terraform` with a net-new `.tf` OR `has_new_tf_resource` (a modified `.tf` that adds a `resource`/`module`/`data` block) OR `has_ci_workflow_change` (a changed `.github/workflows/*.ya?ml`): dispatch `mx2-devops-build-deploy` even at XS/S, since IaC/CI-workflow blast radius is decoupled from line count AND from whether the file is net-new; mirrors the Checkov net-new-tf-or-new-resource trigger and the size-independent `changes_public_surface` rule; and EXCEPT `adds_capability`: load dispatch.md for its orchestrator-owned Active Reuse-Search step, which runs even at XS/S with no specialist dispatch implied, since capability duplication is decoupled from line count and one motivating miss, PR #10944, was 21 lines), [synthesis.md](synthesis.md), [verification.md](verification.md), [diagrams.md](diagrams.md) |
| default / `--once` / `--mine`, M+ | all of the above plus [dispatch.md](dispatch.md), [dispatch-mechanics.md](dispatch-mechanics.md), [synthesis.md](synthesis.md), [static-analyzers.md](static-analyzers.md) | [verification.md](verification.md) at M when no BLOCKING-class findings |
| L+ | plus [verification.md](verification.md) | |
| trigger-conditional, any size | [checkov.md](checkov.md) (`has_terraform` + net-new tf), [diagrams.md](diagrams.md) (M+ AND `multi_service`), [design-doc.md](design-doc.md) (Confluence link in body), [context.md](context.md) (migration/series triggers), [freshness.md](freshness.md) / [grounding.md](grounding.md) when those checks need their exact commands | |

The Stop-hook backstop (`stop-validate-pr-intel.sh`) still validates every render, so a misjudged reading path degrades to a caught retry, not a silent miss. Mandatory PHASES (provenance classification, bot reactions) are unaffected by reading paths; only reference depth varies.

**Flagging an unverifiable cross-system or repo-HEAD claim is a first-class outcome of
the initial pass, not a fallback.** Neither PR size nor "I found no specific unverified
claim" gates it. When a finding's verdict would rest on a falsifiable cross-system or
repo-wide-state assertion you have not actually traced (a mirror-table column existing,
"all callers migrated", a stated end-to-end effect such as "returns 404", a frozen or
high-blast-radius module touch per architecture.md), do NOT state it as a confident
verdict: run the local investigation (synthesis.md Cross-System Investigation for the
mirror-column class) and surface an UNVERIFIED-ASSERTION finding if it does not resolve.
Surface it during the original synthesis, including at XS-S where dispatch and
synthesis.md are otherwise skipped, so the verdict reflects the honest result. Default
toward investigating when in doubt; an XS prefix lowers neither the investigation bar nor
the verification bar. The dead @claude-bot question is retired; `@claude review once`
(managed Code Review) is the manual out-of-band escalation for inconclusive cases.

**Empirical execution beats precedent-citation on disputed test behavior.** When the
author and the reviewer disagree about what a test DOES (an assertion "doesn't work",
a mock "doesn't intercept", a fixture "breaks under xdist"), do not re-cite precedent
a second time: dispatch a worktree agent to check out the PR tip, restore or write the
disputed test, and RUN it (`pants test <target>`), iterating on the failure output up
to 3 attempts. The author's observation is usually real even when their diagnosis is
wrong, and only execution distinguishes the two; the deliverable is a verified patch
plus the actual root cause, which ends the loop in one round (PR #9725, 2026-07-16:
three assertion-deletion rounds ended by one empirical run that found a repo-global
moto fixture shadowing `responses.calls`).

## Data Gathering

**Pre-flight checklist.** Before Phase 0, confirm each of these was executed or explicitly deemed not applicable. Skipping a conditional step (e.g., Jira ticket hydration when no ticket is referenced) is fine; skipping a conditional step when the trigger IS present is the failure mode this checklist exists to prevent.

- [ ] PR metadata fetched
- [ ] Run self-registered in the inject log (Skill-tool invocations; see Self-register the run)
- [ ] Diff fetched (skip for `--quick`)
- [ ] PR head ref fetched locally (for worktree)
- [ ] Merge Base Freshness checked
- [ ] **Prior review memories loaded** via `bd memories pr-<number>` (see [prior-reviews.md](prior-reviews.md))
- [ ] **DynamoDB prior reviews loaded** (skipped if SSO not active) via `pr_review_state.list_reviews_for_pr` (see [prior-reviews.md](prior-reviews.md))
- [ ] **Jira ticket hydrated** if `MX2-NNNNN` or similar appears in PR body
- [ ] **Design doc hydrated** if any `<company>.atlassian.net/wiki/` URL appears in PR body (see lesson #11 in `reviewer-discipline.md`)
- [ ] Inline review comments fetched if prior reviews exist (required for dedup)
- [ ] PR Series context checked if Jira ticket was found
- [ ] Service Context extracted from CLAUDE.md or README

Narrative details for each step follow below.

Fetch all PR data using these commands. Run them **in parallel** for speed:

```bash
# Metadata (always needed)
gh pr view <number> --json title,author,baseRefName,headRefName,headRefOid,state,isDraft,labels,body,commits,reviews,comments,files,statusCheckRollup,url,additions,deletions,changedFiles,reviewDecision

# Diff (skip for --quick mode)
gh pr diff <number>

# Repo name (needed for inline comments)
gh repo view --json nameWithOwner --jq '.nameWithOwner'

# Pre-fetch PR head ref (ensures commit is locally reachable for worktree creation)
# headRefName comes from the PR metadata above
git fetch origin <headRefName>
```

**Sanitize the fetched title before any render.** Graphite/GitHub PR titles routinely
carry U+2014 (PR #10818: `... rewrite [U+2014] summary/derived-artifact ...`), and the
title is echoed verbatim into the `## PR #<N>: <title>` header, so the em-dash gate in
output-formats.md cannot catch it by re-reading authored prose. Replace it at the source
once, and every downstream render inherits the clean string:

```bash
gh pr view <number> --json title --jq '.title' | sed 's/\xe2\x80\x94/-/g'
```

The same applies to any upstream string quoted into the briefing (bot comment text,
author reply text, Jira summary, commit messageHeadline): sanitize on echo, never
paste through.

**Self-register the run** (required, once per invocation, alongside the metadata fetch):
append this run to the inject log so `nudge-handrolled-review.sh` knows /pr-intel ran for
this PR in this session. The UserPromptSubmit hook only logs runs the user typed; a
Skill-tool invocation must log itself or later posts to this PR get a false nudge
(three occurrences, 2026-07-15):

```bash
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"${CLAUDE_CODE_SESSION_ID}\",\"pr\":\"<PR_NUMBER>\",\"prompt_preview\":\"skill-invoked /pr-intel <PR_NUMBER>\"}" >> ~/.claude/logs/pr-intel-contract-inject.jsonl
```

### Prior Reviews

Before any other analysis, check if this PR has been reviewed in a prior session
across two channels in parallel:

1. `bd memories pr-<number>` for terminal-side review memories that `/post-review`
   writes on every successful post.
2. The DynamoDB `pr-review` table (cross-modality state shared with the Slack bot).

**Without this step, dedup against prior rounds runs only against in-conversation
comments; multi-day re-reviews silently re-raise points already posted.** The
delta-focused diff (`git diff <prior_head_sha> <headRefOid>`) sent to specialists
is also the single highest-value signal on re-reviews; it cannot be computed
without the prior `head_sha`.

For the `bd memories` key format, DynamoDB SSO fallback (the table is in the dev
account, the heredoc needs `AWS_PROFILE=dev AWS_DEFAULT_REGION=us-east-1` and
`uv run --with boto3 --with 'pydantic>=2'`), revision-delta computation, prior-
review dedup, briefing header format, and default-recommendation-shift rules,
see [prior-reviews.md](prior-reviews.md).

If both channels fail, proceed as first-round (see `correction:skill:pr-intel-first-round`
in beads memory).

### Merge Base Freshness & Ghost Diffs

After fetching the PR head ref, run two local git checks (always run):

1. **Merge Base Freshness**: files in the PR's changeset whose content is
   identical to current main (already shipped via a sibling PR). Store
   `merge_base_freshness` (`stale_files`, `net_new_files`, `is_stale`); Size
   Classification, Dispatch Signals, and inline comments all use net-new only.
   If ALL files are already on main, short-circuit: the branch needs a rebase.
2. **Ghost Diffs (reverse freshness)**: files in the 2-dot `git diff` but ABSENT
   from the PR's file list. GitHub's three-dot merge base hides these; they are
   usually a rebase conflict silently reverting a recently-merged change.
   **High-consequence: surface as BLOCKING** with the recently-merged PR
   reference. Cannot receive inline comments; report in the review body.

If `git fetch` failed earlier, skip both and treat all files as net-new. For the
exact `git diff`/`git log` commands, the `merge_base_freshness` field shapes, and
the downstream-effects list, see [freshness.md](freshness.md).

After metadata is loaded, fetch inline review comments (in addition to the issue-level
comments already pulled via `gh pr view --json comments`). Bot commenters split across
both endpoints: Copilot and Sentry leave inline review comments; SonarQube, PR Metrics,
Vercel, Mergify, Datadog leave issue-level comments. **Always fetch both** - reporting
only one is incomplete. This fetch is also required for dedup during synthesis; if
skipped, the dedup step in synthesis.md cannot run and bot comment pile-on will occur.

Use `gh api` (the GitHub MCP was rejected 2026-04-14 due to auth brittleness):

```bash
gh api /repos/<owner>/<repo>/pulls/<number>/comments \
  --jq '[.[] | {id: .id, user: .user.login, path: .path, line: .line, body: .body, in_reply_to_id: .in_reply_to_id}]'
```

This returns a flat list. Treat each entry as an independent comment for dedup purposes.
The `is_outdated` flag is unavailable from this endpoint; treat all comments as current.
Group by `in_reply_to_id` if thread structure is needed (root = null, replies = parent id).

If `gh api` fails, note the failure explicitly and proceed with synthesis; flag in the
output that bot dedup could not run.

### Jira Ticket Hydration

Scan the PR body for `MX2-\d+` references (or other known project prefixes). If
found, hydrate the ticket using the procedure in
[`../enrich/sources.md`](../enrich/sources.md) Section 1 (Jira Tickets), in parallel
with other post-metadata fetches.

**Without Jira hydration, the AC Compliance Check below cannot run, and the
empty-ticket-blocking rule (template-boilerplate detection) silently passes.**

Store the same fields named in `enrich/sources.md`: summary, status, assignee,
priority, `description` AND `customfield_11220` (both render in the Jira UI as
of ~2026-04-30; per project convention non-SF tickets put content in
`description` while SF-specific tickets mirror to `customfield_11220` - check
whichever has content), comments, and `issuelinks`. Plus, for review use:
- **Acceptance criteria** (may live in the description body, or in a dedicated AC field)
- **Issue type** (Story, Bug, Task; informs what "correct" looks like)

If no ticket reference is found in the PR body, note this in Phase 0 as a
description quality gap (same as today) but skip hydration. If the MCP call fails,
note the failure and continue without ticket context. Do not block on Jira
availability.

### Design Doc Hydration & Spec Compliance Check

After metadata is loaded, scan the PR body for Confluence links matching
`<company>.atlassian.net/wiki/`. If found, hydrate the page body and comments (via
`mcp__atlassian__getConfluencePage` + inline/footer comment calls) in parallel
with Jira hydration, then compare the implementation against the spec: trace each
behavioral specification in the diff, flag deviations (response shapes, parameters,
routing, unhandled edge cases), and surface unresolved design-doc comments as open
threads. Deviations are not automatically bugs; the goal is to let the reviewer ask
"was this intentional?" This is the class of issue code-only review (all specialist
agents) cannot detect. Produces a **Design Doc Compliance** output section; runs in
default and `--mine`, skipped for `--quick`. If no Confluence link is found, skip
silently. For the exact MCP calls (cloudId, page-ID extraction), the stored fields,
and the deviation taxonomy, see [design-doc.md](design-doc.md).

### PR Context (series, service, migration)

After Jira hydration, run three context-gathering checks before specialist dispatch:

1. **PR Series Context**: when a Jira ticket was hydrated and sibling PRs exist,
   classify new exports as referenced or unreferenced across the series.
2. **Service Context**: scan for service-level CLAUDE.md / README in the changed
   paths and surface a 3-5 line orientation block.
3. **Migration State** (permanent as of 2026-07-02; 2026-07-01 audit: revisit
   never ran, check in active use): when the PR touches an in-flight migration,
   load operational state from `bd memories <migration-name>` before forming
   review concerns.

**Without these, sibling-PR awareness is missing (orphan-export false positives
when a peer PR consumes the export), service-level orientation is missing
(reviewers waste effort relearning the codebase), and migration state is missing
(review concerns about "sequencing risk" or "missing fallback" fire on
already-resolved cutovers).**

For trigger detection, tiered fetch logic, the bead-memories migration query
patterns, downstream effects on specialist preamble / synthesis / Draft Review
Summary, and the rationale for the authoritative-state principle, see
[context.md](context.md).

If no Jira ticket was hydrated, no migration signal is detected, and no
service-level docs are found, all three checks degrade silently (note absence,
do not block).

### Size Classification

Extract size from the PR title prefix (XS, S, M, L, XL, 2XL, 3XL). If no prefix,
infer from additions + deletions: <=500 = S, <=1500 = M, else XL.

Size drives two behaviors:
1. **Diff strategy**: XL+ PRs skip the full diff; fetch individual files as needed
   with `gh pr diff <number> -- <path>`.
2. **Verification depth**: L+ PRs run a challenge/consult loop on findings before
   output. See the Verification section below.

### Dispatch Signals

Compute these booleans from the diff for specialist dispatch:
- **has_try_except_raise**: added lines contain `try:`, `except `, or `raise `
- **has_security_patterns**: added lines contain `SecretStr`, `logger.`, `.info(`, `.error(`, `.exception(`
- **security_files**: changed file paths matching `auth|security|token|jwt|permission|rbac|document|upload|download|access|audit|secret|credential|patient`
- **has_test_files**: changed files matching `*_test.py|test_*|conftest.py`
- **has_terraform**: changed files matching `*.tf` or `*.hcl`
- **has_new_tf_resource**: `has_terraform` is true AND an added line declares a new top-level Terraform block: `^\+(resource|module|data)\s+"`. Set by a MODIFIED `.tf` that appends a block, not only a net-new file. IaC blast radius (a new secret, a new plan-time `data` read against a shared multi-env stack) is decoupled from line count AND from whether the file is new, so this drives `mx2-devops-build-deploy` dispatch at any size, exactly like a net-new `.tf`. (PR #10554: a +18 modified `salesforce.tf` adding one `module` block gated a shared dev+prod secrets stack; the net-new-file trigger alone would have skipped the dispatch.)
- **has_ci_workflow_change**: changed files matching `.github/workflows/*.ya?ml`, added OR modified. CI/CD workflow blast radius (secret exposure via `${{ secrets.* }}`, untrusted-actor trigger gating, `permissions:`/`id-token` scope, supply-chain via unpinned `uses:`) is decoupled from line count, exactly like `has_terraform`, so this drives `mx2-devops-build-deploy` dispatch at any size. (PR #10836: an XS +58 net-new `claude.yml` gated `ANTHROPIC_API_KEY` behind an author-association trigger guard and a write-capable OIDC app token; the XS-no-dispatch default would have skipped the devops lens on a security-sensitive file.)
- **has_typescript_files**: changed files matching `*.ts|*.tsx|*.mts|*.cts` AND outside `src/gen-typescript/` (generated TS is excluded; review the generator instead)
- **structural_risk_size**: diff > 200 lines OR > 5 files changed
- **has_python_module_change**: changed files include a `src/python/**/*.py` that is added, deleted, or renamed, OR whose added lines declare a net-new top-level `def `/`class ` (column-0 on a `+` line). Drives `module-cohesion-reviewer` dispatch (cross-file cohesion lens). A changeset whose only Python changes are test files (`*_test.py|test_*|conftest.py`) does not set it unless production/test-only mixing is the concern.
- **has_file_history**: count of merged PRs in last 180 days touching ANY file in the changeset (computed via `gh pr list --state merged --search "<file>" --limit 5` per top-3 changed files, cap at 3 per file). Boolean = aggregate count >= 3.
- **has_pattern_precedent**: at least one file in changeset has >= 2 prior merged PRs in last 180 days AND the diff adds new public symbols. Symbol detection: added lines matching `^\+\s*(export |def |class |interface |type )`. Reuses the same `gh pr list` calls as `has_file_history`.
- **changes_public_surface**: added/removed/modified lines declare a public symbol. Detection: lines matching `^[+-]\s*(def |async def |class |interface |type |export )`, OR `^[+-]\s*[A-Z_]+\s*[:=]` (constants, enum values), OR `^[+-]\s*\w+:\s*\w+` inside files matching `*Settings*` or Pydantic model classes (schema/Settings field changes). Excludes private symbols (leading underscore in Python, non-exported in TS). Drives `bot-review` dispatch (cross-file blast-radius lens). Size is a poor proxy for blast radius; an XS PR that changes a public type signature has higher downstream impact than an M PR refactoring internals.
- **adds_capability**: added lines introduce a NEW outbound capability rather than extending an existing one. Any of: an HTTP call (`requests.`, `httpx.`, `urllib.request`, `aiohttp`, `fetch(`); a subprocess invocation (`subprocess.`, `os.system`, `shell=True`); a queue or topic publish (`publish(`, `send_message(`, `put_events(`); a new route declaration (`@app.`, `@router.`, `APIRouter(`); a new CLI entry point (`argparse`, `click.`, a new `__main__` block); a system-package or image install (`apt-get install`, a Dockerfile `RUN` adding a binary); or a new raw SQL or warehouse query string. Test-only files alone do not set it. Compute at ALL sizes, XS included: it drives the orchestrator-owned Active Reuse-Search in [dispatch.md](dispatch.md), not a specialist dispatch, so the XS/S no-dispatch default does not apply (PR #10944, one of the motivating misses, was 21 lines). Pattern set is duplicated from the `adds_capability` row in `~/.claude/skills/review/SKILL.md` step 2, the canonical copy per docr-z3qw4; if the two drift, reconcile toward the /review copy.
- **multi_service**: changed files (net-new only) span 2+ distinct top-level service directories. Service directory = first path segment after `src/python/mx2/`, `src/typescript/mx2/`, or `infra/`. Files outside these prefixes (root scripts, generated code) do not contribute. Drives the optional Sequence Diagram briefing section for M+ PRs. See [diagrams.md](diagrams.md).
- **spot_check_eligible**: ALL of (a) size in {L, XL, 2XL, 3XL}, (b) net-new file count >= 10 AND median per-file diff lines <= 25 (mechanical-pattern proxy: many small uniform edits), (c) PR description contains a methodology statement detectable by regex (`script:|ran (the )?(command|script|tool)|applied (rule|codemod|transform)|using (yapf|ruff|isort|black|sed|jscodeshift|comby|grit)|migration script|codemod`). Drives the spot-check mode under Specialist Dispatch (the engineering lead's Code Review Guide #11: "focus your review on the methodology... spot-check a few instances"). Conservative-by-default: when any of (a)/(b)/(c) is uncertain, set to false (full-diff dispatch is the safe default; spot-check trades coverage for speed and that trade only makes sense when the mechanical pattern is unambiguous).
- **has_observability_signal**, **has_pydantic_settings_signal**: defined in [dispatch.md](dispatch.md); compute them when dispatch.md loads (M+ PRs).

## Phase 0: Description Quality Check

Before dispatching specialists, evaluate the PR description:
- Is it present and non-boilerplate?
- Does it explain intent (why), not just content (what)?
- Is there a linked Jira ticket or meaningful context?

Boilerplate detection patterns (any of these alone is sufficient to
fail Phase 0):
- Description IS the ticket title (no additional context)
- Only template skeleton remains ("As a [type of user]", "Given that...",
  unfilled checklist headers)
- Lists WHAT changed without WHY: leads with verbs like "Adds X / Implements
  Y / Refactors Z" without any "because", "to fix", "needed for", or other
  rationale connective
- Single sentence < 30 chars
- Empty body with only `Jira issue link: MX2-XXXX`

If the description is absent or inadequate, **short-circuit**: produce a
brief "send it back" briefing instead of full specialist dispatch. The
framing is the engineering lead's #1 explicitly: "don't waste your time reviewing
without context." Skip CI status check, AC compliance, SonarCloud
pre-check, and specialist dispatch entirely. The output should:

- Set Action to **Comment** (NOT Approve with Comments; the PR is not
  ready for that signal)
- Open the Draft Review Summary with one sentence naming what's missing
  (intent, ticket link, rationale) and asking the author to fill it in
  before the next review pass
- List what a good description should contain for this PR based on the
  diff scope (3-5 bullets: the components touched, the user-facing
  effect, the rationale, any operational risk)
- Set Front Door count to 1 (description) in the Review Recommendation
  header, even though no other front-door findings were detected
- Skip the Front Door section's findings table; the briefing IS the
  short-circuit, so the Draft Review Summary carries the action

The short-circuit avoids the cost of specialist dispatch on a PR that the
author should fix before further review. Re-running `/pr-intel` after the
author updates the description is the right next step.

### CI Status + AC Compliance Checks

After Phase 0 description quality, run three pre-dispatch checks:

1. **CI Status Check**: parse `statusCheckRollup` from PR metadata; if failures
   exist, fetch the last 3 merged PRs to classify each as PR-specific regression
   vs global flake.
2. **AC Compliance Check** (when Jira ticket is available): trace each
   acceptance criterion against the diff, flag deviations, and run the
   empty-ticket-blocking detector.
3. **Static Analyzer Pre-Check** (always; specific sub-tools depend on what
   posted on the PR): query each available static analyzer for findings
   scoped to the PR. Three sub-tools today: SonarCloud (MCP available),
   Datadog code analysis (MCP via `search_pr_insights`), Sentry (no live
   bot on MX2 PRs; static patterns ride in `mx2-code-reviewer` instead).
   The engineering lead's Code Review Guide #7 explicitly says review these findings
   and call out anything that should be blocking.

**Without compliance-checks.md, CI failures are reported without distinguishing
PR-specific regressions from global flakes (over-escalation of approvals over
unrelated breakage), and AC compliance silently passes on tickets with only
template boilerplate (the empty-ticket-blocking rule never fires).** Both
failure modes have shipped before; the rules are load-bearing.

For the failing-check classification logic (test/build vs code-quality gate),
the boilerplate-detection patterns ("As a [type of user]", "Given that..."),
the deviation taxonomy, and the mode-irrespective always-runs invariant, see
[compliance-checks.md](compliance-checks.md).

### Static Analyzer Pre-Check

Three static analyzers post on MX2 PRs (or could): SonarCloud
(`mcp__sonarqube__*`), Datadog code analysis (`mcp__datadog__search_pr_insights`),
and Sentry (no live bot on MX2 PRs as of 2026-05-28; static patterns ride in
`mx2-code-reviewer`). Surface their findings alongside specialist results so the
reviewer sees the engineering lead's #7 in one place rather than scattered across bot comments.

**Always runs** (mode-irrespective, like AC Compliance); `--quick` skips only the
SonarCloud leak-period diff filter. Static-analyzer findings are **inline-iterate,
not Front Door class**: a finding can still be BLOCKING in its own severity bucket,
which routes through the regular Recommendation Table (BLOCKING -> Request Changes),
not the Front Door track. The **shared dedup rule** (an analyzer finding overlapping
a specialist finding on the same file+line keeps the specialist finding and appends
the analyzer rule code as an attribution line) runs in synthesis Step 2.

For the per-tool fetch paths and process, the SonarCloud leak-period scope filter
and severity-by-metric mapping (rule violations vs coverage-flag-only vs gate
conditions), the catalog-walk secondary, the Datadog `search_pr_insights` process,
the Sentry no-bot rationale and future trigger conditions, and the dated calibration
(`feedback:pr-review:sonarqube-leak-period-scope` 2026-05-18, PR 9274 coverage-gate
phrasing 2026-05-21, `config:sonarcloud-mcp` 2026-05-21), see
[static-analyzers.md](static-analyzers.md).

## Specialist Dispatch

For worktree isolation (the one shared worktree per invocation, the `--mine`
skip, setup/teardown bash, and the git-fetch-failed BRANCH WARNING fallback),
Spot-Check Mode for large mechanical refactors (deterministic 3-file sample,
the mandatory briefing-addition template, what stays full-diff, the
one-step-more-conservative recommendation), and `--mine` Review-Cache Reuse
(diff-identity HIT/MISS keying, the reuse roster, the always-re-dispatch
`mx2-pr-precedent` rule, bead `docr-xvnr`), see
[dispatch-mechanics.md](dispatch-mechanics.md).

### Dispatch

Evaluate dispatch triggers using the computed signals. Launch all triggered
specialists **in parallel** via the Agent tool. This is NOT optional for default mode.

**Active reuse-search precedes the fan-out.** When `adds_capability` fired, run the orchestrator-owned Active Reuse-Search in [dispatch.md](dispatch.md) BEFORE building specialist prompts, so its candidate-owner results ride into the `mx2-code-reviewer` and `module-cohesion-reviewer` prompts as grounding evidence. It runs at every size (including XS/S renders that dispatch no specialists), and its outcome always renders on the header `reuse-search:` line per output-formats.md.

**CRITICAL: All specialist agents MUST be foreground calls.** Do NOT use
`run_in_background: true`. Send all Agent calls in a single message (parallel
foreground), wait for ALL results, THEN begin synthesis. If you start writing
output while agents are still running, the results arrive as async notifications
and get appended as awkward "noted, agent returned" postscripts instead of being
integrated into the briefing. The user sees a finished report followed by
trailing acknowledgments. This is broken output.

For dispatch triggers and specialist prompt templates, see [dispatch.md](dispatch.md).

### Inline IaC Analysis (Checkov)

When `has_terraform: true` AND mode is `default` or `--mine`, run a Checkov pass on
net-new `*.tf` files in parallel with specialist dispatch. This is an inline tool call
(not a subagent), bounded to 5-10 seconds per file. Findings flow through synthesis
alongside specialist results. See [checkov.md](checkov.md) for invocation, suppression
list, and severity mapping.

For `--quick` mode: skip specialist dispatch entirely.

## Synthesis

After specialist results return, synthesize into the final briefing. For the full
synthesis process, consequence assessment, design review surfaces, review recommendation
logic, and verifiability map, see [synthesis.md](synthesis.md). Before writing ANY
output, read [output-formats.md](output-formats.md) for the active mode's template.
The template is the structural contract: populate each section in order, do not
free-form narrate findings.

### Optional: Sequence Diagram

When size is M or larger AND `multi_service: true` AND mode is `default`, generate a
Mermaid sequence diagram for the briefing per [diagrams.md](diagrams.md). The section
is emitted only when the diff produces an unambiguous call-path summary; the generator
emits a sentinel (`SEQUENCE_UNCLEAR` / `SEQUENCE_TOO_LARGE`) when grounding fails, and
the section is omitted in that case rather than fabricating relationships.

## Provenance Classification

After Synthesis produces the finalized Draft Inline Comments list (and any
substantive Draft Review Summary bullets that warrant classification), batch-dispatch
the `provenance-classifier` agent to classify each finding as `speed-amplified`
(reviewer would have caught from careful single-file diff reading; the bot got
there faster) or `bot-surfaced` (verification path required live-state checks,
multi-page document synthesis, or cross-file blast-radius analysis the reviewer
could not have sustained at speed).

**This is a mandatory top-level phase, not an optional step.** The dispatch
happens REGARDLESS of size (XS/S/M/L/XL), regardless of specialist dispatch
outcome, and regardless of finding count. Zero findings is still a valid input;
the agent returns an empty classification array. The classifications drive the
`Provenance:` and `Decision count:` lines in the Review Recommendation header
(enforced by `stop-validate-pr-intel.sh`) and the per-finding `Classification:`
line in each Draft Inline Comment briefing context.

For the full dispatch contract (input schema, agent prompt construction,
classification application, low-confidence handling, source-tagging discipline
upstream), see [provenance-classification.md](provenance-classification.md).

**Skip rule**: `--quick` mode skips this phase entirely (no inline comments to
classify; the quick template has no Provenance line). `--mine` mode runs the
phase normally; the classification still informs the briefing-context audit
even when no comments will be posted.

## Bot Reactions

After Provenance Classification, build the bot reactions list from the dedup
decisions made during Synthesis Step 2. Bot comments that overlapped with
synthesizer findings get classified as either `+1` (bot finding is correct)
or `-1` (bot finding is a false positive), independent of whether the
reviewer also keeps an inline comment for additional context or rebuttal.

**This is a mandatory top-level phase, not an optional step.** Reactions are
how the reviewer signals bot accuracy WITHOUT duplicating bot prose in their
own comments; thumbs-down on a false positive is how the reviewer discourages
that bot's noise patterns over time. The reactions list is consumed by
`/post-review` Step 3.5, which posts the reactions via `gh api .../reactions
-X POST -f content=<+1|-1>`.

For the full 5-category decision tree, reaction-vs-comment orthogonality,
endpoint distinction (inline review comments vs issue-level conversation
comments), and the handoff schema for /post-review, see
[bot-reactions.md](bot-reactions.md).

**Skip rule**: `--quick` and `--mine` modes skip this phase (no review is
being posted; no reactions to apply). Default mode always runs it; empty
reactions list is valid output when no bot comments overlapped.

## Verification

After synthesis, run a verification pass scaled to PR size to catch false positives.
For the verification process, see [verification.md](verification.md).
Skip for XS/S PRs.

## Output

The output MUST follow the structural template in [output-formats.md](output-formats.md) for the
active mode (default, --once, --mine, --quick). This is not optional and does not depend on PR size,
specialist dispatch, or number of findings.

<!-- summary-from: output-formats.md key: required-sections -->
A default-mode render must contain, in order: the `## PR #<N>: <title>` header block, Scope, Review Recommendation (metadata lines only), a fenced Draft Review Summary, Draft Inline Comments (or an explicit "None"), and a Verdict. This holds for every size and even for an Approve with zero findings.
<!-- /summary-from -->

The template is the output contract. Do not narrate findings in free-form prose.

**Anchor check before emitting (mandatory, every mode with inline comments).** Every
drafted inline anchor must sit inside the PR's net three-dot diff hunks or GitHub 422s
it, and `/post-review` catches it only after the briefing is rendered and previewed:

```bash
python3 ~/.claude/skills/pr-intel/verify-anchors.py --base <baseRefName> --head <headRefOid> <path:line> ...
```

On `NOT_IN_HUNK`, apply the grounding.md remedy in PREFERENCE ORDER: re-anchor to the
nearest net-new line that names the behavior (the script prints it as `nearest:`) and
make the comment text self-locating ("on line 222 just below this hunk"); only when no
net-new line triggers the finding at all, move it to the Draft Review Summary. A
body-folded finding has no resolvable thread, so it is materially likelier to be skipped:
on #10818 the author actioned every inline in the same review and silently skipped the
one body-folded item, costing an extra round. Do not emit an
anchor the script rejected. This is the mechanical enforcement of grounding.md's
anchor-grounding rule, which lives in a trigger-conditional sub-file that XS-S runs skip.

## Unverified-Assertion Containment (default mode)

Default mode is a one-shot briefing; the multi-phase `@claude` verify loop is retired
(PR #9888 removed the self-hosted bot, which answered targeted questions; the managed
Claude Code Review replacement is a full-PR reviewer, not a Q&A bot). A finding whose
verdict would rest on an unverified falsifiable or cross-system assertion is contained as
an UNVERIFIED-ASSERTION finding rather than a posted bot question: run the local
investigation (synthesis.md "Unverified-Assertion Containment + Cross-System
Investigation"; for the mirror-column class the named Cross-System Investigation recipe),
and let the result drive the verdict (default/--once Comment, --mine "Needs work first",
--quick "Warrants careful review" when it does not resolve). `@claude review once`
(managed Code Review) is the manual out-of-band escalation when local investigation is
inconclusive; it is operator discretion and never gates the first-round verdict.

## Section Conditionality

Omit ANY section that would say "nothing to note." Always-present sections:
Scope, Review Recommendation, Verdict, Draft Review Summary.

Exception: when `mx2-security-auditor` was dispatched, include positive confirmation
even if clean: "Reviewed for: PII exposure, auth/authz, audit trails, encryption. No concerns identified."

## Principles

- **Actionable output.** Every finding should help the reviewer take a specific action.
- **High signal, no noise.** Only flag things with evidence. False positives erode trust.
- **Two audiences per finding.** Briefing text (reviewer) and draft comment (PR author).
- **Review the why, not just the what.** A PR is a claim that a change achieves a goal; the review's first job is to test that claim, not only to check that the surface code is well-built. Anchor on the goal (the description's why, the ticket intent), then ask whether the implementation achieves it AND whether it is the simplest path given what the deployment platform, runtime, framework, and existing services already provide. A clean specialist fan-out that never asks "does this mechanism need to exist at all?" will approve code that should not exist. Operationalized by the Goal-Fit & Mechanism Necessity design-review surface (synthesis.md) and the `mx2-skeptic` necessity question (dispatch.md); do not let surface-level polish substitute for the goal-fit question.
- **Depth by default, speed on request.** Specialist dispatch is default. `--quick` for triage.
- **Don't duplicate existing tools.** No `pants` runs. Posting is delegated to `/post-review`, never reimplemented. The briefing itself is never auto-posted, and `/pr-intel` performs no posting of its own; all posting is `/post-review` after your explicit OK.
- **The engineering lead's priority order is the human-reviewer standard.** The engineering lead's
  [Code Review Guide for Humans](https://<company>.atlassian.net/wiki/spaces/PPET/pages/5684789249)
  (Mar 2026) defines the priority order: description, then types, then
  complexity / naming, then boolean / behavior-switching params, then tests,
  then correctness-via-tests (NOT in-head execution), then static analyzers,
  then pragma review, then exception design, then large-refactor methodology.
  Phase 0 (description quality) implements item 1; the specialist dispatch
  route (`mx2-code-reviewer` Design Judgment Checks) implements items 2-10.
  When a Phase 0 short-circuit fires, the briefing stops at "send it back"
  without further specialist dispatch, matching the engineering lead's "don't waste your
  time reviewing without context."

## Additional Resources

- For specialist dispatch triggers and prompt templates, see [dispatch.md](dispatch.md)
- For inline Checkov IaC analysis (Terraform PRs), see [checkov.md](checkov.md)
- For Mermaid sequence diagram generation (M+ cross-service PRs), see [diagrams.md](diagrams.md)
- For synthesis process, consequence assessment, design surfaces, and verifiability map, see [synthesis.md](synthesis.md)
- For size-gated verification process, see [verification.md](verification.md)
- For output format templates for each mode, see [output-formats.md](output-formats.md)
- For grounding rules and evidence categories, see [grounding.md](grounding.md)

