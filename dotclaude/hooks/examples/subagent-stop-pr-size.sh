#!/usr/bin/env bash
# SubagentStop hook: surface PR scope when a launch-implementer or mx2-executor
# subagent reports DONE on a worktree-based implementation.
#
# Why: catches plan-vs-execution drift. The launch-implementer.md self-flag
# (Scope Sanity Check) catches over-scoped PLANS at scope determination time.
# This hook catches the orthogonal failure: a reasonable plan that executed
# past threshold due to mid-flight refactor, test expansion, or scope discovery.
#
# Threshold: 250 lines added (vs trunk), aligning with the team's "Large" PR
# tagging convention of 100-499 LOC. Production-vs-test split is still surfaced
# separately so test-heavy PRs are obvious. Threshold is a conversation trigger,
# not a hard cap; the hook surfaces and blocks until the operator confirms.
#
# Behavior:
#   exit 0 = clean (under threshold, or unable to measure), parent continues
#   exit 2 = over threshold; stderr explains, parent acknowledges before
#            continuing
#
# Input contract: SubagentStop event, JSON on stdin with:
#   - transcript_path: path to subagent's transcript
#   - agent_type: should be launch-implementer or mx2-executor (matcher filters)
#   - cwd: subagent's working directory (may be the worktree)
#
# Registered in settings.json under SubagentStop with matcher
# "launch-implementer|mx2-executor".
#
# Test scenario: ~/.claude/scratch/subagent-stop-pr-size-test/README.md
# covers the four cases (over-threshold, wrong agent_type, no worktree,
# under-threshold) with a stub transcript and reproducible test worktree.
#
# Evidence: Faros AI Engineering Report 2026 pp 13-14 (PR size +51.3%, files/PR
# +59.7%); pp 18-19 (review tax: +441% median PR review, +480% lead time);
# 2026-05-08 PR-1a 1543-line incident that shipped without scope-flag.

set -uo pipefail

source "${HOME}/.claude/hooks/lib/log-event.sh"
hook_instrument "$(basename "$0")"

THRESHOLD=250

INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // empty')
SUBAGENT_CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

case "$AGENT_TYPE" in
  launch-implementer|mx2-executor) ;;
  *) exit 0 ;;
esac

WORKTREE=""
if [[ -n "$TRANSCRIPT" && -f "$TRANSCRIPT" ]]; then
  WORKTREE=$(jq -rs '
    .[] |
    select(.type == "user") |
    .message.content[]? |
    select(.type == "text") |
    .text
  ' "$TRANSCRIPT" 2>/dev/null | grep -oP "WORKTREE:\s*\K\S+" | head -1)
fi

if [[ -z "$WORKTREE" && -n "$SUBAGENT_CWD" && "$SUBAGENT_CWD" =~ /\.?launch-worktrees/ ]]; then
  WORKTREE="$SUBAGENT_CWD"
fi

if [[ -z "$WORKTREE" || ! -d "$WORKTREE" ]]; then
  exit 0
fi

# Resolve the worktree's branch parent. For stacked launches off a non-main
# base, diffing against `main` reports the full inherited downstack work as
# this subagent's output and fires the flag every cycle. Prefer the branch's
# upstream; fall back to main/master only when no upstream is set.
TRUNK=$(git -C "$WORKTREE" rev-parse --abbrev-ref "@{upstream}" 2>/dev/null || true)
if [[ -z "$TRUNK" ]]; then
  if git -C "$WORKTREE" rev-parse --verify main >/dev/null 2>&1; then
    TRUNK="main"
  elif git -C "$WORKTREE" rev-parse --verify master >/dev/null 2>&1; then
    TRUNK="master"
  else
    exit 0
  fi
fi

DIFF_STAT=$(git -C "$WORKTREE" diff "$TRUNK" --numstat 2>/dev/null)
if [[ -z "$DIFF_STAT" ]]; then
  exit 0
fi

read PROD_ADDED TEST_ADDED <<<"$(echo "$DIFF_STAT" | awk '
  $1 == "-" { next }
  {
    added = $1 + 0
    file = $3
    if (file ~ /(^|\/)test_/ || file ~ /_test\.[a-z]+$/ || file ~ /(^|\/)tests?\// || file ~ /\.test\.[a-z]+$/ || file ~ /(^|\/)__tests?__\//) {
      test_added += added
    } else {
      prod_added += added
    }
  }
  END { printf "%d %d\n", prod_added, test_added }
')"

TOTAL_ADDED=$((PROD_ADDED + TEST_ADDED))

if (( TOTAL_ADDED <= THRESHOLD )); then
  exit 0
fi

# One-shot guard against Stop-hook loops. When this hook fires with exit 2 the
# size flag is injected as user input; the agent's "Confirm" reply counts as a
# new turn, which re-fires Stop, which re-fires this hook. Without a guard the
# loop burns thousands of dollars of compute and never converges.
#
# Marker stores the size at the last flag fire. Re-fire only when the diff
# grows materially (>50 lines or >10%), so a confirmed size doesn't keep
# nagging but a genuine scope expansion still surfaces. Marker is per-worktree;
# worktree removal cleans it up naturally.
MARKER="${WORKTREE}/.subagent-stop-pr-size.flagged"
if [[ -f "$MARKER" ]]; then
  LAST_FLAGGED=$(cat "$MARKER" 2>/dev/null || echo "0")
  LAST_FLAGGED=${LAST_FLAGGED//[^0-9]/}
  LAST_FLAGGED=${LAST_FLAGGED:-0}
  GROWTH=$((TOTAL_ADDED - LAST_FLAGGED))
  GROWTH_PCT=0
  if (( LAST_FLAGGED > 0 )); then
    GROWTH_PCT=$(( (GROWTH * 100) / LAST_FLAGGED ))
  fi
  if (( GROWTH < 50 && GROWTH_PCT < 10 )); then
    exit 0
  fi
fi
echo "$TOTAL_ADDED" > "$MARKER"

FILE_BREAKDOWN=$(echo "$DIFF_STAT" | awk '
  $1 != "-" {
    printf "  %5d  %s\n", $1, $3
  }
' | sort -rn | head -10)

cat >&2 <<EOF
SCOPE FLAG: ${AGENT_TYPE} produced a PR exceeding the size threshold.

Threshold: ${THRESHOLD} lines added (vs trunk: ${TRUNK}).
Actual: ${TOTAL_ADDED} lines added (production: ${PROD_ADDED}, tests: ${TEST_ADDED}).
Worktree: ${WORKTREE}

Top files by lines added:
${FILE_BREAKDOWN}

Surface this to the operator BEFORE declaring the PR ready. The operator decides:
  - Confirm: proceed with the current scope (a tightly-scoped large PR is fine
    if it represents one coherent concern that cannot reasonably be split).
  - Split: restack into multiple PRs, each shipping independently.

Apply the canonical concern-split test: does the work map to multiple ratified
design decisions (e.g., two separate Jira tickets, two beads, or two acceptance
criteria), or to one? Multiple = split candidate.

Reference: Faros AI Engineering Report 2026 pp 13-14, 18-19 (PR size +51%,
review tax +441%); 2026-05-08 PR-1a 1543-line incident that shipped without
scope-flag and required a split-and-restack at /pr-intel time. Threshold is a
conversation trigger, not a hard cap.
EOF

exit 2
