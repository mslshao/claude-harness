# Phase 4 Approval-Gate Plan Template

The converged plan format the user sees at Phase 4 (the first synthesis-level
user-facing output). The SKILL.md Phase 4 section points here. This is a
user-facing presentation template, not a downstream-parsed contract; the
load-bearing structural invariants (hard stop, mandatory sections, ESCALATE-ROUTE
conditional) remain in SKILL.md Phase 4 + Rules.

```markdown
## Launch Plan: [topic, 3-8 words]  (low-confidence)?

[Suffix `(low-confidence)` on the H2 IF the Phase 3.6 gate forced a
low-confidence PROCEED (2 ITERATE rounds hit the cap, or user opted out
of ESCALATE-QUESTIONS with "you decide"). Add a "Low-confidence reason:"
line at the end of Summary stating which path triggered it.]

### Summary
[2-5 sentences: what this builds, design decisions, key constraints]

### Iteration Log
[Always present even when Round 0 was final, so the user sees the gate
ran. List each round with verdict + action taken:]
- Round 0 (initial): N work items drafted; DELTA_CATEGORY=<X>.
- Round 1 (if any): VERDICT (REASON). Action: <what changed>.
- Round 2 (if any): VERDICT (REASON). Action: <what changed>.
- Final verdict: PROCEED | LOW-CONFIDENCE | ESCALATE-ROUTE.

### Convergence Delta  [CATEGORY: CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT]
> [What changed during stress-testing. 2-4 bullets showing modifications
> from challenge/consult. The CATEGORY tag is load-bearing: CONFIRMED
> means specialists agreed with concrete evidence (not punted);
> MAJOR_REVISIONS or SCRAPPED_AND_REBUILT means the original framing
> did not survive.]

### Prior Thinking Comparison  [only when INPUT_MODE = mechanism-prescribed]
[Surface how the converged plan compares to the ticket's prescribed
mechanism. One of:
- "Specialists agreed the prescribed mechanism is right. <Brief evidence.>"
- "Specialists refined the prescribed mechanism: <what changed>"
- "Specialists recommended a different mechanism: <X>. <Why.>"
- "Specialists recommended scrapping the prescribed mechanism: it
  should be folded into <Y> as a feature of <Y>, not a new noun."
  (canonical Fulfillment-vs-Coverage outcome)
This section makes mechanism-vs-feature decisions visible BEFORE the
agent team starts writing code. Omit when INPUT_MODE = problem-framed.]

### Skeptic Lens
[Verbatim 🔻 block from Phase 3.5. Always present (the pass is
mandatory). If returned "🔻 No concerns from this lens", include that
line verbatim so the user sees the pass ran.]

### Work Items
[For each item in dependency order:]

#### [N]. [Title]
**Type**: [task/feature/bug]
**Agent**: [implementer | tester | flex-{role}]
**Phase**: [A | B | C | ...]
**Context**: [greenfield | legacy | hybrid]
**Depends on**: [item numbers or "none"]

[Description: 2-4 sentences.]

**Acceptance criteria:**
- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

**Verification path:** [How the implementer (and orchestrator at
checkpoint gating) will know this is correct BEFORE committing. Cite
specific test, command, or pattern. 1-2 sentences.]

**Consequence of wrong:** [low | med | high. If high, must have a
matching Verification path OR explicit risk-reduction note.]

---

### Agent Roster
| Agent | Role | Phase | Specialist access |
|-------|------|-------|-------------------|
| implementer | [scope] | [phase] | mx2-code-reviewer, mx2-silent-failure-hunter |
| tester | [scope] | [phase] | test-quality-reviewer, /test-forge |
| flex-infra | [scope] | [phase] | mx2-devops-build-deploy |

### Phasing
[Phase diagram with gates:]
Phase A: [agents] → Gate: [criteria] → Phase B: [agents] → ...

### Commit Strategy
[One commit | N commits at behavior boundaries. Explain the gates.]

### Open Assumptions
[FRAGILE/UNVERIFIABLE assumptions the user should confirm. Include any
mixed-input disagreements from Phase 1. Omit only if none.]

---

### OR: Escalation: No Agent Team Dispatched  [only when final verdict was ESCALATE-ROUTE]
[Replaces the Work Items / Agent Roster / Phasing / Commit Strategy
sections when the Phase 3.6 gate fired ESCALATE-ROUTE. 2-3 sentences
naming the SUGGESTED_NEXT_SKILL and the reason no agent team is being
dispatched. Format:

"The launch gate fired ESCALATE-ROUTE: <reason from gate>. No agent
team is being dispatched; the suggested next step is
<SUGGESTED_NEXT_SKILL: /converge, /ideate, or /investigate>. The draft
work items are preserved above for reference, but /launch is not the
right tool for this ticket yet."

The Iteration Log + Convergence Delta + Prior Thinking Comparison +
Skeptic Lens are still shown so the user understands WHY the gate
refused to launch.]

---

[When final verdict is PROCEED or LOW-CONFIDENCE:]
**Approve?** Reply "yes" to start execution, or provide feedback to revise.

[When final verdict is ESCALATE-ROUTE (replaces "Approve?" line):]
**No agent team will be dispatched.** Run the suggested next skill
(`<SUGGESTED_NEXT_SKILL>`) instead, or provide feedback if you believe
`/launch` is still the right tool here.
```
