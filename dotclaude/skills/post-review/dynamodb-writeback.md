# DynamoDB Write-Back (cross-modality, best-effort)

Supplementary state write to the `pr-review` DynamoDB table so cross-modality
consumers (the Slack bot, future review tooling) see this round. Best-effort:
on failure, log and continue. The GitHub post (Step 3) is authoritative; this
is supplementary. The SKILL.md Step 6 points here.

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
            id=str(<stable_id>), path=<file>, line=<line>,
            body=<comment_body>, status="posted",
            posted_comment_id=str(<github_comment_id>),
        ),
        # one entry per posted inline comment
    ],
    source="terminal",
)
write_review(review)
print(f"Wrote review {review.pr}@{review.timestamp} to DynamoDB")
PY
```

**Type note**: `ProposedComment.id` and `.posted_comment_id` are `str` fields. GitHub comment
IDs (from the `gh api .../reviews` POST response and `/pulls/comments`) come back as ints, so
wrap with `str(...)` or `write_review` raises a Pydantic `ValidationError`.

Populate the placeholders from the review you just posted:
- `<PR_NUMBER>`: integer PR number
- `<UTC_ISO_TIMESTAMP>`: the review's `submitted_at` from the Step 3 reviews POST
  response (authoritative review time, and the record's range key, so use the real
  value rather than approximating). Fall back to current UTC only if the POST
  response is unavailable.
- `<HEAD_SHA>`: the `headRefOid` from PR metadata (same as the `<head_sha_short>` source in Step 5)
- `<PR_TITLE>`, `<PR_AUTHOR>`, `<SIZE>`: from PR metadata and size classification
- `<FULL_BRIEFING_MARKDOWN>`: the full text of the briefing produced by /pr-intel
- `proposed_comments`: one `ProposedComment` per inline comment that was posted.
  The reviews POST in Step 3 returns the REVIEW id, not per-comment ids, so fetch
  each `posted_comment_id` from `/pulls/{n}/comments` filtered by that review id:

  ```bash
  gh api /repos/{owner}/{repo}/pulls/{n}/comments \
    --jq '.[] | select(.pull_request_review_id==<STEP_3_REVIEW_ID>) | {id, path, line}'
  ```

  Filter by `pull_request_review_id`, NOT by author+path. A concurrent same-author
  review on the same PR (Michael runs multiple windows) contaminates an author+path
  filter: observed on PR #9838, where a parallel-window review posted a comment on
  the same file ~5s before this one and an author+path fetch returned both.

**Behavior on write failure**: Log the exception, continue. Do not surface the DynamoDB
error to the user as a review failure. The GitHub post is the authoritative action;
DynamoDB is supplementary state for cross-modality coordination.

**Reusable helper (preferred over hand-writing the heredoc/script).** Write a
params JSON (`{repo, pr, timestamp, head_sha, title, author, size, briefing_path,
comments: [{id, path, line, body}]}`, comments omitted for body-only) and the
briefing markdown, then run:

```bash
AWS_PROFILE=dev AWS_DEFAULT_REGION=us-east-1 uv run --with boto3 --with 'pydantic>=2' \
  python3 ~/.claude/scratch/scripts/pr_review_ddb_writeback.py <params.json>
```

The helper encapsulates the `sys.path` insert, the `str()`-wrapping of comment ids
(the Pydantic ValidationError gotcha above), and the Review/ProposedComment build,
so each writeback is a data file, not reconstructed code. The heredoc above remains
the from-scratch fallback if the helper is unavailable.
