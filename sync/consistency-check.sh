#!/usr/bin/env bash
# consistency-check.sh: catches the defect classes scrub-check.sh does not.
#
# scrub-check.sh answers "did we leak something proprietary". This answers
# "is the published content internally consistent": a dangling relative
# link (a file the mirror references but never shipped), or a hooks-count
# claim that drifted from the catalog it describes.
#
# Motivated 2026-08-19: a sync pass needed a 22-agent, ~2.7M-token exhaustive
# review to catch exactly these two defect classes by hand (a hook count
# miscounted twice in a row, three dangling relative links to files that
# were never added to the mirror). Both are mechanically checkable; this
# script is that mechanism, run cheaply on every sync instead of only when
# someone remembers to ask for a full review.
#
# Exit 0: clean. Exit 1: one or more findings. Exit 2: misconfiguration.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ ! -d "$REPO_ROOT/.git" ]; then
  echo "consistency-check: expected $REPO_ROOT to be a git repo root" >&2
  exit 2
fi

cd "$REPO_ROOT"

FINDINGS=0

echo "=== Dangling relative links ==="
# Every markdown [text](path) link whose target is NOT http(s). Resolve
# relative to the linking file's own directory (markdown link semantics),
# then check the target exists. Four exclusions, all high-confidence and
# established by the repo's own conventions, not links a mirror should ever
# resolve:
#   - private-tree pointers to /workspaces/main or the -workspaces-main
#     memory tree: the README documents these as intentional pointers into
#     the (unpublished) live tree, not repo-internal links.
#   - angle-bracket placeholders (<filename>.md, <topic-slug>-...): template
#     docs illustrating a naming convention, not a real target.
#   - a link inside a backtick code-span: documenting markdown SYNTAX itself
#     (e.g. `- [Title](file.md): one-line hook` inside a one-line code
#     example), not a real link. Detected by backtick PARITY before the
#     match position, not literal adjacency: the span often opens well
#     before the `[` (a whole example line wrapped in one code span).
#   - files whose own name matches *template*: their entire content is
#     illustrative placeholder rows by design (scaffolding/*-template.md).
while IFS=: read -r file line link; do
  target="${link%%#*}"
  [[ -z "$target" ]] && continue
  case "$target" in
    /workspaces/main/*|*-workspaces-main*) continue ;;
    *'<'*) continue ;;
  esac
  case "$(basename "$file")" in
    *template*) continue ;;
  esac
  # A code-span check needs the actual character OFFSET of the match, not a
  # reconstructed literal pattern ($link may contain glob/regex metachars
  # that make bash/grep pattern-matching on it unreliable). awk's index()
  # takes a plain string, no metachar risk, so do the offset lookup and the
  # backtick-parity count there in one pass.
  src_line=$(sed -n "${line}p" "$file")
  in_code_span=$(awk -v s="$src_line" -v needle="($link)" '
    BEGIN {
      pos = index(s, needle)
      if (pos == 0) { print "0"; exit }
      before = substr(s, 1, pos - 1)
      n = gsub(/`/, "", before)
      print (n % 2 == 1) ? "1" : "0"
    }')
  [[ "$in_code_span" == "1" ]] && continue
  dir="$(dirname "$file")"
  resolved="$dir/$target"
  if [[ ! -e "$resolved" ]]; then
    echo "  DANGLING: $file:$line -> $link (resolves to $resolved, does not exist)"
    FINDINGS=$((FINDINGS + 1))
  fi
done < <(
  grep -rnoE '\[[^]]*\]\(([^)h][^)]*|https?://[^)]*)\)' \
    --include='*.md' dotclaude/ project-tier/ patterns/ dispatch/ scaffolding/ 2>/dev/null \
  | grep -vE '\]\(https?://' \
  | sed -E 's/^([^:]+):([0-9]+):.*\(([^)]+)\)$/\1:\2:\3/'
)
[[ "$FINDINGS" -eq 0 ]] && echo "  none"

echo ""
echo "=== Hooks count consistency ==="
# Ground truth: distinct backtick-quoted hook filenames under #### headers in
# dotclaude/hooks/README.md, excluding the "Shared library" section (that's
# the one explicitly-separate shared-lib entry, not a hook).
HOOKS_FILE="dotclaude/hooks/README.md"
if [[ -f "$HOOKS_FILE" ]]; then
  # Anchor to #### HEADER lines only. A body-text grep overcounts: a hook is
  # often mentioned in OTHER hooks' prose ("similar to X.sh") without that
  # being a second entry for X.sh. Headers are the one-row-per-hook ground
  # truth; body mentions are not.
  ACTUAL_HOOKS=$(awk '/^### Shared library/{exit} 1' "$HOOKS_FILE" \
    | grep '^#### ' \
    | grep -oE '`[a-zA-Z0-9_./-]+\.(sh|py)`' \
    | tr -d '`' | sort -u | wc -l | tr -d ' ')
  echo "  Catalog documents: $ACTUAL_HOOKS distinct hooks (excl. shared-library entry)"
  # Any "<N> hooks" claim anywhere in a tracked markdown file must match.
  # ERE only (no -P): PCRE lookahead is not worth mixing matcher engines for
  # (real GNU grep rejects -E and -P together outright, "conflicting
  # matchers specified"; only tripped this because an interactive-shell
  # `grep` override tolerated it and masked the bug during testing).
  while IFS=: read -r file claimed; do
    if [[ "$claimed" != "$ACTUAL_HOOKS" ]]; then
      echo "  STALE COUNT: $file claims \"$claimed hooks\", catalog actually documents $ACTUAL_HOOKS"
      FINDINGS=$((FINDINGS + 1))
    fi
  done < <(grep -rnoE '[0-9]+ hooks' README.md WORLDMAP.md "$HOOKS_FILE" 2>/dev/null \
    | sed -E 's/^([^:]+):[0-9]+:([0-9]+) hooks$/\1:\2/')
else
  echo "  SKIPPED: $HOOKS_FILE not found"
fi

echo ""
echo "=== Reference counts (eyeball against prose claims, not auto-flagged) ==="
echo "  dotclaude/agents:  $(find dotclaude/agents -maxdepth 1 -type f -name '*.md' ! -name 'WORLDMAP.md' | wc -l | tr -d ' ')"
echo "  dotclaude/skills:  $(find dotclaude/skills -maxdepth 1 -mindepth 1 -type d | wc -l | tr -d ' ') directories, $(find dotclaude/skills -type f ! -name 'WORLDMAP.md' ! -path '*__pycache__*' | wc -l | tr -d ' ') files"
echo "  dotclaude/commands: $(find dotclaude/commands -maxdepth 1 -type f -name '*.md' ! -name 'WORLDMAP.md' | wc -l | tr -d ' ')"
echo "  project-tier/agents: $(find project-tier/agents -maxdepth 1 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
echo "  project-tier/skills: $(find project-tier/skills -maxdepth 1 -mindepth 1 -type d 2>/dev/null | wc -l | tr -d ' ')"
echo "  project-tier/rules:  $(find project-tier/rules -maxdepth 1 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"

echo ""
if [[ "$FINDINGS" -eq 0 ]]; then
  echo "consistency-check: clean (0 findings)"
  exit 0
else
  echo "consistency-check: $FINDINGS finding(s)"
  exit 1
fi
