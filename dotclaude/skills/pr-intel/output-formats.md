# Output Formats

## Mode: Reviewing Others (default)

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
[Modules touched, blast radius: low/medium/high, 2-3 lines max]

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

### Review Recommendation
**Action**: Request Changes | Comment | Approve with Comments | Approve
**Blocking**: N | **Discussion (high-consequence)**: N | **Discussion (low-consequence)**: N | **Minor**: N

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
<Ready-to-paste text for the top-level review body. Overall assessment first, then specific concerns worth discussing. Collaborative tone: acknowledge what the PR does well before raising concerns. Written in second person to the PR author. Target: 60-100 words for a clean PR with 1-3 concerns, ≤ 150 words for a PR with multiple distinct issues that need separate framing. Hard ceiling: 200 words; beyond that, the inline comments should carry more weight and the summary should compress. No severity tags. Strip the Michael verbosity tells from reviewer-discipline.md (V1 meta-preamble, V2 both-sides-with-concession, V3 trailing since/because justifications). When AC deviations exist, mention them naturally: "The dedup logic handles all entries rather than only complete=True entries per the ticket AC, was that intentional?">
```

---

### Draft Inline Comments

Ready-to-post comments, grouped by file. Each comment is the actual text
to paste on the PR. The reviewer can copy them verbatim or edit before posting.

**Comment budget**: Scale to the number of real findings, not to a fixed cap. Zero is a legitimate count: a 2XL infra PR with nothing to flag should get an approval with no inline comments, not padded findings to meet a typical-range floor (empirical case: PR #9022, 696-line Redshift Serverless PR approved with zero inline comments by a high-trust reviewer). Typical range when findings exist: 2-3 for a clean PR with minor observations, 5-8 for one with real issues, 10-15 for a large PR with multiple discussion-class concerns. Beyond 15, consolidate related findings into the review summary or use cross-references to point multiple sites at the same canonical thread (P13 in reviewer-discipline.md). BLOCKING findings always get a comment regardless of count. When trimming, drop MINOR findings first. When in doubt, drop the comment: a PR with two precise questions is more useful than one with eight padded observations.

**Structural variation**: Not every comment needs the same shape. Mix these forms (examples lifted from the the senior-reviewer corpus across PRs #8931, #8741, #8066):
- Bare question: "where does this come from?", "why?", "intentional?", "must they be?"
- Short observation: "this silently drops the error context from the original exception."
- Suggestion with concrete anchor: "consider extracting a `create_worker` function in another module."
- Cross-reference: "see pydantic-settings suggestion below" (point at the canonical comment instead of repeating)
- Hedged proposal: "Maybe X? (I'm unclear what Y is for, so maybe not)"
- Pattern-named smell: "this is craving some DI", "IsA vs HasA?", "roundabout way of calling verify()?"

Avoid uniform [SEVERITY] / title / code quote / explanation structure on every comment. Use severity tags in the briefing context (for the reviewer) but omit them from the pasteable text (for the PR author). A human reviewer does not prefix comments with [BLOCKING].

Format: file heading, then numbered comments. Each comment has a target line, a fenced block with the ready-to-paste text, and a briefing-context section the reviewer can read but does not post.

#### `strategy.py`

1. **Line 42** (`method_name`)

   ```
   <Ready-to-paste comment text. Varied voice: direct statement, question, or suggestion. No severity tag. Length matches complexity: 1-2 sentences for MINOR, 3-10 sentences across multiple paragraphs for BLOCKING/DISCUSSION. One thought per paragraph. This is what gets posted.>
   ```

   **Briefing context**
   [BLOCKING] ✓ VERIFIED
   `ClassName` > `method_name` - `<verbatim code quote>`
   <1-2 sentence explanation for the reviewer, not posted>
   Agent checked: <what was grep'd/read to verify this>

2. **Line 78** (`other_method`)

   ```
   <Ready-to-paste comment text.>
   ```

   **Briefing context**
   [MINOR] ○ DIFF-VISIBLE
   `ClassName` > `other_method` - `<verbatim code quote>`
   <explanation>
   Reviewer verify: <what to check to confirm this>

#### `processor.py`

3. **Line 15** (`process_message`)

   ```
   <Ready-to-paste comment text, phrased as a question for the PR author.>
   ```

   **Briefing context**
   [DISCUSSION] ? QUESTION
   `process_message` - `<verbatim code quote>`
   <explanation>
   Agent searched: <what was searched, why inconclusive>

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
- <Concrete suggestion: DynamoDB query, CloudWatch metric, Datadog monitor>

---

### Open Threads
[Unresolved conversations from prior review rounds.
Stale comments (non-HEAD commits) listed separately with staleness note.]

### Verdict
[Ready / Needs Work / Blocked, plus ordered action items if not ready]
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
```

## Tone Rules

Apply tone rules from `memory/review-voice.md` (formatting, content filters, voice).
For tiebreaking principles when specialists disagree, see `memory/reviewer-discipline.md`
(Review Voice Tenets T1-T5).

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

The diff line is half the comment; do not restate it. The the senior-reviewer corpus on PR #8741 includes a 1-word inline comment ("why?"). The table below accepts that shape; the compression step makes it the default for design-judgment findings.

Strip Michael's verbosity tells during synthesis (see reviewer-discipline.md):
- V1 (meta-observation preamble): "just noting...", "for the record...", "as a follow-up...".
- V2 (both-sides framing with closing concession): "Either way is fine", "no strong opinion".
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

**Ceiling calibration**: word counts above are post-hoc empirical, not aspirational. The the senior-reviewer corpus median for design-judgment DISCUSSION is ~12 words; the corpus ceiling (when concrete anchors are present) lands around 25-30 words. Hard 15-word ceilings produce false over-ceiling flags on legitimate scaffolded comments and lead to either trim-too-far compression or apparent rule violations on perfectly fine comments. Calibrated 2026-05-13.

**Severity override** (T2 exception): When a clear rule violation is detected, use directive tone regardless of evidence level. Ground the directive: "(per our error-handling standards)", "don't use `@patch` - use monkeypatch or mockito per python-testing.md", etc. a senior reviewer's only directive across 34 comments in 3 sample PRs was this exact shape.

**Pattern deviation voice**: Code that works but doesn't match project patterns uses collaborative inquiry backed by a codebase reference: "We typically use X for Y (see `other_file.py:42`). Any reason not to follow that here?"

**Cross-reference voice** (P13): When the same concern applies to multiple sites, comment once on the canonical anchor and point from the others: "see pydantic-settings suggestion below" or "same concern as my note on `line_42` above".
