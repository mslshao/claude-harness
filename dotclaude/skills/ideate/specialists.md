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

Choose specialists based on problem-domain keywords. Run the domain-matcher
output from Phase 1 against this routing table:

| Keyword pattern | Specialist |
|-----------------|------------|
| `security`, `auth`, `pii`, `audit`, `secret` | `mx2-security-auditor` |
| `observability`, `metric`, `log`, `trace`, `datadog`, `monitor` | `observability-reviewer` |
| `error`, `exception`, `silent`, `failure`, `retry` | `mx2-silent-failure-hunter` |
| `terraform`, `lambda`, `ecs`, `deploy`, `infra`, `build` | `mx2-devops-build-deploy` |
| `settings`, `config`, `pydantic`, `env` | `mx2-pydantic-reviewer` |
| `typescript`, `react`, `nextjs`, `frontend`, `ui` | `mx2-typescript-reviewer` |
| `pr`, `review`, `precedent`, `prior` | `mx2-pr-precedent` |
| `test`, `tests`, `pytest`, `mock`, `coverage`, `refactor`, `test-architecture` | `test-quality-reviewer` |
| (any code-structure problem) | `mx2-code-reviewer` |

**Default specialist** (always include): `mx2-tech-lead`. The tech lead
handles sense-making across the problem space and produces the
broadest-shape approaches.

**Roster size**: 3 specialists by default. Add a 4th if approach count
is 5 AND a second domain-relevant specialist is clearly indicated.

**Fallback** (when domain-matcher returns noise or no clear specialists
map): Use the default pair `mx2-tech-lead` + `mx2-code-reviewer`, with
each agent asked for 2 approaches (yielding 4 total). When the
approach-count target is 5, add `mx2-pr-precedent` for a third broad
lens. Do NOT include `mx2-skeptic` in the divergence roster; that
agent is reserved for the post-ranking pass in Phase 3c, and conflating
the two invocations produces ambiguous routing.

## Parallel Dispatch (Mandatory)

Launch all specialists in a single message with multiple Agent tool
calls. Do not serialize.

## Minimal-Viable Candidate (Mandatory, Set-Level)

The candidate pool MUST contain a minimal-viable approach, explicitly
labeled as such in its title: the smallest thing delivering ~80% of the
STATED goal (extend the existing path, the off-the-shelf option, the
"do nothing new" path). Reason: every specialist is asked to steelman,
which biases the pool toward elaborate approaches; without a simple
anchor on the table, the ranking cannot pick simple even when simple is
correct.

Source it explicitly: instruct `mx2-tech-lead` (always in the roster)
to make ONE of its approaches the minimal-viable candidate, steelmanned
like any other (the strongest case for the ~80% version, not a strawman
set up to lose). After collection, if no candidate is a genuine
minimal-viable, the orchestrator synthesizes one and adds it to the pool
before Phase 3 ranking. It counts toward the 3-5 target and is the
reference point for the Phase 3 right-sizing flag.

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

## ITERATE Re-dispatch (called from Phase 4b)

When Phase 4 returns ITERATE with a WEAK_DIMENSION, re-dispatch with the
same roster plus an additional instruction targeting the weak dimension:

- WEAK_DIMENSION = `verifiability`: "Each approach must include a
  verification path achievable in under 1 hour before committing to it."
- WEAK_DIMENSION = `consequence`: "Each approach must minimize blast
  radius; prefer reversible / additive changes over destructive ones."
- WEAK_DIMENSION = `distinctness`: "Generate approaches that are
  structurally different from these existing candidates: <list>. Do
  NOT refine the existing approaches; produce orthogonal alternatives."
- WEAK_DIMENSION = `effort` or `fit`: "Generate approaches that
  explicitly trade <X> for <Y>: <list of current top-3 with their
  tradeoffs>."

Merge new approaches into the candidate pool. Re-score in Phase 3a-b.
Re-run skeptic (Phase 3c). Re-gate (Phase 4a).
