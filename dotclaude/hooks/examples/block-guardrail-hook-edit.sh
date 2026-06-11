#!/usr/bin/env bash
# PreToolUse hook: two-tier gate on edits to guardrail/enforcement surfaces.
#
# Tier 1 (subagent => DENY): a subagent must never modify the guardrails that
# police it. permissionDecision "ask" is a NO-OP for subagent tool calls (they
# auto-accept with no prompt, verified by probe 2026-06-10, bd docr-pnx9), so
# subagent-originated edits to any gated surface are hard-denied. Discriminator:
# the PreToolUse payload carries `agent_type` ONLY for subagent calls
# (gotcha:claude-code-pretooluse-subagent-discriminator).
#
# Tier 2 (main loop => ASK): a skill running an auto-accept flow (e.g. the
# /compound accept gate) can ride a single blanket "y" over an Edit/Write that
# loosens a guardrail matcher. Emitting permissionDecision "ask" surfaces a
# per-change confirmation prompt that a chat-level blanket "y" cannot
# pre-satisfy; the user's answer is the unforgeable per-change confirmation.
#
# Scope: edits to ~/.claude/hooks/{block-*,stop-validate*,subagent-stop-*,lint-*}.sh
# (the matchers that block or validate; extended 2026-06-10 after
# subagent-stop-result-contract.sh slipped the original block-*/stop-validate*
# allowlist), plus ~/.claude/hooks/lib/* and ~/.claude/settings.json. Advisory
# hooks (post-edit-*, logging, session-start) are not gated. Loosen-vs-tighten is
# intentionally NOT classified: any reliable detector would be a brittle regex
# heuristic, and confirming a tightening edit costs one keystroke, so every edit
# to a guardrail surface is gated (the safe direction).
#
# New guardrail hooks must use one of the four gated name prefixes to be
# auto-covered. This hook gates itself (it matches block-*.sh).
#
# See bd memories correction:workflow:guardrail-self-edit-needs-explicit-auth.
set -euo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

case "$TOOL_NAME" in
  Edit | Write | MultiEdit) ;;
  *) exit 0 ;;
esac

# Actor discriminator (verified 2026-06-10 probe, bd docr-pnx9): the PreToolUse
# payload carries an `agent_type` key ONLY for subagent-originated tool calls;
# main-loop calls have no such key (they carry `effort` instead). session_id and
# transcript_path are identical for both, so they cannot discriminate. This is
# load-bearing: permissionDecision:"ask" is a NO-OP for subagents (they
# auto-accept with no prompt), so the gated branch below must hard-DENY a
# subagent edit, while the main loop keeps the per-change "ask".
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // empty')

FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[[ -z "$FILE_PATH" ]] && exit 0

# Gated surfaces (2026-06-09 audit closed two bypasses):
#   1. block-*.sh / stop-validate*.sh under ~/.claude/hooks (original scope)
#   2. ~/.claude/hooks/lib/* (decision logic the guards depend on)
#   3. ~/.claude/settings.json (where guardrail hooks are wired/unwired; an
#      Edit there can neuter enforcement without touching any hook file.
#      Gating every settings edit costs one keystroke; same loosen-vs-tighten
#      philosophy as the rest of this hook.)
HOOKS_DIR="${HOME}/.claude/hooks"
GATED=false
if [[ "$FILE_PATH" == "${HOME}/.claude/settings.json" ]]; then
  GATED=true
elif [[ "$FILE_PATH" == "${HOOKS_DIR}/lib/"* ]]; then
  GATED=true
elif [[ "$FILE_PATH" == "${HOOKS_DIR}/"* ]]; then
  BASENAME=$(basename "$FILE_PATH")
  # Enforcement-hook prefixes. subagent-stop-*.sh and lint-*.sh were added
  # 2026-06-10 (bd docr-pnx9): a launch subagent edited
  # subagent-stop-result-contract.sh to escape a retry loop and it slipped this
  # allowlist (matched neither block-* nor stop-validate*); only the
  # non-deterministic security classifier caught it. Any hook whose exit 2 / deny
  # blocks a tool call is an enforcement surface and belongs here.
  case "$BASENAME" in
    block-*.sh | stop-validate*.sh | subagent-stop-*.sh | lint-*.sh) GATED=true ;;
  esac
fi
[[ "$GATED" != "true" ]] && exit 0

BASENAME=$(basename "$FILE_PATH")

# Subagent-originated edit to an enforcement surface => HARD DENY. A subagent
# must never modify the guardrails that police it (2026-06-10 launch-flex
# incident: an agent under retry-loop pressure edited subagent-stop-result-contract.sh
# to escape enforcement). "ask" does not stop a subagent, so deny outright;
# legitimate guardrail changes are authored from the main loop.
if [[ -n "$AGENT_TYPE" ]]; then
  DENY_REASON="BLOCKED: subagent (agent_type=${AGENT_TYPE}) attempted to edit guardrail surface ${BASENAME}. Subagents may not modify enforcement hooks, guard library code, or settings.json wiring. If this change is genuinely needed, surface it to the orchestrator via your RESULT block (DISCOVERED / NEEDS-DECISION); the main loop authors guardrail changes, not the agent the guardrail polices. (bd docr-pnx9; gotcha:claude-code-pretooluse-ask-subagent-noop)"
  jq -nc --arg reason "$DENY_REASON" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    },
    systemMessage: $reason
  }'
  exit 0
fi

REASON="Guardrail-surface edit: ${BASENAME} is a blocking/validating hook, guard library code, or the settings.json wiring that enforces them. Editing it can loosen enforcement; this needs an explicit per-change confirmation and must not ride a skill-flow blanket accept. Confirm only if you intend to change this guardrail surface. (correction:workflow:guardrail-self-edit-needs-explicit-auth)"

jq -nc --arg reason "$REASON" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "ask",
    permissionDecisionReason: $reason
  },
  systemMessage: $reason
}'
exit 0
