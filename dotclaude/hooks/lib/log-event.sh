#!/usr/bin/env bash
# Shared hook logger. Source this at the top of any hook.
#
# Usage (one-liner):
#   source "${HOME}/.claude/hooks/lib/log-event.sh"
#   hook_instrument "$(basename "$0")"
#
# Appends one JSONL line per invocation to ~/.claude/logs/hooks.jsonl with:
#   ts, hook, outcome (allow|block|error), exit, duration_ms, session_id,
#   model, effort
# session_id comes from the CLAUDE_CODE_SESSION_ID env var the harness exports
# to hook processes (empty string when absent, e.g. manual runs); it enables
# per-session block-rate analysis (bd docr-bkiji ADAPTIVE v2 dependency).
# model (docr-jysu1, 2026-07-15): no env var carries the session model, so it
# is derived from the tail of the session transcript (assistant API entries
# carry "model":"<id>"); empty when the transcript is absent (manual runs,
# contexts with their own session ids). effort comes from the CLAUDE_EFFORT
# env var. Both enable per-model/effort block-rate comparison, the direct
# measure of weak-vs-strong orchestrator compliance.
#
# Exit conventions (per Claude Code hook protocol):
#   0  -> allow
#   2  -> block (intentional intervention)
#   *  -> error (unintentional, likely a broken hook)
#
# advisory (docr, 2026-08-17): outcome is derived purely from the exit code, so a
# hook that WARNS and exits 0 logged identically to one that found nothing. That
# made the whole advisory class unmeasurable: nudge-*, surface-*, and
# verify-bd-content-field-write.sh could not be shown to have ever fired, while
# still costing 20-30ms on every Bash call. A hook that emits guidance calls
# `hook_advisory` before exiting 0 and the row carries "advisory":true, which
# stats.py counts in its `warn` column.
#
# Opt-in on purpose. Auto-detecting stderr output would mean redirecting fd 2
# through a process substitution on every invocation, and at 300k+ invocations a
# week that per-fire subshell costs more than the signal is worth.

_HOOK_LOG_FILE="${HOME}/.claude/logs/hooks.jsonl"
_HOOK_NAME=""
_HOOK_START_EPOCH_MS=""
_HOOK_ADVISORY="false"

# Mark this invocation as having emitted advisory output. Call it on the branch
# that actually warns, not at the top of the hook.
hook_advisory() { _HOOK_ADVISORY="true"; }

_hook_now_ms() {
  date -u +%s%3N 2>/dev/null || echo "$(date -u +%s)000"
}

_hook_now_iso() {
  date -u +%Y-%m-%dT%H:%M:%SZ
}

# Session model, derived once per hook process from the transcript tail.
# Path convention: ~/.claude/projects/<cwd with / replaced by ->/<session>.jsonl
_HOOK_MODEL=""
_hook_model() {
  if [[ -z "$_HOOK_MODEL" && -n "${CLAUDE_CODE_SESSION_ID:-}" ]]; then
    local proj t
    proj=$(printf '%s' "${PWD:-}" | tr '/' '-')
    t="${HOME}/.claude/projects/${proj}/${CLAUDE_CODE_SESSION_ID}.jsonl"
    if [[ -f "$t" ]]; then
      _HOOK_MODEL=$(tail -n 40 "$t" 2>/dev/null | grep -oE '"model":"[^"]+"' | tail -1 | cut -d'"' -f4)
    fi
  fi
  printf '%s' "$_HOOK_MODEL"
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
  printf '{"ts":"%s","hook":"%s","outcome":"%s","exit":%d,"duration_ms":%d,"session_id":"%s","model":"%s","effort":"%s","advisory":%s}\n' \
    "$(_hook_now_iso)" "$_HOOK_NAME" "$outcome" "$exit_code" "$duration_ms" \
    "${CLAUDE_CODE_SESSION_ID:-}" "$(_hook_model)" "${CLAUDE_EFFORT:-}" \
    "${_HOOK_ADVISORY:-false}" \
    >> "$_HOOK_LOG_FILE" 2>/dev/null || true
}

hook_instrument() {
  _HOOK_NAME="${1:-unknown}"
  _HOOK_START_EPOCH_MS=$(_hook_now_ms)
  trap '_log_hook_end $?' EXIT
}
