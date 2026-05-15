# Prior Reviews (bd memories + DynamoDB)

This file documents how /pr-intel discovers prior review history for a PR and folds it into the current review's data-gathering, specialist preamble, dedup context, and default recommendation.

Two channels are checked in parallel:
1. `bd memories pr-<number>` for terminal-side review memories (`/post-review` writes these).
2. DynamoDB `pr-review` table for cross-modality state (terminal sessions and the Slack bot share this).

If both channels fail, the review proceeds as first-round.

## Prior Review Memory (bd memories)

`/post-review` writes a memory on every successful post, keyed as `review:pr-<number>:<YYYY-MM-DD>` (see post-review Step 5).

Run in parallel with the other data-gathering commands:
```bash
bd memories pr-<number>
```

Parse the output for entries matching `review:pr-<number>:*`. For each prior round, extract:
- **date** (from the key suffix and body)
- **event** (APPROVE / COMMENT / REQUEST_CHANGES)
- **head_sha_short** (the commit the prior round was posted against)
- **commit_count** (rough revision number at prior review)
- **findings_summary** (one-line per posted comment / body-fold)
- **review_url**

Store as `prior_reviews` list, sorted oldest to newest.

**Downstream effects** when one or more prior reviews exist:

1. **Revision delta**: Compute `current_commit_count - latest_prior.commit_count`.
   Surface in the header as `Revision: rev <current> (delta +N commits since last review on <date>)`.
2. **Delta-focused diff**: For the `git diff` sent to specialists, include a second
   scope showing only what changed since the prior head:
   ```bash
   git diff <latest_prior.head_sha> <headRefOid>
   ```
   Specialists are instructed to prioritize this delta; the full PR diff is secondary
   context. This is the single highest-value signal on re-reviews; it is the actual
   "what's new since we last looked."
3. **Dedup input**: Append the `findings_summary` bullets from prior rounds to the
   dedup context so specialists do not re-raise points we already posted.
4. **Briefing header**: Add a `Prior Reviews` section listing each round with date,
   event, rev number, and a link. Example:
   ```
   Prior Reviews:
   - 2026-04-13 COMMENT (rev 12, 3 inline): bd memories review:pr-8282:2026-04-13
   - 2026-04-16 APPROVE (rev 30, 2 inline + 1 body): bd memories review:pr-8282:2026-04-16
   ```
5. **Default recommendation shift**: If the latest prior review was APPROVE and the
   delta is small (<= 3 commits, no structural file changes), the default
   recommendation should bias toward APPROVE unless new evidence says otherwise.
   Prior approval is signal, not noise. Conversely, if the prior review was
   REQUEST_CHANGES, verify the requested changes landed before any new approval.

**Behavior when `prior_reviews` is empty**: This is a first-round review. No delta
available. Proceed with normal first-round defaults (see
`correction:skill:pr-intel-first-round` in beads memory: default to Comment for L+
PRs, novel patterns, external contracts, or unverified claims).

**Behavior when `bd memories` fails**: Note the failure in the briefing, proceed as
if first-round. Do not block on beads availability.

## DynamoDB Prior Reviews (cross-modality)

Run in parallel with the `bd memories` call above. This provides state shared with
the Slack bot (and any other future callers that write to the same table).

**Step 1: Verify SSO is active.**

```bash
aws sts get-caller-identity --profile dev 2>&1 >/dev/null
```

If this returns nonzero, log:
> DynamoDB state integration skipped (SSO not active; run `aws sso login --profile dev` to enable)

and skip the rest of this subsection. Do not fail the review.

**Step 2: List prior reviews from DynamoDB.**

The `pr_review_state` module imports `boto3` and `pydantic>=2`. These are not
installed on the system python in this codespace (the Fargate bot ships its own
container with them baked in). Use `uv run --with ...` so the heredoc runs in
an ephemeral env without needing a persistent venv.

The `pr-review` table lives in the dev account (`574892373306`, `us-east-1`).
The default SSO role in this codespace points at a different account, so the
heredoc must set `AWS_PROFILE=dev` and `AWS_DEFAULT_REGION=us-east-1`. Note:
boto3 reads `AWS_DEFAULT_REGION`, not `AWS_REGION`.

```bash
AWS_PROFILE=dev AWS_DEFAULT_REGION=us-east-1 uv run --with boto3 --with 'pydantic>=2' python3 - <<'PY'
import sys, json
sys.path.insert(0, '/home/vscode/.claude/tooling/pr-review-bot/pkg')
from pr_review_state import list_reviews_for_pr
reviews = list_reviews_for_pr("<company>/docr", <PR_NUMBER>)
for r in reviews:
    print(json.dumps({
        "timestamp": r.timestamp,
        "source": r.source,
        "head_sha": r.head_sha,
        "proposed_count": len(r.proposed_comments),
        "posted_count": sum(1 for c in r.proposed_comments if c.status == "posted"),
    }))
PY
```

**Step 3: Merge into `prior_reviews`.**

If the output is non-empty, append each DynamoDB row to the same `prior_reviews` list
built from `bd memories`. Distinguish source in the Briefing header:
- `bd`-sourced rows keep their existing format.
- DynamoDB rows tagged `source: "terminal"` show a `(terminal)` suffix.
- DynamoDB rows tagged `source: "bot"` show a `(bot)` suffix.

Example merged entry:
```
- 2026-04-15 COMMENT (rev 8, 3 inline): DynamoDB 2026-04-15T14:32:00Z (terminal)
```

**Step 4: Full briefing retrieval (when needed for dedup).**

If you need the full comment body from a prior DynamoDB review (for dedup in
synthesis), call `get_review`:

```bash
AWS_PROFILE=dev AWS_DEFAULT_REGION=us-east-1 uv run --with boto3 --with 'pydantic>=2' python3 - <<'PY'
import sys, json
sys.path.insert(0, '/home/vscode/.claude/tooling/pr-review-bot/pkg')
from pr_review_state import get_review
review = get_review("<company>/docr", <PR_NUMBER>, "<TIMESTAMP>")
print(json.dumps(review.__dict__ if review else None, default=str))
PY
```

**Behavior when the module call fails**: Note the failure, proceed as if no DynamoDB
history. Do not block on DynamoDB availability.
