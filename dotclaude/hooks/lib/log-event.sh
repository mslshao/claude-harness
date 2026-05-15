#!/usr/bin/env bash
# Shared hook logger. Source this at the top of any hook.
#
# Usage (one-liner):
#   source "${HOME}/.claude/hooks/lib/log-event.sh"
#   hook_instrument "$(basename "$0")"
#
# Appends one JSONL line per invocation to ~/.claude/logs/hooks.jsonl with:
#   ts, hook, outcome (allow|block|error), exit, duration_ms
#
# Exit conventions (per Claude Code hook protocol):
#   0  -> allow
#   2  -> block (intentional intervention)
#   *  -> error (unintentional, likely a broken hook)

_HOOK_LOG_FILE="${HOME}/.claude/logs/hooks.jsonl"
_HOOK_NAME=""
_HOOK_START_EPOCH_MS=""

_hook_now_ms() {
  date -u +%s%3N 2>/dev/null || echo "$(date -u +%s)000"
}

_hook_now_iso() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

_log_hook_end() {
  local exit_code="${1:-0}"
  local end_ms
  end_ms=$(_hook_now_ms)
  local duration_ms=$(( end_ms - ${_HOOK_START_EPOCH_MS:-$end_ms} ))
  local outcome
  case "$exit_code" in
    0) outcome="allow" ;;
    2) outcome="block" ;;
    *) outcome="error" ;;
  esac
  mkdir -p "$(dirname "$_HOOK_LOG_FILE")" 2>/dev/null || true
  printf '{"ts":"%s","hook":"%s","outcome":"%s","exit":%d,"duration_ms":%d}\n' \
    "$(_hook_now_iso)" "$_HOOK_NAME" "$outcome" "$exit_code" "$duration_ms" \
    >> "$_HOOK_LOG_FILE" 2>/dev/null || true
}

hook_instrument() {
  _HOOK_NAME="${1:-unknown}"
  _HOOK_START_EPOCH_MS=$(_hook_now_ms)
  trap '_log_hook_end $?' EXIT
}
