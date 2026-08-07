# Prior Reviews (bd memories + DynamoDB + own live GitHub review)

This file documents how /pr-intel discovers prior review history for a PR and folds it into the current review's data-gathering, specialist preamble, dedup context, and default recommendation.

Three channels are checked in parallel:
1. `bd memories pr-<number>` for terminal-side review memories (`/post-review` writes these).
2. DynamoDB `pr-review` table for cross-modality state (terminal sessions and the Slack bot share this).
3. The reviewer's OWN live GitHub review, re-checked just before render (not only at data-gathering): scan `reviews[]` for an entry whose `author.login` is the running reviewer (`mslshao`). A review posted MANUALLY (GitHub UI, not via `/post-review`) lands in neither channel 1 nor 2, and one posted CONCURRENTLY during the run is absent from the initial metadata fetch, so a late re-check (`gh pr view <n> --json reviews`) right before producing the briefing catches both. When a self-review is found that channels 1-2 do not already cover, surface it BEFORE the briefing ("You already have a <STATE> review on this PR posted <date>, not via /post-review; read it first, this run may duplicate it") and default to a delta/confirm posture rather than a fresh full briefing. (Observed 2026-06-24 on #9926: a manual `mslshao` APPROVE landed mid-run, the briefing did not account for it, producing "read what I wrote instead.")

If all three channels fail or are empty, the review proceeds as first-round.

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

**Full-detail fallback**: `bd memories pr-<number>` lists matching keys with truncated one-line previews (enough to parse `findings_summary`). To read the FULL content of a specific prior round (complete findings, not the preview), use `bd recall <key>`:
```bash
bd recall review:pr-<number>:<YYYY-MM-DD>
```
Reach for this when a steer says "look at the prior review for #N", or when delta-aware dedup needs the verbatim prior findings. Fall back to the posted GitHub review (`gh api .../pulls/<number>/reviews` and `.../comments`) only when you need inline-comment thread positions or bot comments beyond what the memory captured.

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

   **Rebase caveat (the 2-dot delta lies on a rebased branch).** The command above is
   a 2-dot diff, clean only while `<latest_prior.head_sha>` is still an ancestor of
   `<headRefOid>`. If the branch was rebased since the prior review (common), the old
   SHA is no longer on the branch's line of history, and `git diff <prior> <head>`
   folds in every main-branch change merged during the rebase, producing a garbage
   delta (observed 2026-07-13: a ~1700-file / ~100k-line "delta" on a PR whose real
   3-dot diff was +36). Guard before trusting it:
   - `git merge-base --is-ancestor <latest_prior.head_sha> <headRefOid>`: exit 0 means
     no rebase (2-dot delta is clean); non-zero means rebased (2-dot delta is polluted).
   - Cheap alternative: if `git diff <prior> <head> --stat` reports far more files than
     the PR's own `changedFiles`, the branch rebased.
   - On a rebased branch, do NOT send the 2-dot delta. Use the current PR 3-dot diff
     (`gh pr diff <N>`) as the primary scope and verify each prior-round finding against
     current file state (grep the specific issue at HEAD), since "what changed since
     last review" is not cleanly expressible via git diff across a rebase.
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
   Prior approval is signal, not noise. This bias is a tie-breaker applied after
   fresh specialists read the delta (see Re-review anti-anchoring below), not a
   reason to skip that read. Conversely, if the prior review was REQUEST_CHANGES,
   verify the requested changes landed before any new approval.

   **Mechanical consequence when your own prior review was REQUEST_CHANGES:** a new
   COMMENT review does NOT clear it on GitHub (reviewDecision stays
   `CHANGES_REQUESTED`, merge stays blocked); only an APPROVE or an explicit dismiss
   clears it. So once the blockers ARE resolved and only non-blocking discussion
   items remain, surface the choice explicitly rather than defaulting to Comment:
   Comment holds the block (correct when a remaining item genuinely should gate
   merge), Approve-with-comments clears it and logs the discussion inline (correct
   when the remaining items are non-blocking, i.e. approve-while-logging-dissent).
   Do not post a Comment assuming it lifts your prior block.

**Gate-state check before clearing blockers (mandatory, not size-gated).** Before
reporting any prior-round blocker as resolved, confirm the PR's actual gate state:
`gh pr checks <n>` plus `gh pr view <n> --json mergeStateStatus,statusCheckRollup`.
A red check or BLOCKED/UNSTABLE from a real failure means the blocker is NOT
cleared, regardless of whether the code change is present. Code-presence is not
mergeability; trace a red check to root cause before rendering the verdict, since
the live blocker is often a DIFFERENT failure than the reviewed one (a BUILD glob,
a coverage gate, a lint failure). (2026-07-15, #9725: a 404-guard blocker was
declared "cleared" on code presence while CI was red from a `python_tests` BUILD
glob with no test files plus a 0%-new-code-coverage Sonar gate; `merge=BLOCKED`
was visible and went unchased.)

**Re-review anti-anchoring (fresh perspective over carried opinion).** On a
re-review with a real content delta (not the empty/rebase short-circuit below),
the orchestrator is the most anchored input present: it carries its own
prior-round verdict and drifts toward confirming it. That pull is strongest
exactly when the delta looks trivial or "resolves my prior finding," which is
when skipping a fresh read is hardest to notice.

- Fresh specialist dispatch on the delta is mandatory; the orchestrator must NOT
  substitute its own read for a specialist pass, however small or mechanical the
  change. A trivial delta changes WHICH specialists trigger, never WHETHER any
  run. Specialists have no memory of the prior rounds, so their delta read is the
  independent perspective the orchestrator cannot supply.
- The item-5 prior-approval bias is a tie-breaker applied AFTER the fresh read,
  not a license to skip it.
- Treat a specialist read that diverges from the orchestrator's carried
  expectation as signal to investigate, not noise to reconcile against the prior
  verdict.

(2026-07-13, #10483 round 3: the orchestrator skipped dispatch on a real code
delta because it "resolved my round-2 finding," self-verified by grep, and
approved. The delta was clean, but the path was the anchored one and a fresh read
was owed.)

**Behavior when the delta is empty (re-review short-circuit)**: When prior reviews
exist but the delta-focused diff (item 2) has no content change (the PR's changed
files are identical between `<latest_prior.head_sha>` and `<headRefOid>` because the
new commits are a pure rebase or `Merge ... origin/main`), do NOT dispatch specialists
or render a full briefing. Short-circuit with a one-line result: `No review needed:
delta empty since the <date> review (rev <prior> to <current> is a rebase or
main-merge, no content change).` Scope the emptiness check to the PR's changed-file
paths (`git diff <latest_prior.head_sha> <headRefOid> -- <changed paths>`), not the
whole tree, since a main-merge touches many unrelated files. This is the re-review
analogue of the Merge Base Freshness all-files-already-on-main short-circuit: the
prior review still stands, so re-running it spends a full specialist pass on unchanged
code.

**Sub-case: zero new commits since the running reviewer's own approval.** The
strongest empty form is `headRefOid` equal to the exact commit the running
reviewer already self-approved (channel 3 above found a self-`APPROVE` whose
`commit.oid` is the current head, with no commits added since). There is no
delta at all, not even a rebase, so the one-line short-circuit applies even
harder. Do NOT render the full template; it buries the only fact that matters
and reads as "why am I reviewing my own approved PR again?" (observed
2026-06-29 on #10113: a full render with the self-approval folded into a
lead-in note still drew "wait, we already approved it?"). Lead with the
one-liner instead: `Already approved: your APPROVE on <date> is on the current
head <short_sha>; nothing has changed since. No re-review needed.`, then list
only the still-open threads from that round. This overrides the pre-fired
`userpromptsubmit-pr-intel-contract.sh` message (that hook runs at invocation,
before the delta is known, so it cannot exempt this case itself); keep the
one-liner free of the structured-template headers and the collapse-pattern
tokens (`Action:`, `Blocking: N`, `#N reviewed`) so `stop-validate-pr-intel.sh`
reads it as a clean short-circuit, not a collapsed render.

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
