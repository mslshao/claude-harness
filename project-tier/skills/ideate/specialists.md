# Phase 2: Specialist Roster + Prompt Template

This file holds the heavy Phase 2 reference content for `/ideate`. SKILL.md
references it; do not duplicate content back into SKILL.md.

## Approach Count (Adaptive)

Choose the target count of approaches based on problem shape:

- **3 approaches** when the problem is well-bounded: refined input under
  100 chars OR bug-fix-shaped (specific error, single failure mode) OR
  has only 2-3 plausible solution spaces.
- **5 approaches** when the problem is open-ended design: refined input
  over 200 chars OR multiple acceptable solution spaces OR no obvious
  dominant approach.
- **4** is the default when neither extreme fits.

## Specialist Roster (Adaptive with Fallback)

Choose specialists based on problem-domain keywords from the refined
problem statement. Match against this keyword table; specialists with
multiple keyword hits should be prioritized over single-hit matches:

| Keyword pattern | Specialist |
|-----------------|------------|
| `security`, `auth`, `pii`, `audit`, `secret` | `mx2-security-auditor` |
| `observability`, `metric`, `log`, `trace`, `datadog`, `monitor` | `observability-reviewer` |
| `error`, `exception`, `silent`, `failure`, `retry` | `silent-failure-hunter` |
| `test`, `tests`, `pytest`, `mock`, `coverage`, `refactor`, `test-architecture` | `test-quality-reviewer` |
| (any code-structure problem) | `code-reviewer` |

Keyword matching is heuristic. When a keyword maps to multiple
specialists, include all that fit within the roster size cap.

**Roster size**: 3 specialists by default. Add a 4th if approach count
is 5 AND a second domain-relevant specialist is clearly indicated.

**Fallback when no domain keywords fire**: Use `code-reviewer` alone,
asking for 3-4 distinct approaches in a single specialist prompt. The
specialist prompt template (below) carries the divergent structure;
the agent is being asked to use its codebase-reading lens to surface
distinct candidate approaches, not to evaluate an existing diff.

**Fallback when only 1 keyword specialist fires**: Run that specialist
for 1-2 approaches AND `code-reviewer` for the remaining slots, so the
divergence roster always has 2+ lenses. Single-lens divergence has
correlated blind spots.

Do NOT include `mx2-skeptic` in the divergence roster; that agent is
reserved for the post-ranking pass in Phase 3c, and conflating the two
invocations produces ambiguous routing.

## Specialist Availability and Dispatch Fallbacks

All specialists in the keyword routing table above are available at
project tier today. The fallback table covers what to do when a
dispatch fails at runtime (agent missing, transient error, future
roster changes):

| Specialist | Fallback on dispatch failure |
|------------|------------------------------|
| `code-reviewer` | none needed (always available) |
| `test-quality-reviewer` | route to `code-reviewer` with test-focused prompt addendum |
| `observability-reviewer` | route to `code-reviewer` with observability-focused prompt addendum |
| `silent-failure-hunter` | route to `code-reviewer` with error-handling-focused prompt addendum |
| `mx2-security-auditor` | route to `code-reviewer` with security-focused prompt addendum |
| `mx2-skeptic` (Phase 3c only) | note "Skeptic Lens unavailable: <reason>" in Phase 4 output and proceed |

When any specialist dispatch fails, the orchestrator falls back to
`code-reviewer` with a topic-prefixed prompt addendum naming the
failed-specialist lens. The Phase 4 output records the dispatch
substitution in the Open Assumptions block so the user can see which
lens did NOT run.

## Parallel Dispatch (Mandatory)

Launch all specialists in a single message with multiple Agent tool
calls. Do not serialize.

Each specialist gets:
- The refined problem statement (from Phase 1).
- The `Loaded context (problem only)` block (from Phase 1).
  **Do NOT include the `User's prior thinking` block.** Specialists must
  originate approaches from the problem, not from the user's prior
  framing. Bias-stripping is structural.
- A focused prompt asking for 1-2 distinct approaches with a steelman.
- The approach-count target so specialists know how aggressive to be.

## Specialist Prompt Template

```
You are brainstorming approaches to a problem. Generate 1-2 distinct
candidate approaches from your specialist lens. Each approach must be:

- DISTINCT: structurally different from other plausible approaches, not a
  small variant. If you can describe two approaches with the same noun
  phrase ("use a queue" vs "use a different queue"), they are the same
  approach.
- STEELMANNED: present the strongest version, including why it would
  succeed. Do not generate weak approaches just to fill a slot.
- SCOPED: name files, services, or modules where possible. Avoid
  hand-waving ("add a microservice" without saying which boundary).
- ORIGINATED FROM THE PROBLEM, NOT FROM A PRIOR ANSWER: you are seeing
  only the problem framing, not any prior recommendations the user
  has sketched. Your approaches must be your own analysis of the
  problem space. If your independent analysis happens to converge
  on what the user already considered, that is a positive
  confirmation signal; but actively seek approaches the user has
  not considered. Same conclusions are acceptable; ONLY same
  conclusions defeat the purpose of /ideate.

Problem:
<refined problem statement>

Loaded context (problem only):
<context block from Phase 1; problem framing, constraints, prior
evidence; NO user solution recommendations>

For each approach, return:

### Approach N: <3-8 word title>
**Shape**: 1-2 sentence description of what this approach actually is.
**Context**: greenfield / legacy / hybrid. Greenfield = building
net-new with few constraints. Legacy = adjusting existing production
code with constraints from data, callers, compatibility. Hybrid = both.
**Steelman**: Why this approach would succeed. What makes it the right
tool.
**Tradeoff**: The cost of choosing this. Be honest; do not hide it.
**Codebase touch points**: Files, services, or patterns this would
modify or follow. Cite specific paths where possible.
**Verifiability**: high / med / low. How confidently could we validate
this approach works BEFORE committing? high = working reference code
exists or prototype under 1 hour. med = similar patterns; prototype
1-3 hours. low = novel; validation requires shipping or multi-day
prototype.
**Verification path**: 1-2 sentences naming what we would do in under
an hour to gain confidence this approach works. Cite the specific
file, command, or pattern to inspect/prototype against. This is the
"how would I test the steelman" before committing.
**Consequence of wrong**: low / med / high. If we ship this and it
turns out to be wrong, what is the cost? low = single PR revert. med
= data migration to undo, customer-visible regression. high = data
corruption, irreversible state, trust loss.

Generate 1-2 approaches. Do NOT rank them; the orchestrator handles
ranking across all specialists.
```

## Manual Re-run on Narrower Scope

`/ideate` does not iterate automatically; the human reading Phase 4
output decides whether to re-run with narrower scope. When you do
re-run, refine the problem statement to:

- Name the constraint that distinguishes the desired approach family
  (e.g., "retrofit on 2M existing docs" rather than just "handle
  re-ingestion"). The previous round's top-3 cluster usually reveals
  which constraint was missing.
- Resolve any framing disagreements that surfaced in "Open Assumptions"
  in the prior round.
- If the prior round's skeptic flagged an unaddressed concern, fold
  the concern into the problem statement so Phase 2 specialists can
  produce approaches that address it.

The second pass is a fresh `/ideate` invocation with a narrower
problem; it is not a continuation of the prior pass. Phase 1 re-runs,
Phase 2 generates new approaches against the narrower problem, and
Phase 3 ranks the new set.
