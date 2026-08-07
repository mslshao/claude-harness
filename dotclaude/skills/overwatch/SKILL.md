---
name: overwatch
description: "Standing work-queue watcher. A self-paced ScheduleWakeup loop that watches the user's beads, GitHub PRs, and Jira on a cadence and surfaces only time-sensitive DELTAS (a bead just became unblocked, a new PR review was requested, an in-progress item is going stale) so the user knows what to work on next without polling by hand. Read-only and surfacing-only: it never mutates code, PRs, or tickets. Chat-only output for v1. Trigger on: 'overwatch', 'watch my work queue', 'keep an eye on my beads/PRs', 'tell me when something needs my attention', 'what should I pick up next' asked as a standing request. Use `--stop` to end the loop."
argument-hint: "[--stop] [--interval <seconds>] [--age-days N]"
allowed-tools: ["Bash", "Grep", "Read", "ScheduleWakeup", "CronCreate", "mcp__atlassian__searchJiraIssuesUsingJql", "mcp__atlassian__atlassianUserInfo", "mcp__atlassian__getAccessibleAtlassianResources"]
---

# Overwatch

A standing loop that watches the user's work queue across beads, GitHub PRs, and
Jira, and surfaces only the DELTAS that mean "something needs your attention now."
It answers "what should I work on next?" continuously, so the user does not have
to run `bd ready`, `gh search prs`, and a Jira query by hand every hour.

Two things make it safe to leave running:

- **Read-only.** It reads state and reports. It never edits code, force-pushes,
  replies on a PR, or transitions a ticket. Contrast babysit-pr, which mutates.
- **Quiet by default.** A cycle where nothing changed and every source succeeded
  produces no chat output at all. It speaks only on a real delta or a source
  failure.

State lives in one tracking bead's `notes` field as a single JSON blob, replaced
in full each cycle, so the loop survives compaction and any wakeup can cold-start
from `bd show <bead-id>`. This is the specialized sibling of `/loop` dynamic mode:
the poll-diff-surface body is fixed and the cadence self-calibrates.

## When to invoke

- User says "overwatch", "watch my work queue", "keep an eye on my beads and PRs",
  "let me know when something needs my attention", "what should I pick up next"
  asked as a standing request rather than a one-shot.
- User is heads-down and wants to be told when a bead unblocks, a review lands on
  their plate, or an in-progress item is stalling, without breaking focus to poll.

## When NOT to invoke / Related skills

| Instead | When |
|---|---|
| `/babysit-pr <number>` | You want to WATCH ONE SPECIFIC PR and take bounded ACTIONS on it (auto-remediate mechanical bot comments, reply inline, escalate humans). babysit-pr is single-PR and MUTATING; overwatch is multi-source and READ-ONLY. babysit-pr is window-bounded (default 1h); overwatch is a standing loop with no window. |
| `/standup-prep` | You want a BACKWARD-LOOKING, one-shot talk-track of what you already did for a past day. standup-prep is a single generation over a fixed past window; overwatch is FORWARD-LOOKING and continuous ("what is newly actionable"). standup-prep never loops. |
| `/loop` (dynamic) | You want to run an arbitrary prompt on a self-paced cadence. overwatch is the specialized variant of that pattern where the loop body (poll beads/PRs/Jira, diff, surface) is fixed. |
| `bd ready` / `gh search prs` / a one-off Jira query | You want the current state ONCE, right now. overwatch is for the standing case where polling by hand is the toil being removed. |

overwatch is personal-tier and watches the user's OWN queue. It is unrelated to
the Emerald team `/watchdog` (a separate, team-owned DevOps first-responder that
acts on production incidents); do not conflate them.

## Argument parsing

Raw invocation: `/overwatch $ARGUMENTS`

- **`--stop`**: terminate the loop durably. Set `"active": false` and a
  `"terminal_reason"` in the state blob (a plain `bd update --notes` write), post
  `[OVERWATCH_TERMINATED]` as an event comment, and do not schedule a wakeup.
  Writing the flag is load-bearing: a wakeup armed by an earlier cycle is still
  queued (ScheduleWakeup does not cancel), so termination cannot rely on "just do
  not schedule". The preflight termination gate (step 3) is what actually stops
  the already-armed fire. All other flags are ignored when `--stop` is set.
- **`--interval <seconds>`**: override the starting cadence. Default 900 (15 min),
  clamped to `[60, 3600]`. Persisted into `interval_seconds` this cycle so a later
  bare `/overwatch` wakeup keeps the override.
- **`--age-days N`**: threshold for the "aged in-progress" category. Default 7.
  Persisted into `age_days`, same reason.
- **`--resume`**: restart a loop that a prior `--stop` set to `active: false`.
  Clears the flag (`active: true`), then runs a normal cycle. Required to restart
  because a bare `/overwatch` cannot: the armed wakeup that `--stop` could not
  cancel ALSO fires a bare `/overwatch`, so if bare re-entry resumed, that queued
  fire would silently un-stop the loop. Resume must therefore be an explicit,
  human-only signal.

A bare `/overwatch` (the wakeup-prompt form) re-enters preflight, finds the
existing tracking bead, and runs one loop cycle when the loop is active. On an
active loop, cold-start and hot continuation are indistinguishable, which is what
lets a fresh session resume an ACTIVE loop; a STOPPED loop stays stopped until
`--resume` (see the termination gate).

## Preflight

Runs on every invocation. Idempotent: it detects an existing loop and resumes it
rather than starting a second one.

### 1. Resolve identities

Take these from live lookups, never from memory (a stale id silently filters the
wrong person's work):

```bash
gh api user --jq '.login'          # GitHub login for @me expansion sanity
git config user.name               # bd actor / owner
```

For Jira, `mcp__atlassian__atlassianUserInfo` gives the accountId and
`mcp__atlassian__getAccessibleAtlassianResources` gives the cloudId. `@me` in the
`gh` queries and `currentUser()` in the JQL resolve server-side, so the ids are a
cross-check, not a substitution.

### 2. Find or create the tracking bead

The tracking bead holds all loop state. It is NOT one of the `overwatch`-labelled
planning beads; it carries a distinct label so the two never collide.

```bash
bd list --label=overwatch-state --status=all --json -n 0
```

If a bead exists, use it. If none exists, create one (first-ever run):

```bash
bd create \
  --title="overwatch: work-queue watcher state" \
  --description="Runtime state bead for the overwatch standing loop. The notes field holds the current-state JSON blob (replaced each cycle). Comments are the event log (one per alerting cycle only). Do not hand-edit." \
  --type=task --priority=3 --label=overwatch-state
bd update <new-id> --claim
```

Record the id for the rest of the run.

**Single-writer lock (2026-07-17, docr-bbj5d)**: the state JSON carries a
`writer_session` + `writer_ts` pair. Before mutating state or scheduling a
wakeup, compare `writer_session` to this session: if it is another session AND
`writer_ts` is newer than one full arming interval, another live session owns
the loop; do NOT write or schedule (a second writer double-fires alerts and
replaces state blobs mid-cycle). Surface it and stop. If `writer_ts` is stale
past an interval, take over: set both fields to this session on your next
state write. Every state write refreshes `writer_ts`.

### 3. Load state and check the termination gate

```bash
bd show <bead-id> --json
```

Parse the `notes` field as JSON (see State schema). `bd show --json` returns
either a single object or a one-element list depending on version; handle both
(`row = data[0] if isinstance(data, list) else data`) before reading `notes`.

**Termination gate (check first).** If the parsed state has `"active": false`,
the loop was stopped by a prior `--stop`. Unless THIS invocation passed
`--resume`, do nothing: do not run the body, do not schedule a wakeup, end the
turn. This gate, not the absence of a new schedule, is the real off switch,
because ScheduleWakeup cannot cancel a queued fire, and it must be absolute for a
bare `/overwatch`: the still-queued wakeup fires a bare `/overwatch` too, so any
bare re-entry that resumed would silently un-stop the loop. With `--resume`, clear
the stop by writing `"active": true` to the bead IMMEDIATELY (its own
`bd update --notes` with the FULL loaded blob and only `active` flipped to true;
`--notes` is full-replace, so write the whole blob, never a fragment, or the other
fields are wiped), before running the body, then continue into a normal cycle
(or the baseline branch if the loaded state is stale). The immediate write is
load-bearing: it makes the resume durable even if the double-fire guard (step 4)
then skips THIS invocation because a pre-stop wakeup is still queued. That leftover
wakeup fires as a bare `/overwatch`, now reads `active: true`, and runs a normal
cycle that re-arms the chain, so the loop ends up alive with exactly one chain
(arming_due defers while the leftover is still pending, so it is never
double-armed).

Otherwise branch on the notes content. Baseline seeding is PER SOURCE, not
uniform, and a baseline cycle surfaces NOTHING (nothing is a delta yet):

- **Well-formed active state present**: normal continuation (loop body).
- **Notes empty / bead just created**: first cycle. Gather, then seed `known`:
  - membership sources (`beads_ready`, `prs_authored`, `review_requests`): record
    every current item as `known`.
  - `in_progress`: record ONLY the currently-aged ids (`now - updated_at >
    age_days`). Seeding every in-progress item would permanently suppress the
    stall alert for work already in progress at loop start; seeding only the
    already-aged ones lets an item that ages AFTER baseline still fire.
  - `prs_reviewing`: record each current key's `updatedAt` as its watermark
    (a map, not a list). Nothing alerts at baseline; only a later watermark
    advance does.
  - any source that returned `status: error` this baseline: leave its `known`
    unset, so it re-baselines silently on its first success (loop-body Step 3)
    rather than flooding on recovery.
  Then persist the full initial blob (State schema shape: `active: true`,
  `last_cycle_at := now`, `interval_seconds` = 900 or the `--interval` override,
  `next_wakeup_at := now + interval_seconds`, `consecutive_quiet_successful_cycles
  := 0`, and the seeded `known_items`), arm the wakeup (Step 6), and end. Persisting
  `next_wakeup_at` here is required: the double-fire guard (step 4) reads it on the
  very next cycle. Surface nothing.
- **Notes present but will not parse as JSON** (a truncated write, a manual edit):
  treat exactly as the empty/first-cycle case above (re-baseline, surface
  nothing), noting the recovery in an event comment. Do NOT route this to the
  catch-up diff path (step 5): with no known set, diffing would surface every
  current item as a false "new" delta. Safe failure direction: at worst a
  one-cycle gap in delta detection, never a crash and never a false-alert flood.

### 4. Double-fire guard

ScheduleWakeup queues wakeups rather than replacing them, so two nearly
simultaneous fires can occur (e.g. a manual `/overwatch` moments before an armed
wakeup). Before running the body:

- If state is absent / first-cycle (no `last_cycle_at`), skip this guard: there is
  no prior cycle to collide with. Proceed.
- Otherwise skip the body ONLY if BOTH `now - last_cycle_at < 60s` AND
  `next_wakeup_at > now` (a future armed fire genuinely still exists and will do
  the work). Skipping means: do not re-persist, do not schedule, end the turn.
- If `now >= next_wakeup_at`, this fire IS the armed wakeup coming due, so do NOT
  skip even when `last_cycle_at` is recent: run the body and let Step 6 re-arm.
  Gating on `< 60s` alone would kill the loop in one ordering: a manual
  `/overwatch` shortly before the armed fire runs the body but defers arming (it
  is mid-interval, Step 6), then the armed fire, now within 60s, would be wrongly
  skipped as a duplicate when in fact no wakeup remains queued.

### 5. Catch-up detection

If well-formed state exists AND `now - last_cycle_at > interval_seconds + 1800`
(the expected cadence plus a 30-minute grace: ~45 min at the 900s base cadence,
and scaling with the backed-off cadence so a routine tick at any tier is never
mislabeled), this is a resume after a gap (overnight, a closed session, a slept
codespace). Run a full gather and diff against the persisted `known` sets exactly
as normal: those sets persist across the gap, so the delta is still correct, it
just covers a longer window. Label the cycle's output as a catch-up so the user
knows it spans more than one interval.

Absent or unparseable state is NOT a catch-up: it has no `known` sets to diff, so
step 3 re-baselines it silently instead. This branch is reached only when a real
known set exists to diff against.

## Loop body

**Fast path (preferred): `cycle.py`.** The six steps below are the spec and the
manual fallback; in practice run them in one call. Gather the Jira record via MCP
(Step 2) into a temp file, then:

```bash
python3 ~/.claude/skills/overwatch/cycle.py <tracking-bead-id> --jira-file /tmp/ow_jira.json
```

It performs NO writes and returns a plan JSON: `{action, chat, event_comment, blob,
persist, arming_due, interval}`. The agent then, IN ORDER (persist after output, per
duplicate-over-drop): if `action == "skip"` or `"terminal"`, do nothing; else if
`chat` is non-null, print it and `bd comment <id> "<chat>"`; if `persist`,
`bd update <id> --notes '<blob>'`; if `arming_due`, `ScheduleWakeup(delaySeconds=
interval, prompt="/overwatch")`. Pass `--stop` / `--resume` / `--interval` /
`--age-days` through. cycle.py ports the steps below verbatim (gate, baseline,
double-fire, catch-up, diff, arming); read them to understand or debug its plan.

Each step below runs in order (manual path), then ends the turn.

### Step 1: Gather (bash-pollable sources)

```bash
python3 ~/.claude/skills/overwatch/gather.py
```

This prints one status-contract record per bash-pollable source
(`beads_ready`, `in_progress`, `prs_authored`, `review_requests`,
`prs_reviewing`) as JSON:

```json
{"beads_ready": {"status": "ok", "items": ["docr-..."]},
 "prs_reviewing": {"status": "ok", "items": [{"number": 42, "repository": "o/r", "updated_at": "..."}]},
 "review_requests": {"status": "error", "error_detail": "..."}}
```

`prs_reviewing` (PRs the user has already reviewed, still open) deliberately
INCLUDES approved-but-still-open PRs: a push after the user's approval is
exactly the author activity worth surfacing.

The load-bearing rule the script enforces, and that the agent MUST preserve when
folding in Jira below: **a source's exit code is authoritative, never its
stdout.** An errored source has a `status: "error"` record with an `error_detail`
and NO `items` key, so it can never be mistaken for a legitimately empty ("quiet")
source. `gh` on a 401 writes an empty `[]` to stdout and exits non-zero; reading
that as "quiet" is the exact silent failure this contract exists to prevent. Never
re-run a gather command piped through `head`/`jq` to inspect it: a pipe masks the
exit code (verified 2026-07-09).

### Step 2: Gather Jira (agent-side, MCP)

Jira is reachable only through the Atlassian MCP tool, which the shell script
cannot call, so the agent gathers it and applies the SAME status contract. Use
`mcp__atlassian__searchJiraIssuesUsingJql` with the candidate-net JQL ported from
standup-prep step 1d (query shape only, not its calendar-day windowing):

```
(assignee was currentUser() OR reporter = currentUser() OR watcher = currentUser()) AND updated >= "<lower>"
```

- `<lower>` is a rolling floor: `last_cycle_at`'s date, or 14 days ago on a
  cold-start baseline. Lower bound ONLY. Do NOT add an upper bound (`updated < ...`):
  a ticket touched this cycle whose `updated` later drifts forward would fall out
  of an upper-bounded net and be silently missed. `was` is intentional (history
  operator: catches a ticket assigned then reassigned); do not change it to `=`.
- Classify the MCP result on the same contract: a tool error (raised, or an error
  object) is `status: "error"` with the message as `error_detail` and no items;
  a successful call is `status: "ok"` with the returned issues as items (an empty
  result set is a legitimate quiet `ok`, never an error).

Merge the Jira record into the gather map under key `jira`.

Request minimal fields and `responseContentFormat: "markdown"`: overwatch only
needs each issue's KEY (for the diff) plus its summary (for the digest line). A
default-fields call overflows the tool token limit even for a few dozen issues and
spills the payload to a file (observed 2026-07-10: 30 issues, 150KB), and even
`fields: ["key"]` did not prevent the spill. When it spills, read the KEYS from the
harness compact projection or the saved file rather than the inline response; do
not treat the spill as a source error (it is a successful `ok` result, just large).

Use the default `issues` result mode; do NOT pass `searchResultMode: "count"`.
Count mode returns only the total and omits the issue keys the diff requires,
forcing a second `issues`-mode query (observed twice on 2026-07-22). The keys,
not the count, are what the diff needs.

### Step 3: Diff each ok source, then update its known set

For every source with `status == "ok"`, compute the delta against the persisted
`per_source[source].known_items`, THEN set the new `known_items` per the update
rule. The update rule is what keeps the diff correct across cycles AND the state
bounded; do not skip it.

- `beads_ready` (membership, key = bead id): `new = current_ids - known_ids` are
  newly-unblocked candidates. Update: `known_items := current_ids`.
- `review_requests` (membership, key = `"<repository>#<number>"`, NOT the bare
  number): `gh search prs` is cross-repo and PR numbers are not unique across
  repos, so a bare-number key can silently drop a genuinely new request that
  collides with a known number in another repo. `new = current_keys - known_keys`.
  Update: `known_items := current_keys`.
- `prs_authored` (membership, key = `"<repository>#<number>"`, same reason):
  `new = current_keys - known_keys` are newly opened authored PRs. Update:
  `known_items := current_keys`.
- `in_progress` (alert-once-aged, key = bead id): `aged = { id : now - updated_at
  > age_days }`; `newly_aged = aged_ids - known_ids`. Update: `known_items :=
  (known_ids ∪ newly_aged) ∩ current_in_progress_ids`. The intersect prunes items
  that left in_progress (closed or moved) so the set stays bounded, and it lets an
  item that leaves and re-enters re-alert when it ages again.
- `jira` (key = issue key): `new = current_keys - known_keys`. Update:
  `known_items := current_keys`. Jira deltas are NOT one of the three named
  categories; they go to the "other changes" digest (Step 4).
- `prs_reviewing` (WATERMARK, key = `"<repository>#<number>"`): not a membership
  source. `known_items` maps each key to the last-seen `updatedAt`; the delta is
  the keys whose CURRENT `updated_at` is newer than the known watermark (author
  pushed or replied on a PR the user already reviewed). A key's FIRST appearance
  is baselined silently (record the watermark, no alert): the usual first
  appearance is the self-echo of the user's own just-posted review bumping
  `updatedAt`. Update: `known_items := {key: current updated_at}` rebuilt from
  the current result in full, which advances fired watermarks, records new keys,
  and prunes keys absent from current (closed/merged PRs) in one step.

Membership sources track current membership, so an item that leaves and re-enters
re-alerts. That is deliberate: a bead that leaves `ready` (claimed, closed) and
later returns is newly actionable again and worth surfacing.

**Classify `prs_reviewing` deltas before surfacing (agent-side).** A watermark
advance only says `updatedAt` moved, and the user's OWN actions also move it
(posting a review or a reply is a self-echo). When a `prs_reviewing` delta fires,
the agent SHOULD run:

```bash
gh pr view <number> -R <repository> --json headRefOid,comments \
  --jq '{head: .headRefOid, last: .comments[-1].author.login}'
```

and DROP the alert if the only activity is the user's own, OR if the only
post-watermark activity is an automated bot comment (e.g. `sonarqubecloud`,
`graphite-app`, `github-actions[bot]`): a CI or static-analysis bot comment on a
PR you have already reviewed is not a re-review trigger (observed on #10847
across three cycles 2026-07-22). Keys also present in
the `prs_authored` known set are skipped entirely (own PRs are already covered by
that source). This classification is agent-side by design: gather.py stays
one-command-per-source.

A source with `status == "error"` is NOT diffed and its `known_items` is carried
forward unchanged (nothing lost or falsely "seen"); it goes to the failure report
in Step 4. A source with NO known set yet (never succeeded, e.g. errored through
baseline) is re-baselined silently on its first success: record its current set as
`known` (aged-only for `in_progress`) and surface nothing for it this cycle.

### Step 4: Category-gate and compose output

Three named categories each trigger a named alert line; `prs_reviewing`
watermark deltas are NOT one of the three but get their own named line rather
than the digest. Every other real delta lands in a single "other changes"
digest line, so nothing is silently dropped. Source errors are reported in
plain text in the same message.

- **Newly unblocked bead** (`beads_ready` delta): render from the gathered row,
  which carries id, title, and priority: `🔓 newly unblocked: docr-XXXX [P<priority>] <title>`.
- **New review request** (`review_requests` delta): `👀 review requested: <repo>#N <title> <url>`.
- **Aged in-progress item** (`in_progress` newly-aged): `⏳ stalling (in_progress, no update in >Nd): docr-XXXX <title>`.
- **Activity on a reviewed PR** (`prs_reviewing` watermark advance, after the
  Step 3 self-echo classification): `🔁 activity on reviewed PR: <repo>#<number> <title> <url>`.
- **Other changes** (any real delta that is not one of the three above, e.g. a
  newly opened authored PR, or Jira activity in the net): one digest line each,
  e.g. `other: opened PR <repo>#N <title>` or `other: jira MX2-XXXXX <summary>`.
- **Source failures**: `⚠️ source <name> failed: <error_detail>` per errored source.

Output rules:

- If there is at least one alert, digest entry, or source failure: print the
  message to chat, then post the same content as ONE `bd comment` on the tracking
  bead (the event log). Prefix a catch-up cycle's output with a note that it
  spans a gap.
- If the cycle is fully quiet (no deltas in any category, no digest entries) AND
  every source returned `status == "ok"`: print NOTHING to chat and post NO
  comment. Silence is the correct output for a quiet, healthy cycle.

Keep the chat output scannable: IDs in code spans, no em-dashes, gender-neutral
(name the author or use singular they; never infer a pronoun).

### Step 5: Persist state

Write the full new state blob AFTER the chat output for this cycle has been
emitted. Ordering matters: if the process dies between output and persist, the
next cycle re-derives the same delta and re-alerts (a duplicate, which is
harmless and visible), rather than persisting a "seen" flag for an alert the user
never received (silent loss). The chosen failure direction is duplicate-over-drop.

```bash
bd update <bead-id> --notes '<new-state-json>'
```

`--notes` REPLACES the field in full, which is exactly what a fixed-size,
per-cycle current-state blob wants: state stays O(1) in the number of cycles no
matter how long the loop runs. This is a deliberate INVERSION of babysit-pr,
which uses append-only `bd comment` for its per-cycle state; babysit-pr is
window-bounded (a handful of cycles) so append is fine there, but overwatch is a
standing loop with no window, and an append-only log would grow without bound.
Here `bd comment` is reserved for the event log (Step 4), which only grows on
cycles that actually alert.

Update `consecutive_quiet_successful_cycles`: increment it when the cycle was
fully quiet AND all sources were ok; reset it to 0 on any alert, digest entry, or
source failure.

Build the full blob here, so the persisted state is self-sufficient for the next
cold-start. It includes: `last_cycle_at := now`; `active: true` (a normal cycle is
an active loop; only `--stop` sets false); the updated per-source `known_items`
(Step 3); `consecutive_quiet_successful_cycles`; `age_days` and `interval_seconds`
(the next interval from the calibration table, honoring any override); and
`next_wakeup_at`, set as follows.

Decide `arming_due` ONCE, from the `next_wakeup_at` value LOADED at the start of
this cycle (Step 3), BEFORE this write overwrites it:
`arming_due = (loaded next_wakeup_at is unset) OR (now >= loaded next_wakeup_at)`.
Then set `next_wakeup_at := now + interval_seconds` if `arming_due`, else carry the
loaded value forward unchanged (a future armed fire is still pending). Anchoring on
the loaded value is load-bearing: re-reading `next_wakeup_at` AFTER this write would
compare `now` to `now + interval` and never arm.

### Step 6: Schedule the next wakeup

Use the interval computed in Step 5 (from `consecutive_quiet_successful_cycles`).

**Arm exactly one chain.** Use the `arming_due` decision from Step 5. If
`arming_due` is true, call ScheduleWakeup below with the Step 5 interval. If it is
false (a manual mid-interval `/overwatch` while a future wakeup is still armed), do
NOT arm: let the already-armed fire do the work. Do NOT re-derive the decision from
the just-written `next_wakeup_at` or from `last_cycle_at` (Step 5 set both to
reflect `now`); either re-derivation would make the guard always trip and the loop
would die after one cycle. Arming unconditionally every cycle instead would stack
parallel chains, which is why the decision is gated on `arming_due`.

```
ScheduleWakeup(
  delaySeconds=<interval>,
  reason="overwatch: next work-queue sweep (<n> quiet cycles, interval <interval>s)",
  prompt="/overwatch"
)
```

The prompt is the bare `/overwatch` with no trigger words. This is deliberate: a
wakeup prompt that mentions drafting, replying, or Slack trips the
`slack-draft-checklist` UserPromptSubmit hook every tick and multiplies per-fire
context cost (observed 2026-06-16). Keep it task-descriptive and bare.

**Harness fallback**: if ScheduleWakeup is rejected or absent, arm a single
CronCreate one-shot at the SAME calibrated interval (not a fixed few minutes, so
backoff is preserved). Cron is minute-granular: convert the local wall-clock time
`interval` seconds from now into explicit fields and pin them, leaving
day-of-week `*`:

```
CronCreate(cron="<minute> <hour> <day-of-month> <month> *", recurring=false, prompt="/overwatch")
```

The only loss is sub-minute precision, which does not matter at a 15-to-60-minute
cadence. CronCreate is a tool-unavailability hedge, NOT a durability mechanism (it
dies with a slept codespace the same as ScheduleWakeup). If neither tool is
available, say so and stop the loop cleanly.

Then end the turn.

## Interval calibration

Cadence starts narrow so early cycles can be eyeballed for correctness, then backs
off once the loop has proven itself quiet, which also bounds cost. The numbers are
the guidance the user gave in the 2026-07-09 AI-tooling office hours (start ~15
min, back off toward 30 or 60 once behavior at each interval is proven), recorded
in `memory/office-hours-ai-tooling-2026-07-09.md`. They are distinct from the
different 30-min/8h-cap numbers in the Emerald `/watchdog` design (a different
tool, shift-bounded).

| `consecutive_quiet_successful_cycles` | Interval |
|---|---|
| `< 3` | 900s (15 min) |
| `3` to `5` | 1800s (30 min) |
| `> 5` | 3600s (60 min) |

Any alert, digest entry, or source failure resets the counter to 0 and the cadence
snaps back to 900s the next cycle. A `--interval` override replaces the 900s floor
but the same backoff multipliers apply above it.

Prompt-cache note: 900/1800/3600 all sit past the 300s cache TTL, so each wakeup
re-enters cold. That is the right trade for a standing personal watcher (a warm
sub-300s cadence would burn budget for a queue that changes on the order of tens
of minutes, not seconds).

## State schema

The tracking bead's `notes` field holds exactly this JSON, replaced in full each
cycle:

```json
{
  "schema_version": 1,
  "active": true,
  "terminal_reason": null,
  "last_cycle_at": "2026-07-09T21:15:00Z",
  "next_wakeup_at": "2026-07-09T21:30:00Z",
  "consecutive_quiet_successful_cycles": 0,
  "interval_seconds": 900,
  "age_days": 7,
  "per_source": {
    "beads_ready":     {"status": "ok", "known_items": ["docr-aaaa", "docr-bbbb"], "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "in_progress":     {"status": "ok", "known_items": ["docr-cccc"],              "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "prs_authored":    {"status": "ok", "known_items": ["mslshao/docr#10484"],     "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "review_requests": {"status": "ok", "known_items": [],                         "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "prs_reviewing":   {"status": "ok", "known_items": {"mslshao/docr#10601": "2026-07-09T20:58:00Z"}, "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "jira":            {"status": "ok", "known_items": ["MX2-NNNNN"],              "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null}
  }
}
```

- `active` / `terminal_reason`: `--stop` sets `active: false` with a reason; the
  preflight termination gate reads `active` before running the body. A normal
  cycle writes `active: true`.
- `next_wakeup_at`: when the currently-armed wakeup is due. Step 6 arms a new one
  only when `now >= next_wakeup_at`, so a mid-interval manual `/overwatch` does not
  stack a second chain.
- `known_items` per source is the set the next cycle diffs against, keyed as in
  loop-body Step 3 (bead id for `beads_ready`/`in_progress`/`jira`,
  `"<repo>#<number>"` for `prs_authored`/`review_requests`). For `in_progress` it
  is the set of currently-aged ids already alerted, pruned to live in-progress
  items, so each alerts once and the set stays bounded. For `prs_reviewing` it is
  a MAP of `"<repo>#<number>"` to the last-seen `updatedAt` watermark, rebuilt
  from the current result each cycle (so departed keys are pruned).
- On an errored source, carry forward the prior `known_items` and
  `last_success_at` unchanged, set `status: "error"` and `error_detail`, so a
  transient failure never drops the baseline.
- The blob is O(open work items) in size and O(1) in cycle count: it does not grow
  as the loop runs, only as the backlog changes.

## Live integration procedure

The fixture tier (`test_gather.py`) runs on every change to `gather.py` and is
network-free. The live tier (`live_check.py`) runs before shipping or after
touching gather logic:

```bash
python3 ~/.claude/skills/overwatch/test_gather.py          # every change to gather.py; must pass
python3 ~/.claude/skills/overwatch/test_cycle.py           # every change to cycle.py; must pass
python3 ~/.claude/skills/overwatch/live_check.py           # before shipping; local-safe
python3 ~/.claude/skills/overwatch/live_check.py --include-external
```

The default `live_check.py` run is safe: it creates and deletes one throwaway
bead, and forces a real `gh` auth failure with a bogus token (no external state
touched) to prove the error path against the live binary. The `--include-external`
tier covers the outward-facing round-trips that must be agent-run (they push a
branch / notify watchers), not silently scripted:

- **PR**: open a throwaway draft PR on a scratch branch, confirm it appears in the
  `prs_authored` gather, then close it and delete the branch.
- **Jira drift case**: create a throwaway ticket, confirm it appears in the JQL
  net, reassign it to someone else, touch it again so `updated` drifts forward,
  and confirm it STILL appears (this is what the lower-bound-only + `was` shape
  guarantees). Then delete/close the ticket.

## Termination

The loop terminates only on:

1. **Operator stop** (`/overwatch --stop`): write `active: false` and
   `terminal_reason: operator-stopped` to the state blob (`bd update --notes`),
   post `[OVERWATCH_TERMINATED]` as an event comment, and do not schedule a
   wakeup. The durable flag is what stops a wakeup an earlier cycle already armed:
   when that queued fire re-enters preflight, the termination gate (step 3) reads
   `active: false` and does nothing (it does not re-arm, so the loop fully drains
   after that one absorbed fire). The tracking bead stays open (its state is the
   resume anchor); `/overwatch --resume` clears the flag and restarts. A bare
   `/overwatch` does NOT restart a stopped loop, by design. Do NOT delete the
   tracking bead while a wakeup armed before the stop is still queued: preflight
   would then find no bead, treat it as a first-ever run, re-baseline, and re-arm,
   silently restarting the loop the stop was meant to end. Let the last armed
   wakeup drain (be absorbed by the gate) first, or leave the stopped bead in place.
2. **Harness has no wakeup mechanism** (neither ScheduleWakeup nor CronCreate
   available): report it and stop cleanly. State is persisted, so `/overwatch`
   resumes when a mechanism is available again.

There is no time window: overwatch is a standing loop by design. It pauses
naturally when the session/codespace sleeps (see Known limitations) and resumes on
the next `/overwatch`.

## Known limitations

Accepted tradeoffs for v1, documented so they are choices and not surprises:

- **In-session coverage only.** Both ScheduleWakeup and CronCreate fire only while
  the REPL is alive and idle; a slept-on-idle codespace kills the loop past the
  idle timeout. There is no server-side mechanism in v1. This was accepted when
  the design chose personal-tier-first + a standing loop over a durable mechanism
  (Datadog monitor, EventBridge, GitHub Actions cron) during the ideation
  narrowing. Resume is cheap: `/overwatch` cold-starts from the tracking bead.
- **Personal-tier scope.** overwatch watches the user's own queue and lives in
  `~/.claude/skills/`. It is not a shared or team artifact.
- **No external ground-truth re-derivation if the tracking bead is lost.** State
  is the bead's notes; if that bead is deleted, the loop re-baselines from scratch
  (one silent cycle) rather than reconstructing prior known-item sets.
- **Chat-only notification (v1).** Deltas print to the loop's chat transcript.
  A delta can be missed across the user's up-to-5 concurrent windows: a wrong or
  insufficient channel does not lose data, but makes the tool quietly worthless
  while still consuming loop budget, and by construction the user will not notice
  (they are not watching the missed channel). Slack self-DM and OS notification
  are a large lift and were explicitly deferred, not rejected; revisit once a
  channel choice is worth the build cost.
- **A background-Bash-poll-primary design was evaluated and deferred.** For the
  bash-pollable sources (`bd`, `gh`), `memory/workflow.md` prescribes a
  `run_in_background` Bash poll as cheaper than ScheduleWakeup. It was deferred for
  v1 because Jira is MCP-only (not bash-pollable), so the loop needs an agent-side
  tick regardless, and a hybrid would reopen the single-writer state invariant and
  rest on an unverified session-resume-lifetime claim. Revisit trigger: measure
  actual ScheduleWakeup cost (Arize / Anthropic billing); if it runs materially
  above the ~3-turns/hour estimate in `workflow.md`, reconsider the hybrid.

## Principles

- **Read-only.** overwatch reports; it never mutates code, PRs, or tickets.
- **Quiet on no-op, loud on delta.** A healthy quiet cycle is silent. Any delta or
  source failure always surfaces.
- **Exit code over stdout.** A source's failure is its exit code, never an empty
  stdout. An errored source is never mistaken for a quiet one.
- **Duplicate over drop.** State is persisted after output, so a crash re-alerts
  rather than silently marking an unseen alert as seen.
- **Idempotent re-entry.** Every `/overwatch` loads state from the bead and runs
  the same body; cold-start and hot continuation are indistinguishable.
