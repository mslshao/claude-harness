# Phase 6: Finalization

Detailed procedure for the finalization phase: verification, commits, the
/review fan-out, PR creation (independent vs stacked), the /pr-intel --mine
self-review gate, cleanup, and the completion report. The SKILL.md Phase 6
section points here and keeps the load-bearing invariants inline.

## 6.1: Verification

Run `pants tlc` against all changed targets in the worktree (skip if
`--skip-checks` was passed). Route failures to the responsible agent:
- Lint/style failures -> implementer or flex agent that wrote the code
- Test failures -> tester (if test is wrong) or implementer (if code is wrong)
- Type errors -> whoever introduced the untyped code

Iterate until clean or circuit breaker (3 attempts).

## 6.2: Commits

Apply the commit strategy from the approved plan:
- **Small tasks**: one commit with a clear message
- **Larger tasks**: separate commits at behavior boundaries, each with a message
  documenting the behavior contract of that commit state

Commit messages include the Jira ticket ID: `[MX2-XXXXX] <description>`

## 6.2.4: /review Fan-Out (broad pre-PR gate)

After commits land on the worktree branch, invoke the `/review` skill against
the worktree diff. `/review` resolves to the more comprehensive of the personal
and project review skills (personal wins via name-overlap precedence and is the
broader fan-out); it dispatches its full parallel review-agent roster
(conditionally triggered), deduplicates overlapping findings, and produces a
severity-grouped report. The roster evolves with the skill, so do not hardcode a
count here.

`bot-review` runs WITHIN `/review`'s fan-out (when public surface changes,
hard-capped at COMMENT/NOTE/SUGGESTION), so its cross-file blast-radius findings
arrive in the same report. All `/review` findings are advisory; PR creation
proceeds regardless. The operator reads the report before flipping the PR from
draft to ready and resolves CRITICAL/WARNING items before publishing.

Invocation: from the worktree directory so `git diff origin/main..HEAD` is
the natural scope, then:

```
Skill(skill="review")
```

Post the report to the tracking bead:

```bash
bd comment <tracking-bead-id> "[/review report: PR-pending]

<skill output>"
```

If `/review` returns CRITICAL findings, surface them to the operator in the
Phase 6.5 report under a `### /review CRITICAL findings` header so they are
not missed among the lower-severity findings.

## 6.2.5: bot-review (folded into /review)

`bot-review` is now one of `/review`'s conditional fan-out agents (6.2.4),
dispatched only when `changes_public_surface` is true and hard-capped at
COMMENT/NOTE/SUGGESTION. Its cross-file blast-radius findings appear in the
`/review` report already posted to the tracking bead; there is no separate
bot-review dispatch (the standalone pass was retired when `/review` absorbed
`bot-review` as a fan-out agent). Strict advisory: the severity hard-bar
guarantees these findings cannot block PR creation.

## 6.3: PR Creation

Always run from the worktree. Never check out the launch branch in the main
workspace. Two sub-paths depending on whether the launch is **independent**
(worktree off `origin/HEAD` / main; default) or **dependent** (worktree off a
non-main parent branch; stacked launch on top of an unmerged parent PR).

> **Em-dash guard**: `~/.claude/hooks/block-em-dash.sh` scans `gh pr create`,
> `gh api -X POST/PUT/PATCH`, `gh pr comment`, `gh pr review`, and `gh issue
> comment` for U+2014 and blocks on match. `gt submit` shells out to `gh`, so
> the same constraint applies. Sanitize the PR body file before invoking
> either path.

**Step 1: Determine the base branch.** Read the worktree's branch parent:
```bash
BASE_BRANCH=$(git -C "$WORKTREE_DIR" rev-parse --abbrev-ref --symbolic-full-name @{upstream} 2>/dev/null | sed 's|^origin/||' \
  || git -C "$WORKTREE_DIR" log --pretty=%D origin/HEAD..HEAD --decorate=full 2>/dev/null | grep -oE 'origin/[^,)]+' | head -1 | sed 's|^origin/||' \
  || echo "main")
```
For a standard non-stacked launch (worktree created from `origin/HEAD` in Phase 5.1)
this resolves to `main`. For stacked launches (worktree created from another branch)
it resolves to that parent. Defaults to `main` if detection fails.

**Step 2: Build the PR body file.** Build `/tmp/pr-body-<branch>.md` BEFORE
invoking either submit path. Read the repo's PR template FIRST
(`<repo>/pull_request_template.md` or `<repo>/.github/PULL_REQUEST_TEMPLATE.md`)
and use its structural skeleton (H1 sections, `Jira issue link:` line,
`# Checklist` items filled out, `Require-reviewers: all` line). Layer the personal
style rules from `memory/pr-template.md` on top (H2 subsections within Summary,
Jira link at the bottom, no hard line-wrapping, clickable markdown links).
Skipping the repo template breaks Mergify's checklist-fill protection and produces
a PR description that does not match the team's structural standard. See the
recurrence note in `~/.claude/CLAUDE.md` PR descriptions rule for the 2026-04-29
instance.

**Step 3: Submit the PR (path depends on Step 1).**

**Path A: Independent launch (`BASE_BRANCH == "main"`).** Raw `gh` is fine. The
PR has no parent relationship to register, and Graphite tracking adds no value.
```bash
cd "$WORKTREE_DIR"
git push -u origin HEAD
gh pr create --draft \
  --title "[MX2-XXXXX] <description>" \
  --body-file /tmp/pr-body-<branch>.md
```

**Path B: Dependent launch (`BASE_BRANCH != "main"`).** Use `gt` so the stack
relationship is registered with Graphite. Without this, the GitHub-level base
branch is set correctly (so reviewers see only the new delta), but Graphite is
unaware: `gt log short` won't show the stack, and `gt restack` / `gt sync` won't
operate on it. Recurrence context: 2026-05-08 PR #8971 silent-failure-hunter
launch shipped via Path A and required retroactive `gt track` cleanup.
```bash
cd "$WORKTREE_DIR"
gt track --parent "$BASE_BRANCH"
gt submit --stack --no-interactive --draft \
  --body-file /tmp/pr-body-<branch>.md
```
- `gt track` is forbidden in the main checkout (CLAUDE.md), allowed in worktrees
  under the worktree exception.
- `gt submit --stack` submits this branch and any tracked ancestors that haven't
  been submitted yet, sets the PR base to the tracked parent automatically, and
  pushes with `-u`. On already-submitted parent PRs it re-pushes commits but does
  not clobber existing PR description bodies (verified 2026-05-09 launch-sfh).
- `--draft` matches the "draft PR always" rule below.

**Step 4: Capture the PR URL** for the report in 6.5:
```bash
PR_URL=$(gh pr view --json url --jq .url)
```

## 6.3.5: Self-Review Gate (`/pr-intel --mine`)

Before cleanup and the final report, run `/pr-intel --mine <pr-number>` on the
just-created draft PR. This is CLAUDE.md `/launch` heuristic 1b ("before
publishing, run /pr-intel --mine") and it is the orchestrator's job, not a
suggestion left to the user. The 6.2.4 `/review` fan-out (bot-review included)
catches issues within the diff; `/pr-intel --mine` adds what it cannot: AC-compliance
trace against the ticket/bead, CI status on the pushed PR, static-analyzer
pre-check (SonarCloud, Datadog), and the cross-phase integration-bug check
(wrong field names at call sites, dropped fields during refactor). Because
6.2.4 already ran `/review` on the same diff, pr-intel's review-cache reuse
path picks up those specialist findings and only adds the self-review-specific
checks, so the cost is the AC/CI/static-analyzer delta, not a full re-dispatch.

Run it while the worktree still exists (before 6.4 cleanup); pass the worktree
as the code root since the main checkout is on `main`, not the PR branch.
Surface the verdict in the 6.5 report. If it returns BLOCKING findings, resolve
and amend before reporting; do not leave a known-blocking PR for the user to
discover at flip time.

Recurrence context: 2026-05-29 MX2-NNNNN / PR #9461, where the orchestrator
declared the launch done after creating the draft plus posting to Jira, and the
user had to prompt "did you run /pr-intel --mine?" The self-review confirmed the
PR was sound, but the step belongs in the flow.

## 6.4: Cleanup

```bash
git worktree remove "$WORKTREE_DIR" --force 2>&1 || \
  (rm -rf "$WORKTREE_DIR" && git worktree prune)
```

## 6.5: Report

Present to the user:
```markdown
## Launch Complete: [topic]

**PR**: [URL] (draft)
**Graphite**: https://app.graphite.dev/github/pr/lawfirm/main/[number]
**Branch**: [branch-name]
**Jira**: [MX2-XXXXX]

### What was built
[2-4 sentences summarizing what the agents implemented]

### Agents dispatched
[Agent roster with what each did]

### Scope creep tickets
[MX2-YYYYY, MX2-ZZZZZ, or "none"]

### Suggested next steps
- [ ] Review the PR on Graphite
- [ ] Review the `/pr-intel --mine` briefing above (run in 6.3.5); resolve any open items
- [ ] Publish when ready
```
