# Granularity Heuristics

These rules help split beads correctly on the first pass:

- **One bead per data model cluster.** If you're creating Pydantic models that other beads depend on, that's its own bead. Don't mix model definition with business logic.
- **One bead per behavioral concern.** In the SObjectQualifier example: type-based dispatch is one concern, date formula evaluation is another, string matching with multi-value operators is a third. Don't lump them.
- **Tests go with their implementation bead** unless the test work produces
  **reusable test infrastructure** (fixtures, factories, corpus files, scenario
  databases) or requires **independent research** (e.g., "what edge cases exist
  in Apex date handling?"). In those cases, a separate test bead is acceptable.
  Rules:
  - Implementation bead's acceptance criteria still include basic smoke tests.
  - Test infrastructure beads CAN run in parallel with implementation (you can
    build a corpus before the parser exists).
  - Test scenario beads that verify implementation behavior MUST depend on the
    implementation bead.
- **Infrastructure/scaffolding is a separate bead only if it unblocks others.** If it's just "create the directory and BUILD file," fold it into the first real implementation bead.
- **Epic beads are for 3+ children.** For exactly 3 children, an epic is justified
  when ALL of: (1) children share a single, concrete end-to-end acceptance test,
  (2) no child is independently meaningful; they only deliver value as a group,
  (3) the epic's acceptance criteria are distinct from the union of child criteria
  (the epic adds integration-level validation no child owns).
  Don't create an epic wrapper for 2 tasks.

## Anti-Patterns to Avoid

- "Write tests for X" as a separate bead when the tests are just unit tests for X's implementation → fold into X's bead
- "Implement X" with no description → always fails the self-check
- Acceptance criteria that say "code works correctly" → not testable
- Design notes that say "follow MX2 patterns" without naming which patterns or which files → not actionable
- A bead that creates models AND implements logic AND writes tests for 5 different type branches → too big
- Dependencies that are actually preferences ("nice to have B before C") rather than hard blockers → remove them

## When the User Gives Feedback

If the user asks for changes after your first presentation, apply the change AND re-run
the self-check gate on all affected beads. Do not present beads that haven't passed.
