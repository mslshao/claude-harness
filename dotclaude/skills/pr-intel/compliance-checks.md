# Compliance Checks (CI status, AC compliance)

This file documents two pre-dispatch checks that gate /pr-intel's review
recommendation logic:

1. **CI Status Check**: distinguishes PR-specific regressions from global flakes
   so failing checks do not over-escalate the recommendation.
2. **AC Compliance Check**: traces each ticket acceptance criterion against the
   diff and surfaces deviations. This machine has no ticket system, so it is skipped.

Both run after Phase 0 description quality, before specialist dispatch.

## CI Status Check

Parse `statusCheckRollup` from already-fetched PR metadata. If any check has
conclusion `FAILURE`, classify against recent CI history to distinguish PR-specific
regressions from global flakes.

1. Extract failing checks (name, conclusion, detailsUrl) from `statusCheckRollup`.
   **First collapse to the latest run per check name.** `statusCheckRollup`
   accumulates every run, so a check re-triggered by rapid re-pushes appears
   multiple times: an early `FAILURE` plus a later `SUCCESS`/`CANCELLED`. Keep
   only the entry with the max `completedAt` per name before classifying; a
   stale `FAILURE` superseded by a later `SUCCESS` is not a failure. Canonical:
   PR 9875's `Empty checklist` showed `FAILURE` entries from pre-checkbox pushes
   while the latest run was `SUCCESS`. Verify with
   `[.statusCheckRollup[] | select(.name=="<check>")] | sort_by(.completedAt) | .[-1]`.
2. If failures exist, fetch recent merged PR check results:
   ```bash
   gh pr list --state merged --limit 3 --json number,statusCheckRollup
   ```
3. For each failing check, determine:
   - **PR-specific failure**: passes on all 3 recent merged PRs but fails here.
     Likely a real regression introduced by this PR.
   - **Global flake**: also fails on at least one recent merged PR.
     Pre-existing, not caused by this PR.
4. Store as `ci_status`:
   - `pr_specific_failures`: list of `{name, detailsUrl}`
   - `global_failures`: list of `{name, detailsUrl}`
   - `all_green`: true if no failures
   - `checks_pending`: true if any check still IN_PROGRESS

**Downstream effects:**
- **Output header**: show PR-specific failures (see output-formats.md)
- **Review recommendation**: classify the failing check before escalating.
  - **Test/build failures** (unit tests, type checks, build steps, CodeQL,
    real correctness gates): if PR-specific and the recommendation would
    otherwise be "Approve" or "Approve with Comments", escalate to "Comment"
    at minimum. Bar Raisers do not approve over real CI breakage that passes
    on main.
  - **Code-quality gate failures** (SonarCloud Quality Gate, lint analyzers,
    complexity/coverage thresholds, Datadog static-analyzer-driven gates):
    surface in the review body as a heads-up; do not auto-escalate. These
    often fire on test-file `any` types or stylistic findings the reviewer
    should triage, not block on. Let the reviewer set the weight after
    seeing the actual issues.
  - When uncertain which class a check belongs to, default to heads-up;
    the reviewer can escalate after one click into the gate's report.
  - **Known no-op rollup checks**: Mergify's `Summary` check (name=`Summary`,
    empty workflowName, `dashboard.mergify.com` detailsUrl) renders the
    merge-protections panel and shows `FAILURE` even when every individual
    protection rule passes. Treat as heads-up, never escalate. The
    `Mergify Merge Protections` check is the substantive signal.
- **Draft Review Summary**: always mention PR-specific failures; note global flakes
  with "failing globally, not specific to this PR"

**Skip condition**: If all checks pass or `statusCheckRollup` is empty, skip the
comparison API call. If checks are pending with no failures, note "CI: checks still
running" without blocking the recommendation.

**Cost**: 0 API calls when green; 1 call when failures exist.

## AC Compliance Check (when a ticket is available)

This company uses neither Jira nor Confluence (Michael, 2026-09-23 10:34 PDT), and
this machine has no ticket system, so there is no ticket to hydrate. Skip this check
and say so in the output. The steps below are kept for a ticket source that may come later.

For each acceptance criterion in the ticket:
1. **Trace it in the diff.** Can you identify the code that implements this criterion?
2. **Check for deviations.** Does the implementation match the spec, or does it
   diverge? Common divergences:
   - AC specifies a condition (e.g., "only when `complete=True`") but code doesn't check it
   - AC specifies behavior on a specific path but code handles a broader/narrower scope
   - AC says "do NOT do X" but the implementation does X (or vice versa)
3. **Flag gaps.** Criteria with no corresponding code in the diff. Could mean the
   criterion is addressed in a different PR, or it was missed.

Deviations are not automatically bugs. The implementation may intentionally
diverge from the ticket for good reasons (scope change, technical constraint,
incremental delivery). The goal is to surface the deviation so the reviewer
can ask "was this intentional?" rather than discover it in production.

This check produces an **AC Compliance** section in the output (see output-formats.md).
It runs regardless of mode (default, --mine, --quick) because spec deviations are
the class of issue most likely to escape code-only review.
