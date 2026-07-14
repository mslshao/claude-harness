# Challenge Embed Protocol

Self-contained protocol for plan-producing skills. Run as a mandatory phase
before presenting plans to the user. No external references - this file is the
complete algorithm.

## When to Embed

Any flow that produces a multi-step plan, a set of beads, or an architecture
decision MUST run this protocol before presenting to the user. Skip for
single-item plans or memory checkpoints.

## The Protocol

### Step 1: Extract

Scan your drafted output. For each statement, ask: "Is this a fact I verified,
or something I'm assuming?" Extract assumptions using these triggers:

- "We'll use..." / "We should..." -> assumption about best approach
- "The existing..." / "There's already..." -> assumption about codebase state
- "The client/user needs..." -> assumption about requirements
- "This will..." / "This should..." -> assumption about outcomes
- "Because of X, we..." / "this enables..." -> reasoning chain assumption
- Any reference to code you haven't Read in this conversation -> codebase assumption
- What's NOT mentioned (error handling, rollback, monitoring) -> scope/completeness

For each assumption, record: the statement, which category it falls into
(codebase / domain / technical / scope / dependency / precedent / reasoning /
completeness / pipeline bypass), and where in your plan it appears.

**Relevance gate**: For each extracted assumption, ask: "If this is wrong, does
the plan change in a way that matters?" Drop assumptions where the answer is no.
Target 3-7 assumptions. If you have 10+, you're scanning too broadly.

### Step 2: Score (fragility + impact, two separate axes)

**Fragility** (how likely to be wrong) - two tests:

1. **Inversion**: What if the opposite is true? Does the plan change direction
   (FRAGILE), change approach (SOFT), or hold (SOLID)?
2. **Staleness**: Was this verified this conversation (SOLID), in a recent
   session via beads/memory (SOFT), or never verified (FRAGILE)?

One FRAGILE on either test -> FRAGILE overall. One SOFT -> SOFT. Both SOLID -> SOLID.

**Impact** (how much breaks if wrong) - one test:

3. **Coupling**: How many plan elements depend on this? 3+ = HIGH, 0-2 = LOW.

### Step 3: Evidence Gathering (FRAGILE assumptions only)

For each FRAGILE assumption, gather evidence. Record what you searched and what
you found. No interpretation in this step.

- **Codebase**: Grep/Read the code. Record: `Searched: <pattern> | Found: <result>`
- **Domain**: Cannot be checked against code. Mark UNVERIFIABLE.
- **Technical/Dependency/Precedent**: Check beads, memory, code. Record searches.
- **Reasoning Chain**: Trace the logical dependency. Does step N-1 actually
  guarantee step N? Record what you checked.

Evidence states:
- **CONFIRMED**: Searched, found, matches assumption.
- **INVALIDATED (absent)**: Searched, code/pattern does not exist.
- **INVALIDATED (partial)**: Searched, exists but behavior differs from assumed.
- **UNVERIFIABLE**: Cannot be checked against code (domain, external).
- **UNVERIFIED**: Could be checked but wasn't. **This is not acceptable.** If a
  FRAGILE codebase or technical assumption reaches this state, go back and verify.

### Step 4: Modify (decision table)

Apply modifications based on adjudication:

| Adjudication | Action on plan |
|-------------|---------------|
| INVALIDATED (absent) | Remove the dependency. Add negative decision: "Why NOT X: does not exist in codebase." |
| INVALIDATED (partial) | Revise to match reality. Note what differs and how the plan adapts. |
| UNVERIFIABLE | Prefix with "ASSUMPTION (unverified):" in the plan element description. |
| CONFIRMED | No change needed. |

### Step 5: Proceed and Report

After modifications, present the plan with a visible callout block:

```
> **Challenge gate**: N assumptions checked. M invalidated, K unverifiable.
> [1-line summary of most significant finding, if any]
```

This callout is always shown (not internal-only) so the user can see that the
gate ran and what it found.

Proceed based on findings:
- **0 FRAGILE or all CONFIRMED**: Proceed normally. Callout shows clean pass.
- **FRAGILE, all resolved**: Proceed with modifications applied. Callout
  summarizes what changed.
- **FRAGILE, unresolvable**: Present with explicit assumption callouts. The user
  MUST confirm these before work begins. Frame as: "This plan assumes X. If X
  is wrong, elements Y and Z would need to change."
