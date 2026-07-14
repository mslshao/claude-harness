# Phase 5 Present Template

The converged-plan format the user sees at Phase 5 (the first synthesis-level
user-facing output). The SKILL.md Phase 5 section points here. This is a
user-facing presentation template; the load-bearing structural invariants
(mandatory sections, ESCALATE-ROUTE conditional, deliverable adaptation) remain
in SKILL.md Phase 5 + Rules.

```markdown
## Converged Plan: [topic, 3-8 words]  (low-confidence)?

[Suffix `(low-confidence)` on the H2 IF the Phase 4.6 gate forced a
low-confidence PROCEED (2 ITERATE rounds hit the cap, or the user
opted out of ESCALATE-QUESTIONS with "you decide"). Add a
"Low-confidence reason:" line at the end of the Summary stating which
path triggered it. Without this signal, the user has no indication the
plan is provisional.]

### Summary
[2-5 sentences: what this plan accomplishes, how many work items, key design decisions]

### Iteration Log
[Always present even when Round 0 was final, so the user sees the
gate ran. List each round with verdict + action taken:]
- Round 0 (initial): N work items drafted; DELTA_CATEGORY=<X>.
- Round 1 (if any): VERDICT (REASON). Action: <what changed>.
- Round 2 (if any): VERDICT (REASON). Action: <what changed>.
- Final verdict: PROCEED | LOW-CONFIDENCE | ESCALATE-ROUTE.

### Convergence Delta  [CATEGORY: CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT]
> [What changed during stress-testing. 2-4 bullet points showing the
> most significant modifications from challenge/consult. The CATEGORY
> tag is load-bearing: CONFIRMED means specialists agreed with
> concrete evidence (not punted); MAJOR_REVISIONS or
> SCRAPPED_AND_REBUILT means the original framing did not survive.]

> **Findings triaged but not incorporated** [only when any exist]:
> [One line per Fix-next / Defer / Won't-fix finding from Phase 4 step 4,
> so the user sees what was consciously left out, not just what was
> fixed. Omit this block entirely when every finding was Fix-now.]

### Minimal-Viable Comparison  [only when SCOPE_SIGNAL present or the right-sizing flag fired]
[Show the minimal-viable 80/20 version of the goal next to the proposed
plan: what the minimal plan would deliver, and what each extra work item
or abstraction in the proposed plan buys beyond it. If the extra
complexity is not justified by a stated constraint, the plan should have
been right-sized in Phase 4 / the gate. Omit when no scope-signal and
the right-sizing flag did not fire.]

### Prior Thinking Comparison  [only when INPUT_MODE = mechanism-prescribed]
[Surface how the converged plan compares to the user's prescribed
mechanism. One of:
- "Specialists agreed the prescribed mechanism is right. <Brief
  evidence cited.>" (CONFIRMED outcome)
- "Specialists refined the prescribed mechanism: <what changed>"
  (MINOR_ADJUSTMENTS)
- "Specialists recommended a different mechanism: <X>. <Brief why.>"
  (MAJOR_REVISIONS)
- "Specialists recommended scrapping the prescribed mechanism: it
  should be folded into <Y> as a feature of <Y>, not a new noun."
  (SCRAPPED_AND_REBUILT, canonical Fulfillment-vs-Coverage outcome)
This section makes mechanism-vs-feature decisions visible BEFORE the
user commits to beads. Omit when INPUT_MODE = problem-framed.]

### Skeptic Lens
[Verbatim 🔻 block from Phase 4.5. Always present (the pass is
mandatory). If returned "🔻 No concerns from this lens", include that
line verbatim so the user can see the pass ran.]

### Work Items

[For each item in dependency order, using the format defined in
work-item-structure.md.]

---

### Dependency Graph
[ASCII representation showing execution order and parallelism]

### Open Assumptions
[Any FRAGILE/UNVERIFIABLE assumptions the user should confirm. Include
any mixed-input precedence disagreements from Phase 1. Omit only if
none.]

---

### OR: Escalation: No Plan Produced  [only when final verdict was ESCALATE-ROUTE]
[Replaces the Work Items / Dependency Graph / Open Assumptions
sections when the Phase 4.6 gate fired ESCALATE-ROUTE. 2-3 sentences
naming the SUGGESTED_NEXT_SKILL and the reason no plan is being
produced. Format:

"The convergence gate fired ESCALATE-ROUTE: <reason from gate>. No
plan is being produced; the suggested next step is
<SUGGESTED_NEXT_SKILL: /ideate, /investigate, or direct execution>.
The draft work items are preserved above for reference, but /converge
is not the right tool for this problem."

The Iteration Log + Convergence Delta + Prior Thinking Comparison
sections are still shown so the user understands WHY the gate
refused to converge.]

---

**Approve this plan?** Reply "yes" to create beads (with optional
human gate on implementation), or provide feedback to revise.
```
