---
name: standup-prep
description: "Generate the user's OWN spoken-standup talk-track from their ENGINEERING activity (git, PRs authored + reviewed, PR/issue comments, Jira, Confluence, beads, plus a Slack sweep for unanswered asks + open threads) for a past day, binned by the user's LOCAL timezone. This is OUTBOUND status generation, not transcript capture. Use for 'verbal standup', 'standup prep', 'prep my standup', '/standup-prep', 'what did I do yesterday/Friday', 'what did I ship'. This is the one-stop standup generator across all those sources. The slack plugin's /standup is the lighter Slack-only alternative (just messages, formatted to post in a channel); to CAPTURE a pasted transcript of a meeting that already happened use /capture-transcript (inbound). On a bare 'help me with standup', prefer this skill when recent context is code/PR/Jira work."
argument-hint: "[<weekday> | <YYYY-MM-DD> | --days N] (default: previous business day)"
---

# Standup Prep

Build a spoken-standup talk-track from the user's OWN activity, to bring INTO the meeting. Output is for the user to TALK THROUGH, not a written report: scannable, IDs in code spans, leads with impact.

This is read-only intelligence gathering. It never posts, comments, or mutates anything.

## When to invoke

- "help me with standup", "verbal standup", "standup prep", "prep my standup", "/standup-prep".
- "what did I do yesterday / Friday / on the 17th", "what did I ship", "catch me up on my last few days" (use `--days N`).

## When NOT to use

| Instead | When |
|---|---|
| slack plugin `/standup` | You want ONLY a Slack-message standup formatted to post in a channel. This skill already sweeps Slack (step 1g) as part of a fuller multi-source talk-track; `/standup` is the lighter Slack-only path. |
| `/capture-transcript` | A transcript of a meeting that already happened is pasted (INBOUND capture of what others said). This skill is OUTBOUND: it generates the user's own status from their activity. They are complementary halves of the same meeting (prep-before vs capture-after), not substitutes. |
| `/handoff` | A cold-start prompt for the next session is wanted, not a standup. |

## Argument handling

Parse `$ARGUMENTS`:
- empty -> previous business day relative to today (Mon -> last Fri; Tue-Fri -> yesterday; weekend -> last Fri).
- a weekday name ("thursday") -> the most recent past occurrence of that weekday.
- a date (`YYYY-MM-DD`) -> exactly that day.
- `--days N` -> a window covering the last N calendar days through the target day (post-PTO catch-up). This widens the window in Step 0 and sub-groups the Step 3 output by day.

Today's date is a runtime fact (check the environment context, not memory). If the target day is a likely company holiday: interactive caller, say so and offer to step back one more day; non-interactive agent caller, proceed with the requested day AND also report the prior working day's data, labeling the holiday. Never silently skip a day.

## Step 0: target day + LOCAL timezone (do this first, it is load-bearing)

Everything must be binned by the user's LOCAL day, not UTC. Worktree/CI commits and GitHub/Jira API responses are UTC-stamped; binning by UTC misfiles late-evening work onto the wrong day. The whole point of this skill is getting the day boundary right.

**CRITICAL: derive today, the day of week, and the target day MECHANICALLY via shell. Never hand-substitute a date or compute a day-of-week in your head - both are where the wrong day silently creeps in (a wrong day-of-week, or assuming June 20 is a Friday when it is a Saturday). The snippet below does all of it from the live clock; do not bypass it.**

1. Derive everything mechanically in one block. This finds the user's local UTC offset from their own commits, then computes today-in-local-tz, its day of week, and the target business day. It applies the offset so it does not drift onto the wrong day late in the user's evening (the container clock is UTC):
   ```bash
   EMAIL=$(git config user.email)
   OFF=$(git log --all --author="$EMAIL" -100 --pretty=%aI \
     | grep -oE '[+-][0-9]{2}:[0-9]{2}$' | grep -v '+00:00' \
     | sort | uniq -c | sort -rn | head -1 | grep -oE '[+-][0-9]{2}:[0-9]{2}')
   echo "Derived local offset: ${OFF:-NONE}"
   python3 -c "
   from datetime import datetime, timezone, timedelta
   off_str = '${OFF:-+00:00}'  # fixed offset from commits; falls back to UTC if none found
   sign = -1 if off_str[0] == '-' else 1
   hh, mm = int(off_str[1:3]), int(off_str[4:6])
   today = (datetime.now(timezone.utc) + timedelta(hours=sign*hh, minutes=sign*mm)).date()
   dow = today.weekday()  # 0=Mon .. 6=Sun
   if dow == 0:        target = today - timedelta(days=3)      # Mon -> last Fri
   elif dow in (5, 6): target = today - timedelta(days=dow-4)  # Sat/Sun -> last Fri
   else:               target = today - timedelta(days=1)      # Tue-Fri -> yesterday
   print(f'today (user-local) = {today} ({today.strftime(\"%A\")})')
   print(f'target business day = {target} ({target.strftime(\"%A\")})')
   "
   ```
   - The printed `OFF` (e.g. `-07:00`) is the user's local timezone, reused for the bounds below. (Commits stamped `Z` are worktree/CI commits; the anchored regex excludes them.) If `OFF` prints `NONE`: the snippet falls back to UTC; an interactive caller should confirm the timezone once, a non-interactive agent should flag the UTC assumption in the output.
   - **Cross-check `today` against the harness-injected context date** ("Today's date is YYYY-MM-DD"). They should match. If they disagree (container clock skew), prefer the context date: re-run with `today` hard-set to the context date, since that is the authoritative "today" the user sees.
   - `target` is what to use when `$ARGUMENTS` is empty. If `$ARGUMENTS` specifies a weekday or date explicitly, use that instead (still confirm its day-of-week by printing `date.fromisoformat(...).strftime('%A')` rather than asserting it).
2. Compute the binning bounds for the target LOCAL day `D` with offset `OFF`:
   - `WIN_START` (UTC) = `D 00:00:00 OFF` converted to UTC.
   - `WIN_END` (UTC, exclusive) = `D+1 00:00:00 OFF` converted to UTC.
   - `DAY_BEFORE` = the local calendar date one day before `D` (format `YYYY-MM-DD`). This is a deliberately LOOSE lower bound for the `gh search` candidate net only; the real gate is the per-item timestamp re-filter against `[WIN_START, WIN_END)`.
   - Worked example, `OFF=-07:00`, `D=2026-06-19`: `WIN_START=2026-06-19T07:00:00Z`, `WIN_END=2026-06-20T07:00:00Z`, `DAY_BEFORE=2026-06-18`. A commit at `2026-06-20T02:29Z` is `2026-06-19 19:29` local, so it bins to the target Friday.
   - Under `--days N`: `WIN_START` = `(D-(N-1)) 00:00:00 OFF` in UTC (one window spanning the whole range), `WIN_END` unchanged, `DAY_BEFORE` = the date one day before `D-(N-1)`. The JQL date bounds in 1d widen to match (lower = `D-(N-1)`).

## Step 1: gather (run the independent queries in parallel)

Identities: GitHub login `gh api user --jq .login`; git author `git config user.email`; repo `gh repo view --json nameWithOwner --jq .nameWithOwner` (default scope is the current repo). Jira: accountId from `mcp__atlassian__atlassianUserInfo`, cloudId from `getAccessibleAtlassianResources`. Always take these from the live MCP lookup; a stale accountId silently breaks the 1d author filter (drops everything or keeps the wrong person). Last-known Morgan-instance values, to be re-verified, not trusted blindly: accountId `712020:e7620f9a-43fa-4ea6-9b7a-38bc2ee47ff5`, cloudId `<atlassian-cloud-id>`.

When the candidate sets are large (a full project day of Jira, or many PRs), delegate the heavy filtering to parallel subagents (one per source) so the raw payloads never enter the main context; for a single normal day inline queries are fine.

### 1a. Git commits authored by the user
```bash
git log --all --author="$EMAIL" --since="$WIN_START" --until="$WIN_END" \
  --pretty=format:"%h | %aI | %s"
```
`--since/--until` filter by COMMIT date; binning and display use the `%aI` AUTHOR date, which is authoritative. For rebased/cherry-picked commits these can differ, so treat the window as a coarse net (add a small buffer if needed) and re-bin each commit by its `%aI` offset.

### 1b. PRs the user authored (created / updated / merged in window)
```bash
gh pr list --author @me --state all --limit 80 \
  --json number,title,state,isDraft,createdAt,updatedAt,mergedAt,url
```
Filter by `createdAt`, `mergedAt`, or `updatedAt` in `[WIN_START, WIN_END)`. For draft PRs, distinguish real CI failures from PR-hygiene gates (`Empty checklist`, `Remove PR template comments`, `check_reviewers` are hygiene, not code failures):
```bash
gh pr view <N> --json statusCheckRollup \
  --jq '[.statusCheckRollup[] | select(.conclusion=="FAILURE") | .name]'
```

### 1c. PRs the user reviewed + commented on
Two complementary paths (run both, dedup by PR number):
- Repo-wide comment streams (most reliable for comments). `since` is a lower bound on `updated_at`, so gate on `created_at` IN window directly in the jq:
  ```bash
  gh api "/repos/$REPO/issues/comments?since=$WIN_START&per_page=100" --paginate \
    --jq ".[] | select(.user.login==\"$LOGIN\" and .created_at>=\"$WIN_START\" and .created_at<\"$WIN_END\") | {url:.html_url, created:.created_at, body:.body}"
  gh api "/repos/$REPO/pulls/comments?since=$WIN_START&per_page=100" --paginate \
    --jq ".[] | select(.user.login==\"$LOGIN\" and .created_at>=\"$WIN_START\" and .created_at<\"$WIN_END\") | {url:.html_url, created:.created_at, body:.body, path:.path}"
  ```
- Formal review submissions (catches APPROVED / CHANGES_REQUESTED, including empty-body reviews that the comment streams miss). Candidate net, then per-PR:
  ```bash
  gh search prs --repo "$REPO" --reviewed-by @me --updated ">=$DAY_BEFORE" --json number
  gh search prs --repo "$REPO" --commenter   @me --updated ">=$DAY_BEFORE" --json number
  # union the numbers, then for each candidate N:
  gh api "/repos/$REPO/pulls/$N/reviews" --paginate \
    --jq ".[] | select(.user.login==\"$LOGIN\") | {state, submitted_at, body}"
  ```
  Keep reviews whose `submitted_at` is in window. (`gh search` `--updated` is the PR's update date, NOT the review date; always re-filter by the actual review/comment timestamp.)

### 1d. Jira tickets the user commented on
This Jira instance has no reliable `commentedBy` JQL function, so cast a candidate net then filter comments by author + date yourself. CRITICAL: do NOT put an upper bound (`updated < ...`) on the candidate net. A ticket commented on the target day whose `updated` field later drifts forward (any subsequent activity bumps it) falls out of an upper-bounded net and is silently missed. The per-comment date filter below supplies all the precision; the candidate net needs a lower bound only.
```
# Primary net (drift-proof + tractable): lower bound only, run via searchJiraIssuesUsingJql.
(assignee was currentUser() OR reporter = currentUser() OR watcher = currentUser()) AND updated >= "<lower>"
# `was` is intentional (history operator: catches issues assigned then reassigned). Do not change to `=`.
# Completeness backstop, page fully, only if the primary net looks thin:
project = MX2 AND updated >= "<lower>" ORDER BY updated DESC
```
`<lower>` is `D` for a single day, `D-(N-1)` under `--days N`; bare dates use the user's Jira-profile tz. Also seed the candidate set with the `[MX2-XXXXX]` keys pulled from the PRs in 1b/1c (an independent catch for drifted tickets). Then fetch the `comment` field for each candidate (batch via `key in (...)`), keep only comments where `author.accountId == <my accountId>` AND `created` (convert from the returned ET/`-0400` to UTC) is in `[WIN_START, WIN_END)`. Report the strategies tried (absence-prone external search).

### 1e. Beads
```bash
bd list --status=in_progress
```
for the "what's active / blocked" framing. Use `bd show <id>` on the day's beads for richer "what's next".

### 1f. Confluence pages created or edited by the user
Run via `mcp__atlassian__searchConfluenceUsingCql` (same cloudId as Jira; `currentUser()` resolves automatically). `contributor` covers both create and edit (superset of `creator`):
```
contributor = currentUser() AND type = page AND lastmodified >= "<DAY_BEFORE>" AND lastmodified <= "<D+1 as YYYY-MM-DD>"
```
expand `content.version,content.history` to get the editor, version number, and edit message. GOTCHA (verified): Confluence CQL evaluates `lastmodified` bare dates in UTC, the OPPOSITE of Jira JQL (profile tz). So cast the net one day wide on each side with bare dates.

**Precision gating GOTCHA (verified in session):** The MCP tool returns `lastModified` as a friendly string ("yesterday at 6:23 PM"), NOT a UTC ISO instant. You cannot do UTC-exact gating from this field alone. Instead: use the friendly string to confirm the page was modified on the target local day (it already reflects the user's local tz), then accept it as in-window.

**Multi-contributor disambiguation GOTCHA (verified in session):** `contributor = currentUser()` returns pages where the user made ANY past edit, not necessarily on the target day. Pages where another person is the listed `author` and the `lastModified` shows someone else's recent edit are false positives. Filter: only include a page in the talk-track if (a) the page `author.displayName` is the user AND `lastModified` is the target day, OR (b) you confirm via a follow-up version fetch that your specific edit landed in window. When in doubt, note the uncertainty rather than silently omitting or overclaiming.

Capture: title, page URL (`webui`), version number (1 = newly created), and the edit message.

### 1g. Slack messages (the user's own)
Slack is a MIXED-signal source: public channels largely echo deploy/PR/Jira items already captured above, but the standup-worthy substance (async doc reviews, decisions worked out with leads, direct asks) lives in DMs and private channels. Its value is the asks, threads, and reviews, not the public chatter. Steps:
1. `mcp__plugin_slack_slack__slack_read_user_profile` (no `user_id`) -> the user's Slack ID + display name. (Last-known: `U095SF76XLL`; re-verify, do not hardcode blindly.)
2. Search the user's own messages for the target day. DEFAULT to `slack_search_public_and_private`: this is the user's OWN activity, and their standup substance (design-doc reviews, lead threads, 1:1 asks) is almost entirely in DMs and private channels. The user invoking standup-prep IS standing consent to sweep their own messages; do not downgrade to public-only or gate on a consent prompt. Public-only silently drops the day's real work (verified 2026-07-08: public returned 1 message, private+DM returned 109 across 6 pages including an async design-doc review and a lead decision thread).
   - Query: `from:<@USER_ID> on:<D>` (single day) or `from:<@USER_ID> after:<D-1> before:<D+1>` (range). GOTCHA: the tool's `after`/`before` PARAMETERS are Unix epoch seconds, NOT dates; put the day filter in the QUERY string as `on:`/`after:`/`before:` `YYYY-MM-DD`, which is evaluated in the user's Slack tz (verified: `on:2026-06-18` returns Pacific-Thursday messages, matching the local-day binning). Use `sort=timestamp`.
   - Paginate to exhaustion: `limit` maxes at 20. If the response returns 20 results AND a `pagination_info` cursor, you are NOT done: more messages exist (an active day spans 2+ pages, and desc sort means page 2 holds the EARLIER messages of the day). Loop on the cursor until the response returns no cursor. Count the pages: you assert the count in the Step 3 calibration note. Stopping at page 1 silently drops the start of the day (verified: a Monday run returned 20 + a cursor; the page-1-only synthesis missed pre-08:40-local messages). GOTCHA: `public_and_private` result blobs routinely exceed the tool token limit and get spilled to a file; parse each saved file by char-range in python (the lines are too long for Read offset/limit), extract channel/time/text per result block, and read the `pagination_info` cursor from the same file.
3. For thread messages (`is:thread`, or a `thread_ts` in the permalink), use `slack_read_thread` to check whether a question the user asked got a reply: that is how you classify an ask as still "unanswered".
4. DEDUPE against 1a-1f: deploy announcements in channels like `#production-changes` and PR-review pings restate items already in Done/Reviews. Do NOT re-report them; keep only what Slack adds that the other sources do not (an unanswered ask, an open thread, a commitment).

## Step 2: filter bot noise

Exclude comments the API attributes to the user but that a bot posted under the user's token. Known Graphite bot patterns (all are NOT review activity):
- Stack-management comments: bodies containing "managed by Graphite", "merge this PR as a stack on Graphite", or "downstack PR is open"
- Merge-activity comments: bodies starting with `### Merge activity` (e.g. "* **Jun 22, 8:15 PM UTC**: @mslshao merged this pull request with Graphite")

Keep only hand-authored comments and real reviews. Flag this exclusion in the output so the talk-track does not overclaim.

## Step 3: synthesize the talk-track

Lead with the single most important fact (what shipped / the headline effort). Then these sections (omit any that are empty). Under `--days N`, sub-group each section by local day, newest first.

- **Done [day]** - shipped, merged, and built, grouped by ticket. One line each: ticket + PR + one-clause what.
- **Reviews** - someone-else's PRs reviewed: author name, verdict (approved / changes / commented), one-clause why, current PR state. (Name the author; never infer pronouns, use the name or singular they.)
- **Jira** - tickets commented on or closed out, with the gist of each comment.
- **Docs** - Confluence pages created or edited (title + page URL + the gist or edit message); a published runbook or design page is a real deliverable and belongs in the talk-track.
- **Open asks / threads (Slack)** - unanswered questions or review-requests the user posted, and threads where the user owes or awaits a reply. This is usually the only standup-worthy Slack content. Skip routine chatter and anything already covered by PRs/Jira/deploys (per 1g dedup). Fold genuine blockers here into Status, follow-ups into Today/next.
- **Status / blockers** - drafts still open, gated/manual deploys pending, real CI failures (not hygiene gates).
- **Today / next** - the immediate next actions and any downstream beads blocked on this work.

Then a **calibration note** (1-2 lines) stating: (a) real outward review work vs bot-attributed noise excluded; (b) **Slack pagination completeness**: how many messages across how many pages, and whether the day was fully paginated to no-cursor or only the first page was read. A page-1-only sweep is an incomplete standup: either finish paginating or flag the gap explicitly. This makes silent Slack truncation impossible and keeps the spoken update accurate.

Style: scannable talk-through bullets; IDs and identifiers in code spans; no em-dashes (use colons, commas, parentheses); gender-neutral; calibrated language (do not call hygiene-gate red checks "failures"). This is the spoken-standup deliverable, so a structured briefing is appropriate here even though normal end-of-turn replies stay terse.

## Edge cases

- **No activity that day**: interactive caller, say so plainly and offer to widen to the prior day or `--days N`; non-interactive agent caller, automatically widen to the previous working day and label that the requested day was empty.
- **Day-boundary items**: when a commit/PR/comment lands within ~1 hour of the local midnight boundary, surface it with its local time and ask (interactive) or note-and-include (agent); the Friday-vs-weekend question recurs.
- **Multi-repo**: default scope is the current repo. `gh search` candidate queries are cross-repo, but the comment-stream and per-PR endpoints are per-repo; if the user works across repos, loop the repo list and note which repos were swept.
