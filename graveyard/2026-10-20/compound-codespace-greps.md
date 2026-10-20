---
component: compound skill, step 3 codespace dedup greps
type: skill lines
status: deleted
source: snapshot
superseded_by: [the surviving greps over ~/.claude/memory, rules and CLAUDE.md]
---

# compound-codespace-greps

## What it was

Lines 104 to 107 and 112 of `skills/compound/SKILL.md` (hash 3f9dfedc), quoted in full:

```
grep -iE "$KW_GREP" ~/.claude/projects/-workspaces-main/memory/workflow.md
grep -riE "$KW_GREP" ~/.claude/projects/-workspaces-main/memory/*.md
grep -riE "$KW_GREP" /workspaces/main/.claude/rules/
grep -riE "$KW_GREP" /workspaces/main/CLAUDE.md ~/.claude/CLAUDE.md
bash /home/vscode/.claude/scratch/domain-matcher/match.sh "$KW_TEXT" | head -10        # optional related terminology
```

## Why it went

Written for the codespace. On this box the four paths do not exist, so every compound and every queue run grepped missing paths (MERGE-2, "Fixes too small to rank", dev-73-2 item 3). the user approved item 3 C7 at about 16:29Z on 2026-10-20.

## What supersedes it

One line, `grep -riE "$KW_GREP" ~/.claude/CLAUDE.md`, plus the `~/.claude/memory/` and `~/.claude/rules/` greps already above it.

**Source: snapshot** `(local snapshot) skills/compound/SKILL.md.txt`
