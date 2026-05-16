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

**SAFETY RULE - CRITICAL**: Extract ONLY the fenced ready-to-paste text blocks as comment body.
NEVER extract briefing context into posted comments. Briefing context appears AFTER the fenced
block under `**Briefing context**` and includes:
- Severity tags: `[BLOCKING]`, `[DISCUSSION]`, `[MINOR]`
- Evidence markers: `✓ VERIFIED`, `○ DIFF-VISIBLE`, `? QUESTION`
- Code references: `` `ClassName` > `method_name` - `<code quote>` ``
- Notes starting with "Agent checked:", "Reviewer verify:", "Agent searched:"

These are for the reviewer's eyes only. If any of this appears in extracted comment text,
stop and re-extract.

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

# Hunk check: extract the +NNN,+M ranges from the PR diff hunks for this file
git diff origin/main <headRefOid> -- <file_path> | grep "^@@"
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
prompt the user to either pick a nearby in-hunk line, fold the comment into the review body
as a file:line bullet, or drop it.

**Clean comments**: include in the preview without annotation.

## Step 3: Preview

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
- Comment N (`file.py:213`, NOT_IN_HUNK): line exists at HEAD but is outside the PR's diff hunks. GitHub will 422 this. Options: pick an in-hunk line nearby, move to the review body as a file:line bullet, or drop.

Reply with:
- **approve** / **comment** / **request-changes** to post the review with that event type as-is (must match the displayed event, or pass a different one to override)
- **no** to cancel
- **drop 2,5** to remove specific inline comments by number, then re-confirm
- **move 3 to 47** to change a comment's line number, then re-confirm
- **edit: [new summary text]** to replace the review summary before posting

The verb-named confirmation (`approve` / `comment` / `request-changes`) is required because a posted review is a cross-system write visible to the PR author and reviewers. Generic acknowledgments ("yes", "go", "ok") are ambiguous to the auto-mode classifier and will be blocked on first attempt; the verb names what's being authorized. See CLAUDE.md "Destructive-op confirmation: name the verb."

---

Wait for user response:
- "approve" / "comment" / "request-changes": if the verb matches the displayed event type, proceed; if it differs, treat as an event-type override + post (re-show preview is not required, the verb itself is the new confirmation)
- "no" or "abort" or "cancel": stop, no API call made
- "drop N,M": remove those comment numbers, re-show preview, wait for confirmation again
- "move N to L": update comment N to line L, re-show preview (re-verify that line), wait for confirmation again
- "edit: <new text>": replace the review summary with the provided text, re-show preview, wait for confirmation again
- "yes" (legacy): accept ONLY if the auto-mode classifier permits the resulting Write/Bash calls; if blocked, fall back to asking the user for the verb-named form

## Step 3: Post

> **Em-dash guard**: `~/.claude/hooks/block-em-dash.sh` scans the review body
> and all inline comments in the `gh api -X POST /repos/.../pulls/N/reviews`
> payload for U+2014 (in both inline heredoc and `--input <file>` forms) and
> blocks the call on match with exit 2. Sanitize the drafted prose before
> building the JSON payload: replace em-dashes with hyphens, commas,
> semicolons, or parentheses. This guard fires regardless of which skill or
> agent invoked the post.

> **Backticks for code identifiers**: GitHub Markdown parses `__text__` as bold
> and `*text*` as italic. Code identifiers without backticks render mangled in
> the posted review: `__init__.py` becomes "**init**.py", `__all__` becomes
> "**all**", `__str__` becomes "**str**". There is no hook for this (GitHub
> accepts the post regardless), so the discipline is at draft time. Wrap in
> backticks: paths (`libs/models/__init__.py`), dunders (`__all__`, `__str__`),
> class/function names (`Activities.RUNNING`, `update_item`), imports
> (`from foo import *`), config files (`pyrightconfig.json`). Recurrence
> context: `bd memories gotcha:review-body-needs-backticks`.

> **Destructive-commands false positive**: `~/.claude/hooks/block-destructive-commands.sh`
> scans the bash command for an `rm <path>` pattern combined with a `-X-r-Y`
> substring and a trailing `*` or path. Review bodies that mention a deletion
> ("rm libs/models", "rm -rf the package") and include any `*` (e.g. quoting
> `from foo import *`) can satisfy the regex when posted via stdin heredoc,
> because the body text becomes part of the bash command. The hook does NOT
> scan file contents passed via `--input <path>`. **Default to `--input <file>`
> for review posts**: write the JSON payload to
> `/home/vscode/.claude/scratch/<pr>-review.json` first (flat path, no
> subdirectory; see personal-tier-vocab note below), then
> `gh api -X POST .../reviews --input <that-file>`. This sidesteps both this
> hook and any future bash-command scanners without changing the API call
> shape. Recurrence context: `bd memories gotcha:post-review-rm-path-hook`.

> **Personal-tier vocab hook catches scratch paths**:
> `~/.claude/hooks/block-personal-tier-vocab.sh` scans the bash command (not
> file contents) for personal-tier slash command names like `/pr-intel`,
> `/launch`, `/converge`. Path arguments to `gh api --input` are part of the
> command text and DO get scanned. A scratch path like
> `/home/vscode/.claude/scratch/pr-intel/9025-review.json` will block the post
> because it contains `/pr-intel`. **Default to a flat scratch path**:
> `/home/vscode/.claude/scratch/<pr>-review.json`. No subdirectory named after
> a personal slash command. Recurrence context: `bd memories
> gotcha:post-review-scratch-path-personal-tier-hook`.

Get the repo owner/name:
```bash
gh repo view --json nameWithOwner --jq '.nameWithOwner'
```

Post the atomic review using the mechanism from `github-review-api.md`:
```bash
gh api -X POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews --input - <<JSON
{
  "body": "<review summary>",
  "event": "<event type>",
  "comments": [
    {"path": "<file>", "line": <N>, "body": "<comment text>"}
  ]
}
JSON
```

When there are no inline comments (e.g., --quick mode), omit the `comments` field entirely:
```bash
gh api -X POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews --input - <<JSON
{
  "body": "<review summary>",
  "event": "<event type>"
}
JSON
```

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

## Step 4: Report

On success:
```
Review posted to PR #NNN.

<review URL>#pullrequestreview-<id>

N inline comments posted. <note if any were skipped with reason>
```

On partial failure (some comments skipped): list which were skipped and why.

## Step 5: Persist to beads memory

After a successful post (any event type, any number of inline comments), record the
review so future sessions can recover context even when the session title is unhelpful.

Gather these facts (most come from the pr-intel output and the successful post response):
- `<pr_number>` - from the pr-intel output
- `<date>` - today in `YYYY-MM-DD` form (for the key suffix and the body)
- `<event>` - APPROVE / COMMENT / REQUEST_CHANGES (the actual event posted, not the
  recommendation; these can diverge if the user overrode with `change`)
- `<head_sha_short>` - first 12 chars of `headRefOid` (fetched earlier during line
  verification); represents the exact commit the review was posted against, so a
  later round can diff against it
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
bd remember --key="review:pr-<N>:<YYYY-MM-DD>" "<YYYY-MM-DD> <event> on PR #<N> (<title>, <author>). Rev <commit_count> at <head_sha_short>. Posted <posted_inline_count> inline + <body_fold_count> body-fold. Findings: <findings_summary>. URL: <review_url>"
```

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

After Step 5 succeeds, also write the review state to the `pr-review` DynamoDB
table so cross-modality consumers (the Slack bot, future review tooling) can see
this round. This is best-effort: if the write fails, log and continue. Do not
block or fail the overall flow. The GitHub post (Step 3) is the authoritative
action; DynamoDB is supplementary state.

**Step 6a: Check SSO.**

```bash
aws sts get-caller-identity --profile dev 2>&1 >/dev/null
```

If nonzero, log:
> DynamoDB write-back skipped (SSO not active; run `aws sso login --profile dev` to enable)

and stop. Step 5 (beads memory) is the durable record either way.

**Step 6b: Write the review record.**

The `pr-review` table lives in the dev account (`574892373306`, `us-east-1`).
The `pr_review_state` module imports `boto3` and `pydantic>=2`; use `uv run --with`
so the heredoc runs in an ephemeral env. boto3 reads `AWS_DEFAULT_REGION`, not
`AWS_REGION`.

```bash
AWS_PROFILE=dev AWS_DEFAULT_REGION=us-east-1 uv run --with boto3 --with 'pydantic>=2' python3 - <<'PY'
import sys
sys.path.insert(0, '/home/vscode/.claude/tooling/pr-review-bot/pkg')
from pr_review_state import Review, ProposedComment, write_review

review = Review(
    repo="lawfirm/main",
    pr=<PR_NUMBER>,
    timestamp=<UTC_ISO_TIMESTAMP>,
    head_sha=<HEAD_SHA>,
    title=<PR_TITLE>,
    author=<PR_AUTHOR>,
    size=<SIZE>,
    briefing_md=<FULL_BRIEFING_MARKDOWN>,
    proposed_comments=[
        ProposedComment(
            id=<stable_id>, path=<file>, line=<line>,
            body=<comment_body>, status="posted",
            posted_comment_id=<github_comment_id>,
        ),
        # one entry per posted inline comment
    ],
    source="terminal",
)
write_review(review)
print(f"Wrote review {review.pr}@{review.timestamp} to DynamoDB")
PY
```

Populate the placeholders from the review you just posted:
- `<PR_NUMBER>`: integer PR number
- `<UTC_ISO_TIMESTAMP>`: ISO-8601 UTC timestamp for this write (e.g. `2026-04-17T14:00:00Z`)
- `<HEAD_SHA>`: the `headRefOid` from PR metadata (same as the `<head_sha_short>` source in Step 5)
- `<PR_TITLE>`, `<PR_AUTHOR>`, `<SIZE>`: from PR metadata and size classification
- `<FULL_BRIEFING_MARKDOWN>`: the full text of the briefing produced by /pr-intel
- `proposed_comments`: one `ProposedComment` per inline comment that was posted,
  using the `id` (GitHub comment ID) returned by Step 3

**Behavior on write failure**: Log the exception, continue. Do not surface the DynamoDB
error to the user as a review failure. The GitHub post is the authoritative action;
DynamoDB is supplementary state for cross-modality coordination.

## Human Editing Step (Context Only)

Between /pr-intel and /post-review, you can edit the pr-intel output in your IDE.
This is the 5-question quick-check from `memory/reviewer-discipline.md`:
1. Did a bot already say this?
2. Can I verify the claim in 30 seconds?
3. Would I have noticed this without tooling?
4. Is this actionable?
5. Am I over-commenting?

This skill does not automate these questions - that's your editorial judgment.
The preview step (Step 2) gives you one final chance to drop comments before posting.

## Rules

- Never post without showing the preview and getting confirmation
- Never post briefing context (severity tags, agent notes) as comment text
- Never retry a failed post without informing the user of what failed
- If the conversation context is ambiguous about which pr-intel output to use, ask once:
  "I found multiple pr-intel outputs. Which PR number do you want to post for?"
