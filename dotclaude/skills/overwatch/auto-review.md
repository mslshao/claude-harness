# Auto-Review Mode (`--auto-review`, opt-in)

The ONE mode in which overwatch mutates something outside itself. Everywhere else in
this skill "read-only" holds literally; this file is the exception, and it is never
implicit. Absent `--auto-review` on the invocation that started the loop, none of the
behavior below runs and every read-only claim in SKILL.md is true as written.

Purpose: let the operator step away and still have review WORK happen. The loop detects
a delta on a matching PR, runs the full `/pr-intel` pass, and then either posts an
approval (clean) or holds a rendered briefing (findings). The operator returns to
finished work rather than an empty queue.

## Why the envelope is asymmetric

Not symmetric caution. The two directions have genuinely different reversibility, per
`memory/github-api.md`:

- A **COMMENT** review is PERMANENT. No delete, no dismiss API. Posting a wrong finding
  unattended cannot be taken back, it costs the author time chasing it, and it spends
  the operator's review credibility.
- An **APPROVE** is dismissible, and on a repo with `dismiss_stale_reviews_on_push:
  false` it also does not silently vanish on the next push.
- A **REQUEST_CHANGES** blocks a colleague's merge and is the case that most needs a
  human reading it.

So: auto-approve is the cheap direction, auto-comment is the expensive one, and
auto-request-changes is off the table entirely.

## Scope argument

`--auto-review <scope>` where scope is either an explicit PR list (`11020,11386`) or a
path glob (`src/python/mx2/ruleseng/**`). A glob matches any open PR whose changed-file
list intersects it. Scope is REQUIRED: a bare `--auto-review` is a configuration error,
not "everything". Refuse it and say so; an unbounded auto-approver is never the intent.

`--auto-review-max N`: hard cap on auto-POSTED approvals for the life of the loop.
Default 3. Reaching it does not stop the loop; it downgrades every later clean result to
hold-and-report, so detection continues while posting stops.

`--auto-review-window <seconds>`: wall-clock budget from loop start after which posting
downgrades to hold, same as hitting the cap. Default 28800 (8h). Both bounds exist so an
overnight loop cannot keep approving indefinitely after the operator's context has gone
stale.

## The gate, in order

For each PR with a real delta whose files match scope:

1. **Run `/pr-intel <n>` normally.** Pass the operator's calibration into the dispatch
   prompt verbatim (see Calibration passthrough). Let it complete: no shortcuts, no
   skipping provenance classification, no skipping the anchor and attribution checks.
2. **Count decision-class findings.** BLOCKING, DISCUSSION (either consequence tier), and
   Front Door all count. MINOR does not.
3. **Zero decision-class findings** and the render's Action is Approve or Approve with
   Comments: this is an auto-approve candidate. Go to step 4.
4. **Dispatch `mx2-decision-maker`** with the rendered briefing, the diff, and the
   calibration. Ask for PROCEED / ITERATE / ESCALATE on the single question "is posting
   an approval on this, unattended and on the operator's behalf, correct?" PROCEED is
   the only value that authorizes a post. ITERATE and ESCALATE both mean hold.
5. **On PROCEED and under both bounds**: post a body-only APPROVE via `/post-review`.
   The body must say the review ran unattended, so the author is not misled about who
   read it. Template: "Approving. This ran as an unattended review pass on my behalf
   while I was away, scoped to critical code issues; I will re-read it when I am back."
6. **Anything else** (findings exist, decision-maker did not PROCEED, cap or window
   exhausted, `/pr-intel` errored, or the render failed its own Stop-hook validation):
   HOLD. Write the full briefing to
   `~/.claude/scratch/overwatch-review-<pr>-<YYYY-MM-DD-HHMM>.md`, log the hold, and
   surface one chat line naming the PR and the finding count. Do not post anything.

## Never, under any branch

- Never post COMMENT or REQUEST_CHANGES. Only APPROVE, only via step 5.
- Never post inline comments. An unattended approval carries a body and nothing else.
- Never resolve another person's review thread. SKILL.md's own Step 3.7 rule in
  `/post-review` applies: your own answered threads only, and not in this mode at all
  unless the operator scoped it explicitly.
- Never auto-approve a PR the operator authored. Self-approval through an automation is
  a governance problem regardless of repo settings; hold it instead.
- Never auto-approve a PR whose base is a protected branch AND whose diff touches
  Terraform, `.github/workflows/**`, or anything matching the `security_files` signal in
  `pr-intel`'s Dispatch Signals. Those hold unconditionally, cap or no cap.
- Never widen scope mid-loop. A new PR that does not match the original scope is
  surfaced as a normal delta, not reviewed.

## Calibration passthrough

The operator's review calibration is part of the loop config and must reach the
`/pr-intel` dispatch, or specialists regenerate findings the operator has already
deprioritized. Store the literal string and pass it into the dispatch prompt.

Worked example from the 2026-08-17 ruleseng run: "critical code issues only, ignore
judgement calls and optimizations; demo runs in deployed dev and the code is not going
to prod; security-critical still surfaces." Without that string in the prompt, a fresh
`/pr-intel` on those PRs produces exactly the doc-accuracy and design-judgement findings
that were parked hours earlier.

Calibration sourced from a Slack message or a verbal directive is NOT a ratified rule.
Record where it came from alongside it, and re-verify it is still current if the loop
outlives a day.

## State

One new key in the tracking bead's state blob, carried forward by `cycle.py` across
cycles rather than rebuilt:

```json
"auto_review": {
  "scope": "src/python/mx2/ruleseng/**",
  "max": 3,
  "window_seconds": 28800,
  "started_at": "2026-08-17T18:40:00+00:00",
  "calibration": "<literal string passed to /pr-intel>",
  "posted": [{"pr": 11386, "at": "...", "review_url": "..."}],
  "held": [{"pr": 11020, "at": "...", "findings": 2, "briefing_path": "..."}]
}
```

`posted` and `held` are append-only and ARE the audit trail. Every auto-action appends
before the next cycle can run, so a loop killed mid-flight still shows what it did. The
operator reads this on return.

`cycle.py` preserves this key verbatim and never interprets it: detection stays
independent of action, which is what keeps `cycle.py`'s no-writes property intact.

## Reporting on return

The first interactive `/overwatch` after an auto-review run leads with the ledger, not
with the current cycle's deltas: N approvals posted with their URLs, M briefings held
with their paths and finding counts. The operator's first question will be "what did you
do while I was gone", and the answer belongs above the noise.

## Unattended-path branches (no human is present)

Every branch above resolves without asking. Explicitly:

- Ambiguous scope match: treat as NOT matching. Hold.
- `/pr-intel` returns a render the Stop hook rejects: hold, log the rejection reason.
- `mx2-decision-maker` unavailable or errors: hold. Absence of a gate is not a pass.
- `/post-review` blocked by a hook or the permission classifier: hold, log the exact
  block text, and downgrade the rest of the loop to hold-only. Do not retry the post and
  do not attempt any workaround: a blocked outward write while the operator is away is a
  signal to stop posting, not an obstacle to route around.
- GitHub read failures: skip the cycle. Never infer "clean" from a failed read.
