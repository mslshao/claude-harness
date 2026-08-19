# sync/

Installation tooling and CI guardrails for the personalized Claude Code harness.

## Files

| File | What it does |
|---|---|
| `install.sh` | Symlink `dotclaude/{agents,skills,hooks,commands}/*` and `dotclaude/CLAUDE.md` into `~/.claude/`. Skips `memory/` and `scratch/`. Backs up existing target files before symlinking. |
| `uninstall.sh` | Remove symlinks created by install.sh. Leaves any non-symlink file alone. |
| `scrub-check.sh` | CI guardrail that scans repo content for proprietary patterns (real teammate names, internal IDs, atlassian cloud/space IDs). Exits 1 on any finding. |
| `consistency-check.sh` | CI guardrail for internal consistency: dangling relative markdown links (a file the mirror references but never shipped) and hooks-count drift between `dotclaude/hooks/README.md`'s catalog and any place that states a total. Exits 1 on any finding. Also prints current agent/skill/command/project-tier counts for a human to eyeball against prose claims elsewhere (not auto-flagged; too many counting conventions to generalize safely). |
| `SCRUB-SPEC.md` | Documentation of what gets scrubbed and why (the 4-tier scrub doctrine). |

## Install

```bash
./sync/install.sh
```

Interactive: asks before overwriting any existing target. Backs up existing files to `~/.claude/.install-backup-<timestamp>/` before symlinking.

Flags:
- `--force`: overwrite without asking (backups still made)
- `--dry-run`: show what would happen, do not modify

## Uninstall

```bash
./sync/uninstall.sh
```

Removes only the symlinks that point into this repo's `dotclaude/`. Backup directories from install remain; manage them manually if you want to restore.

Flags:
- `--force`: remove without asking
- `--dry-run`: show what would happen, do not modify

## CI

`scrub-check.sh` and `consistency-check.sh` should both run on every PR to this repo; they catch different defect classes (proprietary leaks vs. internal inconsistency) and neither substitutes for the other. Both scripts are exit-code-friendly:

- Exit 0: clean
- Exit 1: one or more findings (CI fails)
- Exit 2: misconfiguration (script run outside the repo root)

See `SCRUB-SPEC.md` for the full scrub doctrine and tier definitions.

## Limitations

`install.sh` assumes the Claude Code `~/.claude/` directory layout. The patterns, dispatch logic, and scaffolding docs in this repo are tool-agnostic, but the sync script itself is Claude Code-specific. For other AI tools (Perplexity Spaces, ChatGPT custom GPTs, Cursor, etc.), the install path is the equivalent prompt/configuration location for that tool, and the user adapts the script accordingly.

The script is idempotent: re-running install over an already-installed setup is safe (skips already-linked files). Re-running uninstall after a previous uninstall is also safe (no-op for symlinks already removed).
