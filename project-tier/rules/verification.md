# Verification

This rule governs AI agent behavior during task completion. For what commands to run, see `build-commands.md`.

## Three Kinds of Verification

Current Claude models self-verify and self-correct while they reason, so telling one to re-read its own work adds cost without adding signal. That does not make this rule redundant: almost everything it asks for is evidence the model cannot produce by thinking harder. Sort a verification instruction into one of these three before deciding it is ceremony.

| Kind | Examples | Keep it? |
|------|----------|----------|
| Self-recheck | "Double-check your answer", "re-verify before responding", a second read-through of your own reasoning | No. The model already does this; a second instruction compounds it and burns tokens. |
| External-oracle | `pants test`, `pants check`, `pants lint`, a formatter diff, a query against live AWS or database state | Yes. No amount of reasoning substitutes for the command's output. |
| Cross-boundary | Reading the `git diff` a subagent produced instead of trusting its summary; confirming a cited claim against the source | Yes. The evidence lives outside the agent making the claim. |

Everything below this section is external-oracle or cross-boundary. The Gate, the Common Failure Modes table (the subagent row in particular), and Verification Reporting are not self-recheck ceremony, and a cleanup pass that trims "redundant verification steps" must leave them intact.

## The Gate

Do not claim work is complete without fresh evidence. Before any completion claim:

1. **Identify** what proves the claim (e.g., `pants test path/to/test.py` for "the test passes"; `pants check path/to/module.py` for "type errors are fixed")
2. **Run** the command in the current session
3. **Read** the output
4. **Verify** the output confirms the claim, then report the result

## Common Failure Modes

The most frequent ways "I claimed it was done" turns into "actually it was not":

| Claim | Required evidence | Insufficient |
|-------|------------------|--------------|
| Tests pass | Test command output: 0 failures, in this session | Previous run, "should pass" |
| Build succeeds | Build command exit code 0 | Linter passing, "logs look fine" |
| Linter clean | Linter output: 0 errors on the changed scope | Partial check, extrapolation |
| Formatting clean | Formatter output: 0 diffs on the changed scope (e.g. `pants fmt --check`, `pnpm format:check`) | "Looks fine in my editor" |
| Bug fixed | Test that reproduces the original symptom now passes | Code changed, assumed fixed |
| Regression test works | Watched it fail for the symptom: a symptom-specific test-first red, or the red-green-revert cycle (see below) | Test passes once |
| Subagent completed | VCS diff (`git diff`, `git status`) shows the expected changes | The subagent's own success report |
| Requirements met | Line-by-line checklist against acceptance criteria | "All my tests pass" |

The subagent row is load-bearing in subagent-heavy workflows. Subagents return summaries describing what they intended to do, not what they actually did. Always check the diff before reporting work as complete.

## Regression Test Verification

A test that "verifies a fix" is only verified itself if you watched it both fail and pass. There are two ways to get that evidence and you need one of them.

**Test written first** (the TDD path in `testing.md`): the red counts only if the test failed for the absence of the behavior it asserts. A collection error, a module-resolution failure (the usual red when the code does not exist yet), an import error, or a typo is not that red. When you have a symptom-specific red, nothing further is required.

**Test written after the fix was already in place, or a test-first red that was not symptom-specific**: nothing has shown yet that this test can fail for the reason it claims to cover, so run the red-green-revert cycle, once per guard the test covers.

1. Run the test; it must pass with the fix in place
2. Revert the fix; run the test again; it MUST FAIL
3. Restore the fix; run the test; it must pass

Skipping the revert leaves you with a test that passes, not a test that proves the fix is necessary. Tests that pass without a corresponding failure mode are documentation, not verification.

The revert cycle matters most when an AI wrote the production code and the test in the same pass. The test then encodes what the code does, so it passes on the first run whether or not the behavior is correct (see the "Tests as the agent's specification" section in `testing.md`).

## Verification Reporting

When making a completion claim, include verification evidence inline so the user can trust-but-verify:

- The command you ran (full, not paraphrased)
- The relevant excerpt of the output (not "all tests passed", but `34 passed, 0 failed, 2.1s` or equivalent)
- For subagent work: the diff range checked (`git diff origin/main -- path/to/file`) and a one-line summary of what changed

This rule exists because the workflow is heavily subagent-driven. Subagent self-reports are unreliable; the parent agent's claim depends on having actually verified the diff. Inline evidence makes that verification visible.

## Banned

These phrases substitute confidence for evidence. Do not use them as completion claims:

- "Should work now"
- "Probably passes"
- "Looks correct"
- "I believe this fixes the issue"

## Pre-existing Failures

Do not dismiss a test failure as unrelated to your change without evidence. Run the test, confirm it was failing before your change, then note it and move on.
