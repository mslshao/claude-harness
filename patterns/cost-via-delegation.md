# Cost Via Delegation

## The pattern

The main conversation uses the strongest available model (Opus, in this harness). Cost optimization happens by delegating bounded work to a smaller model (Sonnet) via subagent dispatch, NOT by switching the main conversation to the smaller model.

The main conversation retains:

- Dispatch decisions (which agent runs for which task)
- Synthesis across multi-source inputs
- Architectural calls with downstream consequences
- Security and compliance judgment (cost of a subtle miss is high)
- Tasks where you cannot write acceptance criteria before starting

A bounded executor agent (Sonnet) handles:

- Well-scoped implementation where root cause is known and the change is pattern-matching against known conventions
- First-pass code from a clear spec
- Mechanical fixes within known files
- Test generation against a clear spec
- Style and lint compliance fixes

The main conversation reviews the executor's diff before committing.

## Why this exists

The naive cost optimization is "use Sonnet directly to save tokens." This fails in two ways:

1. **Sonnet self-assessment is unreliable.** If you ask Sonnet "do you need to escalate to Opus?", the answer biases toward "no." Sonnet completes work that should have been escalated, sometimes plausibly enough that the wrong call is not caught until review.
2. **The asymmetry is wrong.** When Sonnet handles a task that exceeded its scope, you pay both the Sonnet call (wasted) AND an Opus call to re-do or repair the work. Better to start with Opus making the dispatch decision and have Sonnet execute under that direction.

The delegation pattern preserves Opus oversight (dispatch + review) while gaining Sonnet's cost advantage on the actual implementation work. Net cost is lower than pure-Opus, with Opus-quality outcomes.

## When to stay on Opus (or escalate mid-conversation)

- Starting with "why is X broken" and you do not know the answer.
- Synthesis across conflicting sources, multiple tickets, competing constraints.
- Architectural decisions with downstream consequences.
- Security and compliance (a subtle miss is costly).
- You could not write acceptance criteria before starting.

When unsure: stay on Opus. The cost of a wrong Sonnet call (wasted Sonnet work plus an Opus rescue) exceeds the cost of a single Opus call.

## Sonnet mode (the rare time the main runs on Sonnet)

When the harness is started in Sonnet mode (explicit downgrade for an extended session of bounded work):

Trial-safe categories in order of increasing risk:

1. Style and lint fixes after CI failure (bounded, verifiable via lint command)
2. Test generation for existing code
3. PR review triage (read-only)
4. Single-file bug fixes where root cause is already known

Escalation triggers:

1. Before any architectural decision
2. When ambiguity cannot be resolved from context
3. When choosing between two reasonable approaches
4. When the task is more complex than initially scoped

Safety rails for Sonnet mode:

- Security-sensitive changes route through a security-audit agent plus user escalation.
- The project's lint+test command must pass post-implementation (stop-validate hook enforces).
- State "I need Opus for this" rather than guessing. Sonnet self-assessment is bad; Sonnet self-flagging-when-stuck is good.

## How this compounds

Over a long session, the pattern produces consistent quality (Opus oversight) at reduced cost (Sonnet execution). The delegation discipline also forces the main conversation to be specific about what work goes to the executor: vague dispatch produces vague execution. Vague dispatch is itself a signal that the work is not ready for delegation.

## Where it has limits

- The dispatch + review overhead is non-trivial. For single-line trivial edits, the overhead exceeds the savings; just do the edit directly.
- Sonnet quality varies by task. For categorically harder tasks (multi-file refactors, ambiguous spec, codebase exploration), delegation produces worse results than direct Opus work.
- The pattern depends on having a model-tier difference to exploit. In a single-tier setup, this pattern does not apply.
