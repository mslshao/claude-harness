# Self-Check Gate

For EACH bead, answer these questions internally. If any answer is "no", revise before presenting.

## All Beads

1. **Actionable without context?** Could an agent pick this up cold from `bd show` and start working? If it needs "see also" or "ask Michael about", it's not ready.

2. **Right size?** Is this completable in one focused session (30-120 min)? If not, split.

3. **Dependencies are minimal and correct?** Does this bead actually need its blockers to complete first, or could it be worked in parallel with a stub? Fewer dependencies = more parallelism.

4. **Negative decisions documented?** For each bead, is there at least one approach that was considered and rejected? Document it as "Why NOT X" in design notes. Examples: "No model_validator because Apex has no cross-field validation", "Do NOT use cqc_engine.OperatorType; these operator strings must match Apex values exactly." Negative decisions prevent future agents from re-introducing things that were deliberately excluded.

## Task Beads (additional)

5. **Boundaries clear?** Can you draw a line around exactly which files are created/modified? If the scope bleeds into another bead, the boundary is wrong.

6. **Acceptance is testable?** Could you write a script or command that checks "done"? "Works correctly" is not testable. "pants test src/python/mx2/foo/tests -- -xvs passes" is testable.

7. **Design references real code?** Does the design field point to specific files/lines in the MX2 codebase, or is it generic advice? Generic → find the real reference.

## Memory/Decision/Discovery Beads (additional)

8. **Reconstructable?** Could a cold-start agent reconstruct the key conclusions from this bead alone, without reading the original conversation?

9. **Rejected alternatives documented?** Are approaches that were considered and rejected listed with reasons? This is what prevents re-litigation.

10. **Actionable boundary?** Is it clear what an agent should DO with this information? "Absorb" is not enough; specify: "When working on X, consult this for Y constraint."
