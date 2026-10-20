# review-default-fanout-all-true-signals

**What it was.** The default that `/review` dispatched every agent whose signal was true. Its wording in `~/.claude/skills/review/SKILL.md` at hash 595190c7:

- Line 6 (description): `fanned out to twelve review agents; severity-grouped`
- Line 286 (step 3): `3. **Fan out in parallel.** Single message with up to eleven Agent tool calls.`
- Step 4: "Dispatch the triggered agents in a single parallel message", with no limit on how many triggered.

Agents this takes out of the default on a non-payments diff: `test-quality-reviewer`, `silent-failure-hunter`, `typescript-reviewer`, `git-historian`, `blast-radius-reviewer`, `skeptic`, `module-cohesion-reviewer`, `records-reviewer`, `devin-library-reviewer`, and `security-review` or `race-reviewer` when more than the cap's slots are true. They still run under `--full`.

**Why it went.** On the three pull requests counted for the trim (a PR, a PR, a PR) the old default ran 24 agents and the capped one 10 (CHANGES.md in `harness-trim-2026-10-20/dev-94/`, bcf4a7ed). the user approved R1 to R8 on 2026-10-20.

**Superseded by.** Step 4a "Cap the set" and the `--full` flag. A payments diff still runs `payments-auditor`, `security-review` and `race-reviewer` (the user's ruling of 2026-10-19).

**Source: snapshot** `(local snapshot) skills/review/SKILL.md.txt`
