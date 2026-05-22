---
name: babysit-pr
description: Autonomous PR-iteration loop. Polls a draft PR on a paced cadence, classifies incoming comments (bot vs human, mechanical vs substantive), auto-remediates mechanical bot suggestions via a pre-staged worktree, replies inline, and escalates human reviewer feedback to the user. Use when stepping away from an open draft PR and wanting the loop to handle bot noise + small mechanical fixes without losing context. Trigger phrases include "babysit this PR", "watch PR #N", "auto-iterate on PR", "/babysit-pr".
argument-hint: "<pr-number> [--authorize-force-push] [--allow-published] [--window <duration>]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Edit", "Write", "ScheduleWakeup"]
---

# Babysit PR

Autonomous polling loop that watches an open draft PR, classifies incoming review comments, and takes bounded actions on the user's behalf while they are stepped away. State persists in a tracking bead so the loop survives session compaction and any single wakeup can cold-start from `bd show <bead-id>`.

This skill is the specialized variant of /loop dynamic mode: the poll-classify-act-persist body is fixed (because the domain is PR iteration), and the cadence is paced against the Claude prompt-cache window.

## When to invoke

- User says "babysit PR #N", "watch this PR", "auto-iterate on PR N", "babysit-pr".
- User is about to step away from a draft PR they just opened or pushed to and wants the loop to handle bot remediation and inline replies in the background.
- After a /launch or /pr publish, when bot feedback is expected (Copilot, PR Metrics, Vercel, Lighthouse, etc.) and the user has signaled they want hands-off handling.

## When NOT to invoke

- The PR is not the user's. The skill amends and force-pushes; that requires the PR to be authored by the operator.
- The PR is published and `--allow-published` is not set. Auto-merge can fire mid-loop, orphaning local amends. Refuse and ask the user to convert to draft.
- The PR is XL+ and the operator has not pre-staged a worktree. Auto-remediate amends on large PRs can race with CI runners; require an explicit worktree path in the start handshake for those.
- No `--authorize-force-push` was passed AND the operator wants auto-remediate. Without the verb, the loop falls back to ESCALATE-everything mode, which defeats the purpose. Either pass the verb or invoke /pr-intel on a cadence instead.

## Argument parsing

Raw invocation: `/babysit-pr $ARGUMENTS`

Extract from `$ARGUMENTS`:
- **PR number**: first numeric token. Required.
- **`--authorize-force-push`**: presence enables AUTO-REMEDIATE classification. Without it, ALL actionable findings escalate.
- **`--allow-published`**: presence overrides the non-draft refusal. Operator accepts auto-merge risk.
- **`--window <duration>`**: total window length. Default 1 hour. Accepts `30m`, `2h`, `90m`, etc.

If no PR number is found and the current branch has an associated PR, infer it via `gh pr view --json number,isDraft --jq '.number'`. Otherwise stop and ask.

## Preflight

Run these checks in order before scheduling the first wakeup. Fail fast on any blocker.

### 1. PR metadata fetch

```bash
gh pr view <number> --json number,title,author,isDraft,state,baseRefName,headRefName,headRefOid,url
```

Confirm `state == "OPEN"`. If the PR is MERGED or CLOSED, refuse. If `isDraft == false` and `--allow-published` is not set, refuse with a one-line explanation of the auto-merge orphan-branch risk and a recommendation to mark as draft (`gh pr ready --undo <number>`).

### 2. Authorship gate

Confirm the PR author matches the operator (`gh api user --jq '.login'`). The skill writes to the PR branch; foreign-authored PRs are out of scope.

### 3. Authorization confirmation

If `--authorize-force-push` is present, record it in the tracking bead and proceed in AUTO-REMEDIATE mode for mechanical fixes.

If absent, surface to the user once:

> Force-push not pre-authorized. The loop will ESCALATE every actionable finding (no auto-amend). To enable auto-remediate of mechanical bot suggestions, restart with `--authorize-force-push`. Proceed in escalate-only mode?

Wait for explicit confirmation. Do not silently drift between modes.

### 4. Worktree staging

Use a dedicated worktree at the PR's HEAD so amends do not touch the operator's main checkout. Two reuse cases come first; create a new worktree only as a last resort.

**Reuse priority:**

1. **Agent-spawned worktree** under `.launch-worktrees/` for the same branch. When babysit follows /autopilot OR /launch, a worktree (`autopilot-<bead-id>`, `launch-<bead-id>-<ts>`, or `launch-<ts>`) already exists on the PR's head branch. Reuse it. Adding a second worktree for the same branch fails with `fatal: '<branch>' is already used by worktree at '<path>'`. Resolve via `git worktree list` and match by branch.
2. **Prior babysit worktree** at `/tmp/babysit-pr-<number>` from an earlier session on the same branch. Reuse after confirming the branch matches.
3. **Fresh worktree** at `/tmp/babysit-pr-<number>` if neither (1) nor (2) exists:

```bash
WORKTREE_DIR=/tmp/babysit-pr-<number>
git worktree add "$WORKTREE_DIR" <headRefName> 2>&1
```

Record the resolved path in the bead. All amends go there. The main checkout stays untouched.

### 5. Tracking bead

Create a bead to hold the state blocks:

```bash
bd create --title="babysit-pr #<number>: <pr-title-truncated-50ch>" --description="Babysit loop tracking bead for PR #<number>. State blocks appended below as the loop progresses." --type=task --priority=3 --label=babysit-pr
bd update <new-bead-id> --claim
```

Save the bead id. Every cycle's state block is recorded as a `bd comment` on the bead (NOT a `bd update --notes`). Reason: `--notes` REPLACES the field's content; it does not append. Reconstructing existing notes via shell pipe and re-passing them is fragile and silently truncates on syntax errors, wiping the audit trail. `bd comment` is append-only and is the correct channel for cycle-by-cycle logging. Use `--notes` only for description-level edits where replacing the whole content is intended.

### 6. Initial state block

Post the cycle-0 state block (see State Schema below) as a `bd comment` on the bead. This is the cold-start anchor; any subsequent wakeup parses the latest `[PR_BABYSIT_STATE]` comment via `bd show <bead-id>` and resumes. Bead `description` should hold the one-time setup context (PR number, mode, authorization basis, worktree path); per-cycle state goes in comments.

### 7. Schedule first wakeup

```
ScheduleWakeup(
  delaySeconds=270,
  reason="babysit-pr #<number>: first poll, cache-warm cadence",
  prompt="/babysit-pr <number>"
)
```

The 270-second cadence sits just under the 300-second prompt-cache TTL so each wakeup re-enters with a warm cache. See Anti-pattern 5 for the rationale; do not regress to 300 or 600 even though those values appear in older docs.

Note: the prompt is the same `/babysit-pr <number>` invocation. The skill re-enters preflight, detects the existing bead via `bd search "babysit-pr #<number>"`, skips re-creation, and jumps to the loop body. Idempotency is load-bearing because the cold-start re-entry must work the same as a hot continuation.

Then end the turn. The loop body runs on the next wakeup.

## Loop body

Each wakeup runs these steps in order. The body must complete inside one turn so the cache stays warm; if any step exceeds the budget, defer it to the next wakeup with a note in the state block.

### Step 1: Load state

```bash
bd show <bead-id>
```

Parse the most recent `[PR_BABYSIT_STATE]` block. Extract `window_end`, `last_check_ts`, `processed_issue_comments`, `processed_inline_comments`, `escalations`, `actions_taken`, `classification_policy`.

If `now >= window_end`, jump to Termination (window expired).

### Step 2: Fetch fresh PR state

In parallel:

```bash
# CI status + metadata
gh pr view <number> --json state,isDraft,mergeable,statusCheckRollup,reviewDecision,headRefOid

# Issue-level comments (Vercel, PR Metrics, Mergify, Lighthouse, SonarQube, Datadog, etc.)
gh pr view <number> --json comments --jq '.comments[] | {id: .id, author: .author.login, body: .body, createdAt: .createdAt}'

# Inline review comments (Copilot, Sentry, human reviewers)
gh api /repos/<owner>/<repo>/pulls/<number>/comments \
  --jq '[.[] | {id: .id, user: .user.login, path: .path, line: .line, body: .body, in_reply_to_id: .in_reply_to_id, created_at: .created_at}]'

# Reviews (approve/request-changes events)
gh pr view <number> --json reviews --jq '.reviews[] | {id: .id, author: .author.login, state: .state, submittedAt: .submittedAt}'
```

If the PR has merged or closed between wakeups, jump to Termination (merged/closed).

### Step 3: Identify new activity

Diff three independent streams against the previously-processed sets in state:
- Fresh issue-level comment IDs vs `processed_issue_comments`
- Fresh inline review comment IDs vs `processed_inline_comments`
- Fresh review submission IDs (`reviews[].id`) vs `processed_reviews`

All three feed the classification step. Reviews must be diffed separately because a reviewer can submit APPROVED / CHANGES_REQUESTED / COMMENTED at review level without leaving any comment, and that submission flips `reviewDecision` invisibly to a comment-only loop. Already-processed IDs are ignored.

### Step 4: Classify each new comment

Walk the classification matrix (see below). Each comment produces exactly one verdict:

- **SILENT-IGNORE**: bot status update with no actionable signal. Mark as processed; take no action.
- **REPLY-ONLY**: bot suggestion that does not warrant a code change (e.g., a Copilot stylistic suggestion the operator's rules already cover). Post a one-line reply with rationale.
- **AUTO-REMEDIATE**: mechanical fix the loop can apply confidently (em-dash, typo, missing import, simple lint fix). Apply in the worktree, amend, force-push, reply with action taken. Only allowed if `--authorize-force-push` was set.
- **ESCALATE**: human reviewer comment, non-mechanical bot suggestion, or any actionable finding when `--authorize-force-push` is absent. Add to `escalations` in state; do NOT auto-act. Surface in the wakeup output so the operator sees it on return.

### Step 5: Take action

For each AUTO-REMEDIATE:
1. Read the relevant file in `$WORKTREE_DIR`.
2. Apply the edit using Edit tool.
3. Run any cheap local check: `pants check <path>` for Python, `pnpm lint` for TS. If the check fails, abort this remediation and reclassify as ESCALATE with a note ("local check failed: <output>").
4. `git -C "$WORKTREE_DIR" commit --amend --no-edit`.
5. `git -C "$WORKTREE_DIR" push --force-with-lease`.
6. Reply inline (see Reply mechanism below) with: "Applied: <one-line description>. Commit: <new-sha-short>."

For each REPLY-ONLY:
- Post the reply with the rationale. Keep it terse (one or two sentences). No bead IDs, no personal paths.

For each ESCALATE:
- Add to `escalations` array in state. Include comment id, author, snippet, and a one-line "why escalated" note.

### Step 6: Persist state

Append a new `[PR_BABYSIT_STATE cycle=N]` block as a comment on the bead with:
- `last_check_ts: <now>`
- Updated `processed_issue_comments`, `processed_inline_comments`, and `processed_reviews`
- Updated `actions_taken` (entries for each AUTO-REMEDIATE and REPLY-ONLY this cycle)
- Updated `escalations` (entries for each ESCALATE this cycle)
- `ci_snapshot: <success_count> SUCCESS / <failure_count> FAILURE / <pending_count> PENDING`
- `review_state: <one-line summary, e.g. "approved by a peer reviewer-forthepeople; awaiting a teammate">`

```bash
bd comment <bead-id> "[PR_BABYSIT_STATE cycle=N]
...block contents...
"
```

Use `bd comment` (append-only) rather than `bd update --notes` (replace). The cycle log is the audit trail; replacing it on each cycle loses the prior cycles' state if anything goes wrong with the shell-pipe reconstruction.

### Step 7: Decide next wakeup

If `escalations` was populated this cycle: STOP. Do not schedule another wakeup. The operator must adjudicate before the loop continues.

Default cadence is `270 seconds` (cache-warm; sits just under the 300-second prompt-cache TTL). This is both the steady-state value and the post-traffic value; there is no separate "adaptive band" because 270 is already the cache-warm maximum. If new comments arrived in the cycle that just ran, the next cycle still fires at 270; no need to drop lower (under 60 burns cache without benefit; the bot publishing rate rarely exceeds one comment per 270s anyway).

If `now + 270 >= window_end`: schedule the final wakeup at `max(60, window_end - now)` so the loop terminates cleanly on the window. The 60-second floor avoids the under-60 cache-thrash anti-pattern even when the window is closing.

```
ScheduleWakeup(
  delaySeconds=270,
  reason="babysit-pr #<number>: cycle N+1, <ci-status-summary>",
  prompt="/babysit-pr <number>"
)
```

### Step 8: Emit wakeup output

One-line status: cycle, new-comments-count, actions-taken-count, escalations-count, next-wakeup-in-seconds. If `escalations` was populated, list each one with the operator's name and the snippet so the operator sees it immediately on return.

End the turn.

## Classification matrix

Walk this matrix top-to-bottom for each new comment. First match wins.

### Bot allowlist: SILENT-IGNORE by default

These bots post status updates that do not warrant a reply or an action. Mark as processed; take no action.

| Bot login | Comment type | Action |
|---|---|---|
| `vercel[bot]` | Preview deploy URL | SILENT-IGNORE |
| `pr-metrics-bot` (or similar metrics bots) | PR size / file count metrics | SILENT-IGNORE |
| `mergify[bot]` | Mergify config status | SILENT-IGNORE |
| `lighthouse-ci[bot]` | Lighthouse audit results | SILENT-IGNORE |
| `sonarqube[bot]` | Quality gate status | SILENT-IGNORE |
| `datadog[bot]` | Datadog deploy or monitor status | SILENT-IGNORE |
| `github-actions[bot]` (CodeQL aggregate only) | CodeQL summary, not specific findings | SILENT-IGNORE |

Specific CodeQL FINDINGS (inline, not the aggregate summary) are not in this allowlist; route them through the general matrix below.

### General classification matrix

For activity not matched by the bot allowlist:

1. **Author is a human reviewer (not a bot)**: ESCALATE. Always. Applies to inline comments, issue-level comments, AND review submissions (APPROVED, CHANGES_REQUESTED, COMMENTED at review level). A human can flip `reviewDecision` to APPROVED with no comment; that submission is still an ESCALATE because the operator needs to know the gate moved. Humans get adjudicated by the operator; the loop does not reply to humans without explicit authorization in the start handshake.

2. **Author is a bot AND comment is an inline code suggestion**:
   - **Convention check (run first for naming/structure/placement suggestions)**: Before classifying a suggestion about test file placement, BUILD target placement, module naming, directory layout, or import ordering, read the worktree CLAUDE.md hierarchy (`./CLAUDE.md`, `./src/python/mx2/CLAUDE.md`, `./src/python/mx2/<service>/CLAUDE.md`). Bot reviewers (Copilot especially) infer conventions from existing legacy files, not from rule files; the canonical convention lives in CLAUDE.md. If the rule contradicts the suggestion, classify REPLY-ONLY with a rule-citation decline (do not escalate). See `bd memories correction:workflow:babysit-load-worktree-claude-md` for the precedent.
   a. **Suggestion is mechanical AND `--authorize-force-push` is set**: AUTO-REMEDIATE.
      - Mechanical patterns: em-dash replacement, simple typo, missing import, single-line lint fix, redundant whitespace, simple rename suggested by Copilot when the new name is unambiguous.
      - All mechanical patterns must pass: change is single-file, single-hunk, and local pre-check (pants/pnpm) is green after the edit.
   b. **Suggestion is mechanical AND `--authorize-force-push` is NOT set**: ESCALATE. Note in state that auto-remediate would have applied if pre-authorized.
   c. **Suggestion is not mechanical (refactor, behavior change, multi-file)**: REPLY-ONLY with a one-line "tracking; will address in a follow-up" or ESCALATE if the change is sufficiently substantive. When in doubt, ESCALATE.

3. **Author is a bot AND submission is a review-decision update** (approve, request-changes, commented-at-review-level): SILENT-IGNORE (state captured in `review_state`). The `copilot-pull-request-reviewer` bot's COMMENTED submissions and `github-code-quality` review noise live here.

4. **Anything else**: ESCALATE. Default to safety.

## State schema

Each cycle appends a `[PR_BABYSIT_STATE cycle=N]` block to the tracking bead's notes. The format is plain key:value with arrays in JSON-style for parseability:

```
[PR_BABYSIT_STATE cycle=0]
mode: <auto-remediate | escalate-only>
window_start: <ISO-8601 UTC>
window_end: <ISO-8601 UTC>
worktree_for_amends: <path>
pr_number: <number>
pr_url: <url>
authorization_basis: <one-line: "operator passed --authorize-force-push at start" or "escalate-only mode">
last_check_ts: <ISO-8601 UTC>
ci_snapshot: <N SUCCESS / N FAILURE / N PENDING>
review_state: <one-line summary>
processed_issue_comments: [<id1>, <id2>, ...]
processed_inline_comments: [<id1>, <id2>, ...]
processed_reviews: [<id1>, <id2>, ...]
escalations: []
actions_taken: []
classification_policy:
  - bot-allowlist status updates: SILENT-IGNORE
  - bot inline suggestions (mechanical): AUTO-REMEDIATE (if authorized) / ESCALATE (if not)
  - bot inline suggestions (non-mechanical): REPLY-ONLY or ESCALATE
  - human review: ESCALATE
```

Subsequent cycles (cycle=1, 2, ...) carry forward and update `last_check_ts`, `ci_snapshot`, `review_state`, the processed arrays, and append to `escalations` and `actions_taken`. Each escalation and action entry includes the comment id and a one-line description so the operator can audit on return.

Terminal state uses `[PR_BABYSIT_RESOLVED]` (operator returned and adjudicated) or `[PR_BABYSIT_TERMINATED]` (window expired, PR merged/closed, etc.) with `ts`, `terminal_reason`, and a one-line summary.

## Reply mechanism

### Inline replies (responding to a specific code-line comment)

```bash
gh api -X POST /repos/<owner>/<repo>/pulls/<number>/comments/<parent-comment-id>/replies \
  -f body="<reply text>"
```

### Issue-level replies (general PR comment)

```bash
gh pr comment <number> --body "<comment text>"
```

### Sanitization (mandatory before every post)

Before any `gh` call that writes to the PR, run the reply body through these checks. Block the post and reclassify as ESCALATE if any check fails:

1. **No em-dash (U+2014)**: replace with colon, semicolon, or sentence break. The hook will block the post anyway, but the skill should not even attempt a post with em-dashes.
2. **No bead IDs**: grep for `docr-[a-z0-9]+` and strip or rephrase.
3. **No personal-tier paths**: grep for `~/.claude/`, `/home/vscode/.claude/`, `memory/feedback_*`, `memory/incident-guardrails`, `memory/reviewer-trust-bands`. Strip.
4. **No PRIVATE-marked memory references**: grep for `(PRIVATE)`, `CONFIDENTIAL`. Strip.
5. **No `/skill-name` references that are personal-only**: confirm any `/skill-name` referenced is listed in `ls /workspaces/main/.claude/commands/ /workspaces/main/.claude/skills/`. If not, rephrase to a mechanism description.
6. **Length cap**: hard limit 500 characters per reply. Longer rationales become an ESCALATE.

### Reply tone

- One or two sentences. Specific to what was done or why no action.
- No greetings, no signoffs, no AI-fluff ("Great catch!", "Thanks for the suggestion!").
- For AUTO-REMEDIATE: state the change and the new commit SHA.
- For REPLY-ONLY: state the rationale terselly, citing the rule that governs the decision when one exists. Do NOT cite personal-tier rule paths; describe the mechanism instead.

## Termination conditions

The loop terminates in any of:

1. **Window expired** (`now >= window_end`): emit final state block as `[PR_BABYSIT_TERMINATED]` with `terminal_reason: window-expired`. Do not schedule another wakeup.
2. **PR merged** (`state == "MERGED"`): emit `[PR_BABYSIT_TERMINATED]` with `terminal_reason: pr-merged`. Note any orphaned local amends in the worktree as a follow-up for the operator.
3. **PR closed** (`state == "CLOSED"` and not merged): emit `[PR_BABYSIT_TERMINATED]` with `terminal_reason: pr-closed`.
4. **Escalations populated this cycle**: emit the cycle's `[PR_BABYSIT_STATE]` block, do not append a TERMINATED block (the loop is paused, not done). Skip the next wakeup; the operator resumes via a fresh `/babysit-pr <number>` after adjudicating.
5. **Code-quality CI fails persistently**: if 3+ consecutive cycles show FAILURE on the same **code-quality** check (Python Tests, Python Lint, TypeScript checks, CodeQL findings, SonarQube quality gate, etc.), ESCALATE and pause. Do not silently keep polling. Code-quality failures indicate a real regression the operator needs to see.

   **Exclude operational-gate checks** from this rule. Operational checks (`check_reviewers` from the Require Reviewers workflow, `mergify` config validation, `lighthouse-budget` thresholds, branch-protection requirements that haven't been met) sit in FAILURE state by design until the operator performs an out-of-band action (assigns reviewers, fixes a mergify rule, etc.). Their FAILURE is steady-state, not a regression, and re-running the loop will not change anything until the operator acts. Note operational FAILUREs in the cycle's `ci_snapshot` for visibility, but do NOT trip the persistent-failure escalation on them.

   The distinguishing question: "would this check pass automatically if we just waited and re-ran the workflow, or does the operator need to do something specific to the repo or PR to make it pass?" If the latter, it's operational; skip the escalation.
6. **Operator explicitly stops**: if the operator types `/babysit-pr <number> --stop` or sends a stop signal, emit `[PR_BABYSIT_TERMINATED]` with `terminal_reason: operator-stopped`.

After termination, clean up the worktree:

```bash
git worktree remove /tmp/babysit-pr-<number> --force 2>&1 || true
```

The bead stays open until the operator closes it manually (the audit trail is the point).

## Anti-patterns

Failures observed during the 2026-05-11 prototype session. The skill must guard against these.

### 1. Transitive authorization of force-push

Verbal "auto-remediate any comments" or "fix the bot feedback" does NOT authorize force-push transitively. The verb must be in the start invocation as `--authorize-force-push`. The auto-mode classifier will correctly block mid-loop force-pushes that lack the verb (see CLAUDE.md `correction:workflow:force-push-in-agent-prompt`).

Mitigation: pre-flight authorization handshake. If `--authorize-force-push` is absent, the loop falls back to ESCALATE-only mode and tells the operator explicitly in the wakeup output.

### 2. Auto-merge mid-loop on published PRs

Published (non-draft) PRs can satisfy merge requirements mid-loop and auto-merge. Mid-cycle merge orphans any local amend in the worktree; the operator returns to a follow-up PR cycle instead of a clean iteration.

Mitigation: refuse on non-draft PRs unless `--allow-published` is set. When the flag IS set, surface the auto-merge risk in the start handshake and check `state == "OPEN"` at the top of every loop cycle.

### 3. Personal-tier leakage in PR-bound replies

Reply bodies must scrub bead IDs, personal-tier paths, PRIVATE-marked memory references, and personal-only `/skill-name` mentions. Shared artifacts (PR comments) reach the team and possibly external reviewers; references that only resolve inside `~/.claude/` confuse readers and leak personal config geography.

Mitigation: mandatory sanitization step before every `gh` write call. See Reply mechanism above.

### 4. State written to volatile locations

Per-session state files in `/tmp/` or in conversation memory disappear on compaction. The next wakeup or a cold-start session loses the loop history.

Mitigation: state lives in the tracking bead's notes (durable across compactions and sessions). The worktree is the only `/tmp/` location used, and it can be recreated from `headRefName` if lost.

### 5. Cache-window thrashing

The prompt-cache TTL is 300 seconds. Sleeping past 300 incurs a cache miss; sleeping at exactly 300 incurs the miss without amortizing it (worst-of-both); sleeping under 60 burns cache constantly for no benefit.

Mitigation: cadence is `270 seconds` for every wakeup, steady-state or post-traffic alike. 270 sits just under the TTL so each cycle re-enters cache-warm; there is no longer a separate steady-state-vs-adaptive split (the older 600/300 numbers in pre-2026-05 versions of this doc are obsolete). Final wakeup at window close uses `max(60, window_end - now)` to honor the under-60 floor.

## Principles

- **Idempotent re-entry**: every wakeup re-loads state from the bead and runs the same loop body. Cold-start and hot continuation are indistinguishable.
- **Bounded blast radius**: only mechanical, single-file, single-hunk auto-remediations. Anything substantive escalates.
- **Loud on escalation, quiet on no-op**: SILENT-IGNORE is genuinely silent. ESCALATE always surfaces in the wakeup output so the operator sees it immediately on return.
- **Authorization gates are explicit**: force-push verb is pre-collected; non-draft override is an explicit flag. No silent drift into more-permissive modes.
- **Durable state, ephemeral compute**: state in beads, compute in the worktree. Either can be recreated from the other.

## Related skills

- `/loop` (dynamic mode): the generic version of this pattern. /babysit-pr is the specialized variant where the loop body is fixed and the cadence is paced against PR comment traffic.
- `/pr-intel`: one-shot PR briefing. /babysit-pr reuses /pr-intel's data-gathering patterns (gh api inline comments, statusCheckRollup parsing, bot identification) but adds the loop + auto-remediate layer.
- `/autopilot remediate`: heavier autonomous pipeline with mx2-decision-maker gating. Use for full automation including bead-state, PR-creation, and remediation across multiple iterations. /babysit-pr is the lightweight variant for one open PR.
