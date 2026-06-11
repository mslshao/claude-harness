# Synthesis

After specialist results return, synthesize into the final briefing.

## Synthesis Steps

1. **Parse and deduplicate** structured FINDING blocks from each specialist
2. **Deduplicate against existing PR comments** - Compare each finding against
   inline review comments and any review body text from prior reviews. This
   includes bot comments (Sentry, Datadog, Copilot) - if a bot already flagged
   the same concern, treat it the same as a human comment for dedup purposes.

   **Position-based same-author dedup (load-bearing structural check; runs
   FIRST, before text-similarity comparison):** for each candidate inline
   finding, scan the fetched inline comments list for any prior comment
   authored by the current reviewer (mslshao) at the same `path` + `line`. If
   a match exists, text similarity is moot: lexical rewording across review
   rounds slips past fuzzy matching even when the substance is identical (PR
   #9221 line 23 of docket_sync/update_scheduler/triggers.py, rounds 1 and 2
   on 2026-05-20, is canonical: 'TypeAdapter(Trigger) version-dependent on
   Pydantic' was reworded to 'Pydantic 2.4+ follows __value__ for
   TypeAdapter, worth a smoke check' and posted as a fresh top-level inline,
   surfacing a reviewer feedback 'you posted the same comment with different
   wording twice in 2 separate threads on the same line'). The rule:
   - If the new finding restates the prior comment with no new context: drop
     the finding entirely (do NOT post a second top-level inline on the same
     line under the same reviewer handle, ever).
   - If the new finding adds genuinely distinct context (additional affected
     sites, a new failure mode discovered post-round-1, version-specific
     clarification triggered by author response): convert it to a REPLY in
     the existing thread by attaching `in_reply_to_id: <prior_comment_id>`.
     The GitHub atomic review endpoint does not accept `in_reply_to_id` (per
     the documented 2026-05-21 S3776 thread limitation); the reply must be
     posted as a separate non-atomic call after the review submits. The
     synthesis output should flag this so /post-review can sequence the
     dispatch correctly.
   - If the new finding applies the same pattern to a different file:line
     not previously covered: post a fresh inline on the NEW file:line with a
     cross-reference back to the prior thread ('see thread on
     `triggers.py:23` for the same root cause'), not a duplicate on the old
     site.

   This check uses structural keys (path + line + author handle) so it
   cannot be defeated by rewording. Text-similarity dedup below still runs
   for cross-author cases (bot comments, other human reviewers) and for
   findings that do not collide on position.

   For each finding that overlaps with an existing comment:
   - If the existing comment covers the same concern adequately: **drop the finding
     from Draft Inline Comments entirely**. It may still appear in the Draft Review
     Summary as an acknowledgment ("already flagged by [author], not adding a separate
     inline comment"). This applies equally to bot comments and human comments.
     "Confirming" a bot finding as an inline comment is still duplication; the review
     summary acknowledgment is sufficient signal (see reviewer-discipline.md lesson #13).

     **For bot comments specifically**: bot reactions (thumbs-up / thumbs-down)
     are handled in a separate top-level phase, NOT inline here. This step
     only owns the dedup decision (drop the duplicate finding); the
     classification of which bot comments get `+1` vs `-1` vs no reaction
     lives in the dedicated Bot Reactions phase. See SKILL.md "Bot Reactions"
     section and [bot-reactions.md](bot-reactions.md) for the 5-category
     decision tree and the reactions list construction. This step just
     records which bot comments overlapped with findings; the reactions
     phase reads those overlap decisions to build the reactions list.
   - If the finding adds genuinely distinct information (different root cause, broader
     impact, or a fix the existing comment missed): **keep it**, but prefix the draft
     comment with "Adding to [author]'s point above:" or similar threading language.
   - If the existing comment is stale (non-HEAD commit) and the finding addresses
     the same code post-update: **keep it** as a fresh assessment.
3. **Resolve disagreements** - surface both perspectives, don't silently pick sides
4. **Categorize by GitHub surface** - specific file+function = inline comment; architectural = review summary
4b. **CI-catchable filter** (a reviewer 2026-05-26 mx2-eng fortnightly: "find things that the linter's gonna catch anyway, or SonarCloud's gonna catch anyway, and then it's like, it's not really worth commenting on, necessarily"): for each finding heading to an inline comment, check whether merged-CI tooling will catch the same issue on the same diff lines. If yes, drop the inline emission entirely and demote to a single-bullet acknowledgment in the Draft Review Summary "Smaller notes" subsection (referencing the CI check by name). The author will see the CI failure with the canonical message; an inline comment that restates it is duplication.

   Catchable patterns (drop the inline, demote to summary if useful):
   - **Ruff**: any finding that maps to a Ruff rule code (E, F, W, I, N, UP, B, SIM, PL, etc.). Ruff runs in `pants tlc` and CI.
   - **MyPy / `pants check`**: typing.Any usage, missing return annotations, incompatible types, untyped function calls. These fail `pants check` and block merge.
   - **SonarCloud rules** (`python:S<NNNN>`): findings that match a rule in `~/.claude/projects/-workspaces-main/memory/sonarcloud-rules.md`. SonarCloud posts these as inline issue comments on the PR. Exception: when SonarCloud has NOT posted on the PR yet (rule reports lag) AND the finding is BLOCKING-class, the inline can stand; otherwise demote.
   - **Pants lint rules**: `pants lint` violations (banned imports, em-dash detection, etc.).
   - **Project-rule violations enforced by hooks**: em-dashes (block-em-dash.sh), `typing.Any` (banned-import.sh), bare except (lint rule). These fail at edit time or in CI.

   When in doubt about CI coverage, KEEP the finding. The filter is for clear-cut cases where the duplication is wasteful, not for "the linter might possibly catch this."

   The filter fires AFTER categorization (step 4) so it only affects inline-targeted findings. Architectural / design-judgment findings in the review summary are NOT CI-catchable by definition and pass through unchanged. The filter fires BEFORE compression (step 5b) and provenance classification (step 5d) so we do not waste classifier dispatch on findings we will drop.

   Counter-signal: a finding that would NORMALLY be CI-catchable but the CI for this PR is not running (the check is skipped, the file is excluded by config, the rule is suppressed locally with a justified `noqa` or `# type: ignore`) STAYS as an inline because the catch-net is not actually catching this case. Use the `checks` data fetched in pr-intel context.md to confirm CI is running before dropping.

5. **Translate to two forms** - briefing text (for reviewer) and draft comment text (for PR author)
5b. **Compress to question core** - for each finding heading to inline comments,
    apply the 10 decision rules in
    [reviewer-discipline.md](../../projects/-workspaces-main/memory/reviewer-discipline.md)
    under "Decision rules for importing into pr-intel synthesis":
    - 0: Defect-class BLOCKING (rule violation, runtime crash, security, data loss)
      uses directive tone, NOT compression. Cite the rule.
    - 1: Phrase as question if the concern survives interrogative form (P1).
    - 2: Hedge only when uncertainty is genuine; default no hedge (P2). Hedges
      run ~8% in the reference corpus, not ~25%.
    - 3: Trim to match concern depth, not template (P3).
    - 4: Anchor concrete when prescribing alternatives (P11).
    - 5: Split if covering multiple concerns (P12).
    - 6: Defer teaching content to reply slot; lead with the smell (P7).
    - 7: Drop if CI or a bot catches it (lesson #6, #13).
    - 8: Cross-reference instead of repeat when the same concern applies to
      multiple sites (P13).
    - 9: Strip meta-observation preamble (V1), both-sides-with-concession framing
      (V2), trailing "since/because" justification (V3). These are reviewer-pad
      patterns; the diff line carries the context.
    - 10: Convert the postable text to a bot-invoked `@claude` question per the
      "Bot-Invoked Comment Form" section below when EITHER (a) the post-compression
      draft genuinely does not fit the Comment-Shape Decision Table ceilings AND the
      verdict requires multi-file tracing (`default` mode only), OR (b) the verdict
      rests on a falsifiable framework/library/repo-wide-state assertion not confirmed
      locally with high confidence (`default` mode only; size-independent, fires even on
      XS/S where the verification pass is gated off). See the first and second triggers
      in that section; rule 11 below adds a third, portfolio-level floor for large PRs.
    - 11: **Size-scaled collaborative-routing floor (the poker discipline).** A
      portfolio-level pass, run ONCE after rule 10 has been applied to every finding,
      not a per-finding rule. Default: zero bot-invoked questions is the correct
      outcome, and stays correct on XS/S PRs and on any PR whose findings are all
      mechanical/rule, all CI-catchable, all bot-dedup confirmations, or all
      defect-class BLOCKINGs with a single visible anchor (citing the rule is the
      load-bearing posture there). The floor is a re-examination prompt that fires ONLY
      when (a) the PR is M+ (size in {M, L, XL, 2XL, 3XL}), AND (b) rule 10 produced
      zero bot-invoked questions, AND (c) at least one substantive net-new finding
      exists that is none of the excluded classes above. When it fires, you MAY route
      the strongest 1-2 such findings through `@claude` per the "Bot-Invoked Comment
      Form" third consideration; prefer findings whose verdict `@claude` can trace
      against repo HEAD (root cause, cross-file contract, "fails because X"), since that
      is where bot routing adds value. This is permission to route, NOT an instruction:
      never manufacture a question to clear the floor; if nothing genuinely qualifies,
      zero stands. Cap at 2 so the review does not become all bot-questions. Disposition
      surfaced across the 2026-06-04 parallel reviews (9646/9627/9641), whose first-pass
      briefings each produced zero `@claude` questions despite substantive local analysis.

    The compression target: design-judgment findings default to ≤ 25 words and
    ≤ 2 sentences (calibrated 2026-05-13 against the a reviewer corpus ceiling),
    often a bare question. Defect-class BLOCKING and design-judgment findings
    that require a named alternative are the only legitimate paths to longer
    comments. When even those don't fit, rule 10 routes to bot-invoked form
    rather than wall-of-text in reviewer voice.

5c. **Hunk-edge pre-check** - for each remaining inline comment after step 5b,
    verify the target line falls within at least one diff hunk in the changed
    file. Parse the `@@ -A,B +C,D @@` headers fetched during data gathering;
    valid post-image ranges are `[C, C+D-1]` per hunk. If a comment's target
    line falls outside every hunk, do NOT emit as an inline comment. GitHub
    rejects out-of-hunk inline comments with 422 "Line could not be resolved"
    and `/post-review` will fold to body anyway, costing a re-confirmation
    cycle. Pre-fold during synthesis:
    - For DISCUSSION or MINOR findings: add as a file:line bullet under a
      "Smaller notes" subsection in the Draft Review Summary.
    - For BLOCKING findings: surface with the file:line reference in the
      Draft Review Summary lede.
    Most-common cause is a finding whose natural anchor is a function or
    class declaration that the PR didn't modify (e.g., naming concerns on a
    function whose body changed but whose signature didn't). The Design
    Review Surfaces section already covers many of these patterns; cross-
    reference rather than duplicate.
5d. **Provenance classification** - moved out of synthesis.md to its own
    top-level pr-intel phase. See SKILL.md "Provenance Classification"
    section and [provenance-classification.md](provenance-classification.md)
    for the dispatch contract and classifier application. Earlier attempts
    to embed the dispatch as a sub-step here were systematically skipped by
    the orchestrator (confirmed 2026-05-21 via transcript inspection: zero
    Agent dispatches on PRs #9276 and #9146 R3 sessions). The phase
    promotion to SKILL.md top level is the attention-floor fix.

(legacy reference block, kept for context; the active spec lives in
provenance-classification.md):

    Findings sent to the agent must include:
    - `finding_id`: stable identifier (specialist source + file:line is
      sufficient when no explicit ID exists)
    - `source`: specialist source if known (e.g., `mx2-code-reviewer`,
      `silent-failure-hunter`, `sonarcloud-pre-check`, `checkov`), OR null
      when the finding came from an inline pipeline step without a source tag
    - `evidence`: VERIFIED / DIFF-VISIBLE / QUESTION
    - `severity`: BLOCKING / DISCUSSION / MINOR
    - `verification`: the verification path text the specialist produced
    - `draft_comment_text`: the rendered comment text (post step 5b
      compression and step 5c hunk-edge pre-check) that will be posted

    The agent returns a JSON array of classifications. Apply each result to
    the corresponding finding's metadata (`classification` field) before
    rendering output. Use the classification to:
    - Set the `Classification:` line in each finding's briefing context
      (output-formats.md Draft Inline Comments template)
    - Compute `Speed-amplified: N | Bot-surfaced: M` counts for the
      Review Recommendation header `**Provenance**:` line
    - Populate the `bot_surfaced_count` and `speed_amplified_count` fields
      that /post-review writes to bd memory (post-review SKILL.md Step 5)

    The agent owns the classifier table (its prompt is the canonical
    reference). Override behavior (mx2-code-reviewer findings that turn out
    to be bot-surfaced based on text mentions of Sonar/Copilot, etc.) lives
    in the agent's decision flow. Do not re-classify the agent's output.

    **Low-confidence flag.** When the agent returns `confidence: low` on a
    classification, surface this in the briefing-context line as
    `Classification: <value> (low confidence)`. Michael's editing pass can
    manually flip these before /post-review consumes the output. Low
    confidence three or more times in a single run signals upstream
    source-tagging is leaking findings without source fields; record via
    `bd remember --key="calibration:provenance-classifier:<topic>"`.

    **Source-tagging discipline upstream of this step.** Inline pipeline
    steps that produce findings without a specialist dispatch (SonarCloud
    Pre-Check, Checkov, Pre-Synthesis Analysis Patterns, AC Compliance
    Check, Spec Compliance Check) MUST set the finding's `source` field
    explicitly so the agent doesn't fall back to text-heuristic alone.
    Speed-amplified is the harder claim to make and source tags are the
    primary signal.

    Default classification by source (reference; the agent's prompt is the
    canonical version):

    | Source | Default classification | Override rule |
    |---|---|---|
    | `mx2-code-reviewer` | speed-amplified | bot-surfaced if VERIFIED via cross-file Grep beyond changed files |
    | `mx2-security-auditor` | speed-amplified | bot-surfaced if VERIFIED via audit-log call-graph traversal |
    | `test-quality-reviewer` | speed-amplified | bot-surfaced if VERIFIED via test fixture/factory cross-reference |
    | `mx2-devops-build-deploy` | speed-amplified | bot-surfaced if VERIFIED via cross-environment Terraform sweep |
    | `mx2-silent-failure-hunter` | bot-surfaced | speed-amplified only if finding is reachable from the single-file diff |
    | `observability-reviewer` | bot-surfaced | bot-surfaced (cross-stack Terraform + code analysis) |
    | `mx2-pr-precedent` | bot-surfaced | bot-surfaced (historical PR comment retrieval) |
    | `mx2-git-historian` | bot-surfaced | bot-surfaced (git log/blame historical analysis) |
    | `bot-review` | bot-surfaced | bot-surfaced (cross-file blast-radius is the agent's whole job) |
    | `mx2-pydantic-reviewer` | bot-surfaced | speed-amplified only if finding is reachable from the single-file diff |
    | AC Compliance Check | bot-surfaced | bot-surfaced (Jira AC trace required reading the ticket) |
    | Spec Compliance / Design Doc | bot-surfaced | bot-surfaced (multi-page design doc synthesis required) |
    | SonarCloud Pre-Check | bot-surfaced | bot-surfaced (external system finding) |
    | Datadog Code Analysis Pre-Check | bot-surfaced | bot-surfaced (external system finding via `search_pr_insights`) |
    | Inline IaC (Checkov) | bot-surfaced | bot-surfaced (tool-only) |
    | Pre-Synthesis Analysis Patterns (Pydantic frozen, pre-existing pattern, error path reachability, opaque constants) | speed-amplified | bot-surfaced if pattern detection required cross-file resolution |
    | `mx2-skeptic` | (not classified - questions, surfaced separately) | n/a |

    **Deterministic override (applies after the classifier returns).** For findings
    whose source is an external system or document trace (SonarCloud, Datadog Code
    Analysis, Copilot, AC Compliance, Spec/Design Doc, Checkov), force `bot-surfaced`
    regardless of the `provenance-classifier` agent's call. The classifier keys on
    whether the underlying code line is diff-visible and recurrently downgrades these
    to speed-amplified when the line is in the diff (a `<T = any>` default, an
    empty-string filter) even though the actionable signal (a coverage-gate miss, a
    duplication-gate hit) came from the external tool, not the diff. The agent prompt
    is canonical for specialist-agent sources; this table is canonical for
    external-system sources. (Recurrences: 2026-05-21 PRs 9251/9271/9225; 2026-06-04
    PR 9671 api/index.ts + extract-last-ai-message.)

    The rule the table encodes: bot-surfaced iff the verification path
    required live-state verification (MCP calls to AWS, Datadog, etc.),
    high-volume document synthesis (Jira AC, design docs at 10+ pages,
    prior-PR archaeology), or cross-file blast-radius pattern matching.
    Speed-amplified iff the finding is reachable from careful single-file
    diff inspection (the bot got there faster, but the reviewer could have
    arrived at it). The discrimination is sharp; the rule preserves
    Michael's voice on findings he owns and surfaces explicit tooling
    provenance on findings he genuinely didn't catch.

    Store the classification on each finding for output-formats.md Draft
    Inline Comments rendering and for the /post-review bd memory write
    (bot_surfaced_count + speed_amplified_count audit fields). See
    `review-voice.md` "Attribute tooling findings to tooling" for the
    voice-rule the classification drives.

6. **Verify grounding** - see [grounding.md](grounding.md)
6b. **Apply series context** - if `series_context` exists, check each "unused export"
    or "dead code" finding against `consumed_exports`. Exports consumed by sibling PRs
    are not orphaned; reclassify as a design review surface question, not a finding.
7. **Assign severity** - BLOCKING / DISCUSSION / MINOR
7b. **Tag Front Door findings** - independent of severity, tag findings that
    match a reviewer's explicit "send back quickly" classes:
    - **Type/model smells**: untyped dicts, `dict[str, Any]`, Literal-key
      dict access (`response["matter_id"]`), `| None` on collections
      (`list[T] | None`, `dict[K,V] | None`), `bool | None`, same model
      representing multiple independent concepts/states. Surfaced by
      `mx2-code-reviewer` Design Judgment Checks (None-Abuse Semantics,
      Literal-Key Dict Detection, Domain model misfit).
    - **Large-refactor methodology gap**: diff > 500 lines + > 5 files + a
      mechanical edit pattern repeated across files + the PR description
      does NOT describe the methodology (script, rule, or command applied).
      Reviewer cannot spot-check without the methodology statement.

    Add `front_door: true` as an attribute on the finding object; preserve
    its severity (BLOCKING/DISCUSSION/MINOR) separately. The two tags are
    orthogonal: a type smell can be FRONT-DOOR + DISCUSSION (cheap to fix,
    but ripples), a security finding is NOT-FRONT-DOOR + BLOCKING (just
    fix inline). Boolean-param smells, pragma misuse, and exception-design
    smells are NOT Front Door; they're iterate-inline findings. a reviewer
    explicitly puts the "send back quickly" framing on description (#1)
    and types (#2); the rest are inline-iterate.

    Description-quality issues do not flow through this step because Phase 0
    short-circuits before specialist dispatch. If Phase 0 passed and Front
    Door is empty, the PR is past a reviewer's send-back gate.

8. **Assess consequence** - for each DISCUSSION finding, evaluate reversibility
   and consequence to determine whether it affects the review recommendation.
   See Consequence Assessment below.
9. **Identify design review surfaces** - extract patterns that need human judgment
   rather than mechanical fixes. See Design Review Surfaces below.
10. **Build verifiability map** - classify what the PR proves, assumes, and leaves
    unverifiable. See Verifiability Map below.

11. **Cognitive decision budget gate** - count the total cognitive decisions the
    posted review will impose on the reader (including the reviewer's own re-read
    pass before posting). Each of the following counts as ONE decision:
    - Each Draft Inline Comment
    - Each AC Deviation requiring follow-up
    - Each Design Review Surface
    - Each Verifiability Map "Assumed" item that requires reviewer follow-up
    - Each Open Thread requiring reviewer judgment

    The ceiling is **5 cognitive decisions per PR**. If total decisions > 5 AND
    size in {L, XL, 2XL, 3XL}, force a compression pass before output:

    1. **Drop MINOR findings first.** MINOR rarely changes the author's actions;
       below-the-line in a review summary acknowledgment is enough.
    2. **Consolidate DISCUSSION with overlapping themes into the Draft Review
       Summary** as a "Smaller notes" bullet section. Three DISCUSSION comments
       on parallel concerns become one summary bullet with three file:line refs.
    3. **Keep BLOCKING and design-judgment findings that need author engagement.**
       These are the load-bearing reviewer signals.
    4. **Target post-compression: ≤5 decisions.** If the PR genuinely has more
       than 5 BLOCKING-class concerns, that's a signal the PR should be broken
       into smaller PRs; surface that as a meta-recommendation in the Draft
       Review Summary lede rather than posting individual nitpicks.

    The reason the gate exists: even Michael glosses over his own pr-intel
    output when the report is long. A wall-of-text review under fatigue (5pm,
    PR #11 of the day) lets stupid findings ship under his name. If the output
    exceeds his own review-capacity at posting time, it cannot serve the trust
    signal it was built for. The 5-decision ceiling is calibrated against the
    a reviewer corpus pattern (median ~3 substantive comments per PR with headroom
    for AC + design surfaces) and against working-memory limits.

    The gate fires AFTER provenance classification (step 5d) so compression
    cuts respect classification: when choosing what to drop, prefer dropping
    speed-amplified MINOR over bot-surfaced MINOR (the bot-surfaced finding is
    something Michael genuinely wouldn't have caught, so the marginal value of
    keeping it is higher even at MINOR severity).

11b. **Body-inline dedup pass (pre-emit)** - findings have ONE venue. For each sentence
    of the Draft Review Summary body, run the operational test: if it shares BOTH its
    core claim AND its anchor (file/line/symbol) with an inline comment, replace it with
    the pointer ("see inline on line N"). This is a concrete test, not a judgment call:
    same claim alone is not enough (the body may legitimately frame a cross-cutting theme
    an inline cannot); same anchor alone is not enough (two distinct concerns can land on
    one line). Both together means the body is restating, and restating doubles the
    author's reading cost.

    Exception (load-bearing): the `@claude` trigger sentence required by the "Bot-Invoked
    Comment Form" posting-side rule is NEVER subject to this pass. Preserve any body
    sentence containing the literal token `@claude` unconditionally. Dropping it strips
    `@claude` from `review.body` and silently suppresses every bot-invoked inline in the
    batch (the 9325 failure).

    The body's positive job is everything with NO inline home: the overall assessment, AC
    deviations, PR-description and process notes, and cross-cutting framing that ties
    several inline findings together. This pass compresses restatement; it does not shrink
    the body to nothing. A clean PR still gets its acknowledgment-first lede and its pointers.

    The reason this is a step and not a template note: the passive "Body-inline
    non-duplication rule" in output-formats.md is honored last and dropped first under
    output fatigue. This is the same class of failure that moved provenance classification
    to a top-level phase; step 11b addresses it within synthesis by making the check
    explicit and numbered rather than prose-buried, a partial fix with known residual skip
    risk on fatigued runs (the Stop-hook overlap-check in stop-validate-pr-intel.sh is the
    fatigue-proof structural backstop). The 9304 anti-pattern is canonical: the
    `sqlworkbench:ListDatabases` question rendered in BOTH the body's numbered list AND
    inline:37 with ~80% prose overlap. The 9646 instance (2026-06-04) is the recurrence
    that forced promotion: a body paragraph previewed the inline `@claude` finding and was
    deleted by hand at emit time. See `bd memories
    calibration:pr-intel-voice-body-inline-duplication-2026-05-21`.

## Trust-band Weighting

PR-comment authors carry trust bands stored in PRIVATE file
`~/.claude/projects/-workspaces-main/memory/reviewer-trust-bands.md`. Bands are
A/B/C plus bots (implicit C); unknown handles treated as middle band. This
synthesis file references the trust-bands file by path and never inlines
assignments. The band lookup is read-only at synthesis time.

**Step 2 refinement (dedup against existing comments)**:
- Full overlap with Band-A or bot: drop the finding (existing rule).
- Full overlap with Band-B: drop the finding, acknowledge in Draft Review
  Summary as "already flagged by <author>".
- Full overlap with a Band-C human: keep the specialist finding (the C-band
  reviewer may have surfaced the issue without the depth a specialist
  catches), threaded as "Adding to <author>'s point" if appropriate.

**Step 3 refinement (resolve disagreements)**:
- Lead with the Band-A perspective if one exists; surface lower-band view as
  the alternate.
- Band-C vs Band-A disagreement is not symmetric: lead with A, frame C as
  "raised Y, here's why the A framing applies."
- Bot vs human: human wins unless the bot cites a cross-file consequence the
  human missed.

**Privacy (load-bearing)**. The band lookup happens internally; synthesis
output never mentions trust bands explicitly. Refer to authors by handle in
the output ("leading with <author>'s perspective") without revealing why.
Downstream readers of the posted review do not see band information. Any
text generated by this skill that names a band assignment is a bug; remove
it before posting.

**Correction-memory surfacing**: when listing unmerged `correction:*`
corrections (manual triage or future helper), order by trust band of the
source attribution. `correction:*` entries are `bd remember` memories, not
beads; source attribution lives in the memory body as a `Source: <handle>`
first line. Band-A first, Band-C and bots last. See the private file's
"How to surface unmerged corrections" section for the concrete `bd memories`
query.

## Pre-Synthesis Analysis Patterns

Before synthesizing specialist results, the pr-intel orchestrator itself should check
for these high-value patterns that specialists may miss (because they operate on diff
hunks, not cross-file type resolution):

1. **Pydantic frozen model mutation.** When the diff assigns to an attribute on a
   Pydantic model instance (e.g., `config.field = value`), check whether the model
   class has `model_config = ConfigDict(frozen=True)` or inherits from a frozen base.
   Frozen models raise `ValidationError` on attribute assignment. This is a runtime
   crash that passes type checking and looks correct in the diff. Use Grep/Read in
   the worktree to inspect the model class definition before accepting the pattern.

2. **Constructor vs. post-init mutation.** When code creates a Pydantic model and then
   mutates it (instead of passing all values at construction), check if there's a
   reason: frozen models require construction-time values or `model_copy(update=...)`.

These patterns catch bugs that are invisible in the diff alone and require resolving
the type hierarchy. They are the class of bug that bots (Sentry, Copilot) catch
because they do cross-file analysis, and that human reviewers miss because they
trust the diff.

3. **Pre-existing pattern detection.** Before flagging a code pattern as a concern,
   check whether the same pattern already exists elsewhere in the codebase. Example:
   a Terraform subscription missing a filter value looks like a bug, but if other
   subscriptions in the same file use the same filter, it's likely intentional. Use
   Grep in the worktree to search for the pattern beyond the diff. If the pattern
   exists unchanged in 2+ other locations, reframe the finding from a bug/concern to
   a question: "This matches the existing pattern in X and Y. Is that intentional?"
   This is the most common source of false positives in infrastructure and config PRs.

4. **Error path reachability.** Before flagging an error-handling concern (e.g.,
   "if X raises here, the caller doesn't catch it"), trace the actual call chain to
   verify the path is reachable. Read the function that produces the value, not just
   the function that consumes it. If the producing function uses a safe accessor
   (try/except internally, returns default, etc.), the error path may be unreachable.
   Unreachable error paths are not findings; drop them. This check is especially
   important for findings about exception propagation through finally blocks,
   cached_property re-evaluation, and double-raise scenarios.

5. **Pre-existing behavior attribution.** When a finding describes behavior that exists
   in the codebase before this PR (e.g., retry re-extraction, idempotency gaps), check
   whether the PR introduced the behavior or merely preserved it during a refactor. Use
   `git diff` or the PR's `-` lines to determine if the code path existed before. If
   the behavior is pre-existing and the PR didn't change its semantics, move the finding
   to the Review Summary as "pre-existing, not introduced by this PR" (same treatment as
   grounding.md rule 1 for unchanged context lines). Do not produce an inline comment
   for pre-existing behavior unless the PR made it worse.

6. **Opaque constants in new code (provenance discipline).** When the diff adds
   string literals matching base64 patterns (≥ 16 chars, `^[A-Za-z0-9+/]+=*$`),
   numeric constants without a named identifier, or unexplained env-var defaults,
   emit a "where does this come from?" finding with VERIFIED + DISCUSSION severity.
   a reviewer's two highest-leverage moves on PR #8931 were both provenance questions
   on opaque base64 IDs (`arize_space_id = "U3BhY2U6..."`, prompt_ids in
   `prompt_client.py`). This is mechanical to detect and the highest-frequency
   missing question in pr-intel output today. The draft comment shape: "where does
   this come from?" or "where does this come from? Can we add a comment". Optionally
   include a one-line briefing-context note about the constant's likely role (e.g.,
   "looks like an Arize space ID") so the reviewer can confirm before posting.

These four patterns (3-6) catch the class of false positive where the finding is
technically correct but misleading (3-5), and the class of true positive that the
synthesizer currently underweights (6).

## bot-review Findings: Fix-this Delegation Links

When rendering `bot-review` findings into Draft Inline Comments or the Draft Review
Summary, append a delegation link so the reviewer or PR author can one-click hand the
fix to a fresh Claude session. Adopted from the Anthropic GHA `claude-code-action`
review pattern (see decision bead `docr-59ev` item 8).

For each `bot-review` finding, build the link as:

```
[Fix this →](https://claude.ai/code?q=<URI_ENCODED_INSTRUCTIONS>&repo=lawfirm/main)
```

`<URI_ENCODED_INSTRUCTIONS>` is the URL-encoded form of a self-contained instruction
including: PR number, branch name, the consumer file:line that needs updating, the
changed-symbol file:line for context, and the invariant articulation. Example
plaintext (before encoding):

```
On PR #<number>, branch <branch>: in <consumer_file>:<consumer_line>, update the
caller to handle the new contract. Context: <changed_symbol_file>:<changed_symbol_line>
changed the contract such that <invariant>.
```

Append the link at the END of the Draft Inline Comment (after the prose), and at the
END of each `bot-review` entry in the Draft Review Summary. Other specialists' findings
do NOT get this link by default; they propose fixes inline rather than delegating.

The link preserves `bot-review`'s advisory-only stance (no proposed fix in the
comment text itself) while making the finding actionable. If `bot-review` produced no
findings, no Fix-this link appears anywhere.

## Bot-Invoked Comment Form

Multi-paragraph trace comments in reviewer voice have three failure modes: (a) they
consume reviewer drafting bandwidth, (b) they read as wall-of-text to PR authors who
must reckon with a senior peer writing seven paragraphs of code tour, (c) they lock
the reviewer into a conclusion before the author can respond. The bot-invoked form
decouples these: the reviewer asks a short anchored question, the GitHub `@claude`
bot does the trace, the reader receives bot-voice analysis, and the reviewer's
actual verdict stays in the briefing context for follow-up if the bot's response is
incomplete or wrong.

**When to convert**: rule 10 in step 5b fires. Concretely, the post-compression
draft genuinely does not fit the Comment-Shape Decision Table ceilings (>25 words
or >2 sentences for design-judgment, >3 sentences for defect-class BLOCKING) AND
the verdict requires multi-file tracing (≥2 files OR cross-referencing a contract:
IAM policy ↔ runtime call, settings field ↔ consumer, type signature ↔ caller
assumptions) AND the conclusion is not trivially visible at the anchor line.

**Second, independent trigger (falsifiable-assertion verification)**: convert to the
bot-invoked form REGARDLESS of comment size when the finding's verdict rests on a
falsifiable assertion about framework/library behavior or repo-wide state ("all
callers migrated off the old kwarg", "field X is unused", "the default TestClient is
loopback", "Pydantic v2 rejects field X") that has not been confirmed locally with
high confidence. Two ways that happens: on XS/S PRs the verification pass
(verification.md) is size-gated off entirely, so any load-bearing falsifiable
assertion is unconfirmed by definition; on M+ PRs, verification.md step 2's local
check came back inconclusive. The `@claude` bot reads repo HEAD with fresh context and
empirically catches confident-but-wrong local assertions that a code-only specialist
pass would otherwise ship; routing the claim as a neutral `@claude` question both
validates it and keeps the reviewer off the hook for a claim they could not verify.
Canonical instance: 9451 (S-sized, so verification was skipped), where a wrong
"Starlette default TestClient is loopback" claim drove a false test-gap finding the
`@claude` bot corrected from repo HEAD. This trigger is OR-ed with the size/trace
trigger above: either path alone suffices to convert.

**Third consideration (collaborative-routing floor, the poker discipline)**: the two
triggers above are reactive and per-finding; each fires only when a specific finding hits
a size/trace ceiling or rests on an unverified falsifiable claim. On a larger PR where
every finding verified cleanly and compressed to direct form, both can stay silent,
leaving the whole review in direct voice with ZERO `@claude` questions. The default is
that zero is correct: a genuinely clean PR earns no manufactured questions. The floor
guards only the case where zero co-occurs with substantive findings on a larger PR, and
the rationale is trust, not verification (these findings are already verified locally). A
larger PR returned as a wall of verified verdicts with zero questions reads as a
fully-revealed hand: nobody plays against face-up cards, it looks like showing off
everything found, and it leaves the author nothing to engage, none of which builds the
back-and-forth that earns review trust. An anchored `@claude` question invites the author
into a discussion (the bot does the trace; the author answers a question, not a verdict)
and keeps the analysis honest by validating it against repo HEAD in the open.

Apply as a portfolio-level check (step 5b rule 11): after the two triggers above have run
across all findings, if the bot-invoked count is ZERO AND the PR is M+, you MAY route the
strongest 1-2 substantive net-new findings through `@claude`, preferring those whose
verdict `@claude` can trace against repo HEAD. Permission, not a quota: it applies only to
a substantive net-new finding that is NOT a defect-class BLOCKING with a single visible
anchor (the rule citation is load-bearing; see "When NOT to convert" below), NOT a
CI-catchable nit, and NOT a bot-dedup confirmation. Never manufacture a question to clear
the floor; if nothing qualifies, zero stands. Cap at 2. `--mine` and `--quick` are exempt
(no post-and-wait step).

**When NOT to convert** (stay in direct voice):
- Finding compresses cleanly to the Comment-Shape Decision Table ceilings, AND the
  falsifiable-assertion trigger does not fire. An unverified falsifiable claim
  converts even when it compresses cleanly; size only governs the first trigger.
- Defect-class BLOCKING with a single visible anchor (rule violation, runtime
  crash visible in the diff itself). The reviewer citing the rule is the
  load-bearing posture; bot mediation dilutes it.
- `--mine` mode. The author is the reviewer; routing through a bot adds latency
  without depersonalizing anything. The falsifiable-assertion trigger does not
  bot-route in `--mine` either: surface an unverified framework/repo-state claim as a
  pre-submission item to check before review, not as an `@claude` question (the
  `--mine` path has no post-and-wait step to consume one).
- `--quick` mode does not emit inline comments.

**Form**: the bot-invoked comment is a neutral question (not a leading one) that:

- Anchors at the suspect code (same line target as the direct form would have used)
- Opens with `@claude` plus an open verb (`can you trace`, `could you check`,
  `does this`)
- Names the specific files, symbols, or contracts the bot should examine
- Asks for the bot's verdict at the end; does NOT pre-state the reviewer's
  conclusion (the bot may reach a different answer; pre-stating bias the response)
- Stays to one paragraph in the postable text; the bot's response is the long form
- Omits the Tool-source attribution prefix. The `@claude` invocation IS the
  attribution; readers see bot-voice provenance directly in the response thread.

**Briefing context preservation**: the finding's full briefing context (severity,
classification, specialist source, verification path, the reviewer's own read of
the expected answer) stays in the briefing-context section per output-formats.md.
The reviewer reads the briefing to decide whether to post and to validate the bot's
eventual response. If the bot reaches a different conclusion than the briefing
indicated, that is a calibration signal worth surfacing (and a reply slot for the
reviewer to correct on-thread).

**Posting-side trigger**: the GitHub `Claude Code` workflow filters on
`contains(github.event.review.body, '@claude')` for `pull_request_review` events
and on `contains(github.event.comment.body, '@claude')` for
`pull_request_review_comment` events. When inline comments are submitted as part
of an atomic review (`POST /pulls/N/reviews` with `comments` array), GitHub
fires the review event and may suppress per-inline events. The Draft Review
Summary body MUST therefore contain literal `@claude` whenever any bot-invoked
draft inline comments exist in the batch; otherwise the workflow skips and no
bot response fires (canonical failure: 2026-05-27 9325 review batch; review body
contained "Pinged Claude" without the @-prefix; six bot-invoked inline comments
posted, zero workflow runs fired, manual wake-up issue comment required).

The simplest body shape that triggers reliably: append one sentence to the
Draft Review Summary like "Some inline questions are tagged for `@claude` to
trace on this round." The sentence is natural in human voice, contains the
literal `@claude` token, and signals to the PR author that bot responses will
land in those threads.

Reference: this section was added 2026-05-27 after the 9325 incident demonstrated
both the load-bearing value of the form (specialist findings landed as @claude
questions read more neutrally than as reviewer monologues) and the posting-side
gotcha (the workflow-filter mismatch).

See `output-formats.md` for the bot-invoked draft template and the Comment-Shape
Decision Table override note.

## Consequence Assessment

Severity alone does not determine the review recommendation. A DISCUSSION about
adding a log line and a DISCUSSION about a silent NOOP in an event pipeline are
both "discussion" but have completely different blast radii. The missing dimension
is **reversibility and consequence**: how bad is it if we're wrong, and how hard
is it to detect and fix later?

For each DISCUSSION finding, classify its consequence:

**High consequence** (hard to fix or detect later):
- **Infrastructure/security boundaries**: IAM, auth, DynamoDB table design,
  EventBridge routing, S3 permissions, encryption
- **Data loss or corruption paths**: code where incorrect behavior means data is
  permanently lost, silently wrong, or unrecoverable
- **Pipeline completeness**: event-driven flows where a message can be consumed
  without producing a downstream effect and without observability
- **Contract changes**: modifications to event schemas, API response shapes, or
  DynamoDB key structures that downstream consumers depend on
- **External system contract changes**: renames of variables, keys, or parameters
  that map to external systems (Arize Prompt Hub templates, Salesforce field names,
  court system API parameters). The rename may be complete in our codebase but the
  external system must also be updated. Tests pass because test fixtures are local
  mocks, not the real external service. Always a blocking question.
- **Race conditions and timing dependencies**: anywhere the code relies on or
  depends on something else happening, but is itself stateless or can't know
  about the other state until it checks. Read-then-write without atomicity,
  concurrent Lambda invocations touching the same resource, ordering assumptions
  between async components. These are the bugs that look correct in review but
  break under load - they pass every test in isolation and fail in production
  because timing assumptions aren't encoded anywhere.

**Low consequence** (easy to fix later):
- Observability improvements where the infra already exists (adding a metric/log)
- Naming, documentation, code organization suggestions
- Test coverage for paths that are already correct (the test formalizes, not fixes)
- Style and pattern consistency within the team's conventions

## Review Recommendation Logic

### First-Round Rule

First-round reviews should default to Comment for PRs that are L or larger, involve
novel integration patterns, external system contracts, or AI-generated code with
unverified claims. The first round is for questions and verification; approve in
round 2 after the author has responded.

For XS/S/M PRs with low risk, no external dependencies, and clean findings, first-round
Approve is fine. The gate is not size alone but complexity and verifiability: a 200-line
PR that renames a variable in an external system contract is higher risk than a 500-line
PR that adds straightforward test coverage.

To detect first-round status: check the `reviews` array from PR metadata. If no prior
review exists from this user (mslshao), or all prior reviews are from bots, this is
a first round. If a prior COMMENT or REQUEST_CHANGES review exists from mslshao, this
is a re-review and the full recommendation table applies without this gate.

### Third-Party Approval Quality Gate

The `reviews` array often contains APPROVED reviews from non-mslshao reviewers.
Before letting any such approval influence the recommendation, run a quality gate
on it. The gate exists because rubber-stamp approvals from low-context reviewers
are common, especially on large or boilerplate-looking PRs, and have shortcut full
independent analysis in the past (2026-05-14 PR #9073: 18,694-line codegen PR
approved with empty body + zero inline comments by a reviewer not on the trust-band
A-tier; first-pass synthesis deferred to the approval and skipped specialist
dispatch).

For each non-mslshao APPROVED review, the approval is **deference-worthy** only if
BOTH:
1. The reviewer handle appears in `~/.claude/projects/-workspaces-main/memory/reviewer-trust-bands.md`
   under Band A.
2. The review has a non-empty body OR at least one substantive inline comment from
   that same reviewer on this PR (bot-authored comments do not count; "lgtm" and
   "+1" do not count as substantive).

If either fails, the approval is **non-signal**:
- Note in the briefing header: "Existing approval by `<handle>` treated as non-signal
  (empty review on a non-A-tier reviewer)."
- Compute the recommendation as if no third-party review exists.
- Do NOT skip specialist dispatch on the basis of "someone already approved."
- For L+ PRs, default to Comment per the first-round rule unless your own analysis
  surfaces zero findings AND verifiability is unambiguous.

The gate is asymmetric on purpose. An A-tier reviewer with substance is real signal;
a non-A-tier empty approval is noise that PR authors (and the AI) instinctively
treat as cover. The cost of running specialists when an existing approval was
genuine is small; the cost of skipping them when the approval was rubber-stamp is
the failure this gate prevents.

### Recommendation Table (re-review or second round)

| Finding type | Consequence | Recommendation effect |
|---|---|---|
| BLOCKING (any) | any | Request Changes |
| FRONT-DOOR (any severity) | any | Comment (back-to-author framing) |
| DISCUSSION | High consequence | Comment (no approval stamp) |
| DISCUSSION | Low consequence | Approve with Comments |
| MINOR (any) | any | Approve with Comments |
| No findings | - | Approve |

When multiple findings exist, the most restrictive recommendation wins.

**Front Door rationale.** A FRONT-DOOR finding (type/model smell or
large-refactor methodology gap; see step 7b) is not always a runtime defect,
but downstream review effort depends on it being right. Approving with
inline comments invites the author to address the type smell in the same
round as 5 other comments on code that may itself need re-shaping once the
type is fixed. a reviewer's framing: "send them back, and quickly." The
recommendation lands at Comment with the Draft Review Summary opening
"the priority for this round is X; let's iterate on that before deeper
review." BLOCKING + FRONT-DOOR still resolves to Request Changes (BLOCKING
is more restrictive). FRONT-DOOR + DISCUSSION/MINOR resolves to Comment.

### Coverage Gate Exception

SonarCloud `new_coverage < threshold` (typically 80% on new code) is NOT a
BLOCKING-class finding regardless of how short coverage falls. Coverage is
a code-quality signal that is not enforced at the GitHub merge gate; authors
get reasonable latitude, especially on massive PRs where mandatory
coverage scales the change scope unfavorably. Coverage gate failure must
NEVER drive the recommendation past Comment, and the framing in the
review summary or inline comments must NOT treat coverage as a
precondition for "ready" (do not write "once the coverage gate is
addressed, this is ready" or any "address X" phrasing that implies
gate-blocking).

Frame coverage shortfall as an observation or question: "new code
coverage is X%; want to land a test for the new helper, or is that
acceptable given scope?" This applies to BOTH `--mine` (own PR pre-publish)
and others-review modes. The rule does NOT apply to SonarCloud rule
violations (`new_violations` count > 0) on new lines, which CAN be
BLOCKING-class when severe; the exception is specifically for the
coverage-threshold metric. Recurrence context: PR 9274 review on
2026-05-21.

"Comment" means: "I've reviewed the code and have observations that need
your input before I can form an opinion." It avoids the false confidence of
"Approve with Comments" (which signals "fine to merge as-is") and the false
severity of "Request Changes" (which signals defects). A Comment-to-Approve
cycle is healthy collaboration, not rework.

## Design Review Surfaces

After synthesizing findings, identify structural patterns in the code that
represent implicit design decisions where human judgment adds the most value.
These are not bugs or style issues - they're places where the code shape
suggests a decision was made (or not made) that a domain-aware reviewer
should evaluate.

Patterns to detect:

1. **Type narrowing at boundaries.** A function returns a primitive (bool, int,
   str) and the caller branches on it to produce different domain types. Signal:
   "This function's return type collapses N domain states into a primitive. The
   caller's branching logic may belong in the callee."

2. **New abstractions that mirror existing ones.** An enum or mapping whose
   variants correspond 1:1 to existing types. Signal: "This indirection creates
   two places to change when the domain evolves. Is it adding value?"

3. **Silent NOOPs in event-driven flows.** A Lambda or message handler has a
   code path that neither publishes a downstream event nor emits observability
   signals. Signal: "In an event pipeline, a silent NOOP is a potential dead
   letter. Does the system need recovery for messages that hit this path?"

4. **Untested paths as implicit design decisions.** An error or edge-case path
   exists in code but has no test. The question isn't "add a test" (that's
   mechanical) but "is the behavior on this path intentional?" A test would
   formalize the decision.

5. **Race conditions and concurrency assumptions.** Read-then-write sequences
   without atomic operations, concurrent access to shared state, ordering
   assumptions between async components. Signal: "This code path assumes X
   happens before Y. What happens when they overlap?"

6. **Cross-service trust boundaries.** Code that assumes the shape, timing, or
   reliability of data from another service. Signal: "What does this service do
   if the upstream data is late, missing, or shaped differently than expected?"

7. **Framing fit (ticket-vs-diff drift).** When a Jira ticket frames the problem
   as X but the diff implements Y, or implements a narrower slice of X without
   acknowledging the scope shift, the framing has drifted. Signal: "The ticket
   describes retry on Salesforce sync (multiple call sites); the diff adds
   tenacity to one. Is the rest in scope, or has the problem been re-scoped?"
   Detected when AC compliance shows partial coverage, or when the diff's surface
   area is meaningfully smaller or different from what the ticket described.
   Requires Jira ticket context; degrade silently when no ticket is hydrated.

8. **Self-classification defensibility.** When a PR makes claims about its own
   risk profile in the description or title prefix ("XS", "no behavior change",
   "config-only refactor"), validate the claim against the diff. Signal: "The
   description says 'low-risk refactor' but the diff modifies error-handling in
   a Lambda hot path. Is the risk classification defensible, or should the
   reviewer expect more scrutiny than the label suggests?" Detected by scanning
   PR body and title for self-assessment claims and cross-checking against
   changed files and behavioral scope.

Present these in the output as "Design Review Surfaces" - explicitly framed as
places where the reviewer's domain knowledge and judgment matter most. These are
the areas where the radiologist's AI circles the scan for the doctor to evaluate.

## Verifiability Map

Classify the PR's behavioral claims into three tiers:

1. **Proven by tests**: behaviors with test coverage that exercises the actual
   code path end-to-end (not just asserts a mock was called).

2. **Assumed (not verified in this PR)**: dependencies on upstream/downstream
   behavior, timing, or state that the PR relies on but does not test. These
   are the trust boundaries - "what do we assume about the producer or consumer
   of this information?"

3. **Unverifiable in current state**: behaviors where there is no mechanism
   (test, metric, log, or query) to determine whether they work correctly in
   dev or production. These are the scariest category because if they break,
   nobody finds out until a user reports a symptom.

Optionally include a "How to verify in dev/prod" row with concrete suggestions
(DynamoDB queries, CloudWatch metrics, Datadog monitors) for the unverifiable items.

The verifiability map helps the reviewer answer: "If this PR ships and something
is wrong, how would we know?" If the answer is "we wouldn't," that's a
high-consequence finding regardless of severity.

## Bot-Review Dismissal Capture (calibration loop)

bot-review findings are calibrated through user dismissals, and the agent
cannot observe them (dismissal happens in this conversation after it returns).
When the user dismisses a bot-review-sourced finding WITH reasoning, record it
before moving on:

```bash
bd remember --key="calibration:bot-review:<short-tag>" "<date>: <pattern>. <why dismissed>. <how to recognize next time>."
```

One entry per distinct pattern (same key overwrites; that is the dedup).
Likewise for mx2-skeptic dismissals when the skeptic was in the dispatch:
`calibration:mx2-skeptic:dismissal:<short-tag>`. `/calibrate --agent <name>`
is the review gate that merges these into the agent's calibration file.
