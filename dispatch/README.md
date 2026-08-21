# dispatch/

Routing logic. When the harness has many specialists, who runs first? When the task is ambiguous, which agent owns the synthesis? When cost matters, which model is right?

This directory captures the IF-THEN rules that drive specialist selection, model selection, and PR review routing. The philosophy is portable across AI tools; the mechanics (specifically the agent invocation primitive) are Claude Code-specific.

## Contents

- `agent-tiers.md` (user-tier, project-tier, plugin-tier and the promotion path between them)
- `agent-dispatch-heuristic.md` (numbered routing rules)
- `pr-review-routing.md` (trigger to tool mapping for review workflows)
- `model-selection.md` (Opus default, Sonnet delegation, when to escalate; the Sonnet-mode safety rails live in this doc rather than in a separate one)
- `dispatch-prompt-contract.md` (what every dispatch prompt must carry once the target is chosen)

The first four answer "who runs this." The fifth answers "what the prompt has to say," which is a separate failure surface: a correctly routed dispatch still fails when the prompt omits something only the dispatching session knows.
