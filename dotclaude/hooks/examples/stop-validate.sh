#!/usr/bin/env bash
# Stop hook: run pants tlc on Python files changed during this session.
# Exit 0 = clean, Claude stops. Exit 2 = failures, Claude sees errors and continues.
set -uo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

# Find Python files modified in the working tree (staged + unstaged)
CHANGED_FILES=$(cd /workspaces/main && git diff --name-only HEAD --diff-filter=ACMR 2>/dev/null | grep '\.py$' || true)

# Also check unstaged new files
UNTRACKED=$(cd /workspaces/main && git ls-files --others --exclude-standard 2>/dev/null | grep '\.py$' || true)

# Also scan active launch worktrees (agents write here during /launch)
WORKTREE_FILES=""
for wt in /workspaces/main/.launch-worktrees/*/; do
  [[ -d "$wt" ]] || continue
  WT_CHANGED=$(git -C "$wt" diff --name-only HEAD --diff-filter=ACMR 2>/dev/null | grep '\.py$' | sed "s|^|$wt|" || true)
  WT_UNTRACKED=$(git -C "$wt" ls-files --others --exclude-standard 2>/dev/null | grep '\.py$' | sed "s|^|$wt|" || true)
  WORKTREE_FILES=$(echo -e "${WORKTREE_FILES}\n${WT_CHANGED}\n${WT_UNTRACKED}")
done

ALL_FILES=$(echo -e "${CHANGED_FILES}\n${UNTRACKED}\n${WORKTREE_FILES}" | sort -u | grep -v '^$' || true)

# Nothing changed -no validation needed
if [[ -z "$ALL_FILES" ]]; then
  exit 0
fi

# Build the target list for pants
TARGETS=""
while IFS= read -r f; do
  if [[ -f "/workspaces/main/$f" ]]; then
    TARGETS="$TARGETS $f"
  fi
done <<< "$ALL_FILES"

if [[ -z "$TARGETS" ]]; then
  exit 0
fi

# Run pants tlc (test, lint, check) on changed files
TLC_OUTPUT=$(cd /workspaces/main && pants tlc $TARGETS 2>&1)
TLC_EXIT=$?

if [[ $TLC_EXIT -eq 0 ]]; then
  # Clean -let Claude stop
  exit 0
fi

# Failures -extract the last 60 lines (enough for error context, not the whole log)
TAIL=$(echo "$TLC_OUTPUT" | tail -60)

# Feed failures back to Claude via stderr (exit 2 = blocking)
cat >&2 <<EOF
pants tlc failed on changed files. Fix the issues below before finishing.

Files checked: $(echo "$ALL_FILES" | tr '\n' ' ')

--- pants tlc output (last 60 lines) ---
$TAIL
EOF

exit 2
