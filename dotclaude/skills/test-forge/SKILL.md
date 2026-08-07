---
name: test-forge
description: Generate behavioral tests with iterative quality review. Use when the user asks to "forge tests", "generate tests", "create tests for this module", or needs tests that verify domain logic, not framework mechanics.
argument-hint: "[source file or module path]"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Agent", "Write", "Edit"]
---

# Test Forge

Generate high-quality behavioral tests for MX2 modules by running the `test-generator`
agent and then feeding its output through the `test-quality-reviewer` agent in a feedback
loop. Stop when the reviewer is satisfied or after 3 iteration cycles.

HARNESS CONSTRAINT (verified 2026-06-09): this skill must run in the main
conversation, never as a `context: fork` execution; forked skill executions are
subagent contexts with no Agent tool, so the generator/reviewer loop would
silently degrade to roleplay. When invoked FROM a subagent (e.g. launch-tester
via the Skill tool), the Agent dispatches in Phases 2-4 are unavailable: do the
generation and review in-context yourself and say so in the report; the
orchestrator's checkpoint review covers the independent-reviewer gap.

## Input

One of:
- A source file path (e.g., `src/python/mx2/intake/processor.py`)
- A module directory (e.g., `src/python/mx2/intake/`)
- A class or function name with enough context to locate it

If ambiguous, use Glob/Grep to resolve before proceeding.

## Phase 1: Understand the Target

Before generating anything, read the source code. Identify:
- **Public interface**: Functions/methods/classes exposed
- **Domain behavior**: What this module DOES in business terms
- **Decision points**: Where the code branches, what conditions change outcomes
- **Error modes**: What can go wrong, what exceptions are raised
- **External boundaries**: AWS, Salesforce, HTTP services touched (see [test-constraints.md](test-constraints.md) for faking strategy)
- **Existing tests**: Check for test files already present

Produce an internal behavioral inventory (not shown to user).

## Phase 2: Generate Tests

Invoke the `test-generator` agent via the Agent tool. Your prompt MUST include:
1. The source file path(s)
2. Your behavioral inventory from Phase 1
3. The constraints from [test-constraints.md](test-constraints.md) (copy verbatim)
4. The engineering lead's 4 test review questions as the generation lens (Code Review Guide
   for Humans, Confluence 5684789249). Tell the generator the tests it
   produces will be evaluated against these criteria at Phase 3, so write to
   the bar:

   - Is the behavior being tested obvious just from the test's name?
     ("test name is a contract" per `.claude/rules/testing.md`)
   - Is the test tightly coupled to implementation? (The refactor test: a
     complete rewrite that preserves behavior should not break the test.)
   - Is every mock/patch/stub necessary? Mocks ONLY for I/O isolation.
     boto3 is auto-faked via moto; HTTP via `responses` fixture. Do not
     mock above the infrastructure boundary. `unittest.mock` is banned.
   - Could someone rewrite the implementation and still have the test
     verify correctness without modification?

   Baking these into the generation prompt reduces the iteration-loop load
   at Phase 3-4 (test-quality-reviewer already enforces them; getting them
   right on first pass shortens the cycle).

## Phase 3: Quality Review

Invoke the `test-quality-reviewer` agent via the Agent tool with:
1. The test file path(s) created in Phase 2
2. The source file path(s) being tested
3. Instruction: "Review these tests. Return your standard severity-triaged findings."

## Phase 4: Iterate or Accept

- **0 findings**: Done. Proceed to Phase 5.
- **Findings exist**: Fix CRITICAL and WARNING findings directly using Edit. Re-invoke
  reviewer. Maximum 3 cycles.
- SUGGESTION findings about missing tests: note but skip (coverage, not quality).

## Phase 5: Verify

Run `pants test <test_file_path>`. Fix failing tests and re-run, with a cap of
3 fix attempts; after the third failure, stop and report `pants test: FAIL`
in the Phase 6 report with the failing output. NEVER loosen, weaken, or delete
an assertion to force green; that defeats the quality loop this skill exists
for. If an assertion genuinely must change, change it and re-run the Phase 3
review on the changed test before counting it green.

## Phase 6: Report

```
## Test Forge: <module name>

**Generated**: <test file path>
**Iteration cycles**: <N> (max 3)
**Tests**: <count> passing
**pants test**: PASS/FAIL

### Behaviors Covered
- <behavior 1>: test_name_1, test_name_2

### Not Covered (out of scope or deferred)
- <behavior or edge case>: reason

### Quality Review Cross-References
- <any cross-references from the reviewer to other agents>
```

## Rules

- Do NOT show intermediate iterations. User sees Phase 1 status and Phase 6 report.
- Do NOT generate tests for Pydantic serialization, FastAPI framework behavior, or fixture wiring.
- If the source module has no testable behavior, say so and stop.
- If existing tests already cover the module, review THOSE instead of generating new ones.

## Additional Resources

- For test constraints and faking strategy, see [test-constraints.md](test-constraints.md)
