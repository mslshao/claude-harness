# Model Selection

When to use the strong model (Opus, in this author's setup) vs the smaller model (Sonnet). The pattern is captured more fully in `patterns/cost-via-delegation.md`; this file is the operational quick-reference for routing decisions.

## The default

The main conversation uses the strongest available model.

Cost optimization happens through delegation:

- Subagent dispatch to bounded executor agents (running on the smaller model)
- Specialist agents (code review, style, security) run on the smaller model
- Main conversation reviews the executor's diff and the specialist's findings

Net cost is lower than pure-strong-model, with strong-model-quality outcomes.

## When to stay on the strong model

- Starting with "why is X broken" and you do not know the answer.
- Synthesis across conflicting sources, multiple tickets, competing constraints.
- Architectural decisions with downstream consequences.
- Security and compliance (cost of a subtle miss is high).
- You could not write acceptance criteria before starting.

When unsure: stay on the strong model. The asymmetry (wrong-Sonnet-call means wasted work plus a strong-model rescue) makes strong-model the correct default.

## Surface-map nuance: a newer generation is not an ambient default

A newer model generation (Fable-class) can be available in some surfaces (CLI, web) but blocked in others. In this setup it is blocked in the IDE/editor surface because that model's terms require data retention while the org runs zero-data-retention (ZDR); the strong default model carries no such requirement. So where the newer model is allowed, it is an explicit per-session opt-in, not something the harness reaches for automatically.

Keep the strong model as the deliberate default. The portable lesson: model availability is surface-conditional and policy-conditional, not just capability-conditional. "Newer and more capable" does not make a model the right default if the surface you are in cannot run it under your org's data policy. Confirm the surface and the policy before reaching for a newer generation.

## When the smaller model alone is fine (Sonnet mode)

When the harness is started in explicit Sonnet mode for an extended session of bounded work:

Trial-safe categories in order of increasing risk:

1. Style and lint fixes after CI failure (bounded, verifiable via lint command)
2. Test generation for existing code
3. PR review triage (read-only)
4. Single-file bug fixes where root cause is already known

## Escalation triggers in Sonnet mode

- Before any architectural decision
- When ambiguity cannot be resolved from context
- When choosing between two reasonable approaches
- When the task is more complex than initially scoped

## Safety rails for Sonnet mode

- Security-sensitive changes route through a security-audit agent plus user escalation.
- Project lint+test command must pass post-implementation (stop-validate hook enforces).
- State "I need the strong model for this" rather than guessing. Sonnet self-assessment is unreliable; Sonnet self-flagging-when-stuck is good.

## Why this exists

The naive cost optimization is "use the smaller model directly to save tokens." This fails in two ways: (1) Sonnet self-assessment biases toward "I can handle this" even when it cannot; (2) when Sonnet handles a task that exceeded its scope, you pay both calls.

The delegation pattern preserves strong-model oversight (dispatch + review) while gaining smaller-model cost advantage on actual implementation. Net cost is lower with same outcomes.

## Where it has limits

- The dispatch + review overhead is non-trivial. For single-line trivial edits, overhead exceeds savings; just do the edit directly.
- Sonnet quality varies by task. For multi-file refactors, ambiguous spec, or codebase exploration, delegation produces worse results than direct strong-model work.
- The pattern depends on having a model-tier difference to exploit. In single-tier setups, this pattern does not apply.
