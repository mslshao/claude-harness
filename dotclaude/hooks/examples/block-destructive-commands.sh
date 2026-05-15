#!/usr/bin/env bash
# PreToolUse hook: block destructive shell commands and accidental writes to system files.
# Exit 2 = block with explanation. Exit 0 = allow.
set -uo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")

if [[ "$TOOL" != "Bash" ]]; then
  exit 0
fi

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")

# --- Destructive filesystem operations ---

# rm -rf on broad targets (root, home, project root, worktrees)
if echo "$COMMAND" | grep -qP 'rm\s+.*-[a-zA-Z]*r[a-zA-Z]*\s+.*(\/\s*$|\*|~\/?\s*$|\/workspaces\/docr\/?(\s|$))'; then
  cat >&2 <<'EOF'
Blocked: rm -rf on a broad or root-level path. Scope the deletion to specific files/directories.
EOF
  exit 2
fi

# Bare rm -rf * or rm -rf / patterns
if echo "$COMMAND" | grep -qP 'rm\s+.*-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+(\/|\*|\.|~)(\s|$)'; then
  cat >&2 <<'EOF'
Blocked: potentially catastrophic rm command. Be more specific about what to delete.
EOF
  exit 2
fi

# chmod/chown on system directories
if echo "$COMMAND" | grep -qP '(chmod|chown)\s+.*\s+(\/etc|\/usr|\/bin|\/sbin|\/lib|\/var|\/sys|\/proc)'; then
  cat >&2 <<'EOF'
Blocked: chmod/chown on a system directory. Not safe to modify system file permissions.
EOF
  exit 2
fi

# Redirect writes to sensitive system files
if echo "$COMMAND" | grep -qP '>\s*(\/etc\/|\/usr\/|\/bin\/|\/sbin\/|~\/\.ssh\/|~\/\.bashrc|~\/\.profile|~\/\.zshrc)'; then
  cat >&2 <<'EOF'
Blocked: redirect write to a system or dotfile. Edit these files explicitly if needed.
EOF
  exit 2
fi

# Overwrite the Claude settings file via redirect (must go through Edit tool instead)
if echo "$COMMAND" | grep -qP '>\s*\/home\/vscode\/\.claude\/settings\.json'; then
  cat >&2 <<'EOF'
Blocked: direct overwrite of settings.json. Use the Edit tool to modify Claude settings.
EOF
  exit 2
fi

# Overwrite any hook script via redirect (hooks must be edited explicitly)
if echo "$COMMAND" | grep -qP '>\s*\/home\/vscode\/\.claude\/hooks\/'; then
  cat >&2 <<'EOF'
Blocked: direct overwrite of a hook file. Use the Edit/Write tool to modify hooks.
EOF
  exit 2
fi

# git push --force to main/master (force-with-lease is fine)
if echo "$COMMAND" | grep -qP 'git\s+push\s+.*--force(?!-with-lease)\s+.*\b(main|master)\b' || \
   echo "$COMMAND" | grep -qP 'git\s+push\s+.*\b(main|master)\b.*--force(?!-with-lease)'; then
  cat >&2 <<'EOF'
Blocked: force push to main/master without --force-with-lease. This can overwrite remote history.
Use --force-with-lease instead, or push to a feature branch.
EOF
  exit 2
fi

# git reset --hard without explicit confirmation pattern in the command
if echo "$COMMAND" | grep -qP 'git\s+reset\s+--hard\b'; then
  cat >&2 <<'EOF'
Blocked: git reset --hard discards uncommitted work. If this is intentional, ask the user to run it manually.
EOF
  exit 2
fi

# Dropping databases / truncating tables (not common but catch the obvious ones)
if echo "$COMMAND" | grep -qiP '(DROP\s+(DATABASE|TABLE|SCHEMA)|TRUNCATE\s+TABLE)'; then
  cat >&2 <<'EOF'
Blocked: destructive SQL statement. Ask the user to confirm and run this manually.
EOF
  exit 2
fi

exit 0
