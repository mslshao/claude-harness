# dispatch/

Routing logic. When the harness has many specialists, who runs first? When the task is ambiguous, which agent owns the synthesis? When cost matters, which model is right?

This directory captures the IF-THEN rules that drive specialist selection, model selection, and PR review routing. The philosophy is portable across AI tools; the mechanics (specifically the agent invocation primitive) are Claude Code-specific.

## Planned contents

- `agent-tiers.md` (user-tier, project-tier, plugin-tier and the promotion path between them)
- `agent-dispatch-heuristic.md` (numbered routing rules)
- `pr-review-routing.md` (trigger to tool mapping for review workflows)
- `model-selection.md` (Opus default, Sonnet delegation, when to escalate)
- `sonnet-mode-guide.md` (when to allow Sonnet, the safety rails)
