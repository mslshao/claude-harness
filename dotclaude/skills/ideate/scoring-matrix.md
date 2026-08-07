# Phase 3: Scoring Matrix

The deterministic ranking layer of `/ideate`. Each approach gets scored
across 9 columns; one is annotation, eight are numeric. SKILL.md
references this file; do not duplicate here.

## Column Definitions

| Criterion | Values | Definition |
|-----------|--------|------------|
| **Context** | greenfield / legacy / hybrid | Is this approach building net-new (`greenfield`, fewer constraints), adjusting existing production code (`legacy`, many constraints from existing data, callers, compatibility), or both (`hybrid`)? Annotation only; not numerically scored, but it changes how the user reads the other columns (legacy + S Effort is impressive; greenfield + S Effort is expected). |
| **Effort** | S / M / L / XL | Implementation effort. S = under 1 day, M = 1-3 days, L = 3-7 days, XL = over a week. Include test + review burden. |
| **Risk** | low / med / high | Probability of failure or production incident if shipped. Consider blast radius. |
| **Reversibility** | easy / hard | Can we roll back if it does not work? "easy" = single commit revert. "hard" = data migrations, schema changes, downstream consumer impact. |
| **Fit** (codebase pattern) | match / new | Does this approach match existing codebase patterns (`match`), or introduce a new one (`new`)? Cite the matched pattern or note the divergence. This is PATTERN fit, not goal fit (see the next row). |
| **Goal fit** | full / partial / weak | How completely does the approach deliver the user's STATED want, judged against the goal as the user framed it (not a lighter proxy)? `full` = delivers the stated outcome; `partial` = delivers a subset or a lighter proxy of it; `weak` = ships something adjacent that leaves the stated want largely undelivered. Cite the stated want. This is the counterweight to Effort and the Right-Sizing flag: proportionality catches OVER-building, Goal fit catches UNDER-delivering (the failure where the least-shipping candidate wins on Effort while delivering little of what was asked). When a `partial`/`weak` score traces to an UNDECLARED user constraint (a required autonomy floor, an expected frequency) rather than a real candidate limitation, do NOT just score it low: that is the Phase 4 ESCALATE-QUESTIONS-on-missing-constraint trigger, not a second re-diverge. |
| **Rules alignment** | aligned / contradicts / N/A | Is the approach covered or recommended by an existing `.claude/rules/*.md` rule? Does it contradict one (e.g., a Redshift query in operational code contradicts `architecture.md` Data Store Selection)? |
| **Verifiability** | high / med / low | How confidently can we validate the approach DELIVERS THE OUTCOME before committing? The validation must prove the CAPABILITY or DECISION is correct, not merely that the mechanism executes without error. `high` = working reference code that mirrors this approach AND demonstrates the outcome, or a prototype achievable in under 1 hour that proves the capability (e.g. the crash-resume actually resumes state; the ranking is actually correct). `med` = similar patterns exist; a capability-proving prototype is 1-3 hours. `low` = novel, OR the only available check proves the mechanism RUNS but not that the outcome is right; proving the capability requires shipping or a multi-day prototype. A path that shows only "it runs without error" is `low`, never `high`. |
| **Consequence of wrong** | low / med / high | If this approach turns out to be wrong AFTER shipping, what is the cost? `low` = single PR revert, no data loss, no customer impact. `med` = data migration to undo, customer-visible regression. `high` = data corruption, irreversible state, trust loss, lost workstream. |

## Composite Score Formula

Map each scored column to a numeric value, then sum. Higher is better.

- Effort: S=4, M=3, L=2, XL=1
- Risk: low=4, med=2, high=1
- Reversibility: easy=3, hard=1
- Fit: match=3, new=1
- Goal fit: full=3, partial=0, weak=-3
- Rules alignment: aligned=2, N/A=1, contradicts=-2
- Verifiability: high=3, med=2, low=1
- Consequence of wrong: low=3, med=1, high=-3

(Context is annotation, not scored. It modifies how the user reads
Effort and Fit.)

Max score = 4+4+3+3+3+2+3+3 = 25. Use the Score column to break ties.
The Goal-fit `weak=-3` mirrors the Consequence penalty: a candidate that
under-delivers the stated want cannot win on low Effort alone.
Do not present the formula to the user; the narrative rationale (see
Phase 5) is what the user reads.

## Asymmetric Weighting of Consequence

The high=-3 penalty is intentional and reflects the trust-asymmetry
principle: one wrong call that destroys a workstream outweighs nine
right calls. When two approaches tie on the rest of the matrix but
differ on Consequence, the lower-Consequence approach wins decisively.

## Right-Sizing Flag (Proportionality)

A FLAG, not just a principle. The minimal-viable candidate (Phase 2) is
the reference point. Compute the flag after ranking:

- **Fires when** the top-Score (recommended) approach is materially
  heavier than the minimal-viable candidate (more components, more new
  abstractions/code paths, or a full Effort tier higher) AND the
  minimal-viable candidate still delivers ~80% of the stated goal.
- **Weights harder** when Phase 1 set `SCOPE_SIGNAL` (the goal carried
  lightweight / simple / minimal / quick / for-most-users words).

When the flag fires, Phase 5 MUST surface it and the winner narrative
MUST justify the extra complexity against the minimal-viable variant
(what does each extra component buy?), or switch the recommendation to
the minimal-viable candidate. "We might need it later" does not justify;
the justification must be a STATED constraint (CLAUDE.md Scope
discipline / YAGNI).

## Goal-Fit Surfacing (symmetric to Right-Sizing)

The Right-Sizing flag catches OVER-building. Goal fit catches the inverse: a
top-Score approach with Goal fit = `partial` or `weak` MUST be surfaced in
Phase 5, and the winner narrative MUST state what of the stated want it leaves
undelivered (or the recommendation switches to a fuller-goal-fit candidate). A
candidate cannot win on low Effort while quietly under-delivering the want. When
the weak goal fit traces to an UNDECLARED user constraint (autonomy floor,
expected frequency), the Phase 4 gate ESCALATE-QUESTIONs on that constraint
rather than accepting the low score or re-diverging.

## Composite Overrides (force last place regardless of Score)

Any ONE of these overrides forces an approach to last place:

1. **Rules alignment = `contradicts`**: existing rules encode hard-won
   lessons; do not route new code around them.
2. **Consequence = `high` AND Verifiability = `low`**: high-blast-radius
   approaches with no way to validate before shipping are the canonical
   workstream-killer. Never recommend without the user explicitly
   acknowledging both columns.

Surface every override explicitly in the Phase 5 rationale.

## Phase 3c: Mandatory Skeptic Stress-Test on Top-3

After ranking, dispatch `mx2-skeptic` on the top-3 by Score. This is
NOT opt-in; the skeptic pass is the canonical adversarial check that
catches the class of issue the convergent ranking assumes away.

```
Agent(
  subagent_type="mx2-skeptic",
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

Fold the skeptic output into the Phase 5 presentation as a
`### Skeptic Lens` section AFTER the recommended winner. If the
skeptic returns `🔻 No concerns from this lens`, still include the
section with that exact line so the user can see the pass ran.

### Edge case: fewer than 3 approaches survived Phase 2

When fewer than 3 approaches survived Phase 2 (rare; usually only
happens when Phase 2 produced near-duplicates that got merged), run
skeptic on whatever exists (top-1 or top-2). The pass still runs;
the prompt's "three candidate approaches" wording becomes "two
candidate approaches" or "the single candidate".

### Failure handling

If the skeptic dispatch fails (agent missing, transient error),
note the failure in the Phase 5 output as a one-line
"Skeptic Lens unavailable: <reason>" and proceed. Do not block
ideation on advisory tooling, but do not silently drop the pass
either; the user must know the adversarial check did not run.

The Phase 4 decision-maker gate receives the skeptic output (or
the unavailable-reason) as input. A missing skeptic pass is itself
a signal the gate considers: PROCEED on a top-1 that was not
adversarially checked carries lower confidence.
