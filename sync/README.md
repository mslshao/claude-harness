# sync/

Installation tooling and CI guardrails.

## Planned contents

- `install.sh` (symlink `dotclaude/agents/*` to `~/.claude/agents/`, `dotclaude/skills/*` to `~/.claude/skills/`, `dotclaude/hooks/*` to `~/.claude/hooks/`, `dotclaude/CLAUDE.md` to `~/.claude/CLAUDE.md`. Skip `memory/` and `scratch/` explicitly. Back up any existing target before symlinking.)
- `uninstall.sh` (remove symlinks, restore backups if present)
- `scrub-check.sh` (CI-style guardrail: scan `dotclaude/`, `project-tier/`, and `patterns/` for known proprietary patterns and fail the build if any leaked through)

## Limitations

`install.sh` assumes the Claude Code `~/.claude/` layout. The patterns and dispatch logic in this repo are tool-agnostic, but the sync script is Claude Code-specific.
