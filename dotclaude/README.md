# dotclaude/

A scrubbed mirror of `~/.claude/`. Same structural layout, content scrubbed of third-party names and proprietary references.

The mirror is structurally identical so `sync/install.sh` can symlink `dotclaude/agents/*` to `~/.claude/agents/`, `dotclaude/skills/*` to `~/.claude/skills/`, and so on. Anyone using Claude Code can drop the harness into their setup with a single script.

Excluded by design: `memory/` (proprietary notes, person-specific context, project knowledge that does not belong in a public artifact) and `scratch/` (transient working files). These never enter the repo; `.gitignore` enforces this at the repo level.

## Planned subdirectories

- `agents/` (personal agent definitions, scrubbed)
- `skills/` (personal skill definitions, scrubbed)
- `hooks/` (descriptions plus scrubbed runnable shell where portable)
- `CLAUDE.md` (scrubbed personal global instructions)

Companion WORLDMAP files in each subdirectory explain each component's purpose.
