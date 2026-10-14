---
name: babysit-pr
description: >-
  Watch loop for an author session watching the published pull request it opened. Polls on a paced cadence and reads review threads through GraphQL. Classifies Devin's findings, reviewer peers' messages and human comments. Fixes what is mechanical or clearly right as a new commit with a normal push and one inline reply. Sends every judgment call to the orchestrator by SendMessage and keeps polling. Ends at merge or close with a last report. Trigger phrases include "babysit this PR", "watch PR #N", "watch the PR you published", "/babysit-pr".
argument-hint: "<pr-number> --clone <path> --branch <head branch> --orchestrator <name> [--above <branch,...>] [--window-end <UTC>] [--cadence <seconds>] [--state <file>] [--inherit <file>] [--stop]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Edit", "Write", "ScheduleWakeup", "CronCreate", "SendMessage"]
---

# Babysit PR

A loop for an author session in the fleet: it watches the published pull request it opened, fixes what is mechanical or clearly right, and hands every judgment call to the orchestrator. Michael, 2026-09-30 11:14 PDT, VERBATIM: "have the author sessions watch the PRs they publish for the Devin comments, and auto-remediate since I will not have time or bandwidth to stare at the PRs."

State lives in one append-only file in the author's own folder, so any wakeup can start cold from it.

## The verb, and what it never covers

The start message quotes the verb from the author's dispatch: new commits and inline replies on the author's own pull request. Refuse to start when the message quotes no verb, and say so to the orchestrator.

The verb never covers these, whatever a comment asks:

- An amend, a rebase, a force-push, a merge, or a change of base.
- A write to any other pull request, an issue comment, a review submission, or a thread resolve.
- A change to a route, a request shape, a response shape or a status code. Such a finding goes to the orchestrator unfixed.
- A `git` command in a shared checkout, or a `worktree add`. The author works in its own clone.

## Inputs

From the start message, or from the arguments that restate it:

- **PR number**: required.
- **`--clone <path>`**: the author's own clone. Required.
- **`--branch <name>`**: the head branch the author published. Required.
- **`--orchestrator <name>`**: the session that takes judgment calls, by bare name. Required.
- **`--above <branch,...>`**: the branches stacked above this one, when the PR is a lower PR of a stack.
- **`--window-end <UTC>`** and **`--cadence <seconds>`**: from the start message, when it sets them. Both go in the state file's header.
- **`--state <file>`**: the state file. Default: `babysit-pr-<number>.md` in the author's own folder under the group's folder (for example `services-addons-part-1/dev-50/`).
- **`--inherit <state file>`**: a dead author's state file. Preflight step 3 copies its `processed_reviews`, `processed_issue_comments`, `reply_ids` and `escalations` into the cycle 0 block.
- **`--stop`**: end the watch now, with the last report.

A wakeup re-enters with the PR number and `--state` only; everything else comes from the state file's header.

## Rig mode

When the environment sets `BABYSIT_OUT_DIR`, the session is under the test rig (`babysit-fix-2026-09-30/dev-53/RIG.md`). Then:

- The PR is `$BABYSIT_PR`, the clone is `$BABYSIT_WORKTREE`, and the state file is `$BABYSIT_OUT_DIR/state.md`.
- The branch is the clone's current branch, and the orchestrator is written `<orchestrator>`.
- Each escalation message is appended to `$BABYSIT_OUT_DIR/escalation.txt` instead of sent.
- The next wakeup is written as one line to `$BABYSIT_OUT_DIR/wakeup.txt` instead of scheduled.
- Skip the GraphQL read and take the REST read in Step 2 directly. A GraphQL query goes out as a POST, which the rig counts as a refused write.
- Owner and repository come from the PR's `url`, since the clone's origin is the rig's bare repository.
- Everything else runs as written. Replies still go through `gh`, which the rig captures.

## Preflight

Run it on the first start and again after every wakeup, since the machine may have slept.

First, when the state file exists, read its last block. When the newest block is `[PR_BABYSIT_TERMINATED]`, run no preflight and no cycle, and schedule nothing. Read the PR once. Reply in one line with the end reason, and say that a restart needs a new window from the orchestrator or Michael.

### 1. The pull request

```bash
gh pr view <n> -R <o>/<r> --json number,title,state,isDraft,headRefName,headRefOid,baseRefName,url,author
```

- `state` must be `OPEN`. A merged or closed PR goes to Termination.
- `isDraft` is recorded and never gates the watch.
- `headRefName` must equal the branch the start message names. Every fleet session shares one GitHub login, so the login proves nothing about which session owns the branch.
- Run every `gh pr view` with `-R <o>/<r>`, the pair from `git -C <clone> remote get-url origin`. A session's working directory is often not a repository, and `gh` then fails.

### 2. The clone

```bash
git -C <clone> rev-parse --abbrev-ref HEAD          # must print <branch>
git -C <clone> status --porcelain                   # must print nothing
git -C <clone> fetch -q origin <branch>
git -C <clone> merge --ff-only origin/<branch>      # the clone is at the published head
```

When the lead pushed the branch from another clone, the author's clone may not have it yet. Fetch it and switch to it first: `git -C <clone> fetch -q origin <branch> && git -C <clone> switch -q <branch>`.

A dirty clone, another branch, or a head that cannot fast-forward is an escalation, and no fix runs until the orchestrator answers.

One head move is not an escalation: another session force-pushed an approved restack, and the orchestrator's message names it. Back up the local head (`git -C <clone> branch backup/<branch>-<sha8> HEAD`), then `git -C <clone> checkout -B <branch> origin/<branch>`, and grep the new head for the line your last commit added. After a restack run `scratch/scripts/pr-checks/manifest-ref-check.sh <clone>`. Run the execution `memory-apply` after the last rebase, never before it (2026-10-01: `records_ref` named an abandoned commit twice).

A pull request that reads CONFLICTING with an unchanged head gets `git -C <clone> merge-tree --write-tree --name-only HEAD origin/<base>` once, and the conflict list is saved in the state file. A later cycle compares against it, so a conflict that moved is named. The command is read-only and writes no ref.

A new memory record takes its id from the clone's own `pnpm memory:new`, which since #196 (merged 2026-10-02T17:40Z, e96a649e) mints a random `MEM-xxxxxxxx` hex id; `docs/memory/records/SCHEMA.md` there says nothing mints the old `MEM-nnnn` shape any more, and existing records keep theirs. Until then `pnpm memory:new` numbered from the clone's own tree and gave MEM-0302 to #171 and #192 at once (2026-10-01), which `next-mem-id.sh` guarded against; that script is retired to `~/.claude/retired/2026-10-02/` because it cannot name a valid new id under the random scheme (dev-13, 2026-10-02).

When `node_modules` is missing, run `pnpm install --frozen-lockfile` in the clone once, so the checks in Step 5 can run.

### 3. The state file

Create it with the Write tool on the first start, with a header: PR number and URL, branch, clone, orchestrator, the branches above, the window end and cadence when set, and the verb quoted. After that, append each block with the Edit tool after a Read. A shell redirect into a `.md` under `~/.claude/` is refused by a hook, and it would skip the pronoun and dash hooks.

On the first start, append the cycle 0 block (State schema below), then run the first cycle at once rather than waiting for a wakeup. With `--inherit`, the cycle 0 block starts from the inherited file's four lists named under Inputs. On a wakeup the file already exists: append nothing here and go to Each cycle.

## Each cycle

### Step 1: Load state

Read the state file and take the newest `[PR_BABYSIT_STATE]` block.

### Step 2: Fetch

Step 2 calls `~/.claude/scratch/scripts/babysit-read.sh <o>/<r> <n> <state file>`, which runs every read below in one call. It prints the head, the tally and the ids that are new against the newest `[PR_BABYSIT_STATE]` block. A non-zero exit is a failed read, never a quiet cycle. Rig mode keeps its REST path: the script tries GraphQL first, which the rig counts as a refused write. The reads it makes:

```bash
gh pr view <n> -R <o>/<r> --json state,mergeable,statusCheckRollup,reviewDecision,headRefOid
gh pr view <n> -R <o>/<r> --json statusCheckRollup --jq '[.statusCheckRollup[] | ((.conclusion | select(. != null and . != "")) // .status // .state)] | group_by(.) | map("\(.[0])=\(length)") | join(" ")'
gh api repos/<o>/<r>/pulls/<n>/reviews --jq '[.[] | {id, user: .user.login, state, body, submitted_at}]'
gh api repos/<o>/<r>/issues/<n>/comments --jq '[.[] | {id, user: .user.login, body, updated_at}]'
```

The second line is the check tally, and it is the cycle's `ci_snapshot`. A status context has only `state`, so the Devin row reads null without the last fallback. An empty-string conclusion reads as absent, so a running check shows its status instead of an empty key.

The review threads, through GraphQL, since only GraphQL says whether a thread is resolved:

```bash
gh api graphql -F o=<o> -F r=<r> -F n=<n> -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved isOutdated comments(first:50){nodes{databaseId author{login} body path line originalLine lastEditedAt replyTo{databaseId}}}}}}}}'
```

The head moves. `babysit-read.sh` prints one `OFF-HISTORY` line when `origin/<branch>` is not a descendant of the clone's head: stop and read what moved before any push. To wait for a push by another session, run `~/.claude/scratch/scripts/pr-head-sync.sh -R <o>/<r> --wait <sha> <seconds> <clone> <n>`. It polls the live head, so no poll loop is typed by hand. (2026-10-01: six poll loops in one evening, and a round named bfc61ac0 when the PR sat at cc1e034a.)

**REST fallback.** When the GraphQL read fails, read `gh api repos/<o>/<r>/pulls/<n>/comments` instead. Treat every thread as unresolved, use `updated_at` where the GraphQL read gives `lastEditedAt`, and write `threads: rest-fallback` in the cycle's block.

A comment's line is `line`, or `originalLine` (`original_line`) when the comment is outdated and `line` is null.

GraphQL gives a bot's login without the `[bot]` suffix that REST gives: Devin is `devin-ai-integration` in one and `devin-ai-integration[bot]` in the other (read on #162, 2026-09-30). Match a bot login with the suffix removed. `lastEditedAt` is null on a comment never edited. A comment's `databaseId` is the REST `id`.

### Step 3: New activity

A comment, review or issue comment is new when its id is not in the state, or when its `lastEditedAt` differs from the one stored. Devin edits its comments in place under the same id, so an id alone misses the change.

Skip a resolved thread. A thread whose last comment is Devin's reply opening "✅ **Resolved**" is done.

Findings from reviewer peers arrive in the conversation as cross-session messages naming this PR. Each one not yet in `peer_findings` is new activity too.

A finding this loop already fixed can come back edited, since Devin moves its comments to the new head after a push. It can also come back rewritten: on #206 Devin replaced a fixed finding's body with a second finding on the fix (dev-27, 2026-10-06). So read the comment's current body, and its earlier bodies in `userContentEdits { nodes { editedAt diff } }` on the comment's node. When the body still describes the finding the head fixed, mark it DONE and act no further. When it describes something else, it is a new FINDING under the old id.

### Step 4: Classify

First match wins.

| # | What it is | Verdict |
|---|---|---|
| 1 | A reply this loop posted (its id is in `reply_ids`), or an empty COMMENTED review by the PR's author, which wraps such a reply | IGNORE |
| 2 | A status bot: `github-actions[bot]`, `linear-code[bot]`, `vercel[bot]` and the like; its delete-and-repost churn is no new activity | IGNORE |
| 3 | A Devin review (`devin-ai-integration`, with or without `[bot]`); its body is a wrapper | IGNORE, but read the flag count first (below) |
| 4 | A Devin reply opening "✅ **Resolved**" | DONE: mark its thread done |
| 5 | A Devin top-level inline comment (no `in_reply_to_id`, or `replyTo` null) | FINDING |
| 6 | A reviewer peer's finding by SendMessage | FINDING |
| 7 | A comment or review by a person on GitHub | ESCALATE; never reply |
| 8 | Anything else | ESCALATE |

**The flag count.** A Devin review body reading "**Devin Review** found N potential issues" names how many findings to expect. Sometimes the body says the flags were not posted on this PR, or fewer than N inline comments exist. Then ESCALATE once with the count and the review's link. The findings get read in Devin's app instead of nowhere.

**Triage first, by consequence** (Michael, 2026-10-01 12:16 PDT; `~/.claude/rules/code-review-policy.md`, "Our own pull requests"). Before the FIX test, every Devin FINDING on a pull request this harness wrote gets two lines in the state file under its id: what it affects (an interaction a person has with the screen, a contract a caller or a route depends on, or an expectation a spec, a story or a record sets), and how badly that thing breaks if the finding is right. A finding with a real consequence goes on to FIX or ESCALATE as below, and the message or the commit names the two lines. A finding with no consequence goes to the orchestrator as a Decision with the two lines and a drafted reply (what it affects, and why that does not break); the reply posts only on the orchestrator's `decline`. No finding is ignored, and none is fixed only because a bot said so.

**A FINDING is fixed only when every one of these holds:**

- It is mechanical or clearly right: a typo, a one-hunk `suggestion` fence, a missing import, a lint fix, or a defect the comment shows at its line with one obvious correction.
- It touches only files this PR already changes.
- It touches no route under `src/app/api/`, no request or response shape, and no status code.
- It changes no test's expected value, and it needs no design choice.

Anything else is ESCALATE. When in doubt, ESCALATE.

### Step 5: Act

**FIX.**

1. Edit the file in the clone with the Edit tool. A code comment the fix adds is two lines at most and says nothing about waves, lanes or tasks.
2. Run `pnpm typecheck`, `pnpm lint`, and the narrowest test covering the file, from the clone. A fix that changes behaviour first gets a test seen red at the finding's line. A text-only fix runs typecheck and lint. The commands for each repository are in `~/.claude/rules/build-commands.md`, which no longer loads in every session.
3. When a check fails, restore the file (`git -C <clone> restore <file>`) and ESCALATE with the failing output.
4. Commit it as a new commit and push it as a fast-forward:

```bash
git -C <clone> add -- <file>
git -C <clone> commit -q -m "<what the fix does, in the active voice>"   # plus the session's attribution lines
git -C <clone> push -q origin HEAD:<branch>
```

5. A rejected push is never forced. ESCALATE with the output, and make no further fix on this PR until the orchestrator answers.
6. Reply inline once, to the comment fixed, naming the commit:

```bash
gh api -X POST repos/<o>/<r>/pulls/<n>/comments/<comment id>/replies -f body="Fixed in <sha7>: <what changed, one clause>." --jq .id
```

Record the printed id in `reply_ids`, so the next cycle reads the reply as the loop's own.

A peer's finding gets no PR reply; send that peer one line by SendMessage naming the commit instead.

7. With `--above` set, tell the orchestrator by SendMessage: the fix's commit and branch, and that the branches above do not have it. Never rebase them.

**ESCALATE.** Send the orchestrator one message per judgment call, by bare name, and keep polling:

```
Decision PR #<n>: comment <id> by <author> at <path>:<line> needs a judgment: <link>. "<first sentence of the comment>". No fix made; the watch continues.
```

The link is the comment's `html_url`, or the PR URL with `#discussion_r<id>`.

### Step 6: Persist

Append a `[PR_BABYSIT_STATE cycle=N]` block with the Edit tool. Never rewrite an earlier block.

### Step 7: Next wakeup

| Since the last push | Delay |
|---|---|
| Under 15 minutes (Devin re-reviews 4 to 12 minutes after a push) | 300 s |
| Later, with new activity this cycle | 300 s |
| Later, quiet | 900 s |
| Three quiet cycles in a row | 1800 s |

With `--cadence` set, it takes the place of the table. With a window set, ask for the smaller of the delay and the window end minus now. A wakeup that lands on the window end is the last read. A new ScheduleWakeup replaces the pending one.

```
ScheduleWakeup(delaySeconds=<delay>, reason="babysit-pr #<n>: cycle N+1", prompt="/babysit-pr <n> --state <state file>")
```

When ScheduleWakeup is refused or absent, use a one-shot `CronCreate` at the same delay, rounded to the minute. When neither exists, tell the orchestrator by SendMessage and stop. A wakeup is not a monitor: the machine sleeps with Windows, so a late wakeup reads live state before it trusts the file.

### Step 8: One line out

Two short sentences. The first gives the cycle and what changed, or "quiet". The second gives the next wakeup in local time and UTC. Counts go in a sentence of their own. Then end the turn.

## Termination

The watch ends on any of these, with a `[PR_BABYSIT_TERMINATED]` block and one SendMessage to the orchestrator giving the last state: head sha, fixes made, escalations still open.

1. **Merged** (`state == "MERGED"`): `terminal_reason: pr-merged`.
2. **Closed** (`state == "CLOSED"`): `terminal_reason: pr-closed`.
3. **Stopped** (`--stop`, or the orchestrator says stop): `terminal_reason: operator-stopped`.
4. **Window expired**, only when the start message set a window: `terminal_reason: window-expired`.

An escalation never ends the watch. A code-quality check failing for three cycles after this loop's own push is an escalation, not a stop. Operational gates that wait on a person (a reviewer requirement, a branch-protection rule) are noted in `ci_snapshot` and never escalated.

## State schema

```
[PR_BABYSIT_STATE cycle=N]
ts: <ISO-8601 UTC>
pr: <number> <url>
branch: <head branch>   clone: <path>   above: [<branch>, ...]
orchestrator: <name>
verb: "<the verb as quoted>"
head: <sha>   threads: graphql | rest-fallback
ci_snapshot: <the Step 2 tally line, for example NEUTRAL=2 SKIPPED=2 SUCCESS=11>
review_state: <one line>
processed_inline: {<id>: <lastEditedAt>, ...}
triage: {<id>: {affects: "<interaction | contract | expectation, named>", breaks: "<how badly, one clause>", verdict: <FIX | ESCALATE | DECLINE-ASKED>}, ...}
processed_reviews: [<id>, ...]
processed_issue_comments: {<id>: <updated_at>, ...}
reply_ids: [<id>, ...]
peer_findings: [{from: <session>, about: <first words>, verdict: <FIX | ESCALATE>, commit: <sha7 or none>}, ...]
done_threads: [<first comment id>, ...]
pushes: [{sha: <sha7>, ts: <ts>}, ...]
actions_taken: [{comment: <id>, commit: <sha7>, reply: <id>}, ...]
escalations: [{comment: <id>, author: <login>, link: <url>, sent: <ts>}, ...]
quiet_cycles: <n>
next_wakeup: <seconds>
```

`[PR_BABYSIT_TERMINATED]` holds `ts`, `terminal_reason` and the one-line summary sent to the orchestrator.

## Replies

Before every post, check the body and escalate instead of posting when a check fails:

1. No em dash (U+2014).
2. No personal path (`~/.claude/`, a memory file name) and no skill name that exists only on this machine.
3. 500 characters at most.
4. One or two sentences: what changed and the commit. No greeting, no thanks, no sign-off.

## Anti-patterns

- **Amend and force-push.** The skill before 2026-09-30 amended and force-pushed. Here every fix is a new commit, so the reviewers' history stays readable and no verb beyond Michael's is needed.
- **Stopping on the first escalation.** A stopped loop leaves Devin's later findings unread while nobody watches. Send the call and keep polling.
- **An id-only diff.** Devin rewrites a comment in place, so an id diff reads an edited finding as old.
- **Replying to a person.** A human reviewer's comment is the orchestrator's to route; the loop never answers it.
- **Personal-tier leakage.** A reply reaches the team; scrub it (Replies, above).
- **State in `/tmp`.** It is reaped within a day; the author's folder is durable.

## Related

- `/pr-intel`: one read of a PR, no loop.
- `/loop` in dynamic mode: the generic loop this one specializes.
