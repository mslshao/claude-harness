---
name: overwatch
description: "Standing work-queue watcher. A self-paced ScheduleWakeup loop that watches the user's beads, GitHub PRs, and Jira on a cadence and surfaces only time-sensitive DELTAS (a bead just became unblocked, a new PR review was requested, an in-progress item is going stale) so the user knows what to work on next without polling by hand. Read-only and surfacing-only by default: it never mutates code, PRs, or tickets unless the opt-in `--auto-review <scope>` mode is explicitly passed, which lets it run a full review pass on matching PRs unattended and post an APPROVE when clean, holding anything with findings. Trigger on: 'overwatch', 'watch my work queue', 'keep an eye on my beads/PRs', 'tell me when something needs my attention', 'what should I pick up next' asked as a standing request; for the auto-review mode, 'watch and review X while I step away', 'let the harness do the reviews', 'auto-review these PRs unattended'. Use `--stop` to end the loop."
argument-hint: "[--stop] [--resume] [--interval <seconds>] [--age-days N] [--quiet-period <seconds>] [--auto-review <pr-list-or-path-glob>] [--auto-review-max N] [--auto-review-window <seconds>]"
allowed-tools: ["Bash", "Grep", "Read", "ScheduleWakeup", "CronCreate", "Agent", "Skill", "mcp__atlassian__searchJiraIssuesUsingJql", "mcp__atlassian__atlassianUserInfo", "mcp__atlassian__getAccessibleAtlassianResources"]
---

# Overwatch

A standing loop that watches the user's work queue across beads, GitHub PRs, and
Jira, and surfaces only the DELTAS that mean "something needs your attention now."
It answers "what should I work on next?" continuously, so the user does not have
to run `bd ready`, `gh search prs`, and a Jira query by hand every hour.

Two things make it safe to leave running:

- **Read-only unless `--auto-review` is explicitly passed.** By default it reads state
  and reports: it never edits code, force-pushes, replies on a PR, or transitions a
  ticket. Contrast babysit-pr, which always mutates. The single exception is the opt-in
  `--auto-review` mode ([auto-review.md](auto-review.md)), which can post an APPROVE on a
  matching PR unattended; it is never implicit, requires an explicit scope, and still
  never comments, requests changes, or touches code. Absent that flag every read-only
  claim in this file holds literally.
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
| `/babysit-pr <number>` | You want to WATCH ONE SPECIFIC PR and take bounded ACTIONS on it (auto-remediate mechanical bot comments, reply inline, escalate humans). babysit-pr is single-PR and always MUTATING, and it acts on the user's OWN draft PR; overwatch is multi-source and read-only unless `--auto-review` is passed, and that mode REVIEWS OTHER PEOPLE'S PRs rather than iterating on your own. babysit-pr is window-bounded (default 1h); overwatch is a standing loop, and `--auto-review` carries its own separate cap and window so the posting authority is bounded even though the loop is not. |
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
- **`--interval <seconds>`**: override the starting cadence. Default 900 (15 min).
  The nominal range is `[60, 3600]`, but nothing enforces it: `interval_for` takes
  the value verbatim as the backoff floor. Contrast `--quiet-period` below, which is
  genuinely clamped, and do not read this bullet as evidence the clamp exists.
  `interval_seconds` is persisted every cycle, but as the interval that was just
  armed, not as a remembered override (Known limitations).
- **`--age-days N`**: threshold for the "aged in-progress" category. Default 7.
  Persisted into `age_days`, same reason.
- **`--quiet-period <seconds>`**: how long author activity on a reviewed PR must be
  quiet before the held alert fires (Path B, loop-body Step 3). Default 7200 (2h),
  clamped to `[300, 86400]`. Persisted into `quiet_period_seconds`. Changing it
  mid-flight re-evaluates open holds against the new value, so a hold can become
  instantly due on the next cycle; that is intended.
- **`--auto-review <scope>`**: opt into unattended reviewing. THE ONLY FLAG THAT LETS
  THIS SKILL MUTATE ANYTHING OUTSIDE ITS OWN TRACKING BEAD. `scope` is required and is
  either a PR list (`11020,11386`) or a path glob (`src/python/mx2/ruleseng/**`); a bare
  `--auto-review` is a configuration error, not "everything". On a matching delta the loop
  runs `/pr-intel`, and posts an APPROVE only when the render is clean AND
  `mx2-decision-maker` returns PROCEED. Findings, a non-PROCEED gate, an exhausted bound,
  or any error all HOLD instead. It never posts COMMENT or REQUEST_CHANGES, never posts
  inline comments, and never auto-approves a PR the user authored. Persisted in the state
  blob under `auto_review` and carried across cycles by `cycle.py`. Full spec, including
  every unattended branch: [auto-review.md](auto-review.md). Read that file before running
  this flag.
- **`--auto-review-max N`**: cap on auto-POSTED approvals for the life of the loop.
  Default 3. Hitting it downgrades later clean results to hold, so detection continues
  while posting stops; it does not terminate the loop.
- **`--auto-review-window <seconds>`**: wall-clock budget from loop start after which
  posting downgrades to hold. Default 28800 (8h). Both bounds exist so an overnight loop
  cannot keep approving after the operator's context has gone stale.
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

**Running a second, scoped watch alongside the general one.** The label-based lookup
above is a singleton by design: one tracking bead per label, one general work-queue
watcher. When a request is genuinely scoped (e.g. "auto-review only PRs touching
`src/python/mx2/ruleseng/**`, while I'm away") and the general watcher already exists
but is currently stopped (`active: false`), do NOT resume it just to get the new scope.
Resuming means `--resume`, and `--resume` runs a normal cycle against the FULL general
source set (all beads, all PRs, all Jira), which on a long-stopped watcher triggers a
catch-up cycle diffing against a stale `known_items` baseline (every current item reads
as "new"), flooding the first cycle with unrelated noise. Instead:

1. Create a dedicated tracking bead for this scoped run (plain `bd create`, no
   `--label=overwatch-state`; a second bead carrying that label makes the generic
   lookup ambiguous between two ready-made watchers).
2. Drive `cycle.py <new-tracking-bead-id> ...` directly, exactly as documented below,
   using that bead ID as the positional argument. `cycle.py` itself has no opinion on
   labels; it operates on whatever bead ID it is given.
3. Embed the bead ID explicitly in every `ScheduleWakeup` prompt for this run:
   `/overwatch --auto-review <scope> --tracking-bead <id>`. A bare `/overwatch` wakeup
   re-enters preflight and resolves the label-based lookup, which would find the
   GENERAL watcher, not this scoped one. `--tracking-bead` is not a flag `cycle.py`
   parses; it exists purely so the agent handling the next wakeup knows which bead to
   drive instead of doing label discovery. Leave the general watcher's bead and state
   untouched throughout; it stays exactly as its owner left it.

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
    (a map, not a list) and seed `holds: {}`. Nothing alerts at baseline; only a
    later watermark advance does. A baseline cycle also never produces a classify
    candidate (every key is a first appearance), so it is always a single call, never
    the two-phase one.
  - any source that returned `status: error` this baseline: leave its `known`
    unset, so it re-baselines silently on its first success (loop-body Step 3)
    rather than flooding on recovery.
  Then persist the full initial blob (State schema shape: `schema_version: 2`,
  `active: true`, `last_cycle_at := now`, `interval_seconds` = 900 or the
  `--interval` override, `next_wakeup_at := now + interval_seconds`,
  `consecutive_quiet_successful_cycles := 0`, `quiet_period_seconds` = 7200 or the
  `--quiet-period` override, and the seeded `known_items`), arm the wakeup
  (Step 6), and end. Persisting
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
python3 ~/.claude/skills/overwatch/cycle.py <tracking-bead-id> --jira-file /tmp/ow_jira.json \
  --gather-out /tmp/ow_gather.json --candidates-out /tmp/ow_candidates.json
```

It performs NO writes and returns a plan JSON: `{action, chat, event_comment, blob,
persist, arming_due, interval}`. The agent then, IN ORDER (persist after output, per
duplicate-over-drop): if `action == "skip"` or `"terminal"`, do nothing; else if
`chat` is non-null, print it and `bd comment <id> "<chat>"`; if `persist`,
`bd update <id> --notes '<blob>'`; if `arming_due`, `ScheduleWakeup(delaySeconds=
interval, prompt="/overwatch")`. Pass `--stop` / `--resume` / `--interval` /
`--age-days` / `--quiet-period` through. cycle.py ports the steps below verbatim
(gate, baseline, double-fire, catch-up, diff, arming); read them to understand or
debug its plan.

**`action: "classify"` (the two-phase branch).** When a `prs_reviewing` watermark
advanced, the fire policy needs per-PR event classification, which is a per-PR `gh`
read and therefore agent-side (Step 3). The call above then returns
`{"action": "classify", "candidates": [...], "arm": {...}, "chat": ..., "persist": false}`.
The generic three-step ordering above applies UNCHANGED to it, which is deliberate:
its `arming_due` mirrors `arm.due` and its `chat` carries every other source's
deltas, so an agent that knows only the generic contract still arms the next wakeup
and still surfaces everything except the reviewed-PR line. Then, IN THIS ORDER:

1. **Arm first.** If `arming_due` (identical to `arm.due`), `ScheduleWakeup(
   delaySeconds=interval, prompt="/overwatch")` NOW, before classifying. Phase 1
   persists nothing, so if the classification round trip dies (a turn limit on a
   chatty PR) an arm-only-at-the-end design would leave the chain dead until the user
   retypes `/overwatch`.
2. **Print `chat` if it is non-null**, before classifying, for the same reason: those
   lines belong to sources that have nothing to do with the PR being classified, and
   the round trip's failure mode is deterministic per PR, so holding them behind it
   would suppress a P1 unblocked bead on every cycle for as long as that one PR stays
   unreadable. Nothing is persisted until phase 2, so a phase 2 that never runs makes
   the next cycle re-derive and re-print them: duplicate over drop. Phase 2 knows
   they were printed and will not repeat them.
3. **Classify** each candidate per Step 3 and write the records to a file.
4. **Phase 2**, which returns a normal `action: "run"` plan:

```bash
python3 ~/.claude/skills/overwatch/cycle.py <tracking-bead-id> \
  --gather-in /tmp/ow_gather.json --reviewing-file /tmp/ow_reviewing.json
```

Those two flags are required TOGETHER; cycle.py exits 2 on either alone, with
`action: "error"` and a note. `--gather-in` replays phase 1's frozen sources so no
candidate can appear between the phases, and it carries phase 1's arm decision and
whether phase 1 printed, so phase 2 returns `arming_due: false`, reuses that
`next_wakeup_at`, and emits only the reviewed-PR lines. Arming in both phases would
stack two chains, which is exactly what `--gather-in` alone used to do: it fell
through to phase 1's branch, ignored the frozen arm, and re-printed the cycle's other
deltas. A cycle with no candidates needs only the single phase-1 call, which is the
common case: only a cycle that saw new activity pays the round trip.

**`--reviewing-file` holds an OBJECT keyed by PR key** (`repo#number`), one record per
candidate, exactly as Step 3 shows it. It is NOT the JSON array that
`--candidates-out` writes; passing that array, or any key whose value is not a record
object, exits 2 with `action: "error"` and changes nothing. Read the note, fix the
payload and re-run phase 2: state has not advanced, so nothing is lost. (Before that
validation existed the mistake raised an unhandled `AttributeError`, which is the
same outcome as skipping phase 2, the one genuinely lossy option below.)

**If you cannot classify a candidate, say so; do not omit it and do not skip phase
2.** Write `{"status": "error", "error_detail": "<what failed>"}` for that key and run
phase 2 anyway. cycle.py then holds that key's watermark (nothing is lost, it
re-candidates next cycle) AND renders a `⚠️ could not read activity on reviewed PR`
line, so the cycle is not counted as quiet. Skipping phase 2 entirely is the one
genuinely lossy option: state does not advance, no reviewed-PR line is emitted, and
the same failure repeats silently every cycle.

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

Every `gh search prs` source pins `--limit 100 --sort updated --order desc`. The
defaults are 30 rows by RELEVANCE, which is unstable between calls: a still-open PR
drops out of one cycle's result with exit 0 and returns in the next, and absence from
this source is meaningful (it prunes the key's watermark, and past the hold grace it
forces the pending alert out early). Sorting by `updated` also keeps the only PRs that
can be mid-burst at the top of the window.

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
- `prs_reviewing` (WATERMARK + QUIET PERIOD, key = `"<repository>#<number>"`): not a
  membership source, and NOT a plain advance-alerts source. `known_items` maps each
  key to the last-seen `updatedAt`; an advance past that watermark is a CANDIDATE, not
  an alert, because `updatedAt` alone cannot say who moved it. A key's FIRST
  appearance is baselined silently (record the watermark, no alert): the usual first
  appearance is the self-echo of the user's own just-posted review bumping
  `updatedAt`. Keys in the `prs_authored` known set are skipped: the watermark is
  recorded, but they are never held and never fire (`prs_authored` already covers the
  user's own PRs). That skip set is the one CARRIED FORWARD in state, not one derived
  from this cycle's `prs_authored` result, so own-PR suppression survives a cycle
  where that source failed; reading it from a failed source yields an empty set and
  leaks the user's own pushes as reviewed-PR alerts on exactly the cycles `gh` is
  down. The fire policy is below; cycle.py's `plan_reviewing` owns this
  whole source (marks, holds, fires, pruning), which is why `diff_and_update` skips it.

  The watermark that gets PERSISTED is the end of the window that was actually
  classified, not simply the row's current `updatedAt`: the earlier of the row's
  `updatedAt` and the agent's echoed `observed_updated_at`, floored at the previous
  mark, and with either value DISCARDED (not clamped) when it sits past `now + 300s`,
  falling back to the previous mark when both do. Each bound blocks a distinct silent
  failure. Advancing past the classified window would skip events no one examined;
  regressing below the previous mark would re-candidate the same window forever; a
  future mark would freeze the key, since nothing could ever advance past it again,
  and clamping such a value to `now` instead of dropping it would persist a window
  boundary no one classified. When a candidate's classification does not come back
  usable, the mark is HELD at the previous value so the key re-candidates next cycle
  (Step 4 reports it; nothing is silently consumed). When the whole source errors, no
  hold is evaluated either, so a settle that came due during the outage fires on the
  first successful cycle rather than being lost: firing needs the current row to
  render the line.

Membership sources track current membership, so an item that leaves and re-enters
re-alerts. That is deliberate: a bead that leaves `ready` (claimed, closed) and
later returns is newly actionable again and worth surfacing.

#### The `prs_reviewing` fire policy: explicit now, author activity once settled

Firing on every advance pings the user on every push. On
`<company>/docr#11539` (2026-08-12), in the 2h05m after the user's review,
the author pushed 6 commits and left 9 issue comments plus an inline reply and its
review body, tooling re-requested review once, and a CI bot commented once: 18
author events (the verified event set, replayed as Fixture 1 in `test_cycle.py`).
Every advancing cycle would have alerted: 6 at the 900s base cadence, and more the
finer the polling splits the burst, which the user counted as roughly 15 pings for one
review round. Volume was only half of it. The user also polled that PR by hand twice
across the same two hours and STILL missed the `@mslshao ready for re-review` at
14:41:25Z, so the policy needs an immediate path and not merely a quieter one. An
advance therefore takes one of two paths:

- **PATH A, fire immediately.** The post-watermark window carries a signal aimed at
  the user: an `@<user>` mention, a reply in a review thread the USER started, or a
  deliberate re-review request. Fires now and closes the burst, opening one first if
  none was open: an explicit signal with NO surviving author activity (rule 2's
  carve-out, a bot-actor re-request) anchors the burst on the new watermark rather
  than skipping it, because the contract invariant is that an explicit event IS
  activity. Path A therefore never fires without a burst to hold the rest of the
  round.
- **PATH B, hold then fire once.** Author activity with no explicit signal does NOT
  fire. It anchors a timer at the last author activity; the alert fires on the first
  cycle where `now - last_author_activity_at >= quiet_period_seconds` (default 2h).
  More author activity refreshes the anchor instead of firing.

One fire per burst. A burst ends when author activity stops for a full quiet period;
the next activity after that starts a new burst, which can fire again.

So an explicit signal arriving inside an already-fired burst is SUPPRESSED OUTRIGHT,
not delayed: it is never re-alerted for that burst, and if it is the author's last
act no later burst ever exists to carry it. On #11539 that is the 14:41:25Z
`@mslshao ready for re-review`, 1h56m after the 12:45 Path A alert for the same
burst. This is the ratified reading of the policy (the user's Fixture 1 expects
exactly one fire for a timeline that contains two explicit signals), so the
suppression stays, but it is recorded: the hold carries
`suppressed_explicit_kinds`, so the drop shows up in state instead of being
invisible. A `max_burst_seconds` force-end, or re-firing on an explicit KIND not yet
reported in this burst, would each surface it at the cost of a second ping per
burst; both are unbuilt and both would change Fixture 1.

**Classify each candidate agent-side, then hand the records back (phase 2).** This
stays agent-side by design: gather.py is one-command-per-source, and the reduction
needs four paginated per-PR reads. Write one record per candidate key:

```json
{"<company>/docr#11539": {
   "status": "ok",
   "observed_updated_at": "2026-08-12T14:43:12Z",
   "last_author_activity_at": "2026-08-12T14:41:25Z",
   "explicit": true, "explicit_kinds": ["mention"], "noted_kinds": ["review_requested"],
   "author_event_count": 18}}
```

Per-key `status: "error"` is required so one unreachable PR does not lose the others;
cycle.py then holds that key's watermark and re-candidates next cycle rather than
guessing. Reduction rules:

1. **Window**: keep events with timestamp strictly `> prev_watermark` and
   `<= observed_updated_at` (both come from the candidate entry; echo
   `observed_updated_at` back verbatim, never a value you computed).
2. **Drop self** (actor == the preflight-resolved login) **and drop bots**:
   `user.type == "Bot"` OR login ends with `[bot]`. Type-first is load-bearing:
   verified on #11539 the real logins are `sonarqubecloud[bot]` and
   `graphite-app[bot]`, so an earlier literal-login denylist (`sonarqubecloud`,
   `graphite-app`) matched neither. For a `committed` event there is no actor, only
   `committer.name` (verified: `"Jordan Byrne"`, a git name); check that against the
   bot names and otherwise attribute it to the PR author.

   **`committer.name: "GitHub"` (and `"web-flow"`) is a synthetic name GitHub itself
   writes for UI/API-driven merge actions** ("Update branch", a squash-merge via the
   web UI), not a human push, but it is not in the bot-committer name set above and has
   no `user.type`/`[bot]` signal to catch it either. Observed on #11020 (2026-08-17): a
   `committed` event with `committer.name: "GitHub"` inside the classification window,
   almost certainly a branch-sync click by a reviewer, not the PR author. Ratified
   default until this is resolved properly: treat it like any other unrecognized
   committer name (attribute to the PR author, count as author activity, PATH B not
   PATH A) rather than guessing who clicked it. This is the conservative direction: it
   costs a delayed settle-alert, never a missed one.

   This drop decides AUTHORSHIP: who may move the quiet timer (rule 3) and what
   counts toward `author_event_count`. It does NOT decide whether the user was
   addressed. Keep the full window available for rule 4's `review_requested` test:
   a request addressed to the user is addressed to the user whichever token sent it,
   and `graphite-app[bot]` is a routine actor on stack re-requests. Judging that
   signal after this drop made it unreachable, and the membership `👀` line no
   longer covers it either (Step 4), so the ask was lost.
3. **`last_author_activity_at`** = max timestamp of the survivors, or `null` if none
   survive. THIS IS THE WHOLE ANTI-NOISE MECHANISM: a bot or self-only advance
   reports `null`, which advances the watermark and touches no timer. Counting a
   per-push CI bot as author activity would hold a burst open forever and the alert
   would never fire.
4. **`explicit`** = true iff either a SURVIVOR is:
   - a comment or review body matching
     `(^|[^A-Za-z0-9_-])@<user>([^A-Za-z0-9_-]|$)`, case-insensitive; or
   - an inline review comment whose thread ROOT author is the user;

   or ANY windowed event (survivor or not, per rule 2's carve-out) is:
   - a `review_requested` event naming the user that is NOT within 300s of a push or
     force-push on the same PR. The adjacency test replaces an actor-identity test,
     which does not work: verified on #11539 that all three `review_requested` events
     naming mslshao have the HUMAN actor `jbyrne` and land 38s to 4m39s after a
     commit, because `gt submit` re-requests reviewers under the author's own token.
     `graphite-app[bot]` appears as actor only on the stack-wide fan-out to OTHER
     reviewers. Without the adjacency test every Graphite push fires Path A and Path B
     never engages. Residual: a deliberate re-request clicked within 5 min of a push
     is held instead of firing, so it arrives up to a quiet period late.

   A `review_requested` naming the user that IS push-adjacent goes into
   `noted_kinds` instead of `explicit_kinds`. It stays held (Path B), but the alert
   that eventually fires names it, which is the only place the user hears about a
   re-review ask on an already-reviewed PR now that the `👀` line is scoped
   (Step 4). `noted_kinds` never fires anything on its own.
5. **Fetch inline review comments UNWINDOWED.** The reply parent may predate the
   watermark and its author identity is what makes the thread-reply signal
   detectable: verified on #11539, comment `3766451082` (12:38:17Z) replies to
   `3762222531`, authored by mslshao at 22:34:31Z, 18 seconds BEFORE the 22:34:49Z
   watermark. A windowed fetch silently downgrades Path A to Path B. If the parent was
   deleted the root lookup misses and the signal degrades the same way.

```bash
R=<company>/docr; N=11539; ME=mslshao
gh api "repos/$R/issues/$N/comments" --paginate \
  --jq ".[] | {kind:\"issue_comment\", t:.created_at, who:.user.login, bot:(.user.type==\"Bot\"), \
               mention:(.body|test(\"(^|[^A-Za-z0-9_-])@$ME([^A-Za-z0-9_-]|\$)\";\"i\"))}"
gh api "repos/$R/pulls/$N/reviews" --paginate \
  --jq ".[] | {kind:\"review\", t:.submitted_at, who:.user.login, bot:(.user.type==\"Bot\"), state, \
               mention:((.body//\"\")|test(\"(^|[^A-Za-z0-9_-])@$ME([^A-Za-z0-9_-]|\$)\";\"i\"))}"
# NO --since here: the reply parent may predate the watermark (rule 5).
gh api "repos/$R/pulls/$N/comments" --paginate \
  --jq ".[] | {kind:\"review_comment\", id, parent:.in_reply_to_id, t:.created_at, \
               who:.user.login, bot:(.user.type==\"Bot\"), \
               mention:(.body|test(\"(^|[^A-Za-z0-9_-])@$ME([^A-Za-z0-9_-]|\$)\";\"i\"))}"
# ISSUES path for a PR timeline. `committed` carries committer.name, not an actor.
gh api "repos/$R/issues/$N/timeline" --paginate \
  --jq '.[] | select(.event=="review_requested" or .event=="committed" or .event=="head_ref_force_pushed")
        | {kind:.event, t:(.created_at // .committer.date), actor:(.actor.login // ""),
           git_name:(.committer.name // ""), requested:(.requested_reviewer.login // "")}'
```

The `--jq` projections deliberately emit a mention BOOLEAN rather than the body, which
keeps comment text out of the transcript and the payload small.

A commit date is client-supplied and a rebase backdates it, so discard any push
outside the window; the failure direction is one missed push, which is why pushes are
the weakest input here. `test_cycle.py` carries this reduction as an executable
contract (`classify_window`) over the real #11539 event set, so the fixtures are
end-to-end replays; the production reduction is still the agent's, and moving it into
a testable `reviewing.py` is the obvious next step if it drifts.

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
  SUPPRESSED only for a PR whose notification the `prs_reviewing` policy is currently
  carrying: it fired for that key this cycle, it holds an unfired burst for it, or it
  holds a fired burst whose last author activity is still inside one quiet period.
  GitHub drops the user from requested reviewers when they submit a review and tooling
  re-adds them on every restack, so during a live burst this membership line would
  re-alert per push and bypass the quiet period entirely (verified on #11539: three
  re-requests in one review round), and there the richer `prs_reviewing` line is the
  alert. Outside that window the policy is contributing nothing, so the line must
  survive: it is the only notification, and `review_requests` consumes the key into
  `known_items`, so a suppressed line there is lost for good rather than re-deltaed.
- **Aged in-progress item** (`in_progress` newly-aged): `⏳ stalling (in_progress, no update in >Nd): docr-XXXX <title>`.
- **Activity on a reviewed PR**, Path A: `🔁 activity on reviewed PR: <repo>#<number> <title> <url> (<why>)`,
  where `<why>` names the signal (`you were mentioned`, `reply on your thread`,
  `re-review requested`), with any `noted_kinds` appended after a semicolon exactly as
  on the Path B line. The reason is always the explicit one when both paths apply this
  cycle: a settled-labelled alert would never tell the user they were named.
- **Settled author activity on a reviewed PR**, Path B: `🔁 settled after author activity: <repo>#N <title> <url> (18 author events over 2h05m, quiet 2h)`
  (that is #11539's burst as this line renders it). The burst counts are what make one
  line stand in for the alerts that were withheld.
  Any `noted_kinds` on the burst are appended (`; re-review requested`), and a burst
  fired because the key fell out of the search result past its hold grace appends
  `; PR left the search result`.
- **Other changes** (any real delta that is not one of the three above, e.g. a
  newly opened authored PR, or Jira activity in the net): one digest line each,
  e.g. `other: opened PR <repo>#N <title>` or `other: jira MX2-XXXXX <summary>`.
- **Source failures**: `⚠️ source <name> failed: <error_detail>` per errored source.
- **Unreadable reviewed PR** (a candidate whose classification came back errored or
  missing): `⚠️ could not read activity on reviewed PR <repo>#N: <detail> (watermark
  held, retrying next cycle)`. This line is mandatory, not diagnostic. The watermark
  is held so the key re-candidates every cycle; without a line the cycle prints
  nothing and still counts as quiet, so a permanently unreadable PR is
  indistinguishable from a healthy queue while real activity sits unread. It is the
  per-key form of the same guarantee the source-level line gives, and it resets the
  quiet counter for the same reason.

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

**`block-bd-computed-field-write.sh` blocks this exact form when `<new-state-json>` is a
shell-substituted value** (`--notes "$(cat file)"`), even on a legitimate full-replace
write with no prior content at risk; it does not accept a literal value read from a
variable inside the same Bash call either. The safe pattern: write the whole
`bd update ... --notes '<blob>'` line into a script file via the Write tool (the JSON
embedded as a literal single-quoted string, not command-substituted), then run that
file with `bash`:

```python
python3 -c "
content = open('/tmp/ow_state_blob.json').read()
with open('/tmp/ow_bd_update_cmd.sh', 'w') as f:
    f.write('bd update <bead-id> --notes \'' + content + '\'\n')
"
```
```bash
bash /tmp/ow_bd_update_cmd.sh
```

Bundled: `bash ~/.claude/skills/overwatch/persist_state.sh <bead-id> <cycle-result-json-path>`
does all three sub-steps (extract, script-file, run) in one call, given the raw JSON
`cycle.py` printed to a file.

Verify the blob has no unescaped single quotes first (`grep -c "'" <blob-file>`; state
JSON never legitimately contains one). Expect this to trip on cycle 1 of every fresh
loop if you skip straight to the naive form above; using the script-file pattern from
the start avoids the block entirely.

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
source failure. A phase 2 whose phase 1 already printed is never counted as quiet
even when phase 2 itself emits nothing: something was surfaced this cycle, so the
cadence must snap back like any other alerting cycle.

Build the full blob here, so the persisted state is self-sufficient for the next
cold-start. It includes: `schema_version: 2`; `last_cycle_at := now`; `active: true`
(a normal cycle is an active loop; only `--stop` sets false); the updated per-source
`known_items` (Step 3) plus `per_source.prs_reviewing.holds`, the quiet-period burst
records; `consecutive_quiet_successful_cycles`; `age_days`; `quiet_period_seconds`
(this run's flag, else the persisted value, else 7200, clamped to `[300, 86400]`, so
a bare wakeup keeps the override); `interval_seconds`; and `next_wakeup_at`, both set
as follows.

`interval_seconds` is the calibration-table interval for the new counter value,
CAPPED at `min(1800, quiet_period_seconds)` whenever any UNFIRED hold is open (never
below the base floor, so a `--quiet-period` under 900 does not poll faster than 900),
and it is written only when this cycle actually arms. When arming defers (a future
wakeup is still pending) the loaded value is carried forward unchanged: writing a
freshly computed interval while the pending fire was armed at the old one would
corrupt both the double-fire guard and catch-up detection, which read
`interval_seconds` as the cadence the queued wakeup is actually running at. In the
two-phase cycle phase 1 owns the arming decision and records it, so phase 2 reuses
phase 1's interval and `next_wakeup_at` and reports `arming_due: false` (see the
classify branch above); its own clamped interval never reaches the blob.

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
| any value, while a `prs_reviewing` hold is OPEN | capped at `min(1800, quiet_period_seconds)` |

Any alert, digest entry, or source failure resets the counter to 0 and the cadence
snaps back to 900s the next cycle. A `--interval` override replaces the 900s floor
but the same backoff multipliers apply above it.

The hold cap exists because a pending hold is NOT an alert: the cycle is genuinely
quiet, the counter keeps climbing, and an unclamped loop would stretch to 3600s and
find the settle up to an hour late. It binds specifically on the cycle that detects a
settle, where nothing advanced so there is no candidate and no classification round
trip. An explicit `--interval` still wins (`--interval 3600` yields 3600), the cap
never dips below the floor either (`--quiet-period 600` at the default floor still
polls at 900, not 600), and only UNFIRED holds count: counting fired ones would pin
the cadence at the cap forever after one PR ever fired. A classify cycle is separately
armed at the 900s reset floor by phase 1, which is already under the cap.

Prompt-cache note: 900/1800/3600 all sit past the 300s cache TTL, so each wakeup
re-enters cold. That is the right trade for a standing personal watcher (a warm
sub-300s cadence would burn budget for a queue that changes on the order of tens
of minutes, not seconds).

## State schema

The tracking bead's `notes` field holds exactly this JSON, replaced in full each
cycle:

```json
{
  "schema_version": 2,
  "active": true,
  "terminal_reason": null,
  "last_cycle_at": "2026-07-09T21:15:00Z",
  "next_wakeup_at": "2026-07-09T21:30:00Z",
  "consecutive_quiet_successful_cycles": 0,
  "interval_seconds": 900,
  "age_days": 7,
  "quiet_period_seconds": 7200,
  "per_source": {
    "beads_ready":     {"status": "ok", "known_items": ["docr-aaaa", "docr-bbbb"], "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "in_progress":     {"status": "ok", "known_items": ["docr-cccc"],              "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "prs_authored":    {"status": "ok", "known_items": ["mslshao/docr#10484"],     "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "review_requests": {"status": "ok", "known_items": [],                         "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
    "prs_reviewing":   {"status": "ok", "known_items": {"mslshao/docr#10601": "2026-07-09T20:58:00Z"},
                        "holds": {"mslshao/docr#10601": {"last_author_activity_at": "2026-07-09T20:41:00Z", "opened_at": "2026-07-09T19:36:00Z",
                                                         "author_events": 11, "fired": false, "fired_at": null, "fired_via": null,
                                                         "noted_kinds": [], "pr": {"repository": "mslshao/docr", "number": 10601, "title": "...", "url": "..."}}},
                        "last_success_at": "2026-07-09T21:15:00Z", "error_detail": null},
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
- `per_source.prs_reviewing.holds` is the quiet-period state, one record per PR with
  an open or recently-fired burst, keyed exactly like `known_items`:
  `last_author_activity_at` is the ONLY timer anchor (bot and self activity never
  write it); `fired` / `fired_at` / `fired_via` implement one-fire-per-burst and record
  WHICH path fired, so a wrong-path bug is visible in state; `opened_at` and
  `author_events` render the burst context in the Path B line. It rides the same
  error-carry-forward as `known_items` and is pruned with it, EXCEPT that an unfired
  hold survives up to 3 cycles of the key being absent from the gather result:
  `gh search prs` is eventually consistent and exits 0 on a lagging index, and
  pruning then would destroy a pending alert (the drop side of duplicate-over-drop).
  `absent_cycles` counts that grace, and the key's watermark is retained alongside the
  hold so a return is not misread as a first appearance; `unclassified: true` marks a
  hold whose latest advance the agent could not classify. When the grace runs out with
  the alert still pending, the burst FIRES on the way out rather than being dropped
  with its watermark (dropping both re-baselined the key silently on its return and
  lost every author event from the absent window), which is why the hold also carries
  `pr`, the identity the alert line needs when the row is gone. A hold with no
  `last_author_activity_at` at all has nothing to describe, so it prunes silently
  instead of emitting a phantom alert. `noted_kinds` are signals seen in the burst
  that did not qualify as explicit, rendered in its alert;
  `suppressed_explicit_kinds` records an explicit signal that one-fire-per-burst
  suppressed, so that drop is visible in state.
- `quiet_period_seconds`: Path B's timer, persisted like `age_days`. A v1 blob has no
  `quiet_period_seconds` and no `holds`; every reader defaults them, so it upgrades in
  place on the next cycle with no migration.
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
bash ~/.claude/scratch/overwatch-mutation-check.sh         # after any fire-policy change
python3 ~/.claude/scratch/overwatch-repair-probes.py       # the silence probes, repaired contract
python3 ~/.claude/skills/overwatch/live_check.py           # before shipping; local-safe
python3 ~/.claude/skills/overwatch/live_check.py --include-external
```

`overwatch-repair-probes.py` drives the real two-phase loop with an independently
written classifier (the reviewer's, in `overwatch_fixture_drive.py`) over the
scenarios that were silent before this pass: a bot-actor re-review request with and
without an in-window push, and a request that arrives after a burst has settled. Run
it alongside the mutation script after any change to the classification contract,
since that contract is agent-side and the fixture tier can only test the copy of it
that lives in `test_cycle.py`.

`test_cycle.py` passes on the first run after any change written alongside it, which
proves nothing on its own, so the mutation script is the actual evidence that the
fire-policy checks can fail: it reverts one guard at a time in a scratch COPY and
asserts the suite goes red. It carries 27 mutations as of 2026-08-12, one per guard
this policy rests on: bot activity refreshing the timer (both the classified and the
unclassified path), the interval clamp, the one-fire-per-burst suppression, the burst
boundary, explicit-over-settled precedence, catch-up absorption, hold pruning and its
absence grace, the skew clamp, watermark validation, the two-phase arm and print
ordering, degraded reporting, the request-suppression scope, and the push-adjacency
rule in the classification contract. Every mutation must print at least one FAIL and
zero tracebacks; a mutation that no longer applies means the code drifted and the
harness needs updating with it.

The last four (M21-M24) are BOUNDARY mutations, and they are a different class from
the rest: instead of deleting a guard they flip one comparison from `>=` to `>`, or
zero one arithmetic result. That class used to survive the suite untouched, because
every case crossed each threshold by hours and `burst_seconds` was only ever asserted
on hand-built fire dicts, never on one the code produced. Keep them boundary-shaped
when the code moves. `reset()` clearing `__pycache__` is load-bearing for exactly this
class: a one-byte source edit keeps the size stable enough that CPython will reuse the
previous mutation's cached bytecode within the same mtime second, which silently
attributed three different mutations to one check on the run that added them.

The default `live_check.py` run is safe: it creates and deletes two throwaway beads,
and forces a real `gh` auth failure with a bogus token (no external state touched) to
prove the error path against the live binary. It also covers the two fire-policy
surfaces no fixture can reach, since `test_cycle.py` stubs `load_state` and drives
`plan_cycle` in process:

- **The live watermark.** `_reviewing_rows` reads `updatedAt` with a `""` default, so
  if that projection ever changes, every watermark becomes empty, `_advanced` reads
  every PR as unchanged, and the watcher goes silent while still reporting `ok`. The
  check asserts every live row parses and yields a `repo#number` key, and says so
  explicitly when the live result is empty rather than banking a vacuous pass.
- **The state round trip and the real CLI.** One Path A cycle is replayed end to end
  through `python3 cycle.py` as a subprocess against a real throwaway bead: the nested
  `holds` map must survive `bd update --notes` plus `bd show --json` in both
  directions, phase 2 must not arm a second chain, and the unpaired flags and a
  list-shaped `--reviewing-file` must exit 2 instead of raising. It stays deterministic
  because phase 2 replays a frozen gather file and `--now` pins the clock; the
  classified record comes from the fixture tier's own reduction over #11539, so there
  is one copy of that ground truth. Note the ordering it depends on: payload-shape
  validation sits inside `plan_cycle`, downstream of the double-fire guard, so those
  rejection checks run before the plan blob is persisted (production never collides
  with this, because phase 1 persists nothing).

The `--include-external` tier covers the outward-facing round-trips that must be
agent-run (they push a branch / notify watchers), not silently scripted:

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
- **Two pre-existing spec-vs-code gaps, found 2026-08-12 and deliberately left alone**
  (fixing either changes behavior beyond the fire-policy change that surfaced them):
  the `--interval` persistence promised in Argument parsing does not happen, because
  the override passed to `interval_for` is always `args.interval` and never the
  persisted `interval_seconds`, so a persisted override is inert on a later bare
  wakeup. (`plan_cycle` used to compute such an override into a local and never read
  it; the local was deleted 2026-08-12, which changes nothing about the gap and only
  stops the code from reading as though the persistence were wired.) Second gap: the
  `writer_session` / `writer_ts` single-writer
  lock described in Preflight step 2 is not written by `cycle.py` at all, so the
  multi-session guard is documented but not enforced.
- **A scoped watch does not scope detection, only the auto-review action.** The
  "second, scoped watch" pattern (Preflight step 2) filters WHICH PRs `--auto-review`
  can post to, but `prs_reviewing`/`review_requests`/etc. still classify every PR in
  the user's queue regardless of the scope glob. A fast-moving, unrelated PR stack
  can cost a full per-PR classification pass every cycle with zero relevance to the
  watch's actual scope (observed 2026-08-18, `docr-9ayhr`: 4 consecutive rounds on a
  6-PR knowledge-graph stack while scoped to `src/python/mx2/ruleseng/**`). Fix would
  filter `prs_reviewing`/`review_requests` gather results by the scope glob (changed
  files) before candidates are even built, not just before auto-review acts on them.
  Tracked: `docr-4aym0`.
- **A tooling restack delays the settle.** Pushes count as author
  activity, so they can start or refresh a burst. A push-only burst is therefore NOT
  silent: it has nothing explicit, so it produces exactly one settled alert (and the
  `👀` line is suppressed for the key while it does, so that alert is the only
  notification). The cost lands the other way: a bot-driven Graphite restack
  force-pushes with a human `committer.name`, which reads as author activity,
  refreshes the timer, and pushes the settle out by up to a quiet period. Bounded by
  restack frequency; dropping pushes from the signal set removes the class entirely
  and changes none of the fixtures, at the cost of silence on a genuinely
  comment-free push burst.
- **The user replying does not cancel an open hold.** If they answer the burst
  themselves while it is held, the settle alert still fires later, which is noise.
  Nothing in the classified record carries the user's own timestamps today (the drop
  in rule 2 is unconditional), and cancelling on self activity is a third path beyond
  the two the policy specifies, so it is unbuilt.
- **An explicit signal inside an already-fired burst is dropped, not delayed.** One
  fire per burst is ratified (Fixture 1), so #11539's `@mslshao ready for re-review`
  is never surfaced; the hold's `suppressed_explicit_kinds` is the only trace. The two
  ways out (a `max_burst_seconds` force-end, or re-firing on a not-yet-reported
  explicit kind) both add a second ping per burst and both change Fixture 1, so
  neither ships without the user re-ratifying the count.
- **A push-adjacent re-review request still arrives up to a quiet period late.** It
  cannot be told apart from `gt submit` tooling (SKILL.md rule 4), so it is held; the
  settle line names it, but it is not immediate.
- **An unclassifiable PR is loud every cycle, not once.** The `⚠️ could not read
  activity` line repeats at the poll cadence for as long as the classification keeps
  failing, exactly like a source-level failure line. That is the deliberate direction:
  a repeated visible warning over a silent hold. If it ever becomes real noise the fix
  is a backoff on the line, not on the warning.
- **A background-Bash-poll-primary design was evaluated and deferred.** For the
  bash-pollable sources (`bd`, `gh`), `memory/workflow.md` prescribes a
  `run_in_background` Bash poll as cheaper than ScheduleWakeup. It was deferred for
  v1 because Jira is MCP-only (not bash-pollable), so the loop needs an agent-side
  tick regardless, and a hybrid would reopen the single-writer state invariant and
  rest on an unverified session-resume-lifetime claim. Revisit trigger: measure
  actual ScheduleWakeup cost (Arize / Anthropic billing); if it runs materially
  above the ~3-turns/hour estimate in `workflow.md`, reconsider the hybrid.

## Principles

- **Read-only, and the one exception is opt-in and bounded.** overwatch reports; it never
  mutates code, PRs, or tickets. `--auto-review` is the sole exception: it can post an
  APPROVE, never a COMMENT or REQUEST_CHANGES, only on an explicitly scoped PR, only when
  the review is clean and `mx2-decision-maker` returns PROCEED, and only within a cap and
  a time window. It still never touches code. Anything unclear holds rather than posts,
  and a blocked outward write downgrades the rest of the loop to hold-only rather than
  being retried ([auto-review.md](auto-review.md)).
- **Quiet on no-op, loud on delta.** A healthy quiet cycle is silent. Any delta or
  source failure always surfaces.
- **Explicit signals ping; plain author activity waits.** On a PR the user already
  reviewed, being named (mention, reply on your thread, a deliberate re-review request)
  alerts immediately; ordinary author churn is held and reported once, after it
  settles. One burst is one alert.
- **Only humans move the quiet timer.** Bot and self activity advance the watermark and
  nothing else. A timer a CI bot can refresh is a timer that never expires.
- **Exit code over stdout.** A source's failure is its exit code, never an empty
  stdout. An errored source is never mistaken for a quiet one.
- **A read that failed is a delta.** The rule above applies at every granularity: a
  per-PR classification that could not be produced surfaces a line and resets the
  quiet counter, the same as an errored source. Nothing that could not be read is
  allowed to look like nothing to report.
- **Duplicate over drop.** State is persisted after output, so a crash re-alerts
  rather than silently marking an unseen alert as seen.
- **Idempotent re-entry.** Every `/overwatch` loads state from the bead and runs
  the same body; cold-start and hot continuation are indistinguishable.
