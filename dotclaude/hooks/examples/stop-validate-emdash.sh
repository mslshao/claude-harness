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
# Why block-and-retry, not auto-fix: block-em-dash.sh auto-replaces em-dashes on TOOL
# inputs via PreToolUse updatedInput. Stop hooks have no equivalent (no updatedInput /
# updatedOutput field), so an already-emitted assistant message cannot be rewritten in
# place. Block-and-retry (exit 2, Claude regenerates) is the ceiling for the chat
# surface, not a regression. Verified API-infeasible 2026-06-04 (aux-harness audit).
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

# Settle guard: the harness can invoke this hook before the just-finished assistant
# message is flushed to $TRANSCRIPT. Measured 2026-08-19 (session 5af1b094): a Stop
# event fired 67ms after a clean message was written, but "last assistant text"
# still resolved to the PRIOR message (with an em-dash) from 4 minutes earlier,
# because the just-finished message hadn't landed in the file yet at read time. The
# resulting block-and-retry then attached to the wrong (already-superseded) turn,
# producing an out-of-order re-emit with no way for the model to know it was stale.
# wc -l is cheap; two short reads bracketing a sleep tell us whether the file is
# still growing under us, and if so we give it one more window before extracting.
LINES_BEFORE=$(wc -l < "$TRANSCRIPT" 2>/dev/null || echo 0)
sleep 0.1
LINES_AFTER=$(wc -l < "$TRANSCRIPT" 2>/dev/null || echo 0)
if [[ "$LINES_AFTER" != "$LINES_BEFORE" ]]; then
  sleep 0.1
fi

# Extract the FINAL assistant text block. Scope is deliberately the last block, NOT a
# full-turn join: a Stop hook can only influence the message about to end the turn.
# Em-dashes in earlier assistant blocks of a multi-message (tool-using) turn are already
# emitted and unfixable, so flagging them produces an unsatisfiable block-retry (the
# turn ends only via the stop_hook_active loop-guard, after spamming warnings for text
# that cannot be changed). Contrast stop-validate-pr-intel.sh, which DOES join the full
# turn because it detects a structured render that may legitimately span blocks; that
# purpose differs from per-message prose hygiene. (aux-harness audit 2026-06-04: a
# full-turn join was tried here and reverted after it fired on already-sent text.)
TURN_TEXT=$(jq -rs '
  [.[] | select(.type == "assistant") | .message.content[]? | select(.type == "text") | .text]
  | last // ""
' "$TRANSCRIPT" 2>/dev/null)

if [[ -z "$TURN_TEXT" ]]; then
  exit 0
fi

# Strip fenced code blocks AND inline-code spans before scanning. Em-dashes inside
# ``` fences or `inline backticks` are tolerated because they are quotation of the
# rule, banned text, external content (e.g. a Jira ticket title), or the em-dash
# character itself being discussed, not prose connectors. Genuine prose em-dashes
# (outside any code span) still fire.
STRIPPED=$(echo "$TURN_TEXT" | awk '
  /^[[:space:]]*```/ { in_block = !in_block; next }
  !in_block { print }
' | sed 's/`[^`]*`//g')

if echo "$STRIPPED" | grep -q "$EMDASH"; then
  # Pre-compute corrected lines with the SAME default substitution block-em-dash.sh
  # applies on every auto-replace surface (spaced em-dash -> " - ", bare -> "-"). Stop
  # hooks cannot rewrite chat in place (no updatedOutput; verified 2026-06-04), so this
  # stays block-and-retry; the difference is the feedback now hands back a ready-made
  # fix, turning the retry into a near-verbatim re-emit instead of a re-derivation
  # (re-derivation is where re-slips happen). Lines come from TURN_TEXT (full, unstripped)
  # so the re-emit suggestion is complete; the rare em-dash-inside-inline-code line is
  # advisory only and the model reviews before re-emitting.
  SUGGESTION=$(echo "$TURN_TEXT" | grep -n "$EMDASH" \
    | sed "s/ ${EMDASH} / - /g; s/${EMDASH}/-/g" | head -10)
  cat >&2 <<EOF
Em-dash detected in chat output. Re-emit with the corrected lines below; the default
substitution is already applied (spaced em-dash to " - ", bare to "-"). Switch to a
colon, comma, paren, or sentence break where it reads better.

Corrected lines (re-emit these, rest of the turn unchanged):
$SUGGESTION

Stop hooks cannot auto-rewrite chat, so this is block-and-retry with a ready-made fix.
Per CLAUDE.md Writing Style rule; see bd memories correction:style:em-dash.
EOF
  exit 2
fi

exit 0
