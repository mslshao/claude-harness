# Synthesis

After specialist results return, synthesize into the final briefing.

## Synthesis Steps

1. **Parse and deduplicate** structured FINDING blocks from each specialist
2. **Deduplicate against existing PR comments** - Compare each finding against
   inline review comments and any review body text from prior reviews. This
   includes bot comments (Sentry, Datadog, Copilot) - if a bot already flagged
   the same concern, treat it the same as a human comment for dedup purposes.
   For each finding that overlaps with an existing comment:
   - If the existing comment covers the same concern adequately: **drop the finding
     from Draft Inline Comments entirely**. It may still appear in the Draft Review
     Summary as an acknowledgment ("already flagged by [author], not adding a separate
     inline comment"). This applies equally to bot comments and human comments.
     "Confirming" a bot finding as an inline comment is still duplication; the review
     summary acknowledgment is sufficient signal (see reviewer-discipline.md lesson #13).
   - If the finding adds genuinely distinct information (different root cause, broader
     impact, or a fix the existing comment missed): **keep it**, but prefix the draft
     comment with "Adding to [author]'s point above:" or similar threading language.
   - If the existing comment is stale (non-HEAD commit) and the finding addresses
     the same code post-update: **keep it** as a fresh assessment.
3. **Resolve disagreements** - surface both perspectives, don't silently pick sides
4. **Categorize by GitHub surface** - specific file+function = inline comment; architectural = review summary
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

    The compression target: design-judgment findings default to ≤ 25 words and
    ≤ 2 sentences (calibrated 2026-05-13 against the the senior-reviewer corpus ceiling),
    often a bare question. Defect-class BLOCKING and design-judgment findings
    that require a named alternative are the only legitimate paths to longer
    comments.

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
6. **Verify grounding** - see [grounding.md](grounding.md)
6b. **Apply series context** - if `series_context` exists, check each "unused export"
    or "dead code" finding against `consumed_exports`. Exports consumed by sibling PRs
    are not orphaned; reclassify as a design review surface question, not a finding.
7. **Assign severity** - BLOCKING / DISCUSSION / MINOR
8. **Assess consequence** - for each DISCUSSION finding, evaluate reversibility
   and consequence to determine whether it affects the review recommendation.
   See Consequence Assessment below.
9. **Identify design review surfaces** - extract patterns that need human judgment
   rather than mechanical fixes. See Design Review Surfaces below.
10. **Build verifiability map** - classify what the PR proves, assumes, and leaves
    unverifiable. See Verifiability Map below.

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
   a senior reviewer's two highest-leverage moves on PR #8931 were both provenance questions
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
| DISCUSSION | High consequence | Comment (no approval stamp) |
| DISCUSSION | Low consequence | Approve with Comments |
| MINOR (any) | any | Approve with Comments |
| No findings | - | Approve |

When multiple findings exist, the most restrictive recommendation wins.

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
