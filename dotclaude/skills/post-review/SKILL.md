---
name: post-review
description: Takes /pr-intel output from conversation context and posts it as an atomic GitHub review with inline comments. Triggers when user says "post review", "post these comments", "submit review", "post my review", or after any /pr-intel run where the user indicates readiness to post.
argument-hint: "[pr-number]"
---

# Post Review

Post pr-intel output as an atomic GitHub review with inline comments.

## Input

Raw invocation: `/post-review $ARGUMENTS`

Parse the raw invocation:
1. **PR number override**: first numeric token, if present. Otherwise extract from pr-intel output.
2. No other flags for v1.

**Same-conversation constraint**: This skill only works when /pr-intel was run earlier in the
same conversation. If no pr-intel output is found, stop immediately:
"No pr-intel output found. Run /pr-intel first, then /post-review."

## Step 1: Extract from Conversation Context

Scan the conversation history for the most recent /pr-intel output. Using LLM interpretation,
extract the following. Reference `~/.claude/skills/pr-intel/output-formats.md` for the
expected structure.

**Extract:**
- **PR number**: from the header `## PR #NNN: <title>` or `PR #NNN`
- **Mode**: Was this a default, `--mine`, or `--quick` run?
  - `--mine` mode: Stop. "--mine output is self-directed (no review summary or event type). /post-review supports default and --quick modes. Re-run /pr-intel (without --mine) to generate postable output."
  - `--quick` mode: Body-only review. Extract review summary (see below). Set inline comments to empty. Skip Step 2 (line verification). Default event type to COMMENT (no Action line in --quick output; infer APPROVE if Verdict says "Looks routine", otherwise COMMENT).
  - default mode: Extract inline comments from "Draft Inline Comments" section
- **Event type**:
  - default mode: from `**Action**: Request Changes | Comment | Approve | Approve with Comments`. Map to GitHub event: see `github-review-api.md`
  - `--quick` mode: infer from Verdict (see above). User can override in preview step.
- **Review summary**: content of the fenced block under `### Draft Review Summary`
- **Inline comments** (default mode only): from `### Draft Inline Comments`, for each numbered comment:
  - File path: from the `#### \`file.py\`` heading
  - Line number: from the `**Line N**` marker (this is file-relative, use directly)
  - Ready-to-paste text: content of the fenced block ONLY
  - Classification: `speed-amplified` or `bot-surfaced` from the briefing-context section's classification line (per `provenance-classification.md`). Telemetry only (does not change comment voice); used to populate audit counts in Step 5.
  - **Reply target** (when present): the briefing-context section may contain a `Reply target: comment <prior_comment_id> (<author> <date> on <path:line>)` line indicating pr-intel synthesis routed this finding to be threaded under a prior-round same-author comment. When present, MOVE this entry from the main inline-comments list to a separate `inline_replies` list (keyed by `prior_comment_id` and `body`). These do NOT go into the atomic review POST in Step 3; they are posted separately in Step 3.6. If a comment has both a `**Line N**` marker AND a `Reply target:` line, the `Reply target:` wins (the line marker is for briefing context only when the comment is a reply). See pr-intel `synthesis.md` Step 2 position-based same-author dedup rule for the upstream logic.
- **Bot reactions** (when present): from the pr-intel `bot_reactions` list (rendered as a `### Bot Reactions (for /post-review)` section in the briefing output per pr-intel's bot-reactions.md). Each entry has `{comment_id, endpoint, reaction, bot_name, finding_summary}` where `endpoint` is `pulls` (inline review comment) or `issues` (issue-level conversation comment), and `reaction` is `+1` (bot finding was correct) or `-1` (bot finding was a false positive). If absent, skip Step 3.5.

**SAFETY RULE - CRITICAL**: Extract ONLY the fenced ready-to-paste text blocks as comment body.
NEVER extract briefing context into posted comments. Briefing context appears AFTER the fenced
block under `**Briefing context**` and includes:
- Severity tags: `[BLOCKING]`, `[DISCUSSION]`, `[MINOR]`
- Evidence markers: `✓ VERIFIED`, `○ DIFF-VISIBLE`, `? QUESTION`
- Code references: `` `ClassName` > `method_name` - `<code quote>` ``
- Notes starting with "Agent checked:", "Reviewer verify:", "Agent searched:"

These are for the reviewer's eyes only. If any of this appears in extracted comment text,
stop and re-extract.

**Briefing-only sections (do NOT extract)**. pr-intel renders three briefing
sections that orient the reviewer but never get posted to GitHub. Their
substance flows into the Draft Review Summary or into specific inline
comments; the sections themselves are navigation aids only:

- `### Front Door` (above Review Recommendation): table of type/model
  smells or large-refactor methodology gaps tagged `front_door: true`.
  The framing ("the priority for this round is X") is already in the Draft
  Review Summary text per pr-intel synthesis.md step 7b. Do not extract
  the Front Door table rows as comments.
- `### Spot-Check Mode` (above Scope, present when `spot_check_eligible:
  true`): describes that specialists ran on 3 representative files
  instead of the full diff. The Draft Review Summary already mentions
  the spot-check sample status. Do not extract the methodology quote or
  file list as comments.
- Phase 0 short-circuit output (default mode, Action=Comment, Front Door
  count=1, no Draft Inline Comments section): post as body-only review.
  The Draft Review Summary contains the "send it back" framing. The
  inline_comments list is correctly empty in this case; extraction logic
  handles this gracefully (no comments to post means body-only).

If pr-intel output is absent or too fragmented to extract reliably, stop:
"Could not extract review data from conversation. The pr-intel output may have been compacted.
Re-run /pr-intel first."

## Step 2: Line Number Verification

**Skip this step entirely for --quick mode** (no inline comments to verify).

Before showing the preview, verify every comment's target line against both the file content
at the PR's HEAD commit AND the PR's diff hunks. The first check catches off-by-one errors;
the second catches lines that exist but are not in GitHub's three-dot diff view (which causes
the API to return 422 "Line could not be resolved" at post time).

For each inline comment, run these two checks per file, in parallel:
```bash
# Content check: verify the target line has the expected text
git show <headRefOid>:<file_path> | awk 'NR==<line> {print NR": "$0}'

# Hunk check: extract the +NNN,+M ranges from the PR diff hunks for this file.
# THREE-DOT (merge-base) diff against the PR's BASE branch is mandatory: GitHub's
# PR view and its 422 line-resolution are merge-base-relative. Use <baseRefName>
# from the PR metadata, NOT a hardcoded main: a stacked PR (Graphite) bases on a
# downstack branch, and diffing against main pulls the downstack PR's lines into
# the hunk ranges. For a non-stacked PR, baseRefName is main, so this is a no-op.
git fetch origin <baseRefName> --quiet && git diff origin/<baseRefName>...<headRefOid> -- <file_path> | grep "^@@"
# Authoritative fallback when local objects are missing:
#   gh api /repos/{owner}/{repo}/pulls/{n}/files --jq '.[] | select(.filename=="<file_path>") | .patch' | grep "^@@"
```

If `headRefOid` is not in the conversation, fetch it:
```bash
gh pr view <number> --json headRefOid --jq '.headRefOid'
```

Parse each `@@` header of the form `@@ -A,B +C,D @@` and build the set of valid post-image
ranges `[C, C+D-1]` for the file. A comment's target line must fall within at least one
range to be postable.

For each comment, record:
- `line_content`: the actual text at that line (trimmed)
- `flag`: one of
  - `BLANK` - line is empty or whitespace-only
  - `SUSPICIOUS` - content looks structurally wrong for the comment (closing brace, lone
    comma, import statement when the comment is about logic)
  - `NOT_IN_HUNK` - line exists in the file but falls outside every `@@` hunk range; GitHub
    will reject this comment with 422 at post time
  - Comments may carry multiple flags; record all that apply.

**Flagged comments**: present to the user with the actual line content AND the reason so
they can decide whether to adjust the line number, drop the comment, move it to the review
body, or post as-is. Do not silently drop them. `NOT_IN_HUNK` comments in particular should
prompt the user to pick a nearby in-hunk line FIRST (preferred: the finding keeps a
resolvable thread, and the comment text can self-locate the real line), falling back to a
review-body file:line bullet only when no in-hunk line relates to the finding, and to a
drop last.

**Clean comments**: include in the preview without annotation.

**Body-prose line-reference check**: the Draft Review Summary body often points at
inline comments by line ("see inline on line N", "lines N and M"). Step 2 may adjust an
inline anchor (off-by-one against actual file content), but that adjustment does NOT
propagate to the body prose, and post-review otherwise never re-checks body line numbers.
After finalizing the verified inline anchors, scan the extracted body for `line \d+` /
`lines \d+ and \d+` references and confirm each matches a posted inline's verified line;
flag any mismatch in the Step 2.6 preview ("body says line 43; inline posts on 44, update
body?") so the prose is corrected before posting. Observed on PR #10836: pr-intel wrote
"lines 29 and 43" while the second inline resolved to line 44.

## Step 2.5: Attribution Check

**Skip for --quick mode** (no inline comments). Runs in default mode before the preview.

Every inline comment pr-intel emits is tool-discovered: it passed through a specialist
agent or an orchestrator pattern check, not Michael's unaided reading. Per the
engineering lead's 2026-05-26 ask (review-voice.md T5 / reviewer-discipline.md T5), each posted inline
comment MUST open with an explicit attribution lede, never in Michael's first-person
voice, and the attribution is the lede, not parenthetical. The review SUMMARY body is
exempt (it is allowed to be in reviewer voice).

Before the preview, verify each inline comment body opens with one of:
- `My automated <specialist> pass flagged ...` / `My `<agent-name>` specialist flagged ...`
- `Cross-file analysis surfaced that ...` / `Cross-service ...`
- `AC item N expects X, the diff implements Y`
- `The design doc specifies X (section N): ...`
- `SonarCloud flagged python:S<code>: ...` / `Copilot flagged ...` / `Datadog flagged ...`
- `Pattern check flagged ...` / `Flagged by <tool> ...`

A comment that merely mentions a tool in prose ("Your decline of Copilot's suggestion...")
does NOT satisfy this: the source must be the opener. If any comment is in unaided
first-person voice, rewrite the lede to attribute the source before posting.

The provenance classification (`speed-amplified` vs `bot-surfaced`) is for audit/telemetry
only and does NOT change this: a `speed-amplified` finding is still bot-discovered and still
requires attribution. The only exception is a comment Michael personally authored during his
editing pass (rare; pr-intel does not emit these).

**Structural enforcement (two layers).** Both call `~/.claude/hooks/lib/check_review_attribution.py`,
which also runs the @-mention guard (no `@person` in any posted body; only `@claude` allowed).
- `block-unattributed-review-comment.sh` (PreToolUse on Bash) parses the `gh api .../pulls/N/reviews`
  POST payload (and single-comment POST/PATCH) from `--input <file>`, a heredoc, or `-f body=@file`,
  and blocks the post (exit 2) if any inline `comments[].body` lacks an attribution lede.
- `block-unattributed-review-comment-file.sh` (PostToolUse on Write/Edit) is the BACKUP: it scans
  any written JSON file that looks like a review payload (conservative shape + filename gate, so it
  never fires on unrelated JSON) and blocks at write time. This catches payloads posted through a
  path the Bash hook cannot see (e.g. a Python subprocess calling `gh ... --input <file>`).

The review summary, reactions, and replies endpoints are exempt. Both hooks are the backstop;
do not rely on the prose instruction alone.

**Run the check yourself before the preview**, against the payload file rather than
per-comment strings: `python3 ~/.claude/scratch/scripts/check-review-attribution.py
<payload.json>`. It calls the same `evaluate()` both hooks call, so a pass here means the
post will not be blocked. Do NOT `cd` into `hooks/lib` to import the module ad hoc; the
Bash cwd persists and the next `gh`/`git` call fails. **Convention:** write review payload JSON via the
Write tool (not an in-script `json.dump`), so the backup hook sees it; a payload both built and
posted entirely inside one subprocess is invisible to both hooks. See
`bd memories correction:skill:post-review-attribution-enforcement`.

## Step 2.6: Preview

Present the verified data for confirmation before any API call. Render as regular markdown (do NOT wrap in a fenced code block):

---
**Ready to post:**

**Event type:** [COMMENT/APPROVE/REQUEST_CHANGES]  *(type to change, or Enter to keep)*

**Review summary:**
<first 3 lines of summary>
...<N more lines>  (if truncated)

**Inline comments** (N total):
[If N > 0:]
1. `path/to/file.py:42` - <first line of comment>
2. `other/file.py:78` - <first line of comment>
...
[If N == 0 (e.g., --quick mode):] "None (body-only review)"

[If any comments were flagged during line verification, show them separately:]

**⚠ Line number warnings** (review before posting):
- Comment N (`file.py:42`, BLANK/SUSPICIOUS): line content is `<actual content>` - adjust line number, drop, or post as-is?
- Comment N (`file.py:213`, NOT_IN_HUNK): line exists at HEAD but is outside the PR's diff hunks. GitHub will 422 this. Options in preference order: re-anchor to the nearest in-hunk line and let the comment text name the real line, else fold into the review body as a file:line bullet, else drop.

Reply with:
- **approve** / **comment** / **request-changes** to post the review with that event type as-is (must match the displayed event, or pass a different one to override)
- **no** to cancel
- **drop 2,5** to remove specific inline comments by number, then re-confirm
- **move 3 to 47** to change a comment's line number, then re-confirm
- **edit: [new summary text]** to replace the review summary before posting

The verb-named confirmation (`approve` / `comment` / `request-changes`) is required because a posted review is a cross-system write visible to the PR author and reviewers. Generic acknowledgments ("yes", "go", "ok") are ambiguous to the auto-mode classifier and will be blocked on first attempt; the verb names what's being authorized. See CLAUDE.md "Destructive-op confirmation: name the verb."

**Verb named in the invocation (`/post-review comment|approve|request-changes`).**
When the invocation already carries the event verb, that verb IS the confirmation
(CLAUDE.md "Don't re-confirm within a directive's scope"; asking for the verb again
after the user typed it is a disguised re-confirm). Render the preview for
transparency so the user sees the exact draft, but do NOT wait for a second verb
reply: post once Step 2 (line verification) and Step 2.5 (attribution) pass clean.
The safety catch still holds: if line verification raises BLANK / SUSPICIOUS /
NOT_IN_HUNK, or attribution fails, STOP and surface the preview for adjudication
before posting, regardless of the named verb. A bare `/post-review` (no verb) always
shows the preview and waits.

---

Wait for user response:
- "approve" / "comment" / "request-changes": if the verb matches the displayed event type, proceed; if it differs, treat as an event-type override + post (re-show preview is not required, the verb itself is the new confirmation)
- "no" or "abort" or "cancel": stop, no API call made
- "drop N,M": remove those comment numbers, re-show preview, wait for confirmation again
- "move N to L": update comment N to line L, re-show preview (re-verify that line), wait for confirmation again
- "edit: <new text>": replace the review summary with the provided text, re-show preview, wait for confirmation again
- "yes" (legacy): accept ONLY if the auto-mode classifier permits the resulting Write/Bash calls; if blocked, fall back to asking the user for the verb-named form

## Step 3: Post

Five hooks can block this POST: the em-dash guard (U+2014 in body/comments),
the destructive-commands false positive (a review body mentioning `rm` + `*`),
and the personal-tier-vocab scan (a `/pr-intel`-style path argument to
`--input`). The em-dash guard also fires on `gh pr comment` / `gh pr review` /
`gh api -X POST/PATCH`. Two defaults sidestep all of them: (1) write the JSON
payload to a FLAT scratch path `/home/vscode/.claude/scratch/<pr>-review-<YYYY-MM-DD>.json`
(no subdirectory named after a slash command; the date suffix matches the Step 5
memory-key scheme so a re-review does not collide with a prior round's stale file
and trip the Write tool's read-before-write guard) via the Write tool, then post
with `gh api --input <that-file>` in a SEPARATE command (the attribution
PreToolUse hook reads the file before the Bash command runs, so build-then-post
in one command validates stale content). (2) GitHub Markdown mangles
unbackticked dunders/paths (`__init__.py` -> bold); backtick code identifiers
at draft time. For the full per-hook explanation and recurrence contexts, see
[post-hooks.md](post-hooks.md).

Get the repo owner/name:
```bash
gh repo view --json nameWithOwner --jq '.nameWithOwner'
```

Post the atomic review using the mechanism from `github-review-api.md`, as a
TWO-STEP sequence (never a stdin heredoc; heredocs trip the destructive-command
and vocab scans and bypass the attribution hook's payload validation):

1. Write the payload with the Write tool to
   `/home/vscode/.claude/scratch/<pr_number>-review-<YYYY-MM-DD>.json`. On a
   same-day second round, append `-N` (`<pr>-review-<date>-2.json`) to match the
   Step 5 memory-key scheme rather than overwriting: each round is a distinct
   artifact, and the prior payload is the only local record of exactly what was
   posted. The Write read-before-write guard is the backstop if you reuse the path:
```json
{
  "body": "<review summary>",
  "event": "<event type>",
  "comments": [
    {"path": "<file>", "line": <N>, "body": "<comment text>"}
  ]
}
```
2. Post it referencing the file in a separate command (capture the response so
   Steps 4-6 need no refetch; `submitted_at` is Step 6's DynamoDB range key):
```bash
gh api -X POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews --input /home/vscode/.claude/scratch/<pr_number>-review-<YYYY-MM-DD>.json \
  --jq '{id, state, html_url, submitted_at}'
```

When there are no inline comments (e.g., --quick mode), omit the `comments`
field entirely from the JSON file; the two-step sequence is otherwise
identical.

**Error handling:**
- 422 "Path could not be resolved": the entire file is not in GitHub's three-dot diff
  (common with squashed/rebased PRs where ghost diffs exist). Do NOT drop these findings.
  Instead, fold all affected comments into the review body as file:line-referenced bullets,
  then re-post as a body-only review (or body + remaining valid inline comments).
  Inform the user: "N comment(s) moved to review body - file(s) not in GitHub's diff view."
- 422 "Line could not be resolved": the line is not in the diff hunk. Remove that comment and
  inform the user: "Comment N ([file]:[line]) skipped - line not in diff. Remaining N-1 comments posted."
  Re-post without the offending comment(s).
- When both path and line errors occur in the same batch, the API returns a single 422
  with multiple error strings. Parse all errors, separate path-level (fold into body) from
  line-level (drop), then re-post.
- Any other error: report the full error message and the command attempted. Do not retry silently.

## Step 3.5: Bot Reactions

After the main review post succeeds, apply `+1`/`-1` reactions to the bot
comments pr-intel classified in its Bot Reactions phase (the upgraded form of
the engineering lead's 2026-05-20 "thumbs-up instead of repeat" feedback). The `bot_reactions`
list (extracted in Step 1) carries `{comment_id, endpoint, reaction, bot_name,
finding_summary}`; POST each to the `pulls/comments/{id}/reactions` (inline) or
`issues/comments/{id}/reactions` (issue-level) endpoint. Skip silently if empty.
For the endpoint split, error handling (404 / 422-already-exists / 403), and the
report-line additions, see [reactions-and-replies.md](reactions-and-replies.md).

## Step 3.6: Inline Replies (thread continuations)

After reactions, post any inline comments pr-intel synthesis tagged for
reply-in-thread (the atomic review endpoint does not accept `in_reply_to_id`,
so these are separate calls). Each carries `{path, prior_comment_id, body}`;
POST to `pulls/{pr}/comments/{prior_comment_id}/replies`. Step 1 already
filtered these OUT of the atomic POST so they do not double-post. Skip silently
if none (the common case). For error handling and the report-line additions,
see [reactions-and-replies.md](reactions-and-replies.md).

## Step 4: Report

On success:
```
Review posted to PR #NNN.

<review URL>#pullrequestreview-<id>

N inline comments posted. <note if any were skipped with reason>
M bot reactions applied (<list bot names>).
```

On partial failure (some comments skipped): list which were skipped and why.

## Step 5: Persist to beads memory

After a successful post (any event type, any number of inline comments), record the
review so future sessions can recover context even when the session title is unhelpful.

Gather these facts (most come from the pr-intel output and the successful post response):
- `<pr_number>` - from the pr-intel output
- `<date>` - today in `YYYY-MM-DD` form (for the key suffix and the body)
- `<event>` - APPROVE / COMMENT / REQUEST_CHANGES (the actual event posted, not the
  recommendation; these can diverge if the user confirmed a different event verb than the recommendation)
- `<head_sha_short>` - first 12 chars of `headRefOid` (fetched earlier during line
  verification; in --quick mode that step is skipped, so fetch it here:
  `gh pr view <number> --json headRefOid --jq '.headRefOid'`); represents the
  exact commit the review was posted against, so a later round can diff
  against it
- `<commit_count>` - number of commits on the PR at review time, as a rough "revision
  number" so a later session can tell how much churn has happened since. Compute with:
  ```bash
  gh pr view <number> --json commits --jq '.commits | length'
  ```
- `<title>` - the PR title (from pr-intel header)
- `<author>` - the PR author login
- `<posted_inline_count>` - number of inline comments actually posted (not dropped/folded)
- `<body_fold_count>` - number of findings that were folded into the body because they
  couldn't be posted inline (NOT_IN_HUNK / path-not-resolved / user-dropped)
- `<bot_surfaced_count>` - number of posted inline comments classified as bot-surfaced
  per `provenance-classification.md` (verification needed live-state, multi-file, or document-synthesis work)
- `<speed_amplified_count>` - number of posted inline comments classified as
  speed-amplified per `provenance-classification.md` (the reviewer could have caught it from
  careful single-file reading). Classification is telemetry only; ALL posted comments carry an
  attribution prefix regardless of class.
- `<bot_reaction_count>` - total number of reactions applied to bot comments in
  Step 3.5 (sum of thumbs-up and thumbs-down)
- `<bot_thumbs_up_count>` - number of `+1` reactions (bot finding agreed-with;
  per bot-reactions.md categories 1, 2, 3)
- `<bot_thumbs_down_count>` - number of `-1` reactions (bot finding disagreed-with
  as false positive; per bot-reactions.md categories 4, 5)
- `<inline_replies_posted>` - number of inline reply-in-thread comments
  successfully posted in Step 3.6 (threading to prior-round comments at the
  same path:line under the same author handle). Zero is the common case;
  non-zero is the signal that the position-based same-author dedup rule in
  pr-intel synthesis fired and routed a finding to the replies endpoint
  rather than letting it land as a duplicate top-level inline. See
  calibration:pr-intel-same-line-dedup-2026-05-20 for the failure mode this
  count tracks.
- `<findings_summary>` - one clause per posted inline comment plus any body-fold
  findings, formatted as `file.py:LINE (short clause)`. Keep each clause under 80
  chars and the total under ~6 lines.
- `<review_url>` - the `html_url` from the POST response

Key scheme: `review:pr-<N>:<YYYY-MM-DD>`. This preserves each round as a distinct
memory so aging can be observed (user sees "reviewed 3 weeks ago on rev 2, current
is rev 9"). The date suffix also prevents overwriting a prior round on the same PR.

If two reviews happen on the same PR on the same day, append `-N` to the date suffix
(`:2026-04-16-2`). Do not overwrite the morning's review with the afternoon's; the
rounds are different artifacts.

Write with:
```bash
bd remember --key="review:pr-<N>:<YYYY-MM-DD>" "<YYYY-MM-DD> <event> on PR #<N> (<title>, <author>). Rev <commit_count> at <head_sha_short>. Posted <posted_inline_count> inline (<bot_surfaced_count> bot-surfaced + <speed_amplified_count> speed-amplified) + <body_fold_count> body-fold + <bot_reaction_count> bot-reactions (<bot_thumbs_up_count> up / <bot_thumbs_down_count> down) + <inline_replies_posted> inline-replies. Findings: <findings_summary>. URL: <review_url>"
```

The `<bot_surfaced_count>` and `<speed_amplified_count>` fields support an
audit signal over time: the ratio of bot-surfaced to speed-amplified posted
comments tracks whether pr-intel output is biased toward bot-noise (high
bot-surfaced count with low author engagement) or genuine reviewer judgment.
Read these back via `bd memories review:pr-` to spot-check the trust signal
direction; if bot-surfaced consistently dominates and author engagement drops,
the skill is producing bot-noise rather than amplifying judgment. The
`<bot_reaction_count>` measures how often the dedup-and-react path fires;
high count signals the bots are catching things upstream.

Example (illustrative only; do not copy verbatim):
```
bd remember --key="review:pr-<NUMBER>:<YYYY-MM-DD>" "<YYYY-MM-DD> <DECISION> on PR #<NUMBER> (<TICKET title, author>). Rev <N> at <SHORT_SHA>. Posted <X> inline + <Y> body-fold. Findings: <file:line summaries>. URL: <review_url>"
```

This step is not optional. If `bd remember` fails (beads unavailable, network error),
note the failure in the user-facing report but do not retry; the posted review is
still the source of truth, this is an index entry.

Consolidate the user-facing report to include this:
```
Review posted to PR #NNN.
<review URL>
N inline comments posted. <skip note if applicable>
Memory: review:pr-NNN:YYYY-MM-DD recorded.
```

## Step 6: Persist to DynamoDB (cross-modality)

After Step 5, also write the review state to the `pr-review` DynamoDB table
(dev account `574892373306`, `us-east-1`) so cross-modality consumers (the
Slack bot, future review tooling) see this round. Best-effort: gate on
`aws sts get-caller-identity --profile dev` (skip with a logged note if SSO is
inactive), then write a `Review` record (one `ProposedComment` per posted
inline) by calling the existing script, NOT by hand-writing the record:

```bash
AWS_PROFILE=dev AWS_DEFAULT_REGION=us-east-1 uv run --with boto3 --with 'pydantic>=2' \
  python3 ~/.claude/scratch/scripts/pr_review_ddb_writeback.py <params.json>
```

`params.json`: `{"repo", "pr", "timestamp", "head_sha", "title", "author", "size",
"briefing_path", "comments": [{"id", "path", "line", "body"}]}` (omit `comments` for a
body-only review). On write failure, log and continue; the GitHub post (Step 3) is
authoritative and the beads memory (Step 5) is the durable record.

Hand-constructing `Review(...)` inline is the recurring failure mode here: the field
names are not what an agent guesses (`pr`, not `pr_number`; `briefing_md` is REQUIRED
with no default), so the guessed call dies on a pydantic `ValidationError` and costs a
re-draft. Six occurrences as of 2026-08-06, the last one in a session where the sub-file
already carried this warning but Step 6 did not surface the script name. For the inline
form (only when the script does not expose a field you need), the
`ProposedComment.id` str-wrap type note, and placeholder population, see
[dynamodb-writeback.md](dynamodb-writeback.md).

## Human Editing Step (Context Only)

Between /pr-intel and /post-review, you can edit the pr-intel output in your IDE.
This is the 5-question quick-check from `memory/reviewer-discipline.md`:
1. Did a bot already say this?
2. Can I verify the claim in 30 seconds?
3. Would I have noticed this without tooling?
4. Is this actionable?
5. Am I over-commenting?

This skill does not automate these questions - that's your editorial judgment.
The preview step (Step 2.6) gives you one final chance to drop comments before posting.

## Rules

- Never post without showing the preview and getting confirmation
- Never post briefing context (severity tags, agent notes) as comment text
- Never retry a failed post without informing the user of what failed
- If the conversation context is ambiguous about which pr-intel output to use, ask once:
  "I found multiple pr-intel outputs. Which PR number do you want to post for?"
