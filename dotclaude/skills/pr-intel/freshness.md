# Merge Base Freshness & Ghost Diffs

Two local git checks that run after the PR head ref is fetched. They detect
content that GitHub's three-dot merge base hides or mis-attributes: files
already on main (stale) and files reverted by a rebase conflict (ghost diffs).
Both always run (local git operations). The SKILL.md Data Gathering section
points here.

## Remote Head Freshness (run first)

`gh pr view --json headRefOid` reads GitHub's cached PR metadata, which can lag the
actual branch ref by minutes when the author has just pushed. Acting on the stale SHA
produces false findings (reporting a fix as "not pushed" when it landed in a commit the
cached metadata does not yet show). Before any diff or freshness check, confirm the true
head:

```bash
git ls-remote origin <headRefName>     # authoritative current ref
# compare against the gh pr view headRefOid; if they differ, the metadata is stale
```

If they diverge, the `ls-remote` SHA is the true head: `git fetch origin <headRefName>`,
use that SHA for all diffs, hunks, line verification, and specialist dispatch, and
recompute size/dispatch signals against it. On a re-review, compute the revision delta
(`git diff <prior_head> <true_head>`) from the true head, not the cached one.

## Merge Base Freshness

After fetching the PR head ref, check whether any files in the PR's changeset have
content identical to current main (changes already shipped via a sibling PR that
merged first). This is a local git operation and always runs.

1. Get files that actually differ from main at the PR's HEAD:
   ```bash
   git diff origin/main <headRefOid> --name-only
   ```
2. Compare against the PR's full file list (from the `files` field in PR metadata).
3. Files present in the PR's file list but **absent** from the 2-dot diff output are
   **already on main**: their content at the PR HEAD is identical to current main.
4. Store as `merge_base_freshness`:
   - `stale_files`: file paths whose content matches main
   - `net_new_files`: file paths with actual differences
   - `is_stale`: true if any stale files detected
5. Downstream effects:
   - **Size Classification**: use net-new additions/deletions, not raw PR totals
   - **Dispatch Signals**: compute from net-new files only; exclude stale files
     from the filtered diffs sent to specialists
   - **Inline comments**: never target stale files (enforced in grounding.md)
   - **Scope**: show breakdown: "Files: 21 (17 net-new, 4 already on main)"

If all files are already on main (pure rebase artifact), short-circuit:
"This PR's diff is entirely content already on main. The branch needs a rebase."

## Ghost Diffs (Reverse Freshness)

Also check the reverse: files in the 2-dot diff that are **absent** from the PR's
file list. These are "ghost diffs" that GitHub's three-dot merge base hides from the
PR diff view. They typically appear when a PR is squashed/rebased and a rebase
conflict resolution accidentally reverts a recently-merged change.

1. Files present in the 2-dot `git diff` output but **absent** from the PR's `files`
   metadata are ghost diffs.
2. For each ghost file, check `git log origin/main -- <path>` (last 5 commits) to
   identify what recently-merged PR touched it. This reveals whether the ghost diff
   is an accidental revert of a specific PR.
3. Ghost diffs are **high-consequence findings** (potential silent reverts of merged
   work). Surface them as BLOCKING in the review summary with the recently-merged PR
   reference.
4. Ghost diffs cannot receive inline comments (not in GitHub's diff view). Include
   findings in the review body with file:line references.
5. Show in Scope: "Ghost diffs (not in GitHub diff): N files - see review body"

This check is the highest-value add for squashed PRs, where inter-revision visibility
is lost and rebase conflict reverts become invisible.

If `git fetch` failed earlier, skip this check and treat all files as net-new.

If `git fetch` fails (network error, fork PR with restricted access), note the failure
and skip worktree creation during specialist dispatch (see Branch Safety in
[dispatch-mechanics.md](dispatch-mechanics.md)).
