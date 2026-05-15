#!/usr/bin/env bash
# uninstall.sh: remove symlinks created by install.sh.
#
# Walks ~/.claude/{agents,skills,hooks} and ~/.claude/CLAUDE.md, removes
# any symlink pointing into this repo's dotclaude/. Does NOT touch memory/,
# scratch/, or any non-symlink file.
#
# Usage:
#   ./sync/uninstall.sh             # interactive, asks before removing
#   ./sync/uninstall.sh --force     # remove without asking
#   ./sync/uninstall.sh --dry-run   # show what would happen, do not modify

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DOTCLAUDE_SRC="$REPO_ROOT/dotclaude"
CLAUDE_DEST="$HOME/.claude"

FORCE=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --force)   FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *)         echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

log() { echo "uninstall: $*"; }

confirm() {
  if [ "$FORCE" -eq 1 ] || [ "$DRY_RUN" -eq 1 ]; then return 0; fi
  read -r -p "$1 [y/N] " response
  [[ "$response" =~ ^[Yy]$ ]]
}

REMOVED=0

remove_link() {
  local target="$1"
  if [ ! -L "$target" ]; then return 0; fi
  local link_dest
  link_dest="$(readlink "$target")"
  case "$link_dest" in
    "$DOTCLAUDE_SRC"/*|"$DOTCLAUDE_SRC")
      if ! confirm "remove symlink $target -> $link_dest?"; then
        log "skip (declined): $target"
        return 0
      fi
      if [ "$DRY_RUN" -eq 0 ]; then
        rm "$target"
        log "removed: $target"
      else
        log "would remove: $target"
      fi
      REMOVED=$((REMOVED + 1))
      ;;
    *)
      # Symlink does not point into our repo; leave it alone.
      :
      ;;
  esac
}

for top in agents skills hooks; do
  if [ -d "$CLAUDE_DEST/$top" ]; then
    for item in "$CLAUDE_DEST/$top"/*; do
      remove_link "$item"
    done
  fi
done

remove_link "$CLAUDE_DEST/CLAUDE.md"

if [ "$DRY_RUN" -eq 1 ]; then
  log "(dry-run; no changes made)"
fi

log "done. $REMOVED symlink(s) removed."
log "backups (if any) remain in $CLAUDE_DEST/.install-backup-*; manage manually."
