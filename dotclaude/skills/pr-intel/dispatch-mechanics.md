# Dispatch Mechanics

Operational detail for the Specialist Dispatch phase: worktree isolation,
spot-check sampling for large mechanical refactors, and `--mine` review-cache
reuse. The SKILL.md Specialist Dispatch section points here; the dispatch
triggers and per-specialist prompt templates live in [dispatch.md](dispatch.md).

## Branch Safety (Worktree Isolation)

Each pr-intel invocation creates its own temporary git worktree so it never
touches the user's working tree. This allows multiple reviews to run in
parallel without checkout conflicts or disrupting the user's terminal.

**Exception: `--mine` mode.** When reviewing your own PR, the user is already
on the PR branch. Skip worktree creation entirely and use `/workspaces/main`
(the main repo) as the code root for all specialist prompts. The user's
working tree already has the code they want reviewed.

Do NOT use `isolation: "worktree"` on specialist Agent calls. That creates
per-agent worktrees which causes git lock contention. Instead, create ONE
worktree for the entire pr-intel invocation and pass the path to all
specialists.

**Before dispatching specialists (default and --quick modes only):**
1. Create a temporary worktree at the PR's HEAD commit:
   ```bash
   # Stable path, NOT /tmp: parallel specialist dispatch can run 10+ min, and the
   # codespace /tmp reaper reclaims the dir mid-run (observed PR #10714, 2026-07-20:
   # 7 of 8 agents found the worktree gone and recreated it). ~/.claude/worktrees is
   # not /tmp-reaped and is where other worktrees already live.
   mkdir -p ~/.claude/worktrees
   WORKTREE_DIR=$(mktemp -d ~/.claude/worktrees/pr-intel-XXXXXX)
   git worktree add --detach -q "$WORKTREE_DIR" <headRefOid> 2>&1
   ```
2. Verify: `git -C "$WORKTREE_DIR" log -1 --oneline` should show `<headRefOid short>`.
3. Save `$WORKTREE_DIR` - all specialist prompts must include it as the
   code root for Read/Grep/Glob operations (see Dispatch below).

**After ALL specialists return and synthesis is complete:**
4. Remove the worktree:
   ```bash
   git worktree remove "$WORKTREE_DIR" --force 2>&1
   ```
5. If removal fails (e.g., locked), prune the stale registry entry:
   ```bash
   git worktree prune
   ```
   Do NOT `rm -rf "$WORKTREE_DIR"`: it trips the destructive-command floor
   (observed 2026-06-26) and is unnecessary (`git worktree remove` in step 4
   deletes the dir; `git worktree prune` clears any stale registry entry). The
   worktree now lives under `~/.claude/worktrees` (not /tmp), so proper teardown
   matters: it is not OS-reclaimed. If a locked dir genuinely must be
   force-removed, surface the path to the user rather than running `rm -rf` yourself.

The user's working tree is never modified. No branch save/restore needed.

If `git fetch` failed in Data Gathering, skip worktree creation and add a
BRANCH WARNING to each specialist prompt instead:
"WARNING: Could not fetch PR branch. Your Read/Grep/Glob results may show code
from a different branch. Rely primarily on the inline diff for analysis."

## Spot-Check Mode (large mechanical refactors)

When `spot_check_eligible: true` AND mode is `default`, the diff sent to
each specialist is reduced from the full PR diff to N=3 representative
files. The engineering lead's Code Review Guide #11: "Rather than reviewing every single
changed line, focus your review on the methodology... spot-check a few
instances, but focus your review on the methodology."

**Sample selection (deterministic):**
1. Sort net-new files alphabetically by path.
2. Pick the first file, the median (by sorted-index), and the last file.
   These three are the "representative sample." Choosing by sorted index
   instead of randomly keeps the briefing reproducible across runs.
3. If fewer than 3 net-new files exist, the spot-check trigger is false
   (only fires when file count >= 10 anyway).

**Briefing addition (always emit when spot-check fires).**
Add a section above Scope:

```
### Spot-Check Mode
Full diff: M lines across F net-new files. Mechanical pattern detected;
methodology referenced in PR description. Specialists ran on 3
representative files: <file_first>, <file_median>, <file_last>. Findings
below are sampled; reviewer should verify the methodology in the PR
description (the script, command, or rule applied) and spot-check
additional files if the sample raises questions.

Methodology quote from PR body:
> <one-line excerpt naming the script/command/rule>
```

**What specialists receive.** Per-agent prompts (see [dispatch.md](dispatch.md))
substitute the `<filtered implementation diff>` placeholder with the diff
of the 3 representative files only. The PR body, file list (full), and
worktree path stay unchanged so the agent has access to the broader
context if it needs to grep.

**What does NOT change in spot-check mode.**
- Static Analyzer Pre-Check still runs on the full PR (the analyzers
  already scoped themselves to the PR).
- AC Compliance Check still runs on the full PR (Jira ACs apply to the
  whole change, not the sample).
- bot-review (cross-file blast-radius) still receives the full file list
  (it's looking for consumer-invariant breakage; the sample would hide
  consumers).
- Phase 0 description quality still gates first (without a methodology
  statement, spot-check doesn't fire).

**Verdict and recommendation.** Specialists' findings on the sample are
representative, not exhaustive. The Draft Review Summary explicitly notes
"spot-check sample" so the reviewer can decide whether to expand the read
or trust the methodology. The Review Recommendation defaults one step
more conservative than the full-dispatch path would suggest: when
spot-check returns no BLOCKING findings on the sample, the recommendation
is `Comment` (not `Approve`), inviting the reviewer to confirm the
methodology is sound before approving.

When `spot_check_eligible: false` (default), this section is omitted from
the briefing and specialists receive the full filtered diff as before.

## Review-Cache Reuse (`--mine` only)

In `--mine` mode, before dispatching specialists, check for a reusable `/review`
cache so an immediately-preceding `/review` on the same unchanged diff does not
pay for a full re-dispatch (bead `docr-xvnr`). Default mode (reviewing another
author's PR) NEVER reads the cache: there is no local `/review` run for a diff
you did not produce.

1. Compute the current diff identity from the worktree. Derive `BRANCH` from the
   PR's `headRefName` (already fetched in pre-flight), NOT from
   `rev-parse --abbrev-ref HEAD`: the worktree is often checked out detached at
   the PR head commit, where `--abbrev-ref HEAD` returns the literal `HEAD` and
   would never match the slug `/review` wrote.
   ```
   BRANCH=<PR headRefName from gh pr view --json headRefName>
   SLUG=$(echo "$BRANCH" | tr '/' '-')
   MB=$(git -C "$WORKTREE_DIR" merge-base origin/main HEAD)
   DIFF_SHA=$(git -C "$WORKTREE_DIR" diff "$MB" | grep -vE '^index ' | sha256sum | cut -d' ' -f1)
   ```
2. Load `~/.claude/scratch/review-cache/<SLUG>.json` if present.
3. **Cache HIT** requires ALL of: file exists; `branch` matches; `diff_sha256`
   equals the computed `DIFF_SHA`; `timestamp` within 2h. Diff identity is the
   PRIMARY key (a byte-identical diff means the findings are still valid no
   matter how much wall-clock elapsed); the 2h TTL is only a secondary guard
   against reusing findings produced by a since-edited agent definition.
4. **On HIT**: reuse the cached `findings` for every overlapping specialist
   (mx2-code-reviewer, test-quality-reviewer, observability-reviewer,
   mx2-silent-failure-hunter, mx2-security-auditor, mx2-devops-build-deploy,
   mx2-typescript-reviewer, mx2-git-historian, bot-review, mx2-skeptic,
   mx2-pydantic-reviewer, module-cohesion-reviewer). Do NOT re-dispatch them. STILL dispatch the
   pr-intel-only specialist absent from any `/review` run: `mx2-pr-precedent`
   (queries `gh` server-side). Feed the reused findings into Synthesis exactly
   as if the agents had just returned. Print one line before synthesis:
   `Reused N specialist findings from /review at <timestamp> (diff unchanged); re-dispatching: mx2-pr-precedent.`
   LIMITATION: `/review` prompts lack the per-specialist Jira-AC-deviation lens
   that pr-intel adds. The synthesis-layer spec-vs-diff trace (Phase 0.5) still
   runs and covers intent drift; full per-specialist AC re-dispatch on HIT is
   deferred.
5. **On MISS** (no file / branch mismatch / diff changed / stale): proceed to
   full dispatch below. Print one line: `No reusable /review cache (<reason>); full specialist dispatch.`
