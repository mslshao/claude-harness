# Durable State: Event Log, Cold-Start, and Retry Protocols

The `/launch` skill uses a bead as its workflow event history. This provides Temporal-style
durable execution: if the orchestrator dies mid-execution, a cold-start re-invocation
reads the event log and resumes from the last verified checkpoint.

Mental model: bead = Temporal event history, agent = activity, orchestrator = workflow.

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

## Bead Acquisition

Before Phase 5 can write events, a bead must exist as the event log target.

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
SELF=$(bd config get user.name 2>/dev/null || echo "")
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

Triggered when `/launch <bead-id>` is invoked and prior LAUNCH_EVENT entries exist.

### Step 1: Read Event Log

```bash
NOTES=$(bd show "$LAUNCH_BEAD_ID" --json | jq -r '.[] | .notes // ""')
EVENTS=$(echo "$NOTES" | grep '^\[LAUNCH_EVENT')
```

If `$EVENTS` is empty: this is a fresh execution. Proceed to normal Phase 5.

### Step 2: Parse State

Process events in order to reconstruct orchestrator position:

- **`LAST_COMPLETED_PHASE`**: highest `phase=X` value in `PHASE_GATE_PASSED` events
- **`COMPLETED_AGENTS`**: set of `(agent, phase)` pairs that have `AGENT_COMPLETED` entries
- **`IN_FLIGHT_AGENTS`**: `AGENT_SPAWNED` entries with no matching `AGENT_COMPLETED` or `AGENT_FAILED` (same agent+phase+iteration)
- **`FAILED_ITERATIONS`**: count of `AGENT_FAILED` entries per `(agent, phase)`

### Step 3: Worktree Recovery

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

### Step 4: Handle In-Flight Agents

For each agent in `IN_FLIGHT_AGENTS`, treat it as failed on its last iteration:
- Increment `FAILED_ITERATIONS` for that `(agent, phase)` pair
- It will be re-spawned by the retry loop with appropriate handoff context

### Step 5: Resume Execution

- Skip all phases where `PHASE_GATE_PASSED` exists
- Skip all `(agent, phase)` pairs in `COMPLETED_AGENTS`
- Start at the first incomplete agent slot, using `FAILED_ITERATIONS` to determine
  the iteration number for the retry loop

Write a new `SESSION_STARTED` event to mark the resumption:
```bash
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_EVENT type=SESSION_STARTED session=$CLAUDE_SESSION_ID ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

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
      prior_commits   = run: git -C $WORKTREE log origin/HEAD..HEAD --oneline
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
    ARTIFACTS=$(git -C $WORKTREE diff origin/HEAD..HEAD --name-only | tr '\n' ',')
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
{output of: git -C $WORKTREE_DIR log origin/HEAD..HEAD --oneline}

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
