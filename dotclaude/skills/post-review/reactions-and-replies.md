# Bot Reactions & Inline Replies

Two secondary posts sequenced AFTER the atomic review POST (Step 3): bot
reactions (Step 3.5) and inline reply-in-thread comments (Step 3.6). Both are
skipped silently when their source list is empty. The SKILL.md Steps 3.5/3.6
point here.

## Step 3.5: Bot Reactions

After the main review post succeeds (Step 3), apply bot reactions (thumbs-up
or thumbs-down) to bot comments that pr-intel classified during its Bot
Reactions phase. This is the upgraded form of the engineering lead's 2026-05-20 "thumbs-up
instead of repeat" feedback: a thumbs-up signals the bot's finding was
correct (whether or not the reviewer also added a comment); a thumbs-down
signals it was a false positive (whether or not the reviewer also wrote a
rebuttal). See pr-intel `bot-reactions.md` for the 5-category decision tree
that produces the `bot_reactions` list this step consumes.

The `bot_reactions` list is part of the pr-intel output (extracted in Step 1
alongside review summary and inline comments). Each entry has:

- `comment_id`: GitHub comment ID
- `endpoint`: `pulls` (inline review comment from Copilot/Sentry/Datadog
  code-quality) or `issues` (issue-level conversation comment from
  SonarQube/Vercel/PR Metrics/Datadog PR-summary)
- `reaction`: `+1` (bot finding was correct) or `-1` (bot finding was a
  false positive)
- `bot_name`: the bot that authored the comment (Copilot, Sentry, Datadog,
  SonarQube, Vercel, PR Metrics, etc.)
- `finding_summary`: one-line description of what the bot caught

For each entry, POST the reaction:

```bash
# For inline review comments (Copilot, Sentry, Datadog code-quality):
gh api -X POST \
  /repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions \
  -f content=<reaction>

# For issue-level conversation comments (SonarQube, Vercel, PR Metrics, Datadog PR-summary):
gh api -X POST \
  /repos/{owner}/{repo}/issues/comments/{comment_id}/reactions \
  -f content=<reaction>
```

Where `<reaction>` is the literal value from the entry (`+1` or `-1`). Auth is
the same as the rest of `gh api`, but in auto mode the classifier may still
gate the POST on intent (see the classifier-denial bullet below).

**Error handling**:
- 404: the bot comment was deleted between pr-intel and post-review. Log and
  skip; do not retry. The classification was based on a comment that no longer
  exists.
- 422 "already exists": Michael already reacted to this comment in a prior
  session. Treat as success (the reaction signal is already on the comment).
  If the prior reaction was the OPPOSITE of the new one (e.g., a `-1` exists
  but the new entry is `+1`), surface to user with a note so they can decide
  whether to clear the prior reaction before re-posting; do NOT silently
  overwrite (changing a reaction requires DELETE on the old reaction ID first).
- 403: token lacks `repo` scope for reactions. Surface to user and skip; main
  review post already succeeded.
- **Auto-mode classifier denial** (not an HTTP error): in auto mode the reaction
  POST is gated on INTENT separately from the review post, so a narrowly-scoped
  approval ("approve", "shorten the comment") can leave the reactions read as an
  unrequested external write and denied, even though the review post itself
  succeeded and `Bash(gh api:*)` is permission-allowed. This is the classifier,
  not auth: a permission rule does NOT fix it (the broad `gh api:*` allow is
  already present and gets overridden). Do NOT work around the denial with
  another tool. Recovery: report the blocked reactions in one line (bot +
  finding) and offer a verb to apply them ("reply `react` to apply the N
  reactions"). The signal is low-stakes and deferrable; a second round-trip is
  fine. Step 3.6 replies share this recovery.

**Skip silently** if `bot_reactions` is empty (no bot overlap on this PR).

Add the reaction counts to the user-facing report:
```
Review posted to PR #NNN.
<review URL>
N inline comments posted. <skip note if applicable>
M bot reactions applied (P thumbs-up, Q thumbs-down across <bot names>).
Memory: review:pr-NNN:YYYY-MM-DD recorded.
```

## Step 3.6: Inline Replies (thread continuations)

After the main review post and bot reactions succeed, post any inline
comments tagged for reply-in-thread by pr-intel synthesis. The atomic review
endpoint (Step 3) does NOT accept `in_reply_to_id`, so these must be
sequenced as separate calls.

pr-intel's `synthesis.md` Step 2 produces these comments when the
position-based same-author dedup rule detects a prior-round inline at the
same `path:line` and the new finding adds genuinely distinct context
(additional affected sites, new failure mode discovered post-round-1,
version-specific clarification). Each tagged inline carries a `Reply
target:` briefing-context line naming the prior `comment_id` to thread
under. See pr-intel `output-formats.md` for the format.

Extract the tagged inlines from the pr-intel output (Step 1 already filtered
them OUT of the atomic POST payload so they would not double-post). Each
entry has:

- `path`: file path the original comment was on
- `prior_comment_id`: GitHub comment ID being replied to
- `body`: the reply text (already drafted by synthesis)

For each entry, POST the reply to the replies subresource:

```bash
gh api -X POST \
  /repos/{owner}/{repo}/pulls/{pull_number}/comments/{prior_comment_id}/replies \
  -f body="<reply text>"
```

**Error handling**:
- 404: the prior comment was deleted or the ID is stale (e.g., the prior
  review was dismissed). Log and skip; do not fall back to a new top-level
  inline because the dedup rule already established the reviewer should not
  post a second top-level on this line. Surface to user so they can decide
  whether to re-post as a fresh inline manually.
- 422 "line could not be resolved": should not happen on a replies endpoint
  (line is inherited from the parent), but log and skip if it does.
- Any other error: report the full error message and the command attempted.
  Do not retry silently.

**Skip silently** if no inline-reply entries exist in the pr-intel output
(the common case; most reviews do not collide with prior rounds).

Add the reply counts to the user-facing report:
```
Review posted to PR #NNN.
<review URL>
N inline comments posted. <skip note if applicable>
M bot reactions applied (P thumbs-up, Q thumbs-down).
R inline replies posted (threading to prior-round comments).
Memory: review:pr-NNN:YYYY-MM-DD recorded.
```
