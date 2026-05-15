---
component: agentcore
type: agent
status: deleted
source: recall
superseded_by: [agent-dispatch-heuristic.md, mx2-tech-lead]
---

# agentcore

Early generic agent. Existed during the harness's first few months when the design was "one agent that does many things, with broad system prompt instructions to handle whichever case arrives."

## What it did

The author recalls agentcore as the catch-all specialist: synthesis, planning, code review, infrastructure questions, all routed to one prompt. The model was expected to figure out which mode to operate in based on the request shape.

## Why it was retired

The pattern did not work. A single agent handling many concerns produces worse output in each concern than a specialist agent focused on one. The agentcore prompt grew to several thousand words trying to cover every case; the model's compliance with such a long prompt was inconsistent. Specific behaviors that worked in one mode would slip in another mode where they were equally relevant.

The decision to retire agentcore and split its concerns out came when the author noticed that "what should I do about X" prompts were producing better output when dispatched to specific specialists than when handled by agentcore directly. Once the pattern was clear, the agent was deleted; its responsibilities migrated to:

- **Synthesis and sense-making** → `mx2-tech-lead` (a dedicated thinking-partner agent)
- **Routing decisions** → the dispatch heuristic in CLAUDE.md (not an agent at all; an inline routing table)
- **Generic code review** → `mx2-code-reviewer`
- **Infrastructure questions** → `mx2-devops-build-deploy`

No single replacement; the agent's purpose was split across multiple narrower specialists plus inline harness rules.

## Lessons captured

The retirement was an early datapoint for the lab-to-production discipline: the agentcore approach was a sandbox experiment that failed, the failure was visible from inside personal-tier use, and the artifact was removed before it could propagate to project tier. The replacement pattern (specialists + dispatch rules) shaped most of the harness's subsequent design.

The Keymaker principle was articulated later, but agentcore is the earliest example of it being applied in practice.
