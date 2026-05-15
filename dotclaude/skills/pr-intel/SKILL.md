---
name: pr-intel
description: Actionable PR intelligence briefing with specialist-backed analysis and draft review comments ready to post. Use when the user asks to review a PR in any phrasing - "review a PR", "analyze PR", "PR intel", "look at PR #123", "check this PR", "thoughts on #456", "can you go through this PR" - or needs a structured briefing before reviewing. Also triggers for self-review with --mine flag when user says "review my PR", "check my changes before I submit".
argument-hint: "[pr-number] [--mine] [--quick] [free-text review context]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "WebFetch"]
---

# PR Intel

Produce an actionable PR intelligence briefing for a human reviewer. Gather context,
dispatch specialist agents for deep analysis, synthesize findings, and present draft
review comments the reviewer can directly use on GitHub.

## Reviewer Context

Raw invocation: `/pr-intel $ARGUMENTS`

Parse the raw invocation above to extract:
1. **PR number**: first numeric token (e.g., `7640`), or a GitHub PR URL
2. **Mode flags**: `--mine` (self-review), `--quick` (triage only), or neither (default)
3. **Reviewer context**: everything else is free-text instructions from the reviewer.
   Use this to steer your analysis focus, specialist prompts, and output framing.
   It takes priority over default analysis behavior.

If no PR number is found, auto-detect from the current branch:
```bash
gh pr view --json number --jq '.number'
```
If that also fails, stop and ask the user for a PR number.

## Data Gathering

**Pre-flight checklist.** Before Phase 0, confirm each of these was executed or explicitly deemed not applicable. Skipping a conditional step (e.g., Jira ticket hydration when no ticket is referenced) is fine; skipping a conditional step when the trigger IS present is the failure mode this checklist exists to prevent.

- [ ] PR metadata fetched
- [ ] Diff fetched (skip for `--quick`)
- [ ] PR head ref fetched locally (for worktree)
- [ ] Merge Base Freshness checked
- [ ] **Prior review memories loaded** via `bd memories pr-<number>` (see [prior-reviews.md](prior-reviews.md))
- [ ] **DynamoDB prior reviews loaded** (skipped if SSO not active) via `pr_review_state.list_reviews_for_pr` (see [prior-reviews.md](prior-reviews.md))
- [ ] **Jira ticket hydrated** if `MX2-NNNNN` or similar appears in PR body
- [ ] **Design doc hydrated** if any `<internal-confluence> URL appears in PR body (see lesson #11 in `reviewer-discipline.md`)
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

### Merge Base Freshness

After fetching the PR head ref, check whether any files in the PR's changeset have
content identical to current main (changes already shipped via a sibling PR that
merged first). This is a local git operation and always runs.

1. Get files that actually differ from main at the PR's HEAD:
   ```bash
   git diff origin/main <headRefOid> --name-only
   ```
2. Compare against the PR's full file list (from the `files` field in PR metadata).
3. Files present in the PR's file list but **absent** from the 2-dot diff output are
   **already on main**: their content at the PR HEAD is identical to current main.
4. Store as `merge_base_freshness`:
   - `stale_files`: file paths whose content matches main
   - `net_new_files`: file paths with actual differences
   - `is_stale`: true if any stale files detected
5. Downstream effects:
   - **Size Classification**: use net-new additions/deletions, not raw PR totals
   - **Dispatch Signals**: compute from net-new files only; exclude stale files
     from the filtered diffs sent to specialists
   - **Inline comments**: never target stale files (enforced in grounding.md)
   - **Scope**: show breakdown: "Files: 21 (17 net-new, 4 already on main)"

If all files are already on main (pure rebase artifact), short-circuit:
"This PR's diff is entirely content already on main. The branch needs a rebase."

### Ghost Diffs (Reverse Freshness)

Also check the reverse: files in the 2-dot diff that are **absent** from the PR's
file list. These are "ghost diffs" that GitHub's three-dot merge base hides from the
PR diff view. They typically appear when a PR is squashed/rebased and a rebase
conflict resolution accidentally reverts a recently-merged change.

1. Files present in the 2-dot `git diff` output but **absent** from the PR's `files`
   metadata are ghost diffs.
2. For each ghost file, check `git log origin/main -- <path>` (last 5 commits) to
   identify what recently-merged PR touched it. This reveals whether the ghost diff
   is an accidental revert of a specific PR.
3. Ghost diffs are **high-consequence findings** (potential silent reverts of merged
   work). Surface them as BLOCKING in the review summary with the recently-merged PR
   reference.
4. Ghost diffs cannot receive inline comments (not in GitHub's diff view). Include
   findings in the review body with file:line references.
5. Show in Scope: "Ghost diffs (not in GitHub diff): N files - see review body"

This check is the highest-value add for squashed PRs, where inter-revision visibility
is lost and rebase conflict reverts become invisible.

If `git fetch` failed earlier, skip this check and treat all files as net-new.

If `git fetch` fails (network error, fork PR with restricted access), note the failure
and skip worktree creation during specialist dispatch (see Branch Safety below).

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

### Design Doc Hydration

After metadata is loaded, scan the PR body for Confluence links matching the pattern
`<internal-confluence> (URLs or Confluence short links). If found, extract the
page ID and fetch the page content AND comments **in parallel** with Jira hydration:

```
mcp__atlassian__getConfluencePage
  cloudId: <your-atlassian-cloud-id>
  pageId: <extracted page ID>
  contentFormat: markdown

mcp__atlassian__getConfluencePageInlineComments
  cloudId: <your-atlassian-cloud-id>
  pageId: <extracted page ID>
  contentFormat: markdown

mcp__atlassian__getConfluencePageFooterComments
  cloudId: <your-atlassian-cloud-id>
  pageId: <extracted page ID>
  contentFormat: markdown
```

Extract and store:
- **Design spec**: the page body (parameters, logic steps, response shapes, limitations)
- **Inline comments**: each with author, resolution status, and the text they annotate
- **Footer comments**: each with author and body
- **Unresolved comment count**: total open inline + footer comments from non-author users

**Page ID extraction**: Confluence URLs contain the page ID as a numeric path segment
(e.g., `.../pages/5799772177/...`). Short links (`/wiki/x/<encoded>`) can be passed
directly as `pageId` to the MCP.

If no Confluence link is found in the PR body, skip silently. If the MCP call fails,
note the failure and continue without design doc context.

**Downstream effects:**
- **Spec Compliance Check**: runs after design doc is loaded (see below)
- **Open Threads**: unresolved design doc comments surface as open threads in the output,
  separate from PR inline comment threads
- **Specialist preamble**: append design spec context so specialists can flag deviations

### Spec Compliance Check (when design doc is available)

When a Confluence design page was successfully hydrated, compare the PR's
implementation against the design spec. This complements AC Compliance (Jira)
with a deeper comparison against the full design document.

For each behavioral specification in the design doc:
1. **Trace it in the diff.** Can you identify the code that implements this spec?
2. **Check for deviations.** Common divergences:
   - Response shapes differ (field names, values, status codes)
   - Parameters differ (naming, optionality, semantics)
   - Routing or branching logic differs from described flow
   - Edge cases described in the spec are not handled (or handled differently)
3. **Surface unresolved design comments.** If the design page has open comments
   from reviewers (especially tech leads), these represent design-level feedback
   that may not have been addressed in the implementation. Flag them as open
   threads regardless of whether they map to code findings.

Deviations are not automatically bugs. The spec may have been updated after the
code, or the author may have intentionally diverged. The goal is to surface the
gap so the reviewer can ask "was this intentional?" This is the class of issue
that code-only review (including all specialist agents) cannot detect.

This check produces a **Design Doc Compliance** section in the output (see
output-formats.md). It runs in default and --mine modes. Skip for --quick.

### PR Context (series, service, migration)

After Jira hydration, run three context-gathering checks before specialist dispatch:

1. **PR Series Context**: when a Jira ticket was hydrated and sibling PRs exist,
   classify new exports as referenced or unreferenced across the series.
2. **Service Context**: scan for service-level CLAUDE.md / README in the changed
   paths and surface a 3-5 line orientation block.
3. **Migration State** (provisional, added 2026-04-27): when the PR touches an
   in-flight migration, load operational state from `bd memories <migration-name>`
   before forming review concerns.

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
- **has_docker**: changed files matching `Dockerfile|docker|BUILD`
- **has_typescript_files**: changed files matching `*.ts|*.tsx|*.mts|*.cts` AND outside `src/gen-typescript/` (generated TS is excluded; review the generator instead)
- **structural_risk_size**: diff > 200 lines OR > 5 files changed
- **has_file_history**: count of merged PRs in last 180 days touching ANY file in the changeset (computed via `gh pr list --state merged --search "<file>" --limit 5` per top-3 changed files, cap at 3 per file). Boolean = aggregate count >= 3.
- **has_pattern_precedent**: at least one file in changeset has >= 2 prior merged PRs in last 180 days AND the diff adds new public symbols. Symbol detection: added lines matching `^\+\s*(export |def |class |interface |type )`. Reuses the same `gh pr list` calls as `has_file_history`.
- **changes_public_surface**: added/removed/modified lines declare a public symbol. Detection: lines matching `^[+-]\s*(def |async def |class |interface |type |export )`, OR `^[+-]\s*[A-Z_]+\s*[:=]` (constants, enum values), OR `^[+-]\s*\w+:\s*\w+` inside files matching `*Settings*` or Pydantic model classes (schema/Settings field changes). Excludes private symbols (leading underscore in Python, non-exported in TS). Drives `bot-review` dispatch (cross-file blast-radius lens). Size is a poor proxy for blast radius; an XS PR that changes a public type signature has higher downstream impact than an M PR refactoring internals.
- **multi_service**: changed files (net-new only) span 2+ distinct top-level service directories. Service directory = first path segment after `src/python/mx2/`, `src/typescript/mx2/`, or `infra/`. Files outside these prefixes (root scripts, generated code) do not contribute. Drives the optional Sequence Diagram briefing section for M+ PRs. See [diagrams.md](diagrams.md).

## Phase 0: Description Quality Check

Before dispatching specialists, evaluate the PR description:
- Is it present and non-boilerplate?
- Does it explain intent (why), not just content (what)?
- Is there a linked Jira ticket or meaningful context?

If the description is absent or inadequate, short-circuit: produce a brief
"send it back" recommendation instead of full specialist dispatch. Include what
a good description should contain for this PR based on the diff scope.

### CI Status + AC Compliance Checks

After Phase 0 description quality, run three pre-dispatch checks:

1. **CI Status Check**: parse `statusCheckRollup` from PR metadata; if failures
   exist, fetch the last 3 merged PRs to classify each as PR-specific regression
   vs global flake.
2. **AC Compliance Check** (when Jira ticket is available): trace each
   acceptance criterion against the diff, flag deviations, and run the
   empty-ticket-blocking detector.
3. **SonarCloud Rule Pre-Check** (always, but especially `--mine` mode): load
   the SonarCloud rule library and walk known detectors against the diff so the
   gate doesn't bounce post-push.

**Without compliance-checks.md, CI failures are reported without distinguishing
PR-specific regressions from global flakes (over-escalation of approvals over
unrelated breakage), and AC compliance silently passes on tickets with only
template boilerplate (the empty-ticket-blocking rule never fires).** Both
failure modes have shipped before; the rules are load-bearing.

For the failing-check classification logic (test/build vs code-quality gate),
the boilerplate-detection patterns ("As a [type of user]", "Given that..."),
the deviation taxonomy, and the mode-irrespective always-runs invariant, see
[compliance-checks.md](compliance-checks.md).

### SonarCloud Rule Pre-Check

The MX2 SonarCloud project (`mx2_docr`) is private; its issue API requires
`SONAR_TOKEN`, which is only available to CI. That asymmetry means
SonarCloud quality-gate failures land AFTER push, costing a force-push cycle
per fix. The pre-check shifts known-rule detection left.

**Process**:

1. Load [~/.claude/projects/-workspaces-main/memory/sonarcloud-rules.md](../../projects/-workspaces-main/memory/sonarcloud-rules.md).
2. For every rule with a `**Detector**` block in the catalog, run the detector
   against the PR diff (`git diff origin/main -- '*.py'` is the canonical
   scope; substitute `--mine` base for stacks).
3. Walk the catalog's "Pre-push self-check" checklist against the diff.
4. Surface findings inline in the pr-intel output under a "SonarCloud risk"
   sub-section of the synthesis. Treat catalog-rule hits as `🚨 critical`
   when in `--mine` mode (would block the gate) and as `⚠️ advisory` on
   others' PRs (the bot will catch it; flag for the author).

**Growth rule**: when a NEW rule fires on a real PR (own or reviewed), the
follow-up bead is "add `python:S<code>` to sonarcloud-rules.md with a
concrete `**Detector**` block." Preventive entries (rules not yet seen on
MX2) are allowed when the SonarSource rule definition is public AND the
detector is concrete enough to be verifiable without re-fetching docs;
mark each entry as `**Preventive**` vs `**Observed**` so provenance stays
auditable and stale entries can be triaged later.

**Token-gap escape hatch**: if the catalog scan turns up nothing but the
gate still fails post-push, ask the user to paste the issue detail from
`https://sonarcloud.io/project/issues?id=mx2_docr&pullRequest=<N>`. One
paste resolves it; guessing burns force-push cycles. Add the new rule to
the catalog as the resolution step.

## Specialist Dispatch

### Branch Safety (Worktree Isolation)

Each pr-intel invocation creates its own temporary git worktree so it never
touches the user's working tree. This allows multiple reviews to run in
parallel without checkout conflicts or disrupting the user's terminal.

**Exception: `--mine` mode.** When reviewing your own PR, the user is already
on the PR branch. Skip worktree creation entirely and use `/workspaces/main`
(the main repo) as the code root for all specialist prompts. The user's
working tree already has the code they want reviewed.

Do NOT use `isolation: "worktree"` on specialist Agent calls. That creates
per-agent worktrees which causes git lock contention. Instead, create ONE
worktree for the entire pr-intel invocation and pass the path to all
specialists.

**Before dispatching specialists (default and --quick modes only):**
1. Create a temporary worktree at the PR's HEAD commit:
   ```bash
   WORKTREE_DIR=$(mktemp -d /tmp/pr-intel-XXXXXX)
   git worktree add --detach "$WORKTREE_DIR" <headRefOid> 2>&1
   ```
2. Verify: `git -C "$WORKTREE_DIR" log -1 --oneline` should show `<headRefOid short>`.
3. Save `$WORKTREE_DIR` - all specialist prompts must include it as the
   code root for Read/Grep/Glob operations (see Dispatch below).

**After ALL specialists return and synthesis is complete:**
4. Remove the worktree:
   ```bash
   git worktree remove "$WORKTREE_DIR" --force 2>&1
   ```
5. If removal fails (e.g., locked), fall back to:
   ```bash
   rm -rf "$WORKTREE_DIR" && git worktree prune
   ```

The user's working tree is never modified. No branch save/restore needed.

If `git fetch` failed in Data Gathering, skip worktree creation and add a
BRANCH WARNING to each specialist prompt instead:
"WARNING: Could not fetch PR branch. Your Read/Grep/Glob results may show code
from a different branch. Rely primarily on the inline diff for analysis."

### Dispatch

Evaluate dispatch triggers using the computed signals. Launch all triggered
specialists **in parallel** via the Agent tool. This is NOT optional for default mode.

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

## Verification

After synthesis, run a verification pass scaled to PR size to catch false positives.
For the verification process, see [verification.md](verification.md).
Skip for XS/S PRs.

## Output

The output MUST follow the structural template in [output-formats.md](output-formats.md) for the
active mode (default, --mine, --quick). This is not optional and does not depend on PR size,
specialist dispatch, or number of findings. Even an "Approve" with zero inline comments must
produce the full template skeleton: header block, Scope, Review Recommendation, fenced Draft
Review Summary, Draft Inline Comments (or explicit "None"), and Verdict.

The template is the output contract. Do not narrate findings in free-form prose.

## Section Conditionality

Omit ANY section that would say "nothing to note." Always-present sections:
Scope, Review Recommendation, Verdict, Draft Review Summary.

Exception: when `mx2-security-auditor` was dispatched, include positive confirmation
even if clean: "Reviewed for: PII exposure, auth/authz, audit trails, encryption. No concerns identified."

## Principles

- **Actionable output.** Every finding should help the reviewer take a specific action.
- **High signal, no noise.** Only flag things with evidence. False positives erode trust.
- **Two audiences per finding.** Briefing text (reviewer) and draft comment (PR author).
- **Depth by default, speed on request.** Specialist dispatch is default. `--quick` for triage.
- **Don't duplicate existing tools.** No GitHub-posted comments, no `pants` runs.

## Additional Resources

- For specialist dispatch triggers and prompt templates, see [dispatch.md](dispatch.md)
- For inline Checkov IaC analysis (Terraform PRs), see [checkov.md](checkov.md)
- For Mermaid sequence diagram generation (M+ cross-service PRs), see [diagrams.md](diagrams.md)
- For synthesis process, consequence assessment, design surfaces, and verifiability map, see [synthesis.md](synthesis.md)
- For size-gated verification process, see [verification.md](verification.md)
- For output format templates for each mode, see [output-formats.md](output-formats.md)
- For grounding rules and evidence categories, see [grounding.md](grounding.md)

