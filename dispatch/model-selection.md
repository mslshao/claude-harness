# Model Selection

When to use the strong model (Claude Opus 5, in this author's setup) vs the smaller model (Claude Sonnet 5). The pattern is captured more fully in `patterns/cost-via-delegation.md`; this file is the operational quick-reference for routing decisions.

The lineup this doc is written against, as of 2026-08: Opus 5 (flagship), Sonnet 5, Fable 5 (a sibling generation, see the availability section below), Haiku 4.5 (cheapest tier). The rules are written in tier terms rather than generation numbers, because the tiers outlive the numbers; which agent is pinned to which tier is a separate question, answered by the gate in `agent-tiers.md`.

## The default

The main conversation uses the strong model, pinned explicitly in settings (`opus[1m]` here, the long-context variant) rather than left to track whatever the installed build happens to default to. Build defaults move without announcement, and a silent downgrade of the supervising conversation is the change you least want to discover after the fact.

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

## Availability nuance: a sibling generation is not an ambient default

Claude Fable 5 is a sibling of the flagship (a different point on the cost, latency, and behavior curve, not a strict upgrade), and its availability in this setup moved through three states in about five weeks:

1. Allowed in the CLI and web surfaces, blocked in the IDE/editor surface, on the stated grounds that the model's terms require data retention while the org was believed to run zero data retention (ZDR). The strong default model carries no such requirement.
2. Disabled org-wide, then found to rest on a mistaken premise: the org did not actually have ZDR enabled, so the retention conflict that justified the block did not exist.
3. Re-enabled, with access granted per person by an admin rather than self-serve.

Two rules survive that history. First, the strong model stays the deliberate default; where a sibling generation is allowed, using it is an explicit per-session opt-in (`/model`), not something the harness reaches for automatically, and a `/model` switch saved in one session is a session convenience rather than a policy change. Second, verify availability instead of assuming it. Model availability is surface-conditional, policy-conditional, and account-conditional, not just capability-conditional: "newer" or "also available" does not make a model the right default if the surface you are in cannot run it under your org's data policy, and in this case a policy claim that sounded authoritative went unchecked against the actual account configuration for weeks while it was wrong.

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
