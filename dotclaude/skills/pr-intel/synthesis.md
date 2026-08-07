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
   surfacing engineering-lead feedback 'you posted the same comment with different
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
4b. **CI-catchable filter** (the engineering lead, 2026-05-26 mx2-eng fortnightly: "find things that the linter's gonna catch anyway, or SonarCloud's gonna catch anyway, and then it's like, it's not really worth commenting on, necessarily"): for each finding heading to an inline comment, check whether merged-CI tooling will catch the same issue on the same diff lines. If yes, drop the inline emission entirely and demote to a single-bullet acknowledgment in the Draft Review Summary "Smaller notes" subsection (referencing the CI check by name). The author will see the CI failure with the canonical message; an inline comment that restates it is duplication.

   Catchable patterns (drop the inline, demote to summary if useful):
   - **Ruff**: any finding that maps to a Ruff rule code (E, F, W, I, N, UP, B, SIM, PL, etc.). Ruff runs in `pants tlc` and CI.
   - **MyPy / `pants check`**: typing.Any usage, missing return annotations, incompatible types, untyped function calls. These fail `pants check` and block merge.
   - **SonarCloud rules** (`python:S<NNNN>`): findings that match a rule in `~/.claude/projects/-workspaces-main/memory/sonarcloud-rules.md`. SonarCloud posts these as inline issue comments on the PR. Exception: when SonarCloud has NOT posted on the PR yet (rule reports lag) AND the finding is BLOCKING-class, the inline can stand; otherwise demote.
   - **Pants lint rules**: `pants lint` violations (banned imports, em-dash detection, etc.).
   - **Project-rule violations**: em-dashes are blocked at edit time (block-em-dash.sh). `typing.Any` and bare except are not edit-time-hooked; they surface via MyPy / `pants check` / lint in CI.

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
    - 10: When a finding's verdict rests on a falsifiable framework/library/repo-wide
      or cross-system-state assertion not confirmed locally with high confidence, do NOT
      emit it as a confident verdict. Run the local investigation (verification.md; for
      the cross-system column/field class, the named Cross-System Investigation recipe in
      the "Unverified-Assertion Containment + Cross-System Investigation" section below),
      and let the RESULT drive the finding: confirmed -> state it directly; unresolved or
      contradicted -> emit an explicit UNVERIFIED-ASSERTION finding (honest uncertainty,
      never a confident verdict) and bind the recommendation per output-formats
      (default/--once Comment, --mine "Needs work first", --quick "Warrants careful
      review"). Size-independent: fires even on XS/S where the verification pass is gated
      off (the exact gate #9896 fell through). The dead @claude-bot question form is
      retired; the manual `@claude review once` (managed Code Review) is the out-of-band
      escalation when local investigation is inconclusive. Rule 11 below adds a
      portfolio-level re-examination floor for large PRs.
    - 11: **Size-scaled re-examination floor.** A portfolio-level pass, run ONCE after
      rule 10 has been applied to every finding, not a per-finding rule. Default: no
      action on XS/S PRs and on any PR whose findings are all mechanical/rule, all
      CI-catchable, all bot-dedup confirmations, or all defect-class BLOCKINGs with a
      single visible anchor (citing the rule is the load-bearing posture there). The
      floor fires ONLY when (a) the PR is M+ (size in {M, L, XL, 2XL, 3XL}), AND (b) at
      least one substantive net-new finding exists that is none of the excluded classes
      above. When it fires, re-examine those findings to confirm none shipped a
      falsifiable framework/repo or cross-system assertion AS A CONFIDENT VERDICT without
      the rule-10 investigation having run; any that did downgrades to an
      UNVERIFIED-ASSERTION finding per rule 10. This is a self-audit of the reviewer's own
      output (the dead @claude collaborative-routing form is retired); it never posts a
      bot question. Disposition surfaced across the 2026-06-04 parallel reviews
      (9646/9627/9641), whose first-pass briefings each produced zero `@claude` questions
      despite substantive local analysis.

    The compression target: design-judgment findings default to ≤ 25 words and
    ≤ 2 sentences (calibrated 2026-05-13 against the engineering lead's corpus ceiling),
    often a bare question. Defect-class BLOCKING and design-judgment findings
    that require a named alternative are the only legitimate paths to longer
    comments. When even those don't fit, the finding renders as a longer direct inline
    comment (the dead bot-invoked form is retired); rule 10 governs only the
    unverified-assertion case, not comment length.

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
    | `module-cohesion-reviewer` | bot-surfaced | speed-amplified only if the smell is reachable from the single-file diff (e.g. a filename that lies about its contents) |
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
    match the engineering lead's explicit "send back quickly" classes:
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
    - **Capability duplication**: the orchestrator Active Reuse-Search
      (dispatch.md) or any specialist names an existing endpoint, service,
      or shared-library symbol that already owns a capability the diff
      adds. The strongest send-back class there is: refining a duplicate
      wastes the entire downstream review. Sourced from `architecture.md`
      Reuse Across Boundaries, not from the engineering lead's guide. The backing inline
      comment must carry the incumbent `file:line` AND the literal search
      terms tried (output-formats.md Draft Inline Comments).

    Add `front_door: true` as an attribute on the finding object; preserve
    its severity (BLOCKING/DISCUSSION/MINOR) separately. The two tags are
    orthogonal: a type smell can be FRONT-DOOR + DISCUSSION (cheap to fix,
    but ripples), a security finding is NOT-FRONT-DOOR + BLOCKING (just
    fix inline). Boolean-param smells, pragma misuse, and exception-design
    smells are NOT Front Door; they're iterate-inline findings. The
    engineering lead explicitly puts the "send back quickly" framing on
    description (#1) and types (#2); the rest are inline-iterate.

    Description-quality issues do not flow through this step because Phase 0
    short-circuits before specialist dispatch. If Phase 0 passed and Front
    Door is empty, the PR is past the engineering lead's send-back gate.

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
    engineering lead's corpus pattern (median ~3 substantive comments per PR with headroom
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
    that forced promotion: a body paragraph previewed an inline finding and was
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
   The engineering lead's two highest-leverage moves on PR #8931 were both provenance questions
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
[Fix this →](https://claude.ai/code?q=<URI_ENCODED_INSTRUCTIONS>&repo=<company>/docr)
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

## Unverified-Assertion Containment + Cross-System Investigation

The job this section does, preserved from the retired @claude-bot form: keep pr-intel from
posting a confident-but-wrong verdict on a claim it could not verify. The mechanism is no
longer a bot question (PR #9888 removed the self-hosted @claude Q&A bot, and the managed
Claude Code Review replacement is a full-PR reviewer, not a question-answerer). The
mechanism is now an explicit UNVERIFIED-ASSERTION finding whose result drives the verdict,
plus a forced local investigation for the one class that has a named recipe.

**Why a positive trip-wire, not self-flagged doubt.** PR #9896 was CONFIDENT
INCORRECTNESS, not recognized uncertainty: the review read a Pydantic field name
(`OCR_Detected_Type__c`) and confidently asserted the Redshift mirror column existed; it
does not (the mirror uses the simplified snake_case `ocr_detected_type`). A containment
that fires only when the agent volunteers doubt never fires on a confidently-wrong agent.
So the trip-wire below keys on an OBSERVABLE DIFF SIGNAL, not on the agent's self-assessed
certainty.

### Cross-System Investigation (CSC) trip-wire

FIRES when ALL of the following are observable in the diff under review:
- (a) the diff adds or modifies a query (SQL `SELECT`/`JOIN`/`WHERE`, a dyntastic/boto3
  `FilterExpression`, or any column-dependent path), AND
- (b) it targets a Salesforce/DynamoDB-mirror surface: a `sf.<schema>.<table>` qualified
  name (literal OR env-templated like `sf."{SF_ENV}".table`), a `*-sf_sync-cache_dyn-*`
  DynamoDB table, or a dyn2red replica, AND
- (c) a finding OR an implicit APPROVE rests on a specific NAMED column/field existing in
  that table.

The fire condition is the REFERENCE in the diff, not the agent volunteering doubt: the
agent does NOT get to classify the column as "confirmed locally" and skip the
investigation. Does NOT fire on: columns the same diff defines (CREATE TABLE / migration),
key-only DynamoDB lookups, a reformat of an unchanged query, or non-mirror application
tables. Env-templated `sf` schema queries fire the SAME as literal (correct-fire; the
mirror-table reference is the discriminator, not literal-vs-interpolated schema).

### CSC investigation (worktree-executable; the result drives the verdict)

When the trip-wire fires, run this BEFORE stating the column exists with confidence:

1. **Resolve the expected mirror column name.** If the asserted name is a raw Salesforce
   field (has `__c` or PascalCase), call `simplify_sf_name` (a pure worktree function,
   `src/python/mx2/salesforce/utilities.py`) to get the snake_case form
   (`OCR_Detected_Type__c` -> `ocr_detected_type`). If it is already snake_case, use as-is.
2. **Confirm via a sibling query in an UNCHANGED file.** Grep for the resolved name against
   the SAME table in a file NOT changed by this diff (exclude `git diff --name-only` to
   avoid circular self-confirmation: in #9896 the only repo match was
   `med/review/matter_sync.py:24`, which was itself in the diff under review).
3. **The result drives the finding** (there is no "cap" to hold or clear):
   - asserted name matches the resolved-and-grep-confirmed name -> column confirmed; state
     it directly; the verdict may be Approve on its own merits.
   - mismatch (raw field name vs snake_case, casing) -> UNVERIFIED-ASSERTION finding; the
     verdict reflects it (default/--once Comment, --mine "Needs work first", --quick
     "Warrants careful review").
   - unresolvable (no consuming model with a generator, hand-written SQL, no sibling in an
     unchanged file) -> UNVERIFIED-ASSERTION finding + the manual escalation note below.

Reading a consumer model's `model_config` `alias_generator` is a SECONDARY hint only,
never the primary resolver: the Redshift query's reader is often a dyntastic model with no
`alias_generator` (the generator lives on the SF-sync write model in another service), so
"find the consuming model and read its alias_generator" does NOT resolve the seed case.

### General falsifiable claims (no named recipe)

For a falsifiable framework/library/repo-wide assertion outside the cross-system column
class (e.g. "all callers migrated", "field X is unused", the 9451 "Starlette default
TestClient is loopback" case), there is no named recipe and no local oracle. Surface it as
an UNVERIFIED-ASSERTION finding (honest uncertainty, verdict capped per mode); the manual
`@claude review once` is the out-of-band escalation. PRESERVE-DISSENT: retiring the bot is
a genuine coverage reduction for this general class (the bot was a repo-HEAD oracle for
arbitrary claims). The COMMENT-on-uncertainty finding is the long-tail substitute, strictly
weaker than a fresh repo-HEAD read. Track recurrence; do NOT re-animate the bot. Grow named
recipes from observed failures instead.

### Growth rule

The CSC recipe is one named entry, seeded by #9896 (mark it Observed). Add a new named
recipe ONLY from an observed failure (mirror the static-analyzers.md Growth rule: tag each
entry Preventive vs Observed so provenance stays auditable). Do not pre-populate guessed
classes; a generic "verify column names" prompt yields "looks correct" and catches nothing.

### Manual escalation (live confirmation)

When local investigation is inconclusive (a live-table check is needed, or a general-class
claim has no recipe), the briefing carries a one-line note: post `@claude review once` as a
top-level PR comment (managed Code Review; NEVER bare `@claude review`, which subscribes the
PR to a paid review on every push) to get an out-of-band repo-HEAD pass. This is operator
discretion, not an autonomous pr-intel action; it never gates or withholds the first-round
verdict.

### Form of an UNVERIFIED-ASSERTION finding

Renders as a normal Draft Inline Comment at the suspect line, opening with the
tool-attribution lede (the `block-unattributed-review-comment*` hooks require it), stating
the resolved-name reasoning and what was and was not confirmed. No `@claude` token is
required in the review body (the dead posting-side workflow filter is retired). The full
briefing context (severity, classification, specialist source, the resolved name, what the
grep confirmed) stays in the briefing-context section per output-formats.md. `--mine`
renders it under "Issues to Fix Before Review" as a pre-submission column-confirm item;
`--quick` (no inline section) expresses it only as the Verdict nudge.

See `output-formats.md` for the unverified-assertion draft template and the Comment-Shape
Decision Table note.

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

"Clean findings" here means no BLOCKING or high-consequence findings, not zero findings.
A first-round XS/S PR whose only findings are non-blocking (MINOR or low-consequence
DISCUSSION) defaults to Approve-with-comments via approve-while-logging-dissent
(output-formats.md), not Comment: log the nit inline and approve. Reserve first-round
Comment for L+/novel/external-contract PRs, for any BLOCKING/high-consequence finding,
or when a finding is a genuine open question the author must answer before the change
is sound.

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

### Peer-Reviewer Findings Baseline (delta re-review)

When a non-mslshao reviewer has already posted a SUBSTANTIVE findings list on the PR
(an inline-comment set, or a review-body findings list, especially an automated
multi-agent / "@claude-fix-round" review), treat it as a dedup-AND-verify baseline,
not merely a dedup source. On a PR the author has since iterated, the highest-value
output is the DELTA: for each of the peer's findings, verify against CURRENT HEAD
whether it is fixed or still-live (read the code, reproduce if cheap), and make that
fixed-vs-still-open split the spine of the review. Re-deriving from scratch buries the
one signal that matters (which already-flagged items the author's fixes actually
resolved). A peer finding still-live after an explicit fix round is a strong
Comment/Request-Changes signal; a now-resolved one gets no re-raise (same moot gate as
bot-reactions.md). Spend fresh specialist dispatch on the angles the peer's pass did
NOT cover. Distinct from the Third-Party Approval Quality Gate above (that governs
whether a peer APPROVAL defers analysis; this governs how a peer's FINDINGS feed the
delta). Grounded: PR #10807 (2026-07-23) - vin's automated-workflow findings list had
been through an @claude fix round; the review's value was verifying still-live-at-HEAD
(find_superseded soundness bug still-live; routes AttributeError fixed).

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

**Front Door rationale.** A FRONT-DOOR finding (type/model smell,
large-refactor methodology gap, or capability duplication; see step 7b) is
not always a runtime defect,
but downstream review effort depends on it being right. Approving with
inline comments invites the author to address the type smell in the same
round as 5 other comments on code that may itself need re-shaping once the
type is fixed. The engineering lead's framing: "send them back, and quickly." The
recommendation lands at Comment with the Draft Review Summary opening
"the priority for this round is X; let's iterate on that before deeper
review." BLOCKING + FRONT-DOOR still resolves to Request Changes (BLOCKING
is more restrictive). FRONT-DOOR + DISCUSSION/MINOR resolves to Comment.

**Settled-type carve-out.** The Comment default assumes the smell is
UNSETTLED and would ripple: the author re-shapes the type, surrounding code
shifts, so a deeper read is premature. When the type decision is already
settled (author self-reviewed and it is in HEAD), the review is otherwise
complete, behavior is verified benign, and the only live front-door item is
an inaccurate description line plus non-blocking type polish, Front Door does
NOT override approve-while-logging-dissent: route to Approve with the
description correction and type nits logged as non-blocking. The test is
whether the finding still forces a re-shape before deeper review can proceed;
if the review is already done and nothing ripples, it is a followup, not a
gate. Pairs with calibration:pr-intel-re-review-approve-default-2026-05-27
(same over-default-to-Comment outcome, different mechanism). Recurrence:
2026-06-26 PR #10143 (a settled, self-reviewed typing pass mis-described as
"pure move" drew a Comment default; the proportionate call was Approve).

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

9. **Goal-fit and mechanism necessity (does this need to exist at all?).** Anchor
   on the PR's stated goal (the "why" in the description or ticket), then ask the two
   questions the how-well-built lenses skip: (a) does the implementation actually
   achieve that goal, or only a narrower or adjacent slice of it? (b) is there a
   materially simpler path to the same goal that the deployment platform, runtime,
   framework, or an existing service ALREADY provides, so part of this diff is
   redundant? Before evaluating HOW a newly added mechanism is built (a custom client,
   helper, metric-submission path, table, queue, or abstraction), confirm the
   capability is not already provided for free by the Lambda layer/extension or a
   sidecar, the framework, a managed service, or a published boundary. Signal: "this
   PR builds mechanism X to achieve goal G, but the platform already provides Y that
   achieves G, so X may not need to exist." Reviewer question: "does this need to exist
   at all, given what the platform already does?" This is the highest-leverage surface:
   a review that only checks whether a mechanism is well-built will approve a mechanism
   that should not exist, and the how-it-is-built debate (this import vs a shared
   package) is wasted effort when the answer is delete it. Detected by reading the PR's
   goal, then checking the runtime and platform primitives (the Lambda extension env
   vars, framework features, existing service endpoints) against every net-new mechanism
   the diff introduces. (2026-07-23, PR #10911: a folio Lambda submitted a custom
   Datadog gauge through an HTTP client imported cross-service from sf_sync, when the
   Datadog Lambda extension already forwarded the service's structured logs; the review
   debated how to import the client, never whether the metric path was needed.)

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
