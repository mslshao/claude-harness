#!/usr/bin/env bash
# SubagentStop hook: deterministic truncation detection for launch-phase agents
# (bd docr-pnx9, 2026-06-09).
#
# Why: subagent self-reports are unreliable and truncation detection was a
# judgment heuristic ("does the result end mid-thought?", CLAUDE.md Self-Review).
# The launch agent defs now require a terminal RESULT block (canonical source:
# ~/.claude/skills/launch/SKILL.md, summary key result-contract). This hook makes
# the absence of that block a structural signal instead of a vibe: a launch-phase
# agent whose final message lacks RESULT:/STATUS: is treated as truncated, and the
# orchestrator's recovery is to RESUME the same agent (SendMessage continuation,
# context intact) asking for the block plus any remaining work; cold re-dispatch
# is the fallback when the agent is no longer resumable.
#
# Sibling of subagent-stop-pr-size.sh (same event, orthogonal concern: that hook
# catches over-scope on DONE; this one catches missing/truncated completion).
#
# Behavior:
#   exit 0 = final message carries the RESULT contract (or transcript unreadable;
#            fail open)
#   exit 2 = no terminal RESULT block; stderr instructs the orchestrator to treat
#            the run as partial and resume the agent
#
# Registered in settings.json under SubagentStop with matcher
# "launch-implementer|launch-tester|launch-flex|mx2-executor".
set -uo pipefail

if [[ -f "${HOME}/.claude/hooks/lib/log-event.sh" ]]; then
  source "${HOME}/.claude/hooks/lib/log-event.sh" 2>/dev/null || true
  hook_instrument "$(basename "$0")" 2>/dev/null || true
fi

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // "unknown"')
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

[[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]] || exit 0

# Loop guard 1: if the harness marks this as a hook-driven retry, allow.
if [[ "$STOP_HOOK_ACTIVE" == "true" ]]; then
  exit 0
fi

# Loop guard 2 (belt and suspenders; 2026-06-10 incident, bd docr-t1nh): the
# first live run looped 30+ times because injected reminder text displaced the
# RESULT block as the LAST assistant text and stop_hook_active was not caught.
# Cap firings per transcript at 2, tracked via a scratch counter.
FIRE_DIR="${HOME}/.claude/scratch/result-contract-fires"
mkdir -p "$FIRE_DIR" 2>/dev/null || true
find "$FIRE_DIR" -type f -mmin +720 -delete 2>/dev/null || true
FIRE_FILE="${FIRE_DIR}/$(basename "$TRANSCRIPT" .jsonl)"
FIRES=$(cat "$FIRE_FILE" 2>/dev/null || echo 0)
if (( FIRES >= 2 )); then
  exit 0
fi

# Tail of assistant text in the subagent transcript. Join the LAST THREE
# assistant text blocks (not just the last one): harness-injected reminder /
# notification text can land as a trailing text block AFTER the agent's RESULT
# block, and matching only the literal last block false-flags a compliant agent
# (the 2026-06-10 loop). A genuinely truncated agent has no RESULT anywhere in
# its tail, so tail-3 keeps detection power.
FINAL_TEXT=$(jq -rs '
  [ .[] | select(.type == "assistant")
        | .message.content[]? | select(.type == "text") | .text ]
  | .[-3:] | join("\n")
' "$TRANSCRIPT" 2>/dev/null)

# Fail open if we cannot read the transcript shape.
[[ -n "$FINAL_TEXT" ]] || exit 0

if echo "$FINAL_TEXT" | grep -q 'RESULT:' && echo "$FINAL_TEXT" | grep -qE 'STATUS:[[:space:]]*(done|partial|blocked)'; then
  exit 0
fi

# Record the firing for loop guard 2 BEFORE flagging.
echo $(( FIRES + 1 )) > "$FIRE_FILE" 2>/dev/null || true

cat >&2 <<EOF
${AGENT_TYPE}: final message has no terminal RESULT block (RESULT: + STATUS: done|partial|blocked). Treat this run as TRUNCATED/partial, not complete, regardless of how confident the prose sounds.

Recovery (in order):
1. Resume the SAME agent via SendMessage (context intact): ask it to emit the RESULT block covering DONE / REMAINING / DISCOVERED / NEEDS-DECISION / VERIFICATION, and to finish any remaining work it can.
2. If the agent is no longer resumable, cold re-dispatch a new agent of the same type with a self-contained handoff: worktree path, what was already done (verify via git status/log, not the prior agent's prose), what remains, and the acceptance criteria.

Verify the worktree state yourself before declaring the work item done (CLAUDE.md Self-Review: subagent self-reports are not evidence; the diff is).

Contract source: ~/.claude/skills/launch/SKILL.md section 5.3b (bd docr-pnx9).
EOF
exit 2
