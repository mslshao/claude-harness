# Phase 3: Scoring Matrix

The deterministic ranking layer of `/ideate`. Each approach gets scored
across 8 columns; one is annotation, seven are numeric. SKILL.md
references this file; do not duplicate here.

## Column Definitions

| Criterion | Values | Definition |
|-----------|--------|------------|
| **Context** | greenfield / legacy / hybrid | Is this approach building net-new (`greenfield`, fewer constraints), adjusting existing production code (`legacy`, many constraints from existing data, callers, compatibility), or both (`hybrid`)? Annotation only; not numerically scored, but it changes how the user reads the other columns (legacy + S Effort is impressive; greenfield + S Effort is expected). |
| **Effort** | S / M / L / XL | Implementation effort. S = under 1 day, M = 1-3 days, L = 3-7 days, XL = over a week. Include test + review burden. |
| **Risk** | low / med / high | Probability of failure or production incident if shipped. Consider blast radius. |
| **Reversibility** | easy / hard | Can we roll back if it does not work? "easy" = single commit revert. "hard" = data migrations, schema changes, downstream consumer impact. |
| **Fit** | match / new | Does this approach match existing codebase patterns (`match`), or introduce a new one (`new`)? Cite the matched pattern or note the divergence. |
| **Rules alignment** | aligned / contradicts / N/A | Is the approach covered or recommended by an existing `.claude/rules/*.md` rule? Does it contradict one (e.g., a Redshift query in operational code contradicts `architecture.md` Data Store Selection)? |
| **Verifiability** | high / med / low | How confidently can we validate this approach works BEFORE committing to it? `high` = working reference code in the codebase that mirrors this approach, or a prototype achievable in under 1 hour. `med` = similar patterns exist; prototype 1-3 hours. `low` = novel approach; validation requires shipping or a multi-day prototype. |
| **Consequence of wrong** | low / med / high | If this approach turns out to be wrong AFTER shipping, what is the cost? `low` = single PR revert, no data loss, no customer impact. `med` = data migration to undo, customer-visible regression. `high` = data corruption, irreversible state, trust loss, lost workstream. |

## Composite Score Formula

Map each scored column to a numeric value, then sum. Higher is better.

- Effort: S=4, M=3, L=2, XL=1
- Risk: low=4, med=2, high=1
- Reversibility: easy=3, hard=1
- Fit: match=3, new=1
- Rules alignment: aligned=2, N/A=1, contradicts=-2
- Verifiability: high=3, med=2, low=1
- Consequence of wrong: low=3, med=1, high=-3

(Context is annotation, not scored. It modifies how the user reads
Effort and Fit.)

Max score = 4+4+3+3+2+3+3 = 22. Use the Score column to break ties.
Do not present the formula to the user; the narrative rationale (see
Phase 5) is what the user reads.

## Asymmetric Weighting of Consequence

The high=-3 penalty is intentional and reflects the trust-asymmetry
principle: one wrong call that destroys a workstream outweighs nine
right calls. When two approaches tie on the rest of the matrix but
differ on Consequence, the lower-Consequence approach wins decisively.

## Composite Overrides (force last place regardless of Score)

Any ONE of these overrides forces an approach to last place:

1. **Rules alignment = `contradicts`**: existing rules encode hard-won
   lessons; do not route new code around them.
2. **Consequence = `high` AND Verifiability = `low`**: high-blast-radius
   approaches with no way to validate before shipping are the canonical
   workstream-killer. Never recommend without the user explicitly
   acknowledging both columns.

Surface every override explicitly in the Phase 5 rationale.

## Phase 3c: Mandatory Tenth-Man Stress-Test on Top-3

After ranking, dispatch `mx2-tenth-man` on the top-3 by Score. This is
NOT opt-in; the tenth-man pass is the canonical adversarial check that
catches the class of issue the convergent ranking assumes away.

```
Agent(
  subagent_type="mx2-tenth-man",
  description="Adversarial stress-test of top-3 ideate approaches",
  prompt="Ask naive, dumb, or obvious-but-unasked questions about these
  three candidate approaches. The user is trying to choose among them.
  Surface risks the convergent ranking assumed away. Pay special
  attention to: (a) Consequence-of-wrong assumptions (could this be
  worse than the score suggests?), (b) Verifiability claims (can we
  actually validate this before shipping?), (c) Context misclassifications
  (is the legacy/greenfield/hybrid annotation right?), (d) Distinctness
  (are these actually orthogonal, or near-duplicates dressed up
  differently?).

  Top-1 (Score: <N>): <approach 1 block>
  Top-2 (Score: <M>): <approach 2 block>
  Top-3 (Score: <L>): <approach 3 block>

  Return your standard 🔻 prefix block. Do NOT recommend a winner;
  surface concerns only."
)
```

Fold the tenth-man output into the Phase 5 presentation as a
`### Tenth-Man Lens` section AFTER the recommended winner. If the
tenth-man returns `🔻 No concerns from this lens`, still include the
section with that exact line so the user can see the pass ran.

### Edge case: fewer than 3 approaches survived Phase 2

When fewer than 3 approaches survived Phase 2 (rare; usually only
happens when Phase 2 produced near-duplicates that got merged), run
tenth-man on whatever exists (top-1 or top-2). The pass still runs;
the prompt's "three candidate approaches" wording becomes "two
candidate approaches" or "the single candidate".

### Failure handling

If the tenth-man dispatch fails (agent missing, transient error),
note the failure in the Phase 5 output as a one-line
"Tenth-Man Lens unavailable: <reason>" and proceed. Do not block
ideation on advisory tooling, but do not silently drop the pass
either; the user must know the adversarial check did not run.

The Phase 4 decision-maker gate receives the tenth-man output (or
the unavailable-reason) as input. A missing tenth-man pass is itself
a signal the gate considers: PROCEED on a top-1 that was not
adversarially checked carries lower confidence.
