# Self-Review Protocol

## The pattern

After writing or modifying code, review your own work before presenting it. After each pass, fix what you find. If a pass produces no changes, you have converged. Stop early.

This protocol applies to code AND to executable specifications (commands, skills, agent definitions). It does not apply to explanations, reviews, or questions.

### Executable specifications

Files under `.claude/commands/`, `.claude/skills/`, `.claude/agents/` are instructions that other agents follow literally. They require the same rigor as code:

- Walk every decision branch for each caller type (interactive human, non-interactive agent). At every point where the spec says "ask", "prompt", or "list for user to pick", verify there is an explicit agent-path alternative.
- Verify API assumptions (field names, URL formats, parameter requirements) against actual tool schemas or documentation. Do not write CQL queries, response field paths, or URL patterns from memory.

### Small tasks (2 passes minimum)

Single function, config change, minor fix:

1. **Correctness.** Bugs, logic errors, typos, wrong assumptions? What inputs or conditions break this?
2. **Style.** Invoke the style-reviewer agent (or equivalent) on the changed files with Author Mode context: "CI has not run yet. Flag everything: style, types, lint, naming, and design issues. The goal is to pre-empt CI failures and catch design problems early."

### Large tasks (4 passes minimum)

New feature, refactor, multi-file change:

1. **Correctness.** Does it do what was asked? Logic flaws? Off-by-one errors?
2. **Clarity.** Can another developer understand this? Simplify naming, reduce complexity, match patterns in surrounding code.
3. **Edge cases.** Error conditions, boundary values, missing validation?
4. **Agent review.** Invoke the code-reviewer agent (or equivalent) on the diff with Author Mode context. If findings span multiple specialist domains (security, style, structure), use a multi-specialist consult skill instead of routing manually. Fix what comes back.

## Verification (every code change, no exceptions)

Run the project's lint+typecheck+test command against the targets you touched (`pants tlc <target>`, `pnpm checks`, equivalent). Fix anything YOU broke, including pre-existing tests that now fail because of your behavior changes (a mock-based test that asserted the old call pattern). If a test was failing before your change AND still fails the same way, note it and move on. Do not attempt to fix unrelated failures.

## Subagent result verification

A subagent's "completed" status is necessary but not sufficient evidence the work shipped. Read the result block: if it ends mid-thought, lacks a status section, or has no PR URL when one was expected, the subagent likely hit a turn limit. Inspect the worktree (`git status`, `git log -1`, PR state) before declaring done.

Recovery from a partial subagent run: re-dispatch a new subagent of the same type with a self-contained prompt that includes (a) the worktree path, (b) what the prior agent already did, (c) what remains, (d) explicit acceptance criteria. Do NOT take over the work in main; the dispatch loop is the right pattern. Iterate until the work is verified done.

## PR scope flag at implementer standup

When a code-writing subagent reports DONE on a PR with more than approximately 1000 lines added in a single commit, surface the size to the user BEFORE bot-review and pre-PR steps: the line count plus file breakdown (production vs test split), whether the work spans a single conceptual responsibility or multiple, and a recommended split if applicable. Do not just trust the implementer's "all AC met" if the scope is large. The canonical concern-split test: does the work map to multiple ratified design decisions (two separate tickets, two separate sub-beads in the same epic), or to one? Multiple equals split candidate.

## No speculation in PR descriptions

Test plan bullets, compatibility notes, and "expect this to happen" claims in the PR body must be verified before the description is written. If a test plan bullet says "expect these tests to need updates," run the tests first. Stale speculation costs a revision cycle and erodes reviewer trust. If the answer is genuinely unknown at write time, note "CI will verify" instead of guessing.

## Why this exists

A code-writing agent operating at machine speed will satisfy whatever bar you set. If the bar is "code that passes tests," you get code that passes tests; you do not get correct code. The self-review protocol is the bar-raising mechanism applied at the point of authorship, before the change goes to a reviewer or to CI. It catches the class of issue that CI does not (design smells, naming, missing edge cases) and reduces the friction of human review by handling the obvious feedback in advance.

The "2 vs 4 passes" split is not arbitrary. Small changes have small blast radii; one pass at correctness plus one pass at style is enough. Large changes have compounding error modes; four passes (correctness, clarity, edge cases, agent review) catches different classes of problem at each stage.

## Where it has limits

- The protocol assumes the author understands what "correct" looks like for the change. If acceptance criteria are unclear, the passes will rubber-stamp wrong work.
- Subagent-driven workflows can produce code so fast that even a 4-pass review feels expensive. The temptation to skip passes grows with throughput. The discipline holds when the cost of a missed bug is high; on prototype work where wrong is cheap, fewer passes is rational.
