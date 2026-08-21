#!/usr/bin/env bash
# Pre/PostToolUse hook: enforce the no-em-dash rule on outbound artifacts.
#
# Two enforcement modes, split by surface:
#
#   AUTO-REPLACE (silent, via PreToolUse updatedInput): prose/comms surfaces where a
#     generic " <U+2014> " -> " - " / "<U+2014>" -> "-" substitution is always safe.
#       - .md file writes (Edit/Write content / new_string)
#       - Jira comment bodies (addCommentToJiraIssue.commentBody)
#       - GitHub MCP write payloads (PR/issue/review bodies, titles, etc.). DORMANT:
#         no github MCP server is configured (evaluated + rejected 2026-04-14, gh CLI
#         adopted; see memory/github-api.md); the case arm + settings matchers stay so
#         coverage activates automatically if a github server ever appears.
#       - gh/git commit writers on the Bash tool (inline command + referenced payload files)
#     The hook emits {hookSpecificOutput:{...,permissionDecision:"allow",updatedInput:<full
#     tool_input>}} and exits 0; the tool runs with the sanitized input, no retry prompt.
#
#   BLOCK (exit 2): source/config file writes (.py/.ts/.tf/.json/.sh/... anything that is
#     not .md). A U+2014 there could be an intentional string literal or test fixture, and a
#     silent rewrite would corrupt it, so the author fixes it by hand (use a unicode
#     escape such as \u2014 for an intentional literal).
#
# Chat-output em-dashes are handled separately by stop-validate-emdash.sh; Stop hooks cannot
# rewrite chat text, so that surface stays block-and-retry (the ceiling, not a regression).
#
# Em-dashes are banned in ALL output per CLAUDE.md Writing Style section.
set -euo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

# Em-dash character via hex escape to avoid the literal appearing in this file.
EMDASH=$'\xe2\x80\x94'

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
HOOK_EVENT=$(echo "$INPUT" | jq -r '.hook_event_name // empty')

# Emit a PreToolUse allow decision carrying the full rewritten tool_input on stdout.
# $1 must be the COMPLETE tool_input object (compact JSON), not a partial.
emit_allow_with_input() {
  jq -nc --argjson ti "$1" \
    '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "allow", updatedInput: $ti}}'
}

case "$TOOL_NAME" in
  Edit|Write)
    FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_result.file_path // empty')
    [[ -z "$FILE_PATH" ]] && exit 0

    if [[ "$HOOK_EVENT" == "PreToolUse" ]]; then
      # Combine the writable text fields: content (Write) and new_string (Edit).
      COMBINED=$(echo "$INPUT" | jq -r '(.tool_input.content // "") + "\n" + (.tool_input.new_string // "")')
      if ! printf '%s' "$COMBINED" | grep -q "$EMDASH"; then
        exit 0
      fi

      if [[ "$FILE_PATH" == *.md ]]; then
        # Prose surface: silently rewrite content and/or new_string before the write.
        UPDATED=$(echo "$INPUT" | jq -c --arg em "$EMDASH" '
          .tool_input
          | (if (.content?     // null | type) == "string" then .content     |= (gsub(" "+$em+" "; " - ") | gsub($em; "-")) else . end)
          | (if (.new_string?  // null | type) == "string" then .new_string  |= (gsub(" "+$em+" "; " - ") | gsub($em; "-")) else . end)
        ')
        emit_allow_with_input "$UPDATED"
        exit 0
      fi

      # Source/config file: block before write (carve-out from auto-replace).
      cat >&2 <<EOF
Em-dash detected in $FILE_PATH. Replace with hyphens, commas, or parentheses.
Auto-replace is intentionally disabled for non-.md files: a U+2014 here may be an
intentional string literal or test fixture. Fix it by hand. If the literal is genuinely
required (a dash counter, a lint check, a test fixture), the "\\u2014" escape does NOT
work: it normalizes to a real dash before this hook sees it. Build the character instead,
e.g. chr(0x2014) in Python or \\x{2014} in Perl.
EOF
      exit 2
    fi

    # PostToolUse safety net: the file is already written, so updatedInput is not
    # available. Advisory block if an em-dash slipped through a surface with no
    # PreToolUse coverage. (For .md the PreToolUse pass already cleaned it; for
    # non-.md the PreToolUse pass blocked the write, so this rarely fires.)
    # SCOPE TO WHAT THIS WRITE INTRODUCED, never the whole file. A whole-file grep
    # reports PRE-EXISTING em-dashes the author never touched, which is pure noise on
    # any file carrying legacy ones: measured ~20 consecutive fires on
    # .claude/commands/pr.md (2026-08-12) with ZERO true positives, every added line
    # clean. It also trains the reader to ignore the hook, which costs the real
    # positives too. Same unscoped-check defect stop-validate-emdash.sh had before
    # correction:hooks:stop-emdash-last-not-fulljoin-2026-06-04 narrowed it to the
    # final assistant block. Reading the written text also removes the need for the
    # per-invocation mktemp scratch this arm used to require.
    WRITTEN=$(echo "$INPUT" | jq -r '(.tool_input.content // "") + "\n" + (.tool_input.new_string // "")')
    if printf '%s' "$WRITTEN" | grep -q "$EMDASH"; then
      HITS=$(printf '%s' "$WRITTEN" | grep -n "$EMDASH" | head -5)
      cat >&2 <<EOF
Em-dash detected in content written to $FILE_PATH. Replace with hyphens, commas, or parentheses.
Line numbers below are relative to the written block, not to the file.

$HITS
EOF
      exit 2
    fi
    ;;

  mcp__atlassian__addCommentToJiraIssue)
    BODY=$(echo "$INPUT" | jq -r '.tool_input.commentBody // empty')
    if [[ -z "$BODY" ]]; then
      exit 0
    fi
    if echo "$BODY" | grep -q "$EMDASH"; then
      UPDATED=$(echo "$INPUT" | jq -c --arg em "$EMDASH" \
        '.tool_input | .commentBody |= (gsub(" "+$em+" "; " - ") | gsub($em; "-"))')
      emit_allow_with_input "$UPDATED"
    fi
    exit 0
    ;;

  mcp__atlassian__createConfluencePage|\
  mcp__atlassian__createJiraIssue|\
  mcp__atlassian__editJiraIssue|\
  mcp__github__add_issue_comment|\
  mcp__github__add_comment_to_pending_review|\
  mcp__github__add_reply_to_pull_request_comment|\
  mcp__github__create_pull_request|\
  mcp__github__update_pull_request|\
  mcp__github__pull_request_review_write|\
  mcp__github__issue_write)
    # NOTE: mcp__atlassian__updateConfluencePage is deliberately ABSENT from
    # this group: page updates re-emit full bodies that may carry COLLEAGUES'
    # em-dashes, and mass-rewriting their prose is a ratified non-goal
    # (memory/atlassian-mcp.md). Creates and Jira issue writes are
    # self-authored prose, so the walk is safe.
    if echo "$INPUT" | jq -r '.tool_input | tostring' | grep -q "$EMDASH"; then
      # Rewrite every string value in the payload. Non-prose fields (owner, repo,
      # branch refs, numbers) never carry em-dashes, so the walk is a no-op on them.
      UPDATED=$(echo "$INPUT" | jq -c --arg em "$EMDASH" \
        '.tool_input | walk(if type == "string" then (gsub(" "+$em+" "; " - ") | gsub($em; "-")) else . end)')
      emit_allow_with_input "$UPDATED"
    fi
    exit 0
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
    if echo "$COMMAND" | grep -qP '(?<![\x22\x27\x60])gh\s+(--repo\s+\S+\s+|-R\s+\S+\s+)?(pr|issue)\s+(create|comment|review|edit)\b'; then
      IS_TARGETED=true
    fi
    # git commit with a message source: -m, --message, -F, --file. Plain `git commit`
    # (no flags) opens $EDITOR and is not Claude's surface; --amend --no-edit reuses the
    # prior message and supplies no new text.
    # Tolerate intervening path/flag args: `git -C /workspaces/main commit -m ...`
    # is the actively-used (and allow-listed) form; adjacency-only matching let
    # it bypass the auto-replace (2026-06-09 audit).
    if echo "$COMMAND" | grep -qP '(?<![\x22\x27\x60])git\s+((-C|--git-dir(=|\s+)|--work-tree(=|\s+))\S*\s+\S*\s*)*commit\b' \
       || echo "$COMMAND" | grep -qP '(?<![\x22\x27\x60])git\s+-C\s+\S+\s+commit\b'; then
      if echo "$COMMAND" | grep -qP '(\s-m\s|\s--message[=\s]|\s-F\s|\s--file[=\s])'; then
        IS_TARGETED=true
      fi
    fi
    if [[ "$IS_TARGETED" != "true" ]]; then
      exit 0
    fi

    # Fix any referenced payload files in place. A file passed via --input/--body-file/-F/
    # --file in these commands is a commit message, PR body, or JSON API body (prose/JSON,
    # never source code), so the generic substitution is safe and honors auto-replace
    # end-to-end even when the body lives in a file rather than the command string.
    # Stays FLAG-ANCHORED on purpose, and is deliberately NOT widened to every
    # token that resolves to a file (2026-08-13). The sibling
    # block-personal-tier-vocab.sh WAS widened that way, correctly: it is a
    # read-only gate, so inspecting an extra file costs nothing. This hook
    # MUTATES with `sed -i`, and the safety argument above (a body file, prose or
    # JSON, never source code) holds only for a file named by one of these flags.
    # Scanning every mentioned path would silently rewrite any file a targeted
    # command happens to reference.
    #
    # Two real gaps this DOES close:
    #   `head -1` handled only the FIRST occurrence of each flag, so a repeated
    #   --input left the actual payload untouched.
    #   The `key=@FILE` form (gh -F body=@file) captured "body=@file", which
    #   fails the -f test, so -F was in the list but never actually resolved.
    # Same defect class as the vocab hook's, found the same day:
    # `bd memories gotcha:vocab-hook-scans-referenced-files-2026-08-13`.
    while IFS= read -r REF_RAW; do
      REF_FILE="${REF_RAW#*=}"   # key=VALUE -> VALUE   (gh -F body=@file)
      REF_FILE="${REF_FILE#@}"   # @FILE     -> FILE
      if [[ -n "$REF_FILE" && "$REF_FILE" != "-" && -f "$REF_FILE" && -w "$REF_FILE" ]]; then
        if grep -q "$EMDASH" "$REF_FILE" 2>/dev/null; then
          sed -i "s/ ${EMDASH} / - /g; s/${EMDASH}/-/g" "$REF_FILE"
        fi
      fi
    done < <(grep -oP -- '(--input|--body-file|-F|--file)(=|\s+)\K[^\s]+' <<< "$COMMAND" 2>/dev/null || true)

    # Rewrite the inline command string (heredoc bodies, -m/--message, --body, -f body=).
    if echo "$COMMAND" | grep -q "$EMDASH"; then
      UPDATED=$(echo "$INPUT" | jq -c --arg em "$EMDASH" \
        '.tool_input | .command |= (gsub(" "+$em+" "; " - ") | gsub($em; "-"))')
      emit_allow_with_input "$UPDATED"
    fi
    exit 0
    ;;
esac

exit 0
