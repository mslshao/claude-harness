#!/usr/bin/env bash
# Pre/PostToolUse hook: block em-dashes in written files and API writes.
#
# Surfaces:
#   PostToolUse (Edit|Write): scans the file for em-dashes after write
#   PreToolUse (addCommentToJiraIssue): scans comment body before posting
#   PreToolUse (mcp__github__*): scans tool_input before posting to GitHub
#   PreToolUse (Bash): scans 'gh api' write commands and 'gh (pr|issue)
#                      (create|comment|review|edit)' subcommands for em-dashes
#                      in heredoc, --input/--body-file paths, or inline --body/-f body= values
#
# Em-dashes are banned in ALL output per CLAUDE.md Writing Style section.
# Use hyphens (-), commas, or parentheses instead.
set -euo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

# Em-dash character via hex escape to avoid the literal appearing in this file
EMDASH=$'\xe2\x80\x94'

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

case "$TOOL_NAME" in
  Edit|Write)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_result.file_path // empty')
    if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
      exit 0
    fi
    if grep -n "$EMDASH" "$FILE_PATH" > /tmp/emdash_hits 2>/dev/null && [[ -s /tmp/emdash_hits ]]; then
      HITS=$(head -5 /tmp/emdash_hits)
      rm -f /tmp/emdash_hits
      cat >&2 <<EOF
Em-dash detected in $FILE_PATH. Replace with hyphens, commas, or parentheses.

$HITS
EOF
      exit 2
    fi
    rm -f /tmp/emdash_hits
    ;;

  mcp__atlassian__addCommentToJiraIssue)
    BODY=$(echo "$INPUT" | jq -r '.tool_input.commentBody // empty')
    if [[ -z "$BODY" ]]; then
      exit 0
    fi
    if echo "$BODY" | grep -q "$EMDASH"; then
      cat >&2 <<EOF
BLOCKED: Em-dash detected in Jira comment body. Replace with hyphens, commas, or parentheses before posting.
EOF
      exit 2
    fi
    ;;

  mcp__github__add_issue_comment|\
  mcp__github__add_comment_to_pending_review|\
  mcp__github__add_reply_to_pull_request_comment|\
  mcp__github__create_pull_request|\
  mcp__github__update_pull_request|\
  mcp__github__pull_request_review_write|\
  mcp__github__issue_write)
    PAYLOAD=$(echo "$INPUT" | jq -r '.tool_input | tostring')
    if echo "$PAYLOAD" | grep -q "$EMDASH"; then
      cat >&2 <<EOF
BLOCKED: Em-dash detected in GitHub MCP call. Replace with hyphens, commas, or parentheses before posting.
EOF
      exit 2
    fi
    ;;

  Bash)
    COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
    if [[ -z "$COMMAND" ]]; then
      exit 0
    fi

    # Two gated surfaces on the Bash tool:
    #   (1) 'gh api' with a writer-shape signal (-X POST/PUT/PATCH/DELETE, --input, -f body=, heredoc)
    #   (2) 'gh (pr|issue) (create|comment|review|edit)' - always a write, no shape gate needed
    # Negative lookbehind (?<![\x22\x27\x60]) excludes gh tokens inside quoted
    # strings or backticks, e.g. a local CLI invocation whose body contains an
    # example "gh pr edit ..." for the operator to copy-paste. Without this
    # anchor, the hook false-positives on non-gh writers.
    IS_TARGETED=false
    if echo "$COMMAND" | grep -qP '(?<![\x22\x27\x60])gh\s+api\s'; then
      if echo "$COMMAND" | grep -qP '(-X\s+(POST|PUT|PATCH|DELETE)|--method\s+(POST|PUT|PATCH|DELETE)|--input\s|-f\s+body=|<<)'; then
        IS_TARGETED=true
      fi
    fi
    if echo "$COMMAND" | grep -qP '(?<![\x22\x27\x60])gh\s+(pr|issue)\s+(create|comment|review|edit)\b'; then
      IS_TARGETED=true
    fi
    if [[ "$IS_TARGETED" != "true" ]]; then
      exit 0
    fi

    BLOCKED_FROM=""
    SOURCE_TEXT="$COMMAND"

    # Raw-grep the command string. Catches heredoc bodies, -f body=..., --body "...", inline args.
    if echo "$COMMAND" | grep -q "$EMDASH"; then
      BLOCKED_FROM="command"
    fi

    # If command references a payload file via --input or --body-file, scan that file too.
    # Common patterns:
    #   cat > /tmp/foo.json <<EOF ... EOF; gh api --input /tmp/foo.json
    #   Write /tmp/pr-body.md (via Edit tool); gh pr create --body-file /tmp/pr-body.md
    if [[ -z "$BLOCKED_FROM" ]]; then
      for FLAG in '--input' '--body-file'; do
        FILE_PATH=$(echo "$COMMAND" | grep -oP -- "${FLAG}\s+\K[^\s]+" 2>/dev/null | head -1 || true)
        if [[ -n "$FILE_PATH" && "$FILE_PATH" != "-" && -f "$FILE_PATH" && -r "$FILE_PATH" ]]; then
          if grep -q "$EMDASH" "$FILE_PATH" 2>/dev/null; then
            BLOCKED_FROM="${FLAG} file $FILE_PATH"
            SOURCE_TEXT=$(cat "$FILE_PATH")
            break
          fi
        fi
      done
    fi

    if [[ -n "$BLOCKED_FROM" ]]; then
      # Show ~20 chars of context on each side of the match; never leak the full payload (PII guard).
      CONTEXT=$(echo "$SOURCE_TEXT" | grep -oP ".{0,20}${EMDASH}.{0,20}" 2>/dev/null | head -1 || true)
      cat >&2 <<EOF
BLOCKED: Em-dash detected in gh command (${BLOCKED_FROM}). Replace with hyphens, commas, or parentheses before posting.

Context: ...${CONTEXT}...
EOF
      exit 2
    fi
    ;;
esac

exit 0
