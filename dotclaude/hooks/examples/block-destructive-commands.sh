#!/usr/bin/env bash
# PreToolUse(Bash) hook: personal complement to the repo Auto Mode safety floor
# (/workspaces/main/.claude/hooks/block-destructive-commands.sh, added in MX2-NNNNN).
#
# The repo floor already covers rm on TRULY-broad targets (/, ~, *, .., glob), git push --force to
# a protected branch, git reset --hard, and destructive SQL, with a quote-aware design that does not
# false-positive on prose. This hook adds ONLY the rules the floor does not cover:
#   1. chmod/chown on a system directory
#   2. redirect-write to a system file or sensitive dotfile
#   3. redirect-overwrite of the Claude settings.json or a hook script (must go via Edit/Write)
#   4. rm -rf of the project root /workspaces/main itself (the floor treats a specific path as a
#      scoped delete and allows it; nuking the whole checkout is not a scoped delete)
#
# It mirrors the floor's technique to avoid prose false-positives:
#   stripped : quoted substrings removed entirely, so a token survives only if it is a REAL
#              command and not a mention inside quoted prose (bd remember "...", git commit -m "...").
#   dequoted : quote characters removed but content kept, so a quoted target like chmod -R "/etc"
#              still exposes its path for matching.
# POSIX `grep -E` only (no -P), so no substring surprises like the old `rm\s+` matching "terrafo[rm]".
# Fails OPEN (exit 0) with a loud warning if jq is missing. Exit 2 = block, exit 0 = allow.
#
# History: this hook previously duplicated the floor's rm/git/SQL rules with a naive `grep -P` that
# substring-matched "rm" inside words like "terraform" and matched destructive keywords inside quoted
# prose. Those overlapping rules were removed 2026-06-06 in favor of the floor; see bd memory
# finding:dup-destructive-hook-2026-06-05.
set -uo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

if ! command -v jq >/dev/null 2>&1; then
  printf 'WARNING: personal destructive-command complement DISABLED: jq not found on PATH.\n' >&2
  exit 0
fi

input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || true)
[[ "$tool" == "Bash" ]] || exit 0
raw=$(printf '%s' "$input" | jq -r '.tool_input.command // empty' 2>/dev/null || true)
[[ -n "$raw" ]] || exit 0

stripped=$(printf '%s' "$raw" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g")
dequoted=${raw//\"/}
dequoted=${dequoted//\'/}

has() { printf '%s' "$1" | grep -Eq "$2"; }
block() { printf 'Blocked (personal floor): %s\n' "$1" >&2; exit 2; }

SYSDIR='(/etc|/usr|/bin|/sbin|/lib|/var|/sys|/proc)([[:space:]/]|$)'

# 1. chmod/chown on a system directory. Confirm a real chmod/chown in the stripped view, then a
#    system-dir argument in the same command segment (no shell separator between) in dequoted.
if has "$stripped" '(^|[^[:alnum:]_-])(chmod|chown)([[:space:]]|$)' \
  && has "$dequoted" "(^|[^[:alnum:]_-])(chmod|chown)([[:space:]]+[^;|&[:space:]]+)*[[:space:]]+${SYSDIR}"; then
  block "chmod/chown on a system directory. Not safe to modify system file permissions."
fi

# 2. redirect-write to a system file or sensitive dotfile. An unquoted '>' survives in stripped;
#    a '>' mentioned inside quoted prose does not.
if has "$stripped" '>[[:space:]]*(/etc/|/usr/|/bin/|/sbin/|~/\.ssh/|~/\.bashrc|~/\.profile|~/\.zshrc)'; then
  block "redirect write to a system file or sensitive dotfile. Edit it explicitly if needed."
fi

# 3. redirect-overwrite of Claude settings.json or a hook script (these must go through Edit/Write).
if has "$stripped" '>[[:space:]]*(~|/home/vscode)/\.claude/(settings\.json|hooks/)'; then
  block "direct overwrite of Claude settings.json or a hook file. Use the Edit/Write tool instead."
fi

# 4. rm -rf of the project root /workspaces/main itself (root only; deeper scoped paths like a
#    specific .launch-worktrees/<name> or a ~/.claude/scratch dir are legitimate cleanups and are
#    intentionally NOT matched). Gate on a real (unquoted) rm in the stripped view for prose safety,
#    then require a SINGLE command segment to carry both the recursive-rm and the bare repo-root
#    target together. Splitting on ;|& and newlines fixes the false positive where a
#    `cd /workspaces/main` (or `git -C /workspaces/main`) in a different segment supplied the root
#    token while the real rm target was a scoped scratch path.
if has "$stripped" '(^|[^[:alnum:]_])rm([[:space:]]|$)'; then
  while IFS= read -r _seg || [[ -n "$_seg" ]]; do
    if has "$_seg" '(^|[^[:alnum:]_])rm[[:space:]]+([^[:space:]]+[[:space:]]+)*-[^[:space:]]*[rR]' \
      && has "$_seg" '(^|[[:space:]])/workspaces/main/?([[:space:]]|$)'; then
      block "rm -rf of the project root (/workspaces/main). Scope it to a specific subdirectory."
    fi
  done < <(printf '%s' "$dequoted" | tr ';|&\n' '\n\n\n\n')
fi

exit 0
