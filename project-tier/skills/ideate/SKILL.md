---
name: ideate
description: >
  Divergent approach generation with evaluative ranking and a mandatory
  adversarial skeptic pass. Use when you have a problem but do not yet
  know which of N approaches to pursue: "what are my options for X",
  "brainstorm Y", "tradeoffs between X and Y", "which approach should
  I take". Accepts free-text, Jira tickets, Slack threads, Confluence
  drafts, or transcripts. Produces 3-5 ranked approaches with a
  recommended winner, preserves rejected alternatives, and stops at
  presentation so the human picks the winner. Distinct from /review
  (PR review), /investigate (root cause), and /enrich (context
  loading).
argument-hint: "[problem statement, Jira ticket, Slack URL, Confluence URL, or transcript]"
allowed-tools: ["Glob", "Grep", "Read", "Agent", "mcp__atlassian__getJiraIssue", "mcp__atlassian__getConfluencePage"]
---

# Ideate

Generate multiple approaches to a problem (divergent), rank them, run
an adversarial skeptic pass, and present the ranked output. The user
reads the table plus dissent and picks a winner themselves.

## Why This Exists

The planning toolkit has a coverage gap for problems where the path
forward is not yet obvious. `/investigate` traces root causes for a
known failure. `/review` stress-tests an existing diff. `/enrich`
loads context. None solve: "I have a problem, I do not yet know which
of N approaches to pursue."

`/ideate` fills the gap. It produces 3-5 candidate approaches, ranks
them on a multi-criteria matrix, runs an adversarial skeptic pass, and
presents the ranked output with a recommended winner. The iterate-or
-proceed call is left to the human reading the output. The skill's
high-judgment ask is yours to own.

## Input

One or more of:
- Free-text problem statement (most common)
- Jira ticket ID (`MX2-\d+`)
- Slack URL or pasted thread excerpt
- Confluence URL or pasted page body
- Conversation transcript

Mixed inputs are consolidated. Precedence on disagreement: inline text >
Slack/transcript > Confluence > Jira. Disagreements surface in Phase 4
"Open Assumptions".

## Pipeline Overview

```
problem
   |
   v
[Phase 1: Refine]
   |
   v
[Phase 2: Diverge]
   |
   v
[Phase 3: Evaluate]
   |   (3a: score; 3b: apply overrides; 3c: mandatory skeptic pass)
   v
[Phase 4: Present]
   |
   v
[Phase 5: Handoff (human picks winner; no auto-invocation)]
```

Phases 1-3 are INTERNAL. Phase 4 is the first user-facing synthesis. No
proceed/iterate gate fires automatically; the human reads the ranked
output plus skeptic dissent and decides whether to act on the winner,
re-run with narrower scope, or escalate.

## Process

### Phase 1: Refine (internal)

Load all inputs, strip bias, clarify the problem.

1. **Load inputs.** For each detected input type, fetch and parse:
   - Jira ID: `mcp__atlassian__getJiraIssue` MCP call.
   - Slack URL `https://*.slack.com/archives/<CHANNEL>/p<TS>`: ask the
     user to paste the thread content as text. No project-tier Slack
     MCP is configured, so the URL cannot be fetched directly. The
     surface-area cost is one round-trip; the alternative (silent tool
     failure on a missing MCP) is worse.
   - Confluence URL `*.atlassian.net/wiki/spaces/<SPACE>/pages/<PAGE_ID>/<slug>`:
     extract `<PAGE_ID>`, then `mcp__atlassian__getConfluencePage`.
   - Pasted text (Slack excerpt, transcript, page body, free-text): use
     as-is.
   - If an MCP fetch tool is unavailable or the call fails, ask the user
     to paste the content (the same fallback the Slack path uses); do not
     proceed on an unloaded input.

2. **Detect terseness.** If consolidated input is under ~30 words or
   lacks explicit constraints, expand the problem statement in-place
   before Phase 2. Surface implicit constraints, scope boundaries,
   success criteria, and any codebase/domain context. Do NOT propose
   approaches or solutions during refinement. Skip when input is
   already precise.

3. **Pre-load domain context** (best-effort, not a gate). Pick 2-3
   keywords from the problem statement that map to the specialist
   roster (see [specialists.md](specialists.md) keyword table) and
   the project rule files. For each keyword: if a service-level
   `CLAUDE.md` exists under the matching `src/python/mx2/<service>/`
   path, read it; if a `.claude/rules/*.md` file is keyword-relevant
   (e.g., `security` -> `security.md`, `architecture` ->
   `architecture.md`), surface it as loaded context. Keyword matching
   is heuristic and may misfire; never block ideation on it.

4. **Bias-stripping (mandatory).** Build TWO context blocks:
   - `Loaded context (problem only)`: problem framing, constraints,
     prior evidence. NO user solution recommendations.
   - `User's prior thinking`: any solution leanings, prescribed
     mechanisms, or preliminary recommendations from inputs.

   Phase 2 specialists receive ONLY the problem-only block. The
   orchestrator retains the prior-thinking block for Phase 4 narrative.
   Convergence with prior thinking is fine and worth noting; the goal
   is to NOT pre-load the user's answer into the specialists' question.

5. **Output**: refined problem (1-3 sentences with constraints) plus
   the two context blocks. Not shown to user.

### Phase 2: Diverge (internal, parallel)

Generate 3-5 distinct candidate approaches via parallel specialists.

For the full protocol (approach-count heuristic, specialist routing
table, fallback logic, and the complete specialist prompt template),
see [specialists.md](specialists.md).

Key invariants:
- Launch all specialists in a single message with multiple Agent tool
  calls. Serializing defeats parallelism.
- Specialists receive ONLY the problem-only context block. Bias-stripping
  is structural, not advisory.
- `code-reviewer` is always in the roster as the broadest-shape lens.
- Each specialist returns 1-2 approaches with Shape, Context, Steelman,
  Tradeoff, Codebase touch points, Verifiability, Verification path,
  and Consequence per approach (the format Phase 3 consumes).

### Phase 3: Evaluate (internal)

Rank approaches on the multi-criteria scoring matrix, then run a
mandatory skeptic pass on the top-3.

For the full scoring matrix (8 columns: Context, Effort, Risk,
Reversibility, Fit, Rules-alignment, Verifiability, Consequence), the
composite Score formula, the override rules, AND the Phase 3c
skeptic dispatch prompt with edge-case + failure handling, see
[scoring-matrix.md](scoring-matrix.md).

Key invariants:
- Composite Score is a tiebreaker; the qualitative tradeoff drives the
  winner pick.
- An approach that contradicts a `.claude/rules/*.md` rule is forced
  to last place regardless of Score.
- Consequence=high AND Verifiability=low is also forced to last place
  (trust-asymmetry override).
- The skeptic pass (`mx2-skeptic`) runs on the top-3 by Score.
  Mandatory, not opt-in. Findings fold into Phase 4 as a `Skeptic Lens`
  block. When fewer than 3 approaches survive Phase 2, run on whatever
  exists. If dispatch fails, note "Skeptic Lens unavailable" and
  proceed; do not block on advisory tooling.

### Phase 4: Present

First synthesis-level output the user sees. No automatic gate fires
between Phase 3 and Phase 4: ranking + skeptic dissent + recommended
winner are presented together, and the human reading the output makes
the iterate-or-proceed call.

```markdown
## Ideate: <problem topic, 3-8 words>

### Refined Problem
<1-3 sentences>

### Approaches

| # | Approach | Context | Effort | Risk | Rev | Fit | Rules | Verif | Conseq | Score |
|---|----------|---------|--------|------|-----|-----|-------|-------|--------|-------|
| 1 | <title> | legacy | M | low | easy | match | aligned | high | low | 21 |
| ... |

(Column key: Rev = Reversibility, Verif = Verifiability, Conseq =
Consequence of wrong. Context is annotation, not numerically scored.)

Per-approach narrative (in Score order):

**N. <title>** (Score: <X>, Context: <Y>)
<Steelman + key tradeoff.>
Codebase touch points: <paths>.
Verification path: <how to validate this before committing>.

---

### Recommended Winner: Approach <N>
<1-3 sentences. State the Consequence-of-wrong / Verifiability pairing
explicitly so the user can sanity-check the asymmetry. Name the matrix
rows that drove the recommendation. The reader should understand why
this approach won without having to recompute the Score themselves.>

### High-Consequence Callout (only when any candidate has Consequence=high)
<Surface every Consequence=high approach with one-line "what could go
wrong". Even rejected high-consequence approaches deserve this; the
user may override the recommendation.>

### Prior Thinking Comparison (only when input contained a user solution recommendation)
<Compare specialist output against the user's prior framing. One of:
"converged on <prior approach> (positive confirmation)" OR "diverged;
recommended <winner> because <reason>" OR "produced an
adjacent-but-novel approach the prior was reaching toward".>

### Rejected Alternatives
<1 sentence per non-winning approach: why rejected + revisit-trigger
clause naming the condition under which this alternative becomes the
right choice. Preserve dissent in durable records.>

### Skeptic Lens
<Verbatim 🔻 block from Phase 3c. Always present (mandatory pass).
Include the "no concerns" line verbatim if that was the result.>

### Open Assumptions
<Any unresolved framing disagreements between mixed inputs, fuzzy
constraints, or other items the user should sanity-check.>

---

### Human Gate (you decide)

`/ideate` stops here. Read the ranked approaches, the recommended
winner, and the skeptic lens. Then make one of three calls yourself:

- **Proceed**: pick the recommended winner (or any other approach you
  prefer), use it as your implementation guide, and run `/review` on
  the resulting diff before committing. Use this when the top-1 has a
  clear gap to top-2 (Score gap >= 3) AND the skeptic surfaced no
  unresolved concern.
- **Iterate**: re-run `/ideate` with a narrower problem statement.
  Use this when the top-3 cluster at similar Score with no clear winner
  (gap to top-2 < 3), the skeptic surfaced an unaddressed concern that
  a narrower problem framing could resolve, or all approaches share a
  weakness (e.g., all low-Verifiability with med+ Consequence).
- **Escalate**: route to a different skill or a senior engineer. Use
  this when the candidates are not actually divergent (Phase 2
  underperformed), the root cause is unknown (try `/investigate`
  first), the problem needs domain expertise outside the specialist
  roster, OR a second `/ideate` pass produced the same cluster issue
  (iteration is not collapsing the candidate space). The
  Consequence=high override already excludes the canonical
  workstream-killer combination from the top-1 slot; escalation
  triggers when ideation itself is the wrong tool, not when the top-1
  is risky.

Weigh the skeptic dissent against the recommendation directly. The
🔻 block names what the convergent ranking may have assumed away;
your job is to decide whether the assumption holds in your context.
```

### Phase 5: Handoff (no auto-invocation)

Stop after Phase 4. Do NOT chain into another skill automatically.
The user reads the table, picks a winner (which may differ from the
recommendation), and acts on it manually.

Rationale: the user may refine the winner's phrasing, combine elements
of two approaches, or reject the table entirely. Auto-invocation
removes that judgment, and the iterate-decision IS the high-judgment
ask of this skill; making the human own it is the whole point.

## Distinctions

- **vs `/review`**: `/review` fans out specialist agents over an
  existing diff. `/ideate` runs specialists generating different
  approaches to the same problem. `/ideate` runs BEFORE there is a
  diff; `/review` runs AFTER.
- **vs `/investigate`**: `/investigate` traces backward from a known
  failure to surface contributing factors and a leading hypothesis.
  `/ideate` runs over an open design question with no known failure.
  If `/investigate` reveals multiple fix candidates, THEN `/ideate`
  over those candidates.
- **vs `/enrich`**: `/enrich` loads context for a known ticket or PR.
  `/ideate` consumes that context (and may invoke `/enrich`-style
  loading internally in Phase 1) and produces ranked approaches.

## When NOT to Use

- **One obvious approach exists**: skip `/ideate` and go straight to
  implementation. `/ideate` is overhead when the divergent step has
  only one candidate.
- **Code review or PR context**: use `/review`.
- **Bug investigation**: use `/investigate`. If the investigation
  reveals multiple fix candidates, THEN `/ideate` over those candidates.

## Rules

- **No intermediate output.** Phases 1-3 are invisible. Phase 4 is the
  first synthesis-level visible output.
- **Parallel is mandatory.** Phase 2 specialists run in parallel via
  a single message with multiple Agent calls. Serializing defeats the
  point.
- **No auto-invocation of other skills.** Phase 5 is a suggested next
  step, not a tool call. The human decides.
- **Strip user solution bias before Phase 2.** Specialists receive only
  the problem-only context block. Convergence with prior thinking is a
  positive confirmation signal; same conclusions are fine, but
  pre-loading the user's answer into the specialists' question
  defeats the purpose.
- **Mixed-input precedence is fixed.** Inline text > Slack/transcript >
  Confluence > Jira. Surface disagreements in Open Assumptions.
- **Steelman, do not strawman.** Each approach in Phase 2 must be the
  strongest version of itself.
- **Distinct approaches, not variants.** Merge near-duplicates during
  Phase 2 collection.
- **Score is a tiebreaker, not the rationale.** Composite Score drives
  ordering; the qualitative tradeoff drives the winner pick.
- **Rules contradictions always lose.** Forced last place regardless
  of Score. Existing rules encode hard-won lessons.
- **Consequence-of-wrong outweighs upside-of-right.** One wrong call
  that destroys a workstream costs more than nine right calls. The
  Consequence=high / Verifiability=low override forces last place
  regardless of how well the approach scores elsewhere. When two
  approaches tie on the rest of the matrix but differ on Consequence,
  the lower-Consequence approach wins decisively.
- **Skeptic pass is mandatory, not optional.** Phase 3c runs on the
  top-3 by Score (or fewer if Phase 2 produced fewer).
- **Iterate decision belongs to the human.** No automatic
  iterate/proceed gate fires. The skill presents and stops; the user
  weighs skeptic dissent against the recommendation and decides
  whether to act, re-run with narrower scope, or escalate.
- **Preserve dissent.** Rejected alternatives appear in Phase 4 with
  "why rejected" + revisit-trigger clause.
- **Calibrated for code-shaped problems.** The specialist roster, the
  Fit-to-codebase column, and the Verification-path framing assume
  the output is a codebase change. Non-coding mode is best-effort;
  several matrix columns become "N/A" and qualitative narrative
  carries more weight.

## Additional Resources

- [specialists.md](specialists.md): Phase 2 roster table, fallback
  logic, full specialist prompt template.
- [scoring-matrix.md](scoring-matrix.md): Phase 3 column definitions,
  composite Score formula, overrides, and the Phase 3c skeptic
  dispatch prompt.
- [walkthroughs.md](walkthroughs.md): two end-to-end examples.
