#!/usr/bin/env bash
# install.sh: drop-in install of dotclaude/ into the user's ~/.claude/
#
# Symlinks dotclaude/{agents,skills,hooks,commands}/* and dotclaude/CLAUDE.md into
# the user's ~/.claude/ directory. Skips memory/ and scratch/ explicitly.
# Backs up existing target files before symlinking.
#
# Usage:
#   ./sync/install.sh             # interactive, asks before overwriting
#   ./sync/install.sh --force     # overwrite without asking (backups still made)
#   ./sync/install.sh --dry-run   # show what would happen, do not modify

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

# Sanity checks
if [ ! -d "$DOTCLAUDE_SRC" ]; then
  echo "install: expected $DOTCLAUDE_SRC to exist" >&2
  exit 2
fi

mkdir -p "$CLAUDE_DEST"

BACKUP_DIR="$CLAUDE_DEST/.install-backup-$(date -u +%Y%m%dT%H%M%SZ)"

log() { echo "install: $*"; }

confirm() {
  if [ "$FORCE" -eq 1 ] || [ "$DRY_RUN" -eq 1 ]; then return 0; fi
  read -r -p "$1 [y/N] " response
  [[ "$response" =~ ^[Yy]$ ]]
}

link_one() {
  local src="$1"
  local rel="${src#$DOTCLAUDE_SRC/}"
  local dest="$CLAUDE_DEST/$rel"
  local dest_parent
  dest_parent="$(dirname "$dest")"

  # Skip excluded paths
  case "$rel" in
    memory/*|memory|scratch/*|scratch) return 0 ;;
  esac

  if [ -e "$dest" ] || [ -L "$dest" ]; then
    # Existing target. Back up before symlinking unless it is already a
    # symlink pointing at our source (idempotent install).
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
      log "skip (already linked): $rel"
      return 0
    fi
    if ! confirm "overwrite existing $dest?"; then
      log "skip (declined): $rel"
      return 0
    fi
    if [ "$DRY_RUN" -eq 0 ]; then
      mkdir -p "$BACKUP_DIR/$(dirname "$rel")"
      mv "$dest" "$BACKUP_DIR/$rel"
      log "backed up: $rel -> $BACKUP_DIR/$rel"
    else
      log "would back up: $rel"
    fi
  fi

  if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$dest_parent"
    ln -s "$src" "$dest"
    log "linked: $rel"
  else
    log "would link: $rel -> $src"
  fi
}

# Link agents (skip _shared and calibration subdirs since they contain
# multiple files; link the parent dirs as a whole).
for top in agents skills hooks commands; do
  if [ -d "$DOTCLAUDE_SRC/$top" ]; then
    for item in "$DOTCLAUDE_SRC/$top"/*; do
      link_one "$item"
    done
  fi
done

# Link top-level CLAUDE.md
if [ -f "$DOTCLAUDE_SRC/CLAUDE.md" ]; then
  link_one "$DOTCLAUDE_SRC/CLAUDE.md"
fi

if [ "$DRY_RUN" -eq 1 ]; then
  log "(dry-run; no changes made)"
fi

if [ -d "$BACKUP_DIR" ]; then
  log "backups in $BACKUP_DIR"
fi

log "done."
