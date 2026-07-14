# Output Formats

<!-- summary key: required-sections -->
A default-mode render must contain, in order: the `## PR #<N>: <title>` header block, Scope, Review Recommendation (metadata lines only), a fenced Draft Review Summary, Draft Inline Comments (or an explicit "None"), and a Verdict. This holds for every size and even for an Approve with zero findings.
<!-- /summary -->

## Mode: Reviewing Others (default)

This template is the briefing for BOTH default and `--once`; the content is identical and both stop here (one-shot). The dead `@claude` verify loop is retired (PR #9888 removed the self-hosted bot); an unverified cross-system or falsifiable assertion surfaces as an UNVERIFIED-ASSERTION finding (synthesis.md "Unverified-Assertion Containment + Cross-System Investigation"), not a posted bot question.

```
## PR #<number>: <title>
Author: <name> | Base: <branch> | Draft: yes/no
Adds: +N | Removes: -N | Files: N [if stale files: "(M net-new, K already on main)"]
[if PR-specific CI failures: "CI: N PR-specific failure(s) (<check names>)"]
[if checks pending with no failures: "CI: N check(s) still running"]
[if prior reviews exist: "Revision: rev <current_commits> (delta +N commits since last review on <date>)"]
[if third-party reviews exist on the PR: "Existing reviews: <EVENT> by `<handle>`<, ...> [(treated as non-signal: <reason>)]". The non-signal annotation is required when the Third-Party Approval Quality Gate in synthesis.md fails for that approval. Required when any third-party review is APPROVED; omit only when no third-party reviews exist.]

### Prior Reviews
[Present ONLY when `bd memories pr-<N>` returned one or more `review:pr-<N>:*`
entries. Omit entirely if first-round. List oldest to newest. Keep each line to
one row; the goal is orientation, not reproduction.]

- <YYYY-MM-DD> <EVENT> (rev <commit_count>, <posted_inline> inline + <body_fold> body): <findings_summary one-liner>
- ...

### Service Context
[Present when CLAUDE.md or README was found for the service. Omit if not found.
3-5 lines max. Orients an external reviewer to the system being modified.]

**<service name>**: <1-2 sentence description of what this service/pipeline does>
- **Dependencies**: <key infra: DynamoDB tables, S3 buckets, upstream/downstream>
- **Docs**: <Confluence link, Datadog dashboard if available>
- **Gotchas**: <known constraints or design quirks relevant to this PR>

### Scope
[Modules touched, blast radius: low/medium/high, 2-3 lines max. The changeset only: what the PR touches and its blast radius. No CI/approval-gate state (that is the header line), no review-process narration.]

### Sequence Diagram
[Present ONLY when size is M+ AND multi_service is true AND the generator produced
a valid grounded diagram. Omit entirely when not all conditions are met or when
the generator emitted a fallback sentinel. See diagrams.md for grounding rules.]

```mermaid
sequenceDiagram
    participant <service_a>
    participant <service_b>
    <service_a>->><service_b>: <verb describing call or event>
    Note over <service_a>,<service_b>: NEW | CHANGED
```

### Front Door
[Present ONLY when at least one finding from synthesis step 7b is tagged
`front_door: true` (type/model smell, large-refactor methodology gap). Omit
entirely when empty. Position: above Review Recommendation so the reviewer
sees it before the verdict header.]

The priority for this round is fixing the items below before iterating on
the rest. Type/model decisions ripple downstream; a large-refactor PR
without a methodology statement cannot be spot-checked. the engineering lead's framing:
send back quickly. The Draft Review Summary opens with this framing.

| Class | Anchor | One-line summary |
|---|---|---|
| types / methodology | `file:line` OR `PR description` | <what's wrong, what to do instead> |

[Each row preserves the underlying severity in the briefing context for the
inline comment that backs it (BLOCKING / DISCUSSION / MINOR), but the Front
Door section itself does not show severity. The fix-this-first framing is
the signal.]

---

### Review Recommendation
**Action**: Request Changes | Comment | Approve with Comments | Approve
**Blocking**: N | **Discussion (high-consequence)**: N | **Discussion (low-consequence)**: N | **Minor**: N | **Front Door**: N
**Provenance**: Speed-amplified: N | Bot-surfaced: M
**Decision count**: N (ceiling: 5)

[This section is metadata ONLY: the four lines above ARE the section. No
parenthetical glosses on values (stop-validate-pr-intel.sh flags any label
value over 15 words as review-rec-prose; the 2026-06-09 firing came from
glosses this template itself used to carry). Speed-amplified = reviewer
would have caught from diff reading; bot-surfaced = required live-state,
multi-page docs, or cross-file analysis. Decision-count ceiling is 5 per
reviewer-discipline.md T6; if > 5, the compression gate consolidated (see
synthesis.md step 11). Do not append a rationale paragraph recapping the
findings or the verification work; that substance lives in the relevant
inline comment's briefing context (or in the Draft Review Summary if the
finding has no inline). A prose recap here is the top duplication source
and is forbidden.]

[Front Door count is the number of findings tagged `front_door: true` in
synthesis step 7b. When > 0, the Action defaults to Comment with
back-to-author framing per synthesis.md Recommendation Table. BLOCKING is
still more restrictive (Request Changes wins).]

---

### AC Compliance
[Present ONLY when a Jira ticket was hydrated. Omit entirely if no ticket was found.]

**Ticket**: <KEY> - <summary> (<link to ticket>)

| Criterion | Status | Notes |
|-----------|--------|-------|
| <AC text, abbreviated> | Met / Deviation / Gap / N/A | <what matches or diverges> |

[If all criteria are met, a single line: "All acceptance criteria verified in the diff."
If deviations exist, each gets a row with a brief explanation of what differs.
"Gap" means the criterion has no corresponding code in this PR.
"N/A" means the criterion applies to a different PR or phase.]

---

### Design Doc Compliance
[Present ONLY when a Confluence design page was hydrated. Omit entirely if no design
doc was linked in the PR body.]

**Design doc**: [<page title>](<Confluence URL>)

| Spec element | Status | Notes |
|--------------|--------|-------|
| <parameter, response shape, or logic step> | Matches / Deviation / Gap | <what matches or diverges> |

[If all spec elements match, a single line: "Implementation matches the design spec."
If deviations exist, each gets a row. Keep rows to the behavioral differences that
matter; don't enumerate every matching parameter.]

**Unresolved design comments** (<N> open):
- <author>: "<abbreviated comment>" (on: "<annotated text>")

[List unresolved inline and footer comments from non-author reviewers. These represent
design-level feedback that may not be reflected in the implementation. If all comments
are resolved or from the author, note "All design comments resolved."]

---

### Draft Review Summary

```
<Ready-to-paste text for the top-level review body. Lead with the explicit verdict as the very first words: for a positive review, open with the approval signal itself (`LGTM` / `looks good`), never a descriptive build-up that only arrives at the verdict (mirror the human reviewer gate: `LGTM. The optional thing I'd consider is X, but this is strictly beneficial.`); any optional suggestion follows the signal and is explicitly flagged optional. For a non-approval, open with the one-line overall assessment. Then pointers to inline comments by line number plus concerns that don't fit inline (PR description suggestions, AC deviations, process notes the author can act on). The body must NOT restate findings that already have an inline comment; if a concern belongs inline, the body says "see inline on line N" rather than reproducing the substance. Collaborative tone: acknowledge what the PR does well before raising concerns. Written in second person to the PR author. Target: 60-100 words for a clean PR with 1-3 concerns, ≤ 150 words for a PR with multiple distinct issues that need separate framing. Hard ceiling: 200 words; beyond that, the inline comments should carry more weight and the summary should compress. No severity tags. Strip the Michael verbosity tells from reviewer-discipline.md (V1 meta-preamble, V2 both-sides-with-concession, V3 trailing since/because justifications). When AC deviations exist, mention them naturally: "The dedup logic handles all entries rather than only complete=True entries per the ticket AC, was that intentional?">
```

**Posted-body is standalone (the GitHub artifact).** The fenced Draft Review Summary is the ONLY prose `/post-review` posts to GitHub, alongside the inline comments. Every other briefing section (Design Review Surfaces, AC Compliance, Verifiability Map, Open Threads, Verdict) is reviewer-facing and does NOT post. So the body must be self-contained: never reference another briefing section by relative position ("the two design questions below", "see the AC table above"); a reader on GitHub has no "below". If a Design Review Surface warrants the author's attention, fold its question into the body text itself rather than pointing at the unposted section. Same root cause as the word targets above (the body is read by teammates without the briefing context): compress it hardest and make it complete on its own. PR #9665 (2026-06-24): a "two design questions below" reference dangled because the surfaces section is not posted, caught and folded in only at post time.

**One-home rule (body, inline, and outer prose).** Every finding has exactly ONE home: its inline comment, or the Draft Review Summary when it has no inline. The Review Recommendation header, the Verdict, the Scope, and any outer briefing prose reference a finding by line number; they never re-narrate its substance or its verification rationale. If a finding renders inline, the body's reference to it is a pointer ("see inline on line 37"), not a paraphrase. The 9304 anti-pattern (2026-05-21) is canonical: the `sqlworkbench:ListDatabases` question rendered substantively in BOTH the body's numbered list AND inline:37 with ~80% prose overlap. Both venues contained the same hedge ("Either way it's harmless") and the same evidence (the `RedshiftDataApi` statement reference). Body must compress to a pointer in this case, not duplicate. The pre-emit check at synthesis time (enforced as synthesis.md step 11b, the body-inline dedup pass): for each body sentence, ask "does an inline comment share both this core claim AND its anchor?" If yes, replace it with `see inline on line N` or drop it. See `bd memories calibration:pr-intel-voice-body-inline-duplication-2026-05-21`.

**No process meta-narration in the body.** The Draft Review Summary carries the assessment and pointers to findings, never narration of the review process itself. Three recurring noise classes to strip before emitting: (1) do not reference a bot comment in the body AT ALL: not its substance, not that you agree, not that you reacted ("reacted 👍", "confirming the bot's flags are accurate", "Copilot's note is fair, thumbs-up'd rather than repeat it"). The Bot Reactions phase is the entire signal: a `+1`/`-1` says "the bot was right/wrong" without spending a word of body prose, and the author already sees the bot's own comment. If a bot finding genuinely warrants more than a reaction, that is an inline comment carrying NEW analysis, never a body paraphrase. (2) Do not include "Reviewed for X / no concerns identified" positive-confirmation prose UNLESS `mx2-security-auditor` was actually dispatched (the sole sanctioned exception, SKILL.md Section Conditionality); a non-security specialist (devops, style, etc.) returning clean is not summary-worthy and reads as unactionable filler. (3) Do not narrate CI or quality-gate status in the body or Scope: not "CI is green", not the description-check failures, not the Require-Reviewers / approval gate, not "merge unblocks on approval", and not the SonarCloud (or any quality-gate) pass/fail, INCLUDING a "the gate is red but it's pre-existing / misattributed / not yours to fix" clarification. The author sees the checks tab; passing or pending CI is not review signal, the approval gate is mechanical, and explaining away a red gate is still gate narration, not a finding. A static-analyzer issue earns body or inline space ONLY when it lands on a changed line AND is independently actionable (then it routes as a normal finding via the Static Analyzer Pre-Check, attributed to the tool); a gate failure driven by pre-existing or line-shifted issues outside the diff gets NO mention at all. The only CI mention is the terse header line, and only for PR-specific failures (see the header template). Classes (1) and (2) were stripped by the user on PR #9885 (2026-06-15); class (3) plus the sharpened (1) on PRs #9993/#9996 (2026-06-18); the gate-misattribution sub-case on PR #9979 (2026-06-18), where a correct "the red SonarCloud gate is pre-existing, not yours" paragraph was still cut as noise (the author has eyes on the gate).

---

### Draft Inline Comments

Ready-to-post comments, grouped by file. Each comment is the actual text
to paste on the PR. The reviewer can copy them verbatim or edit before posting.

**Comment budget**: Scale to the number of real findings, not to a fixed cap. Zero is a legitimate count: a 2XL infra PR with nothing to flag should get an approval with no inline comments, not padded findings to meet a typical-range floor (empirical case: PR #9022, 696-line Redshift Serverless PR approved with zero inline comments by a high-trust reviewer). Typical range when findings exist: 2-3 for a clean PR with minor observations, 5-8 for one with real issues, 10-15 for a large PR with multiple discussion-class concerns. Beyond 15, consolidate related findings into the review summary or use cross-references to point multiple sites at the same canonical thread (P13 in reviewer-discipline.md). BLOCKING findings always get a comment regardless of count. When trimming, drop MINOR findings first. When in doubt, drop the comment: a PR with two precise questions is more useful than one with eight padded observations.

**Structural variation**: Not every comment needs the same shape. Mix these forms (examples lifted from the the engineering lead corpus across PRs #8931, #8741, #8066):
- Bare question: "where does this come from?", "why?", "intentional?", "must they be?"
- Short observation: "this silently drops the error context from the original exception."
- Suggestion with concrete anchor: "consider extracting a `create_worker` function in another module."
- Cross-reference: "My `<agent>` specialist flagged the same thing as my note below" (point at the canonical comment instead of repeating; the attribution lede is still required, so a bare "see suggestion below" is hook-blocked at post time)
- Hedged proposal: "Maybe X? (I'm unclear what Y is for, so maybe not)"
- Pattern-named smell: "this is craving some DI", "IsA vs HasA?", "roundabout way of calling verify()?"

Avoid uniform [SEVERITY] / title / code quote / explanation structure on every comment. Use severity tags in the briefing context (for the reviewer) but omit them from the pasteable text (for the PR author). A human reviewer does not prefix comments with [BLOCKING].

**Tool-source attribution rule** (the engineering lead 2026-05-26 mx2-eng fortnightly: tool-discovered findings must be posted as the tool, not as Michael):

Every finding emitted by pr-intel passed through a specialist agent or an orchestrator pattern check; none of them came from Michael's unaided reading. Treat ALL of them as bot-discovered for voice purposes. Open each draft inline comment with an explicit attribution prefix naming the source. Examples:

- Specialist-source: "My `silent-failure-hunter` specialist flagged a potential silent failure here: ..." / "Cross-file analysis (via `bot-review`) surfaced that ..." / "My `mx2-code-reviewer` pass flagged this pattern: ..."
- AC compliance: "AC item N expects X, the diff implements Y; was that intentional?"
- Spec compliance / design doc: "The design doc specifies X (page section 3), this implementation returns Y; intentional divergence?"
- SonarCloud: "SonarCloud flagged this as `python:S<code>`: ..."
- bot-review: "Cross-file consumers of this symbol assume X (`<consumer file:line>`); this change weakens that invariant: ..."
- Orchestrator pattern check (Pre-Synthesis Analysis Patterns 1-6 in synthesis.md): "Pattern check flagged a frozen-Pydantic mutation here: ..." / "Opaque constant detected: where does this come from?"
- Multi-specialist convergence: when two specialists flag the same finding, still lead with ONE specialist and note the other mid-sentence (e.g. "My `agent-a` specialist flagged this, and `agent-b` independently agreed: ..."). The attribution hook (`check_review_attribution.py`) matches the singular "My `<agent>` specialist <verb>" shape; a plural "My `a` and `b` specialists both flagged ..." lede fails the matcher and blocks the post at write time (observed 2026-06-24, PR #9664).

The attribution prefix is the lede; the finding follows. A human reading the posted PR can tell at a glance that a tool surfaced the finding rather than Michael's unaided reading, which is the trust signal the engineering lead asked for. The reverse failure (an automation-discovered finding posted in Michael's voice with no signal that a tool fed it) is the exact pattern the engineering lead called out by name at the 2026-05-26 fortnightly.

The speed-amplified vs bot-surfaced provenance classification (synthesis.md step 5d) stays in place for telemetry and audit (the `bot_surfaced_count` and `speed_amplified_count` fields /post-review writes to bd memory). It no longer drives voice. The classification answers "could Michael have caught this from careful single-file reading?", which is useful for understanding pr-intel's value-add. The voice rule answers "did Michael actually catch this himself?", and the honest answer is no for everything that came through a specialist or orchestrator check.

The only voice exception: comments Michael personally writes during his editing pass (after pr-intel output is rendered but before /post-review consumes it). Those stay in Michael's voice with no attribution prefix, because they ARE Michael's unaided judgment. Pr-intel itself does not emit them.

This is structural enforcement of `review-voice.md` "Attribute tooling findings to tooling" and reviewer-discipline.md T5 (Transparent Tooling). Replaces the prior speed-amplified-no-attribution rule (which let bot findings ride under Michael's voice when the classifier judged them reachable from diff reading); the 2026-05-26 the engineering lead feedback surfaced that even those findings should be attributed because Michael didn't actually catch them himself, the tool did.

Format: file heading, then numbered comments. Each comment has a target line, a fenced block with the ready-to-paste text, and a briefing-context section the reviewer can read but does not post.

#### `strategy.py`

1. **Line 42** (`method_name`)

   ```
   <Ready-to-paste comment text. Varied voice: direct statement, question, or suggestion. No severity tag. Length obeys the Ceiling calibration below (~25-30 word corpus ceiling, even for BLOCKING/DISCUSSION): 1-2 sentences for MINOR, 2-3 tight sentences for BLOCKING/DISCUSSION (not multiple paragraphs). One thought per sentence; no teaching, restating, or "not hypothetical" hedging prose. This is what gets posted. Opens with an explicit attribution prefix naming the specialist or orchestrator pattern that surfaced the finding, per the Tool-source attribution rule above. The Classification line below is telemetry only; both speed-amplified and bot-surfaced get attribution prefixes.>
   ```

   **Briefing context**
   [BLOCKING] ✓ VERIFIED | Classification: bot-surfaced (specialist: `silent-failure-hunter`, verification path: cross-file Grep)
   `ClassName` > `method_name` - `<verbatim code quote>`
   <1-2 sentence explanation for the reviewer, not posted>
   Agent checked: <what was grep'd/read to verify this>

2. **Line 78** (`other_method`)

   ```
   <Ready-to-paste comment text.>
   ```

   **Briefing context**
   [MINOR] ○ DIFF-VISIBLE | Classification: speed-amplified (specialist: `mx2-code-reviewer`, verification path: single-file diff inspection)
   `ClassName` > `other_method` - `<verbatim code quote>`
   <explanation>
   Reviewer verify: <what to check to confirm this>

#### `processor.py`

3. **Line 15** (`process_message`)

   ```
   <Ready-to-paste comment text, phrased as a question for the PR author.>
   ```

   **Briefing context**
   [DISCUSSION] ? QUESTION | Classification: bot-surfaced (specialist: `mx2-pr-precedent`, verification path: prior-PR archaeology)
   `process_message` - `<verbatim code quote>`
   <explanation>
   Agent searched: <what was searched, why inconclusive>

4. **Reply on line 23** (`triggers.py` thread continuation)

   ```
   <Ready-to-paste reply text, adds genuinely new context to the prior thread.>
   ```

   **Briefing context**
   [DISCUSSION] ? QUESTION | Classification: speed-amplified (specialist: `mx2-code-reviewer`, verification path: single-file diff inspection)
   Reply target: comment 3275599283 (mslshao 2026-05-20 on `docket_sync/update_scheduler/triggers.py:23`)
   `triggers` > `Trigger` - `<verbatim code quote>`
   <explanation of what new context the reply adds beyond round-1>
   Reviewer verify: <what to check to confirm this>

5. **Line 40** (`THEN file."OCR_Detected_Type__c"`), unverified-assertion form

   ```
   My `mx2-code-reviewer` pass flagged a cross-system column reference to verify: this
   selects `file."OCR_Detected_Type__c"` from the `sf.prod.doc_file_info` Redshift mirror,
   but that mirror uses the simplified snake_case name `ocr_detected_type` (via
   `simplify_sf_name`), not the raw Salesforce field name. A sibling query confirms it:
   `med/review/matter_sync.py:24` selects `ocr_detected_type` from the same table. As
   written this column does not exist and the query errors at runtime; did you mean
   `ocr_detected_type`?
   ```

   **Briefing context**
   [BLOCKING] ✓ VERIFIED | Classification: bot-surfaced (specialist: `mx2-code-reviewer`; Cross-System Investigation resolved `OCR_Detected_Type__c` -> `ocr_detected_type` via `simplify_sf_name`, grep-confirmed `matter_sync.py:24` in a file unchanged by the diff) | Form: unverified-assertion (CSC trip-wire fired; mismatch, so the verdict is Comment)
   `get_query` - `THEN file."OCR_Detected_Type__c"`
   The CSC investigation resolved the expected mirror column and a sibling query in an
   unchanged file confirms `ocr_detected_type` is the real name; the asserted
   `OCR_Detected_Type__c` is the Salesforce field name, so the verdict reflects the
   mismatch and is Comment. No `@claude` token in the body is needed (the posting-side
   workflow filter is retired); the manual `@claude review once` note would be attached
   only if a live-table check were required, which it is not here.

**Reply-target convention**: when synthesis.md Step 2's position-based
same-author dedup rule routes a finding to be threaded under a prior-round
comment, the briefing-context section opens with a `Reply target: comment
<prior_comment_id> (<author> <date> on <path:line>)` line. /post-review
Step 1 extraction MOVES these entries to a separate `inline_replies` list
so they do NOT go into the atomic review POST in Step 3 (the GitHub atomic
endpoint does not accept `in_reply_to_id`); Step 3.6 posts each one
separately via `POST /repos/{owner}/{repo}/pulls/{N}/comments/{prior_id}/replies`.
The `**Line N**` heading on a reply-target entry is briefing-context only
(the line is inherited from the parent comment at post time); the
`Reply target:` line is the load-bearing routing signal. See pr-intel
`synthesis.md` Step 2 for the upstream rule and
`bd memories calibration:pr-intel-same-line-dedup-2026-05-20` for the
canonical 9221 anti-pattern this prevents.

---

### Bot Reactions (for /post-review)
[Present ONLY when the Bot Reactions phase classified one or more bot
comments. Each entry tells /post-review to react with `+1` (thumbs-up: bot
finding correct) or `-1` (thumbs-down: bot finding false positive) on that
specific bot comment. This section does NOT appear in the posted review
body; it is /post-review's input list for Step 3.5. Omit entirely if no
bot comments were classified. See bot-reactions.md for the 5-category
decision tree that produces this list.]

- `<bot_name>` comment `<comment_id>` (endpoint: `<pulls|issues>`,
  reaction: `<+1|-1>`): "<finding_summary>"
- ...

[Example:
- `copilot` comment `2843291847` (endpoint: `pulls`, reaction: `+1`):
  "broad except masks auth exceptions in `auth.py:42`"
- `datadog` comment `2843312900` (endpoint: `pulls`, reaction: `-1`):
  "no-console flag on the console.warn I explicitly asked for as
  partial-failure signal"
- `sonarqube` comment `2843312901` (endpoint: `issues`, reaction: `+1`):
  "python:S1192 - string literal duplicated 3 times in `models/foo.py`"
]

---

### Design Review Surfaces
[Present ONLY when patterns are detected. These are not bugs or style issues -
they're places where the code makes an implicit design decision that benefits
from human evaluation. Frame each as a signal + question, not a directive.]

1. **<Pattern name>** (`file.py` > `function_name`)
   <1-2 sentence description of the structural signal detected>
   **Reviewer question**: <The judgment call only a domain-aware human can make>

---

### Verifiability Map

**Proven by tests:**
- <Behavior with end-to-end test coverage exercising the actual code path>

**Assumed (not verified in this PR):**
- <Dependency on upstream/downstream behavior, timing, or state>

**Unverifiable in current state:**
- <Behavior with no mechanism to determine correctness in dev or prod>

**How to verify** *(optional, for unverifiable items)*:
- <Concrete suggestion: DynamoDB query, CloudWatch metric, Datadog monitor, the Cross-System Investigation recipe (synthesis.md) for mirror-column claims, or `@claude review once` (managed Code Review) as a manual out-of-band check for framework-internal / repo-wide-state claims>

---

### Open Threads
[Unresolved conversations from prior review rounds.
Stale comments (non-HEAD commits) listed separately with staleness note.]

### Verdict
[Ready / Needs Work / Blocked. When Ready, ONE line; do not recap findings the Draft Review Summary or an inline comment already carry. When not Ready, the ordered action items reference findings by line number, not re-narrated prose.]
```

## Mode: Self-Review (`--mine`)

```
## PR #<number>: <title>
Files: <count> | Draft: yes/no

### Pre-Submission Checklist

- [ ] **Description matches diff**: <assessment>
- [ ] **AC compliance**: <if Jira ticket found: "All N criteria met" or "N deviations - see below">
- [ ] **Scope is clean**: <accidental inclusions? unrelated changes?>
- [ ] **CI passing**: <status, failing checks>
- [ ] **No debug artifacts**: <leftover prints, commented code, TODOs?>

### AC Compliance
[Present ONLY when a Jira ticket was hydrated. Same table format as default mode.
For --mine mode, deviations are framed as "fix before review" or "add rationale to PR description".]

### Issues to Fix Before Review

[Grouped by file, same as default mode.]

#### `file.py`

1. [BLOCKING] <title>
   `ClassName` > `method` - `<verbatim code quote>`
   <What's wrong, what to fix, why a reviewer will flag this>

2. [SHOULD FIX] <title>
   `function_name` - `<verbatim code quote>`
   <explanation>

### Reviewer's Likely Questions

1. **"Why did you choose X over Y?"**
   `file.py` > `function_name` - `<code quote>`
   Suggested preemptive answer: <text to add to PR description>

### Verdict
[Ready to request review / Needs work first]
[If not ready: what to fix, ordered by priority]
[If a Cross-System Investigation trip-wire (synthesis.md) fired and the mirror column did not resolve, Verdict is "Needs work first" with the column-confirm item under Issues to Fix Before Review, not a posted bot question.]
```

## Mode: Quick Triage (`--quick`)

```
## PR #<number>: <title>
Author: <name> | Base: <branch> | Draft: yes/no
Adds: +N | Removes: -N | Files: N

### Files Changed
[Each file: new/modified/deleted + one-line characterization]

### AC Compliance
[Present ONLY when a Jira ticket was hydrated. Same table format as default mode.
For --quick, keep it brief: one-line per criterion, flag deviations only.]

### Quick Assessment
[2-3 sentences: what this does, surface-level risk, obvious concerns]

### Draft Review Summary

```
<One-liner ready to paste as the review body. Same conversational voice as default mode but shorter - one sentence covering verdict and comment count. E.g., "LGTM, two non-blocking comments, but maybe worth a look-see.">
```

### Verdict
[Looks routine / Warrants careful review / Red flags present]
[If a Cross-System Investigation trip-wire fires (a query against a Salesforce/DynamoDB mirror references a column whose existence the change depends on), Verdict is at most "Warrants careful review", never "Looks routine", with the one-line reason in Quick Assessment. --quick emits no inline comment, so this is the only expression of the signal.]
```

## Tone Rules

Apply tone rules from `memory/review-voice.md` (formatting, content filters, voice).
For tiebreaking principles when specialists disagree, see `memory/reviewer-discipline.md`
(Review Voice Tenets T1-T5).

**Proportionality and dual-audience density (duty to the author).** Output length
scales to the change, not to how much analysis happened. A 10-line PR gets a few
information-dense sentences, not a multi-section essay. The test: a human reviewer AND
an agent must reach the SAME conclusion from the SAME text in seconds. If a human needs
ten minutes to act on an approval for a ten-line diff, the review failed its duty to the
author. Dense-but-crisp beats complete-but-long; cut any sentence that restates the diff,
recaps another section, or hedges a settled call. Length is earned by distinct findings,
never by re-narration. This governs every section and the postable text alike.

**The removable-sentence test (apply to every sentence before emitting).** Besides the verdict line itself (`LGTM`), ask of each sentence: would removing it change the review's outcome or what the author does next? If no, it is noise; delete it. A sentence earns its place only by carrying a distinct finding, a required action, or the verdict. This subsumes the specific cuts above (restating the diff, recapping a section, hedging a settled call, narrating a bot or a gate the author already sees) under one disposable-by-default rule: the burden is on the sentence to justify staying, not on the reader to tolerate it.

**Code spans**: Use single-tick backticks for all identifiers in output text - class
names, function names, variable names, file paths. This applies to the draft review
summary, draft inline comments, and briefing context sections.

**No hard line-wrapping**: Do not insert hard newlines to wrap long lines in draft
review summary or inline comment text. GitHub renders hard newlines as actual line
breaks, breaking the visual flow of the comment. Write each paragraph as a single
continuous line; let the reader's viewport wrap it.

**No em-dashes (mandatory pre-output gate)**: Never use em-dashes (U+2014) in any
text this skill emits. Scope covers ALL output: the outer briefing prose (Service
Context, Scope, Review Recommendation commentary, Verdict), the Draft Review
Summary, the Draft Inline Comments, AND any free-form text between structural
sections. Before writing each of these sections, scan the composed text for U+2014
and replace it. Before the final message goes out, do one final scan across the
entire composed response. This is a required step, not a style preference.
Four reported violations on record across sessions; the rule is not "resolved"
once fixed in a past conversation, it requires the scan every time. Use semicolons,
commas, parentheses, or separate sentences instead. Common slip: a dash joining
two clauses ("X [U+2014] Y") should become "X; Y", "X, Y", or two sentences.

**No personal-tier vocabulary (pre-output gate)**: The Draft Review Summary and
Draft Inline Comments post to GitHub, where teammates without the local harness read
them. Never use personal-tier terms in that pasteable text: `bead`/`beads` (write
"follow-up ticket", "tracking ticket", or "work item" instead), or personal
slash-command names (`/pr-intel`, `/launch`, `/converge`, etc.). Scan both the
Draft Review Summary and the Draft Inline Comments for these before emitting.
`block-personal-tier-vocab.sh` enforces this at post time, so catching it at draft
time avoids a re-draft round-trip (the 9460 review hit this on "tracked bead"). The
briefing-context sections are reviewer-only and not subject to this; only the
pasteable blocks are. See `correction:style:audience-tier-tooling-references`.

## Delivery Style Patterns

These shape the voice of draft comments. Apply alongside the Comment-Shape Decision Table below.

**Default to question framing for non-blocking findings.** "Should this raise?", "Is this try/except worthwhile?", "Wdyt?" Question framing invites the author into the reasoning rather than imposing a verdict. Use directive framing only when the evidence is VERIFIED and the severity is BLOCKING.

**Approve-while-logging-dissent for borderline cases.** When a PR is correct enough to ship but contains a pattern worth revisiting, the recommendation is COMMENT (or APPROVE in --mine), not REQUEST_CHANGES. Log the dissent inline ("ok fine but for the record this stinks; the next change here should X") and approve. State-level CHANGES_REQUESTED is reserved for genuine blockers; pushback lives in inline comments.

**Proposes-and-permits for tests on legacy code.** When a change touches code that lacks tests, the comment shape is: "Would be good to add tests here. If too much scope creep, then fine." Frames the request as preferred-not-required so the author can scope the fix without negotiation.

**Retract cleanly when proven wrong.** If a finding is invalidated during synthesis (the pattern doesn't apply, the assumption was wrong, the file was misread), drop it without ceremony. Do not double down or hedge. The verification pass exists for this reason.

**Surgical, no padding.** One thought per comment paragraph. The diff and the line number do the heavy lifting. Don't restate what the diff already shows.

## The Compression Step

Before emitting any draft comment, attempt to compress to its question core. If the finding can be expressed as "where does this come from?", "intentional?", "can this be private?", "why?", plus the line context, that is the comment. Add scaffolding only when:

- (a) the alternative is not visible in the diff and requires a name to invoke (e.g., "consider extracting a `create_worker` function" needs the function name),
- (b) the comment carries a concrete code anchor or file reference,
- (c) the finding is a defect-class BLOCKING (rule violation, runtime crash, security boundary, data loss). In that case the directive tone overrides compression.

The diff line is half the comment; do not restate it. The the engineering lead corpus on PR #8741 includes a 1-word inline comment ("why?"). The table below accepts that shape; the compression step makes it the default for design-judgment findings.

Strip Michael's verbosity tells during synthesis (see reviewer-discipline.md). The verbosity tells appear in BOTH inline comments AND the Draft Review Summary body; scan both venues for them before emitting.

- V1 (meta-observation preamble): "just noting...", "for the record...", "as a follow-up...", **"Meta-observation (not for this PR)"** (2026-05-21 instance on PR #9304: out-of-scope team-flag in per-PR body where it adds noise for the author; if the audience is the team, route to Slack instead).
- V2 (both-sides framing with closing concession): "Either way is fine", "no strong opinion", **"Either way it's harmless"** (2026-05-21 instance on PR #9304: same concession rendered in both the body and the inline; pick one venue, drop from the other).
- V3 (trailing "since/because" justification on suggestions when the line context already carries it).

## Comment-Shape Decision Table

Maps evidence + severity + class to default shape. Compression is the discipline, not template fitting. See Review Voice Tenets in reviewer-discipline.md and the Positive Pattern Reference for the discipline behind this table.

| Evidence | Severity | Class | Default shape | Expand only if... |
|---|---|---|---|---|
| VERIFIED | BLOCKING | Defect (rule, runtime crash, security, data loss) | Direct directive citing the rule, ≤ 2 sentences | Fix isn't obvious from diff context |
| VERIFIED | BLOCKING | Design judgment (architecture, naming, encapsulation) | Question form, ≤ 25 words / ≤ 2 sentences | Pattern name or alternative needed and not visible in diff |
| VERIFIED | DISCUSSION | any | Question form, ≤ 25 words / ≤ 2 sentences | Pattern name or concrete alternative needed |
| VERIFIED | MINOR | any | Bare question or short note, ≤ 12 words | Never |
| DIFF-VISIBLE | BLOCKING | Defect | Directive with hedge, ≤ 3 sentences | Fix isn't obvious |
| DIFF-VISIBLE | BLOCKING | Design judgment | Question with hedge, ≤ 25 words / ≤ 2 sentences | Pattern name needed |
| DIFF-VISIBLE | DISCUSSION | any | Question with hedge, ≤ 25 words / ≤ 2 sentences | Concrete alternative needed |
| DIFF-VISIBLE | MINOR | any | Single-sentence question | Never |
| QUESTION | any | any | Interrogative, ≤ 15 words | Never. If more is needed, downgrade evidence and route to summary |

**Ceiling calibration**: word counts above are post-hoc empirical, not aspirational. The the engineering lead corpus median for design-judgment DISCUSSION is ~12 words; the corpus ceiling (when concrete anchors are present) lands around 25-30 words. Hard 15-word ceilings produce false over-ceiling flags on legitimate scaffolded comments and lead to either trim-too-far compression or apparent rule violations on perfectly fine comments. Calibrated 2026-05-13.

**Severity override** (T2 exception): When a clear rule violation is detected, use directive tone regardless of evidence level. Ground the directive: "(per our error-handling standards)", "don't use `@patch` - use monkeypatch or mockito per python-testing.md", etc. the engineering lead's only directive across 34 comments in 3 sample PRs was this exact shape.

**Pattern deviation voice**: Code that works but doesn't match project patterns uses collaborative inquiry backed by a codebase reference: "We typically use X for Y (see `other_file.py:42`). Any reason not to follow that here?"

**Cross-reference voice** (P13): When the same concern applies to multiple sites, comment once on the canonical anchor and point from the others, still leading with the attribution lede: "My `<agent>` specialist flagged the same thing here as on `line_42` above" or "Same `<agent>` finding as my note on `line_42` above". The attribution opener is mandatory even for cross-references; a bare "see suggestion below" / "same concern as my note above" fails `block-unattributed-review-comment*.sh` at post time (observed PR #10478, 2026-07-09).

**Unverified-assertion override** (applies after this table): the table governs DIRECT-voice shapes. When the verdict rests on a falsifiable framework/library/repo-wide or cross-system-state assertion the local pass could not confirm with high confidence, the finding is NOT a confident direct comment: run the local investigation (synthesis.md "Unverified-Assertion Containment + Cross-System Investigation"; for the mirror-column class the named Cross-System Investigation recipe) and, if it does not resolve, render an UNVERIFIED-ASSERTION finding whose result drives the verdict (default/--once Comment, --mine "Needs work first", --quick "Warrants careful review"). The briefing-context section retains the full specialist trace and the resolved-name reasoning. The postable block opens with a tooling-attribution lede; no `@claude` token is required in the body (the dead posting-side workflow filter is retired). `@claude review once` (managed Code Review) is the manual out-of-band escalation when local investigation is inconclusive. This is uniform across modes (no bot-routing in any mode); in `--mine` the unverified claim is a pre-submission item, in `--quick` it is the Verdict nudge.
