# Static Analyzer Pre-Check

Three static analyzers post on MX2 PRs (or could). Surface their findings
alongside specialist results so the reviewer sees the engineering lead's #7 in one place
rather than scattered across bot comments. Each sub-section below documents
the fetch path, severity mapping, and dedup rule against specialist findings.

Per-tool default-mode behavior:

| Tool | Fetch path | Default severity | Front Door? |
|---|---|---|---|
| SonarCloud | `mcp__sonarqube__*` (verified) | Rule violations: BLOCKING in --mine, advisory others | No |
| Datadog code analysis | `mcp__datadog__search_pr_insights` (verified via `datadog/unblock-pr` skill) | Vulnerabilities: BLOCKING; Quality: DISCUSSION | No |
| Sentry | N/A (no live bot on MX2 PRs as of 2026-05-28) | (see Sentry sub-section) | No |

Static-analyzer findings are inline-iterate, not Front Door class. the engineering lead's
"send back quickly" framing applies to description and types specifically
(synthesis.md step 7b). A static-analyzer finding can still be BLOCKING in
its own severity bucket; that just routes through the regular Recommendation
Table (BLOCKING -> Request Changes), not the Front Door track.

**Dedup rule (shared).** When a static-analyzer finding overlaps with a
specialist finding on the same file + line, keep the specialist finding and
append the analyzer's rule code as an additional attribution line on it
("also flagged by SonarCloud S5754" / "also flagged by Datadog rule X").
Preserves provenance without double-commenting. The dedup runs in synthesis
Step 2 (Dedup overlapping findings).

## SonarCloud

**Direct-access rule.** SonarSource MCP is available and verified
(`config:sonarcloud-mcp`, 2026-05-21). Do not ask the author to paste a
screenshot or paste from `sonarcloud.io`; query the MCP directly. The only
case where asking is appropriate is if the MCP errors out AND the local
catalog walk turns up nothing AND the gate is still red. Even then, name
the MCP error in the ask so the user can debug their token. The legacy
"SonarCloud is private and only CI has the token" framing is obsolete.

**Process (in order; later steps run only if earlier ones come up empty):**

1. **Primary: query the MCP.** Call
   `mcp__sonarqube__search_sonar_issues_in_projects` with
   `projects=["mx2_docr"]`, `pullRequest="<N>"`,
   `issueStatuses=["OPEN", "CONFIRMED"]`. Call
   `mcp__sonarqube__get_project_quality_gate_status` with
   `projectKey="mx2_docr"`, `pullRequest="<N>"` to get the gate state and
   the `new_violations` threshold breach count. The filter param is
   `pullRequest` (not `pullRequestId`), and for `mx2_docr` its value is just
   the GitHub PR number, so pass `<N>` directly. Do NOT call
   `list_pull_requests` to "discover" the key (the MCP tool descriptions
   suggest it): its output is large enough to blow the tool-result token
   budget, and the key is already known.

2. **Leak-period scope filter (mandatory; skipped in `--quick`).** For each
   returned issue, check `textRange.startLine` against the PR's actual
   diff hunks. SonarCloud's leak-period mode flags pre-existing violations
   in any file touched by the PR; those are tech-debt artifacts, not
   author responsibility for this PR. The diff-hunk filter is computed
   once from `gh api /repos/<owner>/<repo>/pulls/<N>/files --paginate`
   (parse `patch` field per file; track `+` and ` ` lines from each `@@`
   hunk header). Drop issues outside hunks unless the user has explicitly
   asked for "all Sonar findings including pre-existing." Surface a
   one-line note that N pre-existing leak-period findings were dropped, so
   the author knows the count comes from the gate's view, not yours. In
   `--quick` mode the diff is not fetched, so the filter is skipped;
   report all issues with the note "leak-period filter skipped (--quick)"
   so the count is auditable. See
   `feedback:pr-review:sonarqube-leak-period-scope` (2026-05-18).

3. **Surface findings, differentiated by Sonar metric.** Inline in the
   pr-intel output under "SonarCloud findings" sub-section. Each in-diff
   issue gets file:line, rule code, and the Sonar message. Severity depends
   on which Sonar metric the finding maps to:

   - **Rule violations on new lines (`new_violations`)**: real defects
     SonarCloud flags via specific rules (S8572, S6796, S1192, etc.). Treat
     in-diff rule violations as `🚨 critical` in `--mine` mode (would block
     the gate; author is about to publish) and as `⚠️ advisory` on others'
     PRs (the bot will catch them; flag for the author).

   - **Coverage threshold (`new_coverage` < threshold, typically 80%)**:
     FLAG ONLY, never BLOCK. Coverage is a code-quality signal but it is NOT
     enforced at the GitHub merge gate, and authors get reasonable latitude
     especially on massive PRs where adding coverage proportional to scope
     would balloon the change. Surface coverage shortfall as `⚠️ advisory`
     in BOTH `--mine` and others-review modes. Frame the comment as an
     observation or question ("new code coverage is X%; is that acceptable
     given the scope, or do you want to land a test?"), NOT as a "before
     ready" precondition. Coverage findings must never drive the review
     recommendation past Comment; do not write "once the coverage gate is
     addressed, this is ready" or any "address X" framing that treats
     coverage as gate-blocking. Recurrence context: PR 9274 review on
     2026-05-21 (the "Once the test mock and the SonarCloud coverage gate
     are addressed, this is ready" phrasing that prompted this rule).

   - **Other gate conditions (reliability rating, security rating,
     duplicated_lines, security_hotspots)**: surface as `⚠️ advisory` in
     both modes; severity escalation belongs to the specific finding the
     gate maps to, not the rating itself.

   Include the new_violations count, new_coverage value, and the
   thresholds from the quality-gate response so the author knows which
   metric drives the gate state. Distinguish the violation count (which
   IS a substantive concern) from the coverage shortfall (which is
   advisory).

4. **Catalog walk (preventive secondary).** Load
   [~/.claude/projects/-workspaces-main/memory/sonarcloud-rules.md](../../projects/-workspaces-main/memory/sonarcloud-rules.md)
   and run each rule's `**Detector**` block against the diff. This catches
   rules Sonar has not yet flagged (e.g., on un-pushed local edits in
   `--mine` mode where Sonar has no PR analysis yet, or where the catalog
   has a stricter detector than Sonar's online rule). Surface as advisory.
   The catalog is also the only signal when step 1 is skipped (e.g.,
   pre-push local review).

**When to skip step 1.** If no PR exists yet (pre-push `--mine` mode where
the branch is still local), the MCP cannot help; go straight to step 4. If
the MCP returns an error, log the error inline ("Sonar MCP errored:
&lt;message&gt;") and fall through to step 4.

**Growth rule.** When a NEW rule fires on a real PR via the MCP (own or
reviewed) and is not yet in the catalog, the follow-up bead is "add
`python:S<code>` to sonarcloud-rules.md with a concrete `**Detector**`
block." Preventive entries (rules not yet seen on MX2) are allowed when the
SonarSource rule definition is public AND the detector is concrete enough
to be verifiable without re-fetching docs; mark each entry as
`**Preventive**` vs `**Observed**` so provenance stays auditable.

**Last-resort escape hatch.** Only after step 1 has errored AND the catalog
walk (step 4) is empty AND the gate is still failing: ask the user to paste
the issue list from
`https://sonarcloud.io/project/issues?id=mx2_docr&pullRequest=<N>`. State
the MCP error in the ask. Add the new rule to the catalog as the
resolution step.

## Datadog code analysis

**Direct-access rule.** Datadog MCP exposes per-PR code-quality and
code-security counts via `mcp__datadog__search_pr_insights`. Do not parse
the `datadog-lawfirm` bot comment text; query the MCP directly. The
bot comment links to dashboards but does not include the finding details
inline; the MCP returns the structured counts. The relevant Datadog skill
guide is `datadog/unblock-pr` (Step 1.5 PR Health subsection); load it on
demand if more context is needed.

**Process:**

1. **Resolve the repo URL.** `repo_url: https://github.com/lawfirm/main`
   (prepend `https://` to the `@git.repository.id_v2` form).

2. **Call the MCP.**
   ```
   Tool: mcp__datadog__search_pr_insights
   repo_url: https://github.com/lawfirm/main
   pr_number: <N>
   ```
   Extract `code_quality` and `code_security` entries from
   `products_status`. Ignore `failed_tests`, `flaky_tests`, and `failed_jobs`
   (CI surface already covered by `statusCheckRollup` parse in Phase 0+).

3. **Surface findings.** Each non-zero count becomes one or more findings
   in the pr-intel briefing:
   - **`code_security` violations**: `🚨 BLOCKING` in `--mine` mode (would
     block the gate if Datadog gating is enabled; author about to publish);
     `⚠️ DISCUSSION` on others' PRs (advisory, but security-class
     findings warrant a comment).
   - **`code_quality` violations**: `⚠️ DISCUSSION` in both modes. Quality
     findings are signals, not defects; treat like SonarCloud rule
     violations of medium severity.

   When `search_pr_insights` returns counts but no file:line detail,
   surface the count plus the Datadog dashboard link from the bot comment
   (`https://app.datadoghq.com/ci/code-analysis/<repo>/<branch>/<sha>/code-quality`
   and `.../code-vulnerabilities`) for the reviewer to drill into. Mark the
   finding `front_door: false` and `source: datadog-code-analysis`.

4. **No data available**: when `products_status` is empty or the tool
   returns no data, skip silently. Do not surface "0 findings" as a
   positive signal; the absence of data does not equal absence of issues.

**When to skip.** `--quick` mode skips the MCP call. Pre-push `--mine` mode
where no PR exists yet skips (the MCP needs a PR number).

**Severity mapping rationale.** Datadog code analysis runs SAST rules that
overlap with SonarCloud. When the same finding appears in both surfaces,
the dedup rule (above) keeps the higher-specificity attribution and folds
the rule codes onto one entry. Datadog's vulnerabilities surface tends to
catch CVE-class issues; SonarCloud's surface catches rule violations.
Both can legitimately be BLOCKING.

## Sentry findings

**No live bot on MX2 PRs (verified 2026-05-28).** A scan of issue-comment
authors across recent PRs returned zero Sentry-style bot users (no `sentry`,
`getsentry`, or `sentry-io` author). The "Sentry-Derived Bug Patterns"
section in `mx2-code-reviewer` carries institutional knowledge from past
Sentry catches that were ported into the agent's review checklist
(`model_dump()` + `json.dumps()` boundary, fragile string parsing on
user-facing identifiers). Those patterns ride on the agent, not on a
pre-check.

**No fetch path until a Sentry MCP exists or a Sentry PR bot is enabled.**
Two future trigger conditions for adding a fetch step here:

- A Sentry bot starts posting on MX2 PRs (parseable from
  `gh api /repos/.../issues/<N>/comments` similar to how SonarCloud cloud
  comments were parsed pre-MCP).
- A Sentry MCP becomes available with per-PR finding query support.

Until then, this sub-section is intentionally empty of fetch logic. The
`mx2-code-reviewer` static-pattern surface is the current Sentry signal.
