# Durable State: Event Log, Stage Events, Cold-Start, and Retry Protocols

The `/launch` skill uses a bead as its workflow event history. This provides Temporal-style
durable execution: if the orchestrator dies mid-execution, a cold-start re-invocation
reads the event log and resumes from the last verified checkpoint.

Mental model: bead = Temporal event history, agent = activity, orchestrator = workflow.

Two parallel mechanisms write to the bead's notes blob:
- **`[LAUNCH_STAGE ...]` entries** for pre-execution stages (Phases 1-3.6).
  Addressable by stage name + round number. Heavy payloads go to scratch
  files referenced by `path=`.
- **`[LAUNCH_EVENT ...]` entries** for execution (Phase 5). Temporal
  sequence of agent activity used by the retry loop.

Bead metadata stores single-value pointers: `launch_skill_version`,
`launch_branch`, `launch_worktree`.

Beads memories are NOT used for launch state. They're reserved for
cross-session knowledge (gotchas, decisions, architecture); launch
state pollutes that namespace.

---

## Schema Version + Stage Manifest

The skill stamps a schema version on the bead at launch start. Within a
version, stage names are fixed. Renames or additions require bumping
the version and updating this manifest in the same PR.

```
SKILL_SCHEMA_VERSION=v1
STAGES=[enrich, decompose, challenge, consult, synthesize, skeptic, gate]
```

Stage names are semantic (not numbered) so we can reorder or insert
phases later without renaming existing stages.

Stage order (used by cold-start to determine resume point):
1. enrich (Phase 1)
2. decompose (Phase 2)
3. challenge (Phase 3a)
4. consult (Phase 3b)
5. synthesize (Phase 3c)
6. skeptic (Phase 3.5)
7. gate (Phase 3.6)

Phases 4, 5, 6 are tracked via `[LAUNCH_EVENT ...]` entries (not stages)
because they're execution sequence, not addressable pre-execution
state.

---

## Event Log Schema

Every event is written via `bd update $LAUNCH_BEAD_ID --append-notes "..."`.

Format (one event per line):
```
[LAUNCH_EVENT type=<TYPE> <key=value>... ts=<ISO8601>]
```

Rules:
- Use `_` for spaces in values (no quotes)
- Timestamp (`ts=`) is always the last field
- Use `$(date -u +%Y-%m-%dT%H:%M:%SZ)` for timestamps

| type | Required fields | Written when |
|------|-----------------|--------------|
| `SESSION_STARTED` | `session=<id>` | Before any Phase 5 action |
| `WORKTREE_CREATED` | `branch=<name>` | After successful `git worktree add` |
| `PHASE_GATE_PASSED` | `phase=<A\|B\|C>` `gate_cmd=<cmd>` | After phase verification passes |
| `AGENT_SPAWNED` | `agent=<name>` `phase=<X>` `iteration=<N>` | **BEFORE** Agent tool call |
| `AGENT_COMPLETED` | `agent=<name>` `phase=<X>` `iteration=<N>` `artifacts=<files>` | After agent returns + verification passes |
| `AGENT_FAILED` | `agent=<name>` `phase=<X>` `iteration=<N>` `reason=<summary>` | After verification fails |
| `CIRCUIT_BREAKER` | `agent=<name>` `phase=<X>` | After 3rd consecutive failure for same agent+phase |

Store worktree metadata separately for fast lookup (not in event log):
```bash
bd update $LAUNCH_BEAD_ID --set-metadata launch_branch="$BRANCH"
bd update $LAUNCH_BEAD_ID --set-metadata launch_worktree="$WORKTREE_DIR"
```

### Example Event Sequence

```
[LAUNCH_EVENT type=SESSION_STARTED session=abc123 ts=2026-04-01T14:00:00Z]
[LAUNCH_EVENT type=WORKTREE_CREATED branch=launch-1743516780 ts=2026-04-01T14:00:05Z]
[LAUNCH_EVENT type=AGENT_SPAWNED agent=flex-infra phase=A iteration=1 ts=2026-04-01T14:00:10Z]
[LAUNCH_EVENT type=AGENT_COMPLETED agent=flex-infra phase=A iteration=1 artifacts=infra/processor/terragrunt.hcl ts=2026-04-01T14:10:00Z]
[LAUNCH_EVENT type=PHASE_GATE_PASSED phase=A gate_cmd=terragrunt_hcl-validate ts=2026-04-01T14:10:05Z]
[LAUNCH_EVENT type=AGENT_SPAWNED agent=implementer phase=B iteration=1 ts=2026-04-01T14:10:10Z]
[LAUNCH_EVENT type=AGENT_FAILED agent=implementer phase=B iteration=1 reason=pants_check_failed:2_type_errors ts=2026-04-01T14:25:00Z]
[LAUNCH_EVENT type=AGENT_SPAWNED agent=implementer phase=B iteration=2 ts=2026-04-01T14:25:05Z]
[LAUNCH_EVENT type=AGENT_COMPLETED agent=implementer phase=B iteration=2 artifacts=src/python/mx2/processor.py ts=2026-04-01T14:38:00Z]
```

---

## Pre-Execution Stage Events

Phases 1-3.6 write `[LAUNCH_STAGE ...]` entries to the same bead notes
blob. Format:

```
[LAUNCH_STAGE stage=<name> round=<N> status=<enum> ts=<ISO8601> <optional fields>]
```

Rules:
- `stage` is one of the names in the Stage Manifest above.
- `round` is the iteration counter starting at 0. ITERATE increments
  all stages' round counters together (round 1 means everything ran a
  second time after a gate-triggered ITERATE).
- `status` is per-stage (see status enums below).
- Optional `path=` field points to a scratch file when the payload
  exceeds the inline threshold (~2KB).

### Status Enums per Stage

| Stage | Status values | Optional fields |
|-------|---------------|-----------------|
| `enrich` | `loaded` / `failed` | `input_mode=<problem-framed\|mechanism-prescribed>`, `path=` for brief if >2KB |
| `decompose` | `drafted` / `failed` | `n_items=<count>`, `path=` for work-item list if >2KB |
| `challenge` | `done` / `failed` | `path=` for findings (always; findings are heavy) |
| `consult` | `done` / `failed` | `path=` for findings (always; findings are heavy) |
| `synthesize` | `confirmed` / `minor-adjustments` / `major-revisions` / `scrapped-and-rebuilt` | `path=` for converged plan (always) |
| `skeptic` | `no-concerns` / `concerns` / `unavailable` | `path=` if concerns (otherwise inline); `reason=` if unavailable |
| `gate` | `proceed` / `iterate` / `escalate-questions` / `escalate-route` / `low-confidence` | `verdict_reason=<short>` or `path=` for long reason; `weak_dimension=<enum>` if iterate; `suggested_next_skill=<skill>` if escalate-route |

### Example Pre-Execution Sequence (with ITERATE)

```
[LAUNCH_STAGE stage=enrich round=0 status=loaded input_mode=mechanism-prescribed ts=2026-05-21T10:00:00Z]
[LAUNCH_STAGE stage=decompose round=0 status=drafted n_items=4 path=~/.claude/scratch/launch-docr-xyz/decompose-0.md ts=2026-05-21T10:01:00Z]
[LAUNCH_STAGE stage=challenge round=0 status=done path=~/.claude/scratch/launch-docr-xyz/challenge-0.md ts=2026-05-21T10:03:00Z]
[LAUNCH_STAGE stage=consult round=0 status=done path=~/.claude/scratch/launch-docr-xyz/consult-0.md ts=2026-05-21T10:03:30Z]
[LAUNCH_STAGE stage=synthesize round=0 status=confirmed path=~/.claude/scratch/launch-docr-xyz/synthesize-0.md ts=2026-05-21T10:04:00Z]
[LAUNCH_STAGE stage=skeptic round=0 status=no-concerns ts=2026-05-21T10:05:00Z]
[LAUNCH_STAGE stage=gate round=0 status=iterate verdict_reason=mechanism-rubber-stamped weak_dimension=mechanism ts=2026-05-21T10:05:30Z]
[LAUNCH_STAGE stage=decompose round=1 status=drafted n_items=5 path=~/.claude/scratch/launch-docr-xyz/decompose-1.md ts=2026-05-21T10:07:00Z]
[LAUNCH_STAGE stage=challenge round=1 status=done path=~/.claude/scratch/launch-docr-xyz/challenge-1.md ts=2026-05-21T10:09:00Z]
[LAUNCH_STAGE stage=consult round=1 status=done path=~/.claude/scratch/launch-docr-xyz/consult-1.md ts=2026-05-21T10:09:30Z]
[LAUNCH_STAGE stage=synthesize round=1 status=major-revisions path=~/.claude/scratch/launch-docr-xyz/synthesize-1.md ts=2026-05-21T10:10:00Z]
[LAUNCH_STAGE stage=skeptic round=1 status=concerns path=~/.claude/scratch/launch-docr-xyz/skeptic-1.md ts=2026-05-21T10:11:00Z]
[LAUNCH_STAGE stage=gate round=1 status=proceed ts=2026-05-21T10:11:30Z]
```

After the final `gate:proceed`, Phase 4 user-approval fires; on
approval, Phase 5 starts and `[LAUNCH_EVENT ...]` entries begin.

### Inline vs Scratch Threshold

Practical rule: if the payload exceeds ~2KB, write it to scratch and
put the path in the entry. If it fits inline, store the relevant
fields directly in the entry (e.g., `verdict_reason=<short text>`).

Heavy payloads (always scratch): challenge findings, consult findings,
converged plan, work-item list when N>3.

Light payloads (always inline): INPUT_MODE enum, item count, gate
verdict, weak dimension, suggested next skill.

---

## Scratch File Convention

Heavy payloads referenced by `path=` in `[LAUNCH_STAGE ...]` entries
live under:

```
~/.claude/scratch/launch-<bead-id>/<stage>-<round>.md
```

Examples:
- `~/.claude/scratch/launch-docr-xyz/challenge-0.md`
- `~/.claude/scratch/launch-docr-xyz/synthesize-1.md`

Format: markdown for human-readable subagent outputs; the
orchestrator parses them as opaque blobs (they get fed back into the
next stage's prompt verbatim, not re-parsed).

Lifecycle:
- **Created** by the orchestrator when writing a `[LAUNCH_STAGE ...]`
  entry with `path=`.
- **Persisted** for the life of the codespace (machine-local; NOT
  Dolt-synced).
- **NOT cleaned up automatically.** "Leave as breadcrumbs" policy:
  scratch files remain after launch completion so retrospectives can
  diff between launches or re-feed prior outputs.

### Codespace Recycling

GitHub recycles inactive codespaces. If a codespace is recycled,
scratch files vanish but bead notes survive. Cold-start logic must
handle missing scratch files gracefully:

- Read the `[LAUNCH_STAGE ...]` entry. Status enum is intact (from
  notes).
- Attempt to read the scratch file at `path=`.
- If file missing: log "scratch payload lost for stage=<name>
  round=<N>; re-running stage". Re-spawn the relevant subagent to
  regenerate the payload.

This is best-effort durability across codespace lifetimes; full
durability requires re-running expensive stages on recycle but the
status sequence is preserved.

---

## Bead Acquisition

Before any `[LAUNCH_STAGE ...]` or `[LAUNCH_EVENT ...]` entry can be
written, a bead must exist as the event log target. The bead is
acquired at the END of Phase 1 (after `prompt-refiner` produces the
implementation brief), not at Phase 5 as in the prior design.

Acquisition timing:
- Earlier acquisition would create beads for inputs that fail
  validation (e.g., user provides no identifier and the skill bails).
- Later acquisition would leave Phase 1's expensive work (Jira fetch,
  domain matcher, prompt-refiner dispatch) undurable.
- Acquiring after the brief is produced is the right tradeoff: by
  then we know the input is valid AND the heavy Phase 1 work has
  already happened (durability matters from this point forward).

The first stage entry written after acquisition is `enrich:0:loaded`,
ALWAYS pointing at the brief via `path=` (write the brief to
`~/.claude/scratch/launch-$LAUNCH_BEAD_ID/brief.md` regardless of size;
`mkdir -p` the directory first, which also guarantees it exists for every
later stage's scratch write). A cold-start that finds `enrich:0:loaded`
recovers the brief from that path. After that, every subsequent stage
writes its own entry on completion.

Also write the schema version stamp on the bead at acquisition:
```bash
bd update "$LAUNCH_BEAD_ID" --set-metadata launch_skill_version=v1
```

Input shapes:
- **Jira-ticket launches**: find existing bead by ticket ID, or create one
  (bash below).
- **Bead-ID launches**: `$LAUNCH_BEAD_ID` is the input argument directly.
- **PR-URL launches**: search by PR number (`bd search "#<pr-number>"`);
  create if no hit, titled `[PR #<n>] <pr-title>`.
- **Free-text / Slack / Confluence / transcript launches**: nothing to search
  on; derive a short slug from the implementation brief's title and create
  directly: `bd create --title "<slug>" --type task --priority 2
  --description "Launch execution bead. Event log in notes."`.

```bash
# For Jira-ticket launches: find or create a bead
EXISTING=$(bd search "$TICKET_ID" --json 2>/dev/null | jq -r '.[0].id // ""')

if [ -n "$EXISTING" ]; then
  LAUNCH_BEAD_ID="$EXISTING"
else
  LAUNCH_BEAD_ID=$(bd create \
    --title "[$TICKET_ID] $JIRA_SUMMARY" \
    --type task \
    --priority 2 \
    --description "Launch execution bead for $TICKET_ID. Event log in notes." \
    2>/dev/null | grep -oE 'docr-[a-z0-9]+' | head -1)
fi

# For bead-ID launches: LAUNCH_BEAD_ID is the input argument directly

# Conflict check: surface if bead is already claimed by a different session.
# Claiming is optimistic locking (not a hard block) - last write wins in Dolt.
# This check is the human safety gate before committing to a worktree.
ASSIGNEE=$(bd show "$LAUNCH_BEAD_ID" --json 2>/dev/null | jq -r '.[] | .assignee // empty' | head -1)
# Do NOT use `bd config get user.name` for identity: when the key is unset it
# prints the literal "user.name (not set)" with exit 0, making SELF a garbage
# non-empty string that never matches and fires a false conflict on every
# cold-start resume of your own bead. Derive from the chain bd uses for --claim.
SELF="${BEADS_ACTOR:-$(git config user.name 2>/dev/null)}"
SELF="${SELF:-$USER}"  # mirror bd's full default chain: $BEADS_ACTOR, git user.name, $USER
if [ -n "$ASSIGNEE" ] && [ "$ASSIGNEE" != "$SELF" ]; then
  # Another session holds this bead. Surface options before proceeding:
  # (1) Resume: check bd show $LAUNCH_BEAD_ID for launch_branch metadata
  # (2) Take over: bd update $LAUNCH_BEAD_ID --claim (overwrites assignee)
  # (3) Abort: exit without creating worktree
  echo "⚠️  Conflict: $LAUNCH_BEAD_ID is claimed by $ASSIGNEE"
fi

# Claim for this session (idempotent if already ours)
bd update "$LAUNCH_BEAD_ID" --claim 2>/dev/null
```

---

## Cold-Start Protocol

Triggered when `/launch <bead-id>` is invoked and prior `[LAUNCH_STAGE ...]`
or `[LAUNCH_EVENT ...]` entries exist. The protocol has two cold-start
modes depending on which phase the prior execution reached:

- **Pre-Execution Cold-Start** (Phase 1-3.6): only `[LAUNCH_STAGE ...]`
  entries exist, no `[LAUNCH_EVENT ...]` yet. Resume by re-running
  the next stage in the manifest order with prior payloads loaded
  from scratch.
- **Execution Cold-Start** (Phase 5+): `[LAUNCH_EVENT ...]` entries
  exist (worktree was created, agents spawned). Resume the retry
  loop on the in-flight agent slot.

### Step 1: Read Notes Blob

```bash
NOTES=$(bd show "$LAUNCH_BEAD_ID" --json | jq -r '.[] | .notes // ""')
STAGES=$(echo "$NOTES" | grep '^\[LAUNCH_STAGE')
EVENTS=$(echo "$NOTES" | grep '^\[LAUNCH_EVENT')
SKILL_VERSION=$(bd show "$LAUNCH_BEAD_ID" --json | jq -r '.[] | .metadata.launch_skill_version // "v1"')
```

If both `$STAGES` and `$EVENTS` are empty: fresh execution. Proceed
to normal Phase 1.

If `$SKILL_VERSION` does not match the current skill schema version
in this file: refuse to resume; log "schema version mismatch (bead:
$SKILL_VERSION, current: v1); restart this launch from scratch" and
exit. Schema changes that break resume should be rare and explicit.

### Step 2: Determine Cold-Start Mode

- If `$EVENTS` is non-empty: Execution Cold-Start (proceed to Step 4).
- Else if `$STAGES` is non-empty: Pre-Execution Cold-Start (proceed to
  Step 3).

### Step 3: Pre-Execution Cold-Start

Parse `$STAGES` to find the latest stage + round + status.

```bash
# Sort by ts to get chronological order; the last entry is the most recent state.
LATEST=$(echo "$STAGES" | tail -1)
```

Compute resume target:
- If latest is `gate round=N status=proceed`: skip to Phase 4 user-approval.
  Load the converged plan from `synthesize round=N path=...`.
- If latest is `gate round=N status=low-confidence`: same as proceed but
  surface low-confidence annotation in Phase 4 output.
- If latest is `gate round=N status=iterate weak_dimension=W`: resume at
  Phase 2 (decompose) round=N+1 with WEAK_DIMENSION=W modifier. Load
  prior work items from `decompose round=N path=...` so the iteration
  modifies them rather than starting fresh.
- If latest is `gate round=N status=escalate-questions`: surface the
  questions to the user. If the user has already answered (a
  user-answered marker exists), fold answers into refined scope and
  resume Phase 1 round=N+1. If not answered, re-prompt.
- If latest is `gate round=N status=escalate-route`: Phase 4 already
  surfaced this; no resume action; user should run the
  SUGGESTED_NEXT_SKILL.
- If latest is `skeptic round=N status=*`: resume at gate round=N.
  Load skeptic payload from path if needed.
- If latest is `synthesize round=N status=*`: resume at skeptic round=N.
- If latest is `consult round=N status=done` and `challenge round=N
  status=done` both exist: resume at synthesize round=N.
- If latest is `challenge round=N status=done` OR `consult round=N
  status=done` (only one): wait for the other? No - cold-start re-runs
  both in parallel. The completed one's payload is loaded from scratch;
  the other is re-dispatched.
- If latest is `decompose round=N status=drafted`: resume at challenge +
  consult round=N (parallel dispatch).
- If latest is `enrich round=0 status=loaded`: resume at decompose round=0.

For scratch payloads (`path=` entries): attempt to read the file. If
missing (codespace recycle), re-run the relevant stage instead of
loading the prior payload.

### Step 4: Execution Cold-Start (Phase 5+)

#### Step 4a: Reconstruct Position

Process `$EVENTS` in order to reconstruct orchestrator position:

- **`LAST_COMPLETED_PHASE`**: highest `phase=X` value in `PHASE_GATE_PASSED` events
- **`COMPLETED_AGENTS`**: set of `(agent, phase)` pairs that have `AGENT_COMPLETED` entries
- **`IN_FLIGHT_AGENTS`**: `AGENT_SPAWNED` entries with no matching `AGENT_COMPLETED` or `AGENT_FAILED` (same agent+phase+iteration)
- **`FAILED_ITERATIONS`**: count of `AGENT_FAILED` entries per `(agent, phase)`

#### Step 4b: Worktree Recovery

```bash
BRANCH=$(bd show "$LAUNCH_BEAD_ID" --json | jq -r '.[] | .metadata.launch_branch // ""')
SAVED_PATH=$(bd show "$LAUNCH_BEAD_ID" --json | jq -r '.[] | .metadata.launch_worktree // ""')

if [ -n "$SAVED_PATH" ] && git -C /workspaces/main worktree list | grep -q "$SAVED_PATH"; then
  WORKTREE_DIR="$SAVED_PATH"
  echo "Resumed worktree at $WORKTREE_DIR"
else
  # Re-create from branch - branch always exists in remote
  WORKTREE_BASE="/workspaces/main/.launch-worktrees"
  mkdir -p "$WORKTREE_BASE"
  WORKTREE_DIR="$WORKTREE_BASE/launch-$(date +%s)"
  git -C /workspaces/main worktree add "$WORKTREE_DIR" "$BRANCH" 2>&1
  bd update "$LAUNCH_BEAD_ID" --set-metadata launch_worktree="$WORKTREE_DIR"
  echo "Re-created worktree at $WORKTREE_DIR from branch $BRANCH"
fi
```

#### Step 4c: Handle In-Flight Agents

For each agent in `IN_FLIGHT_AGENTS`, treat it as failed on its last iteration:
- Increment `FAILED_ITERATIONS` for that `(agent, phase)` pair
- It will be re-spawned by the retry loop with appropriate handoff context

#### Step 4d: Resume Execution

- Skip all phases where `PHASE_GATE_PASSED` exists
- Skip all `(agent, phase)` pairs in `COMPLETED_AGENTS`
- Start at the first incomplete agent slot, using `FAILED_ITERATIONS` to determine
  the iteration number for the retry loop

Write a new `SESSION_STARTED` event to mark the resumption:
```bash
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_EVENT type=SESSION_STARTED session=$CLAUDE_SESSION_ID ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

#### Step 4e: Single-Writer Session Lock (check BEFORE any mutation)

Concurrent orchestrator sessions are the sharpest resumption hazard: a crashed
session resumed while a replacement session is already running the same launch
will double-execute agent slots and force-push competing branches over the
live stack (observed 2026-07 in a pilot of exactly this shape; reconciliation
required forensic diffing). The `SESSION_STARTED` event doubles as the lock:

1. BEFORE writing your own `SESSION_STARTED` and before ANY worktree, branch,
   or bead mutation, read the most recent `SESSION_STARTED` in the event log.
2. If its `session` is not this session AND any event in the log is newer
   than 30 minutes, the launch is potentially live elsewhere: do NOT resume.
   Append `[LAUNCH_EVENT type=SESSION_HOLD session=$CLAUDE_SESSION_ID ts=...]`,
   surface to the user ("another session appears to own this launch; last
   event <ts>; resume anyway?"), and stop.
3. If the log has been quiet for over 30 minutes, assume the prior session is
   dead: write your `SESSION_STARTED` (above) and proceed. During long waits
   (CI, reviews) re-append a `SESSION_STARTED` heartbeat so a genuinely live
   session is never mistaken for a dead one.
4. Never resolve a suspected double-writer by force-pushing over the other
   session's work: hold, reconcile from `git log` and PR state, then continue.

#### Unattended decision-point policy (`--gate=agent` runs)

Added 2026-07-17 (docr-mpgav; decision record docr-1vqfg). In an unattended
run there is no human to answer, so EVERY human-decision point resolves the
same way: **halt loudly, never wait, never loop, never auto-resume.**

The four decision points this covers:
1. **Phase 3.6 ESCALATE-QUESTIONS** (gate-prompts.md): no narrowing-question
   round; the questions fold into the halt report.
2. **Phase 4 approval**: covered by the agent-gate verdict contract
   (gate-prompts.md "Phase 4 Agent Approval Gate").
3. **Phase 5 escalation rows that say "Ask user"** (SKILL.md Escalation
   Protocol, e.g. external verification needed): halt instead of asking.
4. **Step 4e SESSION_HOLD** (above): step 2's "surface to the user ...
   resume anyway?" becomes a halt; auto-resume would recreate the exact
   double-writer incident this lock exists to prevent, and a silent hang is
   the walk-away failure mode nobody notices.

Halt loudly means, in order: (a) append the relevant event
(`SESSION_HOLD`, `AGENT_GATE_HALT`, or `UNATTENDED_ESCALATION`) to the bead
log; (b) `bd comment` the launch bead with the decision needed and the
evidence gathered so far; (c) send a PushNotification naming the bead and the
decision; (d) STOP all work on this node/launch. An orchestrating skill
(e.g. /campaign) treats the halt as node failure per its own whole-chain
policy. Resume is always an explicit human action, never a timer.

---

## Retry Loop Protocol

Applies to each agent slot in the current phase. Replaces the one-shot spawn model.

```
FOR EACH agent in current phase (respecting COMPLETED_AGENTS from event log):

  iteration = 1 + count(AGENT_FAILED events for this agent+phase in event log)

  IF iteration > 3:
    WRITE: [LAUNCH_EVENT type=CIRCUIT_BREAKER agent=$agent phase=$phase ts=...]
    ESCALATE to user:
      "Agent $agent in phase $phase has failed 3 times. Circuit breaker triggered.
       Failure summaries:
       1. [first AGENT_FAILED reason for this agent+phase]
       2. [second AGENT_FAILED reason]
       3. [third AGENT_FAILED reason]
       Please review the worktree at $WORKTREE_DIR and advise how to proceed."
    STOP execution (do not spawn Phase N+1)

  IF iteration == 1:
    spawn_prompt = standard agent prompt (no retry context)
  ELSE:
    spawn_prompt = standard agent prompt + RETRY_CONTEXT block (see below)
    Assemble RETRY_CONTEXT:
      # BASE_REF (docr-ib6nd): recover from bead metadata; on stacked launches
      # origin/HEAD would mis-attribute the entire parent stack as this node's.
      BASE_REF        = bd metadata launch_base_ref (default origin/HEAD)
      prior_commits   = run: git -C $WORKTREE log $BASE_REF..HEAD --oneline
      last_failure    = last AGENT_FAILED reason for this agent+phase from event log
      passed_files    = files from AGENT_COMPLETED entries for other agents in this phase
                        + any acceptance criteria already passing per verification output
      failure_output  = re-run the gate verification command, capture output (truncate to 500 chars)
      specific_gap    = orchestrator-synthesized 1-3 sentence directive translating
                        the failure into a focused action (e.g., "The test
                        test_invalid_email fails because validate_email in processor.py
                        does not raise ValidationError for empty string. Add that case.")

  # WRITE BEFORE SPAWN (Temporal pattern: pre-execution journal entry)
  bd update $LAUNCH_BEAD_ID --append-notes \
    "[LAUNCH_EVENT type=AGENT_SPAWNED agent=$agent phase=$phase iteration=$iteration ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"

  # Spawn the agent
  [Agent tool call with run_in_background: true]

  # Wait for agent completion (process standups while waiting per 5.4)

  # Run gate verification command from plan YAML gate_cmd field
  RESULT=$(run gate verification command)

  IF verification passes:
    # Collect artifact file paths from agent standups and worktree diff
    ARTIFACTS=$(git -C $WORKTREE diff "${LAUNCH_BASE_REF:-origin/HEAD}"..HEAD --name-only | tr '\n' ',')
    bd update $LAUNCH_BEAD_ID --append-notes \
      "[LAUNCH_EVENT type=AGENT_COMPLETED agent=$agent phase=$phase iteration=$iteration artifacts=$ARTIFACTS ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
    BREAK  # Done with this agent slot

  ELSE:
    SUMMARY=$(echo "$RESULT" | head -3 | tr ' ' '_' | tr '\n' ' ')
    bd update $LAUNCH_BEAD_ID --append-notes \
      "[LAUNCH_EVENT type=AGENT_FAILED agent=$agent phase=$phase iteration=$iteration reason=$SUMMARY ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
    CONTINUE  # Next iteration

# After ALL agent slots in phase complete:
bd update $LAUNCH_BEAD_ID --append-notes \
  "[LAUNCH_EVENT type=PHASE_GATE_PASSED phase=$phase gate_cmd=$(echo $GATE_CMD | tr ' ' '_') ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

---

## Structured Handoff Format (RETRY_CONTEXT Block)

Appended to the agent spawn prompt when `iteration >= 2`. The orchestrator fills in
all bracketed fields before spawning.

```markdown
## RETRY CONTEXT

You are on iteration {N} of this task. Your prior work exists in the worktree.
Do not start from scratch - build on what you already completed.

**Prior commits (what you already built):**
{output of: git -C $WORKTREE_DIR log $BASE_REF..HEAD --oneline, where BASE_REF
comes from the launch_base_ref bead metadata (default origin/HEAD)}

**What is already correct - do NOT modify these files:**
{comma-separated list of files whose acceptance criteria are already passing}

**Why verification failed:**
Command: {exact verification command from plan gate_cmd}
Output (truncated to 500 chars):
```
{verification output}
```

**Specific gap to fix:**
{orchestrator-synthesized 1-3 sentence directive. Example:
"The test test_invalid_email_raises_validation_error fails because validate_email
in processor.py returns None instead of raising ValidationError for empty string
input. Add a guard at the top of validate_email that raises ValidationError when
the input is empty or whitespace-only."}

**Your constraints:**
- Address ONLY the gap above. No refactoring, renaming, or reorganizing prior work.
- Branch: {BRANCH}. Do not create a new branch.
- Worktree: {WORKTREE_DIR}. All file operations use this path.
```

The "Specific gap to fix" is written by the orchestrator - it is not templated output.
The orchestrator reads the verification failure and translates it into a targeted
directive that names the specific file, function, and fix needed.
