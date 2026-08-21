#!/usr/bin/env bash
# Stop hook: run pants tlc on repo Python files THIS SESSION touched
# (via Edit/Write/MultiEdit in the transcript).
# Exit 0 = clean, Claude stops. Exit 2 = failures, Claude sees errors and continues.
#
# Session-scoping (2026-06-09 audit fix): the previous design validated the
# entire dirty working tree, so under 5 concurrent windows one window's WIP
# triggered pants runs (and blocks) on every other window's Stop. Now: parse
# the transcript for files this session actually edited; fall back to the
# dirty-tree scan only when the transcript is unavailable. Launch-worktree
# files are intentionally NOT scanned: they belong to agent sessions, and the
# old worktree leg never validated them anyway (absolute paths were discarded
# by the target filter; dead code removed).
set -uo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

INPUT=$(cat)

# Loop guard: when the harness re-invokes after a prior block, stand down
# rather than blocking forever on an unfixable failure (pre-existing broken
# test, env breakage). Each retry costs a 60-86s pants run; one block is signal,
# an unbounded loop is a hang.
if [[ "$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)" == "true" ]]; then
  echo "stop-validate: prior block unresolved; standing down (stop_hook_active)." >&2
  exit 0
fi

TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)

if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
  # Settle guard against a measured transcript-flush race (2026-08-19; full
  # writeup: bd recall gotcha:stop-hook-transcript-flush-race). The harness can
  # invoke this hook before the just-finished assistant message is flushed to
  # $TRANSCRIPT; two short reads bracketing a sleep tell us whether the file is
  # still growing under us.
  LINES_BEFORE=$(wc -l < "$TRANSCRIPT" 2>/dev/null || echo 0)
  sleep 0.1
  LINES_AFTER=$(wc -l < "$TRANSCRIPT" 2>/dev/null || echo 0)
  if [[ "$LINES_AFTER" != "$LINES_BEFORE" ]]; then
    sleep 0.1
  fi

  # Files this session edited via Edit/Write/MultiEdit/NotebookEdit. Bash-side
  # file mutations are not captured; accepted tradeoff vs cross-window blocking.
  ALL_FILES=$(jq -r '
    select(.type=="assistant") | .message.content[]?
    | select(.type=="tool_use" and (.name=="Edit" or .name=="Write" or .name=="MultiEdit" or .name=="NotebookEdit"))
    | .input.file_path // empty' "$TRANSCRIPT" 2>/dev/null \
    | grep '^/workspaces/main/' | grep '\.py$' | sed 's|^/workspaces/main/||' | sort -u || true)
else
  # Fallback: transcript unavailable - scan the dirty tree (old behavior).
  CHANGED_FILES=$(cd /workspaces/main && git diff --name-only HEAD --diff-filter=ACMR 2>/dev/null | grep '\.py$' || true)
  UNTRACKED=$(cd /workspaces/main && git ls-files --others --exclude-standard 2>/dev/null | grep '\.py$' || true)
  ALL_FILES=$(echo -e "${CHANGED_FILES}\n${UNTRACKED}" | sort -u | grep -v '^$' || true)
fi

# Nothing touched this session - no validation needed
if [[ -z "$ALL_FILES" ]]; then
  exit 0
fi

# Group targets by checkout root. EnterWorktree sessions edit files under
# .claude/worktrees/<name>/, which is a full git checkout with its own pants
# root; pants_ignore hides .claude/ from the main root, so those files must be
# validated from inside the worktree (running them from /workspaces/main dies
# on "Unmatched glob" before testing anything). .launch-worktrees/ and other
# .claude/ paths stay excluded: agent sessions own the former, the latter are
# not pants targets.
ROOTS=()
declare -A ROOT_TARGETS
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  root="/workspaces/main"
  rel="$f"
  if [[ "$f" == .claude/worktrees/*/* ]]; then
    name="${f#.claude/worktrees/}"
    name="${name%%/*}"
    root="/workspaces/main/.claude/worktrees/${name}"
    rel="${f#.claude/worktrees/${name}/}"
  elif [[ "$f" == .claude/* || "$f" == .launch-worktrees/* ]]; then
    continue
  fi
  if [[ -f "${root}/${rel}" ]]; then
    if [[ -z "${ROOT_TARGETS[$root]:-}" ]]; then
      ROOTS+=("$root")
    fi
    ROOT_TARGETS[$root]="${ROOT_TARGETS[$root]:-} ${rel}"
  fi
done <<< "$ALL_FILES"

if [[ ${#ROOTS[@]} -eq 0 ]]; then
  exit 0
fi

# Skip roots where everything this session touched is committed AND pushed:
# the hook guards the edited->pushed gap; past that, CI owns validation.
# Transcripts span compaction, so stale long-shipped edits otherwise
# re-validate on every Stop (false-fired 2026-07-20 on es-upldr-bulkerror).
# Roots with no upstream always validate (rev-parse gate), since @{u} errors
# would otherwise read as "nothing unpushed" and wrongly skip.
LIVE_ROOTS=()
for root in "${ROOTS[@]}"; do
  if git -C "$root" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1 \
     && [[ -z "$(git -C "$root" status --porcelain -- ${ROOT_TARGETS[$root]} 2>/dev/null)" ]] \
     && [[ -z "$(git -C "$root" rev-list '@{u}..HEAD' 2>/dev/null)" ]]; then
    continue
  fi
  LIVE_ROOTS+=("$root")
done
if [[ ${#LIVE_ROOTS[@]} -eq 0 ]]; then
  exit 0
fi

# Run pants tlc (test, lint, check) per checkout root
FAILED=0
FAIL_REPORT=""
for root in "${LIVE_ROOTS[@]}"; do
  TLC_OUTPUT=$(cd "$root" && pants tlc ${ROOT_TARGETS[$root]} 2>&1)
  if [[ $? -ne 0 ]]; then
    # Lock contention is not a validation result; don't block on it.
    if echo "$TLC_OUTPUT" | grep -q "Another pants invocation is running"; then
      echo "stop-validate: pants lock held by another session for ${root}; skipping (not a failure)." >&2
      continue
    fi
    FAILED=1
    FAIL_REPORT+="Root: ${root}
Files checked:${ROOT_TARGETS[$root]}

--- pants tlc output (last 60 lines) ---
$(echo "$TLC_OUTPUT" | tail -60)

"
  fi
done

if [[ $FAILED -eq 0 ]]; then
  # Clean - let Claude stop
  exit 0
fi

# Feed failures back to Claude via stderr (exit 2 = blocking, one retry max via
# the stop_hook_active guard above)
cat >&2 <<EOF
pants tlc failed on files this session touched. Fix what YOUR changes broke;
if a failure pre-dates your change (verify), note it and finish.

$FAIL_REPORT
EOF

exit 2
