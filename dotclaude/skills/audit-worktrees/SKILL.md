---
name: audit-worktrees
description: Audit and clean up stale agent/autopilot worktree branches in /workspaces/main. Identifies orphaned launch agents, merged-and-shipped branches, and other-authored /pr-intel staging areas. Confirms before any deletion. Trigger on "audit worktrees", "clean up worktrees", "stale branches", or when worktree count grows past comfort threshold.
argument-hint: "[--auto]"
---

# Audit Worktrees

Audit `/workspaces/main/.launch-worktrees/` and produce a deletion plan with verification evidence per branch. Confirm with the user before deleting unless `--auto` is passed AND the deletion count is at or below 15.

## Why this skill exists

Worktree cleanup is a recurring chore in heavy `/launch` and `/autopilot` use. The
`worktree-create-log.sh` and `worktree-remove-log.sh` hooks handle the happy path
(clean agent termination), but accumulate sad-path orphans:

- `/launch` agents whose terminal closed before WorktreeRemove fired
- `/autopilot` runs that crashed or were interrupted
- `/pr-intel` staging areas where another engineer's commits were used as a working copy
- Manual `MX2-NNNNN/...` or `chore/docr-XXXX-...` branches abandoned mid-flow

This skill codifies the per-branch verification ladder so it does not need to be
re-invented each time. See bd memories `gotcha:orphaned-worktrees-2026-05-07`.

## Scope (do check)

All worktrees in `git worktree list` except the main checkout (homes: `/workspaces/main/.launch-worktrees/` and `/workspaces/main/.claude/worktrees/`), with branch names matching:
- `agent/*` (WorktreeCreate-hook agent worktrees, the dominant current pattern) and `<user-prefix>/<jira-or-bead>` (e.g. `mslshao/mx2-...`)
- `autopilot/*` (autopilot bead-driven runs)
- `MX2-NNNNN/*` (Jira-prefixed feature branches)
- `chore/*`, `fix/*` (bead-driven chores)
- `launch-<timestamp>` (legacy /launch worktrees; the current hook produces `agent/*` instead)

## Scope (do NOT touch)

- The main worktree (no branch in `git worktree list` whose path is `/workspaces/main` itself)
- Any branch with an OPEN PR
- Any worktree with uncommitted changes (dirty `git status`)
- Any branch the user names explicitly in the invocation as protected

## Process

### Step 1: Enumerate worktrees and check status

```
git -C /workspaces/main worktree list
```

For each worktree, capture: path, branch name, dirty status, unique-commit count vs `origin/main`.

```
git -C /workspaces/main fetch origin main --quiet
git -C <worktree> status --short
git -C /workspaces/main rev-list --count "origin/main..<branch>"
```

### Step 2: Resolve PR for each branch

Use a sequence of search strategies (per personal CLAUDE.md "Exhaust search strategies before claiming external-system absence"):

```
gh pr list --head "<branch>" --state all --repo <company>/docr --json number,state,mergedAt --limit 3
```

If empty for a branch with unique commits, also try:
- `gh pr list --search "head:<branch>" --state all`
- `gh search prs --head "<branch>" --repo <company>/docr --state closed`

Three empty searches = "no PR exists" with reasonable confidence.

### Step 3: Classify each branch

| Signal | Classification |
|--------|----------------|
| OPEN PR | SKIPPED-IN-FLIGHT |
| Dirty worktree | SKIPPED-IN-FLIGHT (regardless of PR state) |
| 0 unique commits vs origin/main | DELETE (no work to lose) |
| MERGED PR + branch->main diff = 0 | DELETE (fully shipped) |
| MERGED PR + non-zero diff | Verify each unique commit's content lives on main via grep, then DELETE if confirmed |
| Closed (not merged) PR | SKIPPED-CLOSED (flag for owner review) |
| No PR + unique commits authored by Michael Shao | FLAGGED-UNSHIPPED-WORK (do not delete; owner must decide) |
| No PR + unique commits NOT authored by Michael Shao | DELETE (likely /pr-intel staging area, per session 2026-05-07 heuristic) |

For the last row, check authorship via:
```
git -C /workspaces/main log "origin/main..<branch>" --pretty=format:"%h | %an"
```

Treat any author other than the user's git identity (`git config user.name`) as a staging-area signal.

### Step 4: Verify dangling commit content (only for MERGED with non-zero diff)

For each unique commit on the branch, check that its specific text is on main:
```
git -C /workspaces/main grep -n "<distinctive-string-from-commit>" origin/main -- <touched-file>
```

If 4+ distinctive strings from the commit are on main, content is shipped.

If `git diff <branch> origin/main -- <touched-files>` is empty, that alone confirms shipping; skip the per-commit grep.

### Step 5: Build the audit report

Produce a markdown table grouped by classification:

```
| Branch | Worktree | PR # | PR State | Action | Notes |
|---|---|---|---|---|---|
```

Group order: DELETE candidates first, SKIPPED-IN-FLIGHT, FLAGGED-UNSHIPPED-WORK, SKIPPED-CLOSED.

### Step 6: Confirm before deletion

Always present the audit table (Step 5) before deleting, so the plan is visible.

Skip the AskUserQuestion confirm gate and proceed when ALL hold: deletion count <= 15,
a recovery SHA is captured for every DELETE candidate (worktree deletion is
reflog-reversible), AND the invocation carries authorization. Authorization =
`--auto` passed, OR an explicit upstream cleanup directive (the user typed "clean up
worktrees" / "audit worktrees", or selected a cleanup action that routed here). Per
~/.claude/CLAUDE.md "Don't re-confirm within a directive's scope": worktree deletion
is the action "clean up" authorizes, and it is reversible, so a second confirm is a
re-confirm to skip. Surface the plan, then proceed.

Ask via AskUserQuestion (yes-all / yes-conservative-subset / hold-off) only when
authorization is absent, OR deletion count > 15, OR any DELETE candidate lacks a
recovery SHA. The count>15 and missing-SHA conditions are the safety floor: large or
irreversible deletions always confirm regardless of directive.

### Step 7: Execute deletions in dependency-safe order

1. Nested worktrees first (worktrees inside another worktree's path)
2. Then their parent worktrees
3. Then everything else

For each branch:
```
git -C /workspaces/main worktree remove <worktree-path>
git -C /workspaces/main branch -D <branch>
# If remote ref still exists (rare on auto-delete-on-merge repos):
git -C /workspaces/main ls-remote origin <branch>
git -C /workspaces/main push origin --delete <branch>  # only if ls-remote returned a ref
```

After all deletions:
```
git -C /workspaces/main fetch origin --prune
git -C /workspaces/main worktree list
```

### Step 8: Report final state

Show: count deleted, count skipped-in-flight, count flagged-unshipped, the final `git worktree list`, and any flagged branches the user should follow up on.

## Constraints

- Personal CLAUDE.md applies: no destructive ops outside the explicit deletion procedure above. No force-pushes. No rebases. No commits.
- Do NOT delete branches that are not attached to a worktree (out of scope; this skill audits worktree-attached branches only).
- Do NOT use `git stash`, `git reset`, or `git checkout` to "clean" a dirty worktree. If dirty, skip and report.
- The "other-authored = staging" heuristic applies ONLY to worktree branches (this is a workflow inference about how worktrees get created in this setup), not to general branch cleanup.

## Recovery

Deleted branches are recoverable from git's object store for ~90 days via:
```
git -C /workspaces/main branch <branch-name> <commit-sha>
git -C /workspaces/main worktree add <path> <branch-name>
```

Capture the `<commit-sha>` for each deleted branch in the final report so recovery is one command away.

## Reference

- `gotcha:orphaned-worktrees-2026-05-07` (heuristics from the original audit session)
- `correction:verification:search-strategy-exhaustion` (multi-strategy PR search rule)
- Existing hooks: `~/.claude/hooks/worktree-create-log.sh`, `~/.claude/hooks/worktree-remove-log.sh` (handle happy path; this skill handles the sad path)
