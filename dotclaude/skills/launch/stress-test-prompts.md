# Phase 3a + 3b: Challenge and Consult Subagent Prompts

This file holds the heavy stress-test subagent prompt templates for
`/launch` Phase 3. SKILL.md and plan-pipeline.md reference it; do not
duplicate content back into either.

## Parallel Dispatch (Mandatory)

**CRITICAL: Launch both Phase 3a (Challenge) and Phase 3b (Consult) in
a single message with multiple Agent tool calls. Do not serialize.**

Both subagents receive the draft plan from Phase 2 + the INPUT_MODE
classification from Phase 1. INPUT_MODE-aware framing is built into
both prompts so mechanism-prescribed inputs trigger enhanced scrutiny
on whether the prescription is the right mechanism (the canonical
Fulfillment-vs-Coverage failure-mode guard).

## Phase 3a: Challenge

Subagent prompt:

```
Apply the challenge embed protocol to this implementation plan.
Target 3-7 assumptions. Focus on:

1. "Does the approach account for existing patterns in the codebase?"
   Verify by reading the target modules.
2. "Are the acceptance criteria verifiable without running CI?"
   Each criterion should be checkable with a specific command or file read.
3. "Does the agent team structure match the ticket scope?"
   Over-staffing wastes context. Under-staffing creates phase bottlenecks.
4. "Are the phase gates specific enough for programmatic verification?"
   A gate like "implementation complete" is too vague. "All public functions
   in document_processor.py have implementations (no pass/NotImplementedError)"
   is verifiable.
5. "Does every work item have a Verification path?" Items without one
   should be flagged as FRAGILE.
6. "Are Consequence=high items paired with a concrete Verification
   path?" If not, flag as FRAGILE+HIGH.

Search bd memories for domain-specific gotchas relevant to this plan.
Read source files to verify codebase assumptions.

INPUT_MODE: <problem-framed | mechanism-prescribed>

If INPUT_MODE is `mechanism-prescribed`, apply ENHANCED scrutiny to
the prescribed mechanism. Treat it as an explicit assumption ("we
will use mechanism X to solve problem Y") and evaluate whether X is
the right tool. Common failure modes: the prescribed mechanism is
actually a feature of an existing noun rather than a new noun (the
Fulfillment-vs-Coverage class), the prescribed mechanism contradicts
a ratified architectural decision, the prescribed mechanism is
over-engineered for the problem scope.

[Full draft plan here]
```

## Phase 3b: Consult

Subagent prompt:

```
Act as tech lead coordinator. Review this implementation plan and dispatch
relevant specialists:

- If the plan touches error handling: mx2-silent-failure-hunter
- If the plan touches config/settings: mx2-pydantic-reviewer
- If the plan touches PII/auth/documents: mx2-security-auditor
- If the plan involves infrastructure: mx2-devops-build-deploy
- For structural review of the decomposition: mx2-code-reviewer

Focus on design-level concerns, not implementation details. The plan hasn't
been built yet. Key question for every specialist: "Does the existing pipeline
already provide this behavior?"

Synthesize findings into: Fix now / Fix next / Defer / Won't fix.

INPUT_MODE: <problem-framed | mechanism-prescribed>

If INPUT_MODE is `mechanism-prescribed`, evaluate whether the
prescribed mechanism fits the problem on first-principles grounds.
Do not assume the prescription is right just because the Jira ticket
prescribed it. Specifically check: (a) is this a new noun or a
feature of an existing noun? (b) does this mechanism contradict any
ratified architectural decision in the bead memories? (c) is this
mechanism over-engineered or under-engineered for the problem scope?

[Full draft plan here]
```

## Output from Phase 3a + 3b

Both subagents return their findings to the orchestrator. Phase 3c
(Synthesize) in plan-pipeline.md merges them, applies modifications to
the draft plan, and assigns the DELTA_CATEGORY label.

## Stage Event Writes

After each subagent returns, write a `[LAUNCH_STAGE ...]` entry to the
bead. Challenge and consult outputs are always heavy enough to warrant
scratch.

```bash
ROUND=${ITERATE_ROUND:-0}

# Challenge
CHALLENGE_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/challenge-$ROUND.md"
echo "$CHALLENGE_OUTPUT" > "$CHALLENGE_PATH"
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_STAGE stage=challenge round=$ROUND status=done path=$CHALLENGE_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"

# Consult
CONSULT_PATH="$HOME/.claude/scratch/launch-$LAUNCH_BEAD_ID/consult-$ROUND.md"
echo "$CONSULT_OUTPUT" > "$CONSULT_PATH"
bd update "$LAUNCH_BEAD_ID" --append-notes \
  "[LAUNCH_STAGE stage=consult round=$ROUND status=done path=$CONSULT_PATH ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)]"
```

The two writes can happen in parallel (separate bd update calls, no
ordering dependency). The orchestrator waits for both subagents to
return before proceeding to Phase 3c.

If a subagent fails (rare but possible), write `status=failed` with
`reason=` instead of creating a scratch file. Cold-start treats failed
subagents as in-flight and re-dispatches them.
