#!/usr/bin/env bash
# Stop hook: scan the current turn's assistant chat output for em-dashes (U+2014).
#
# Why: block-em-dash.sh covers Edit/Write, Bash gh writers, Jira/GitHub MCP, but NOT
# chat-only output (no tool call). Recurring rule violations land in chat output where
# no hook fires. This Stop hook closes that gap by scanning the transcript at end of turn.
#
# Behavior:
#   exit 0 = clean OR loop-prevention triggered, turn ends
#   exit 2 = em-dash hit in current turn's assistant text; stderr feeds back to Claude
#           to fix and retry
#
# Loop prevention: respects $stop_hook_active from Claude Code. If we're already in
# a retry from this hook, allow the turn to end rather than loop forever.
#
# Code-block exemption: strips fenced ``` blocks before scanning so legitimate
# em-dash quotation (e.g. discussing the rule itself) doesn't false-positive.

set -uo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

EMDASH=$'\xe2\x80\x94'

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
STOP_HOOK_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false')

if [[ -z "$TRANSCRIPT" || ! -f "$TRANSCRIPT" ]]; then
  exit 0
fi

# Loop guard: if Claude Code is already retrying due to this hook, allow the turn.
if [[ "$STOP_HOOK_ACTIVE" == "true" ]]; then
  echo "stop-validate-emdash: stop_hook_active=true, allowing turn to prevent loop" >&2
  exit 0
fi

# Extract assistant text content since the last real user prompt.
# A "user" line with content type "tool_result" is NOT a real prompt; filter those out.
TURN_TEXT=$(jq -rs '
  . as $arr |
  ([range(0; length) | . as $i | $arr[$i] |
    (if .type == "user" and ([.message.content[]?.type] | any(. == "text"))
     then $i
     else null end)
  ] | map(select(. != null)) | last // 0) as $start_idx |
  $arr[($start_idx+1):] |
  map(select(.type == "assistant") | .message.content[]? | select(.type == "text") | .text) |
  join("\n")
' "$TRANSCRIPT" 2>/dev/null)

if [[ -z "$TURN_TEXT" ]]; then
  exit 0
fi

# Strip fenced code blocks before scanning. Em-dashes inside ``` are tolerated
# because they may be legitimate quotation of the rule, banned text, or external content.
STRIPPED=$(echo "$TURN_TEXT" | awk '
  /^```/ { in_block = !in_block; next }
  !in_block { print }
')

if echo "$STRIPPED" | grep -q "$EMDASH"; then
  CONTEXT=$(echo "$STRIPPED" | grep -oP ".{0,30}${EMDASH}.{0,30}" | head -3)
  cat >&2 <<EOF
Em-dash detected in chat output. Replace with hyphens, commas, parentheses, or a sentence break, then end the turn.

Context (up to 3 hits):
$CONTEXT

Per CLAUDE.md Writing Style rule. This is the structural enforcement that catches what slips past the deliberate scan. See bd memories correction:style:em-dash for history.
EOF
  exit 2
fi

exit 0
