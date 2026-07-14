---
name: challenge
description: Assumption-challenging for plans, designs, and decisions. Extracts unstated assumptions, scores by fragility, and stress-tests against codebase evidence and domain constraints. Use when reviewing a plan before presenting, when the user provides new context that may invalidate a plan, or when explicitly invoked via /challenge.
argument-hint: "[new context, or no args to challenge the most recent plan]"
---

# Challenge

Extract and stress-test the assumptions underlying a plan, design, or decision.
Same core operation whether invoked by a human or embedded in a plan-producing flow.

## Entry Points

### Human-Invoked (`/challenge`)

The user calls `/challenge` with one of:
- **No argument**: Challenge the most recent plan/proposal in the conversation.
- **New context**: e.g., `/challenge "client needs real-time, not batch"`. New
  information that may invalidate assumptions the agent couldn't have known.

### Agent-Embedded (Phase 2.5)

Plan-producing skills (bead-forge, plan agents) embed the challenge as a mandatory
phase using the protocol in [embed-protocol.md](embed-protocol.md). The agent runs
the protocol before presenting. Output includes a visible callout block so the user
sees that the gate ran.

## Process

### Phase 1: Identify the Plan

- If human-invoked with no args: identify the most recent plan, proposal, or set
  of beads in the conversation.
- If human-invoked with context: identify the plan AND note the new context as a
  constraint that existing assumptions must be tested against.
- If agent-embedded: the plan is whatever was just drafted in the current flow.

After identifying the plan, detect the mode:
- **Plan mode** (default): The plan describes future work. Assumptions are
  forward-looking ("will this approach work?"). Some will be UNVERIFIABLE.
- **Post-impl mode**: The plan was already built (code exists, PR merged, bead
  closed, or user says "we shipped this"). Assumptions can be verified against
  actual code. In Phase 4a, do not mark codebase/technical assumptions
  UNVERIFIABLE when you can Read the implementation to confirm or invalidate.

**Enrich preamble** (lightweight pre-load before assumption extraction):

1. **Identifier-driven enrich** (when references detected): If the plan
   references a Jira ticket (`MX2-\d+`) or bead ID (`docr-\w+`), fetch the
   ticket's AC and related beads. This gives Phase 2 concrete acceptance
   criteria to check assumptions against, and Phase 4a domain-specific
   gotchas from beads memories. Skip if no identifiers found.

2. **Domain-matcher enrich** (best-effort, not a gate): Run the domain-matcher
   to surface prior terminology decisions for the plan's domain:

   ```bash
   bash /home/vscode/.claude/scratch/domain-matcher/match.sh "<plan text>" \
     | cut -d: -f1 | head -10
   ```

   For each matched keyword, run `bd memories <keyword>` and skim the top
   5 results. Cap pre-loaded context at roughly 2KB to avoid Phase 1 bloat.
   Use the loaded context to (a) avoid challenging things that are already
   established fact (false positives), and (b) sharpen what counts as
   FRAGILE by anchoring against known state.

   **Quality bar.** Best-effort context loader, not a gate. Matcher
   calibration is ~79% recall / ~82% precision (n=18 baseline); misfires
   are expected. If the matcher returns no results, returns noise, or
   fails to run, skip the matcher pre-load and continue. A misfire must
   NOT block the challenge.

Skip codebase grep here (Phase 4a handles that per-assumption).

### Phase 2: Extract Assumptions

Scan the plan using trigger phrases from
[assumption-taxonomy.md](assumption-taxonomy.md). The taxonomy defines nine
categories (codebase, domain, technical, scope, dependency, precedent, reasoning
chain, scope/completeness, pipeline bypass) with specific trigger phrases.

After extraction, apply the **relevance gate**: for each assumption, ask "If
this is wrong, does the plan change in a way that matters?" Drop assumptions
where the answer is no. Target 3-7 assumptions. If you have 10+, cut the ones
that don't pass the gate.

This requires judgment about what matters, constrained by the inversion test
(if wrong, does the plan change?), not by opinion about code quality.

**Language Precision lens** (run after factual extraction, score the same way):

Scan the plan for fuzzy referents that look concrete but resolve ambiguously:

- "the document" / "the cache" / "the existing pipeline" / "the worker"
  (which one specifically?)
- "a mechanism" / "some way" / "appropriate handler" (unspecified design)
- "somehow" / "eventually" / "when needed" (unspecified time/condition)

For each fuzzy term, ask: "which X specifically?" Cite candidates from the
enrich preamble context (Phase 1) if available, or propose an explicit name.
Score using the standard fragility scale:

- **SOFT**: ambiguity is recoverable later (Phase 5 spec, code review,
  implementation will pin it down naturally).
- **FRAGILE**: load-bearing ambiguity that will derail Phase 3 specialists
  or produce different plans depending on which referent is meant.

Surface Language Precision findings as a separate row category in the
Findings table (Category = "Language") so they are not conflated with
factual codebase/domain/technical assumptions.

### Phase 3: Score

Rate each surviving assumption on two independent axes. See
[assumption-taxonomy.md](assumption-taxonomy.md) for full criteria and examples.

**Fragility** (SOLID/SOFT/FRAGILE): How likely to be wrong? Based on inversion
test (what if the opposite is true?) and staleness test (when was this verified?).

**Impact** (HIGH/LOW): How much breaks if wrong? Based on coupling (3+ plan
elements depend on it = HIGH).

When new context was provided by the user, test each assumption against it
directly: "Does this new information invalidate, weaken, or have no effect on
this assumption?"

### Phase 4a: Evidence Gathering

For FRAGILE assumptions only. Gather evidence using tools. Record what you
searched and what you found. **No interpretation in this step.** In Post-impl
mode, prefer reading the actual implementation over marking assumptions
UNVERIFIABLE - the code is the evidence.

- **Codebase**: Grep/Read the code. Record: `Searched: <pattern> | Found: <result>`
- **Domain**: Cannot be checked against code. Mark UNVERIFIABLE.
- **Technical/Dependency/Precedent**: Check beads, memory, code. Record searches.
- **Reasoning Chain**: Trace the logical dependency. Does step N-1 actually
  guarantee step N?
- **Scope/Completeness**: Check whether the omitted concern is addressed elsewhere
  in the codebase or in prior beads/decisions.

### Phase 4b: Adjudication

Interpret evidence using the decision table:

| Evidence | Grep/Read result | Adjudication |
|----------|-----------------|--------------|
| Code exists as assumed | Match found, behavior matches | CONFIRMED |
| Code exists but differs | Match found, behavior differs | INVALIDATED (partial) |
| Code does not exist | Zero results | INVALIDATED (absent) |
| Cannot check (domain/external) | N/A | UNVERIFIABLE |
| Could check but didn't | No tool used | UNVERIFIED |

**UNVERIFIED is not an acceptable final state** for codebase or technical
assumptions. If a FRAGILE assumption could be checked but wasn't, go back
to Phase 4a and verify it. This prevents false confidence.

### Phase 5: Escalation (rare)

Only escalate to specialist dispatch when:
- 2+ FRAGILE assumptions require different specialist agents (e.g., one needs
  `mx2-security-auditor`, another needs `mx2-devops-build-deploy`; see
  `consult/specialists.md` for the dispatch routing)
- A single FRAGILE assumption requires deep structural analysis (3+ modules)

If all FRAGILE findings map to one specialist, route directly. If they span
two or more, use `/consult`. This is the exception. Most challenges resolve
at Phase 4 with Grep/Read.

### Phase 6: Report

**Human-invoked output (three sections):**

```
## Challenge: <plan title, 3-8 words>

### Verdict
<1-3 sentences: Is the plan safe to proceed? What's the biggest risk? What
should change before execution? Be opinionated. This is the "so what.">

### Findings

| # | Assumption | Category | Fragility | Impact | Evidence |
|---|-----------|----------|-----------|--------|----------|
| 1 | <statement> | Codebase | FRAGILE | HIGH | INVALIDATED: <1-line> |
| 2 | <statement> | Reasoning | FRAGILE | HIGH | UNVERIFIABLE |
| 3 | <statement> | Scope | SOFT | LOW | CONFIRMED |

Detail on FRAGILE findings only (skip SOLID/SOFT unless user asks):

**1. <assumption statement>** [Codebase | FRAGILE + HIGH]
- Searched: `grep -r "FormulaEngine" src/python/mx2/`
- Found: 0 results
- Adjudication: INVALIDATED (absent)
- Impact: <which plan elements break>
- Resolution: <what to do about it>

**2. <assumption statement>** [Reasoning | FRAGILE + HIGH]
- Checked: <what logical dependency was traced>
- Adjudication: UNVERIFIABLE
- Impact: <which plan elements depend on this logic>
- Resolution: <specific question the human needs to answer>

### Actions
<Concrete modifications to the plan. Each action references which finding
drives it. If no actions needed, state "No plan changes required. Proceed
as drafted." This section is MANDATORY - never omit it.>
```

Omit any section with zero items except Actions (always present). Within
Findings, order by fragility (FRAGILE first), then by impact (HIGH first).

**Agent-embedded output:** Follow [embed-protocol.md](embed-protocol.md).
Modify the plan using the decision table, then show the challenge gate
callout block.

## Principles

- **Relevance over completeness.** 3-7 high-signal assumptions beat 15 that
  include obvious truths. The relevance gate is the most important step.
- **Evidence or admit you didn't check.** Every FRAGILE codebase/technical
  assumption must show what was searched. No claiming CONFIRMED without evidence.
- **Verdict first.** The user wants to know "is this plan safe?" before reading
  the details. Lead with the answer.
- **Actions are mandatory.** Findings without "so what" are useless. Every
  challenge report ends with concrete next steps or an explicit "proceed."
- **Lightweight by default.** Most challenges resolve with Grep/Read, no
  specialists.
- **Conservative scoring.** 1-3 FRAGILE per plan is normal. 50%+ means
  recalibrate.
- **Delta, not re-plan.** Show what changes, not a full rewrite.
- **Unverifiable is OK.** Domain assumptions can't be checked against code.
  Flag them clearly and let the human decide.
