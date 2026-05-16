# Build Your Context Engine

> **Where this fits**: This page operationalizes section 3 of [AI Coding Tools](./ai-coding-tools.md) (giving AI better instructions) by turning real review findings into rules. It is a peer subpage to [Spotting AI Failure Patterns](./spotting-failure-patterns.md), [Teaching AI to Remember](./teaching-ai-to-remember.md), and [AI-Assisted Debugging](./ai-assisted-debugging.md). Read in any order.
>
> **Format**: Solo read, any pace. The optional exercise takes about 20 minutes if you want to do it.
> **Prereq**: [Spotting AI Failure Patterns](./spotting-failure-patterns.md) is a useful precursor (it ends with a one-sentence rule in your AI config). You can read this page without it, but the exercise here builds on that rule.
> **Foundation**: If you don't yet have a personal `CLAUDE.md` at all, [Personalize Claude for Your Context](./personalize-claude.md) establishes the foundation (about-you, communication style, autonomy thresholds). This page assumes that foundation exists and teaches you how to grow it.
> **Output**: A "Review findings I've codified" section in your `CLAUDE.md`.
> **If you only have 5 minutes**: read sections 1 and 2. They are the load-bearing concepts; the rest operationalizes them.

The parent page's section 3 covers how to give AI better instructions. This page goes one level deeper on **where those instructions should come from**: real review findings on real PRs, captured into rules that survive every future session. Pattern recognition (the prior page) is the input; this page is the pipeline.

---

## 1. The Faros thesis, operationalized

The parent page's section 1 and the prior subpage both cite the Faros AI Engineering Report 2026 (page 21 framing): the review tax falling on senior engineers is not a review-side problem to solve with more reviewer attention. It is an authoring-side problem to solve with better authoring.

This page operationalizes that. The question is: when a reviewer catches a pattern, **where does the catch live afterward?**

* In a PR comment: it rots. The next AI-assisted task has no memory of it.
* In your head: it survives until you context-switch.
* In a personal `CLAUDE.md` rule (or your AI tool's equivalent persistent-instructions file): it compounds for you across sessions.
* In a project rule file (`.claude/rules/*` in this repo, or your tool's team-level config): it compounds for the whole team.

Each level up is roughly a 10x increase in leverage and roughly a 30-second increase in cost to capture. The math is asymmetric. A 30-second rule-write at PR-1 saves N reviews going forward. The Faros review-tax curve flattens only when we treat review findings as code that needs to be written somewhere durable.

---

## 2. What "context engine" means

A context engine is the set of rules, memories, and configurations that load automatically into every AI session. You did not build one when you started using AI. You acquired one accidentally, in the form of: whatever your tool defaults to, plus whatever scraps of context you remember to paste at the top of each chat.

A deliberate context engine has three properties:

1. **It loads without you remembering.** If you have to copy-paste it into a prompt every time, it is not yet engineered, it is just discipline.
2. **It grows from real findings, not from imagined ones.** Every entry traces to a concrete review comment, incident, or correction. No "good practices in general" entries.
3. **It distinguishes personal from team.** Your personal `CLAUDE.md` carries findings specific to how you work. The project's `.claude/rules/*` carries findings the whole team has converged on.

The pipeline this page builds: review finding → personal rule → (when validated across multiple engineers) → team rule.

> 💡 **Don't have a personal** `CLAUDE.md` yet? [Personalize Claude for Your Context](./personalize-claude.md) walks through creating one from scratch via a structured interview prompt. The "Review findings I've codified" section this page produces sits inside that file as one more section.

---

## 3. Optional exercise: the plan-vs-implementation delta (20 minutes)

This is the hardest of the optional exercises in the corpus. Skip it without guilt if you are at capacity. The framing in section 4 is the actual takeaway; the exercise is one way to surface raw material for it.

Pick one of your recent AI-assisted tasks where you used a "plan first, then implement" workflow (any session where you explicitly asked the AI to write a plan or design before coding). If you have not used a plan-first workflow yet, pick a recent PR you authored with AI assistance.

**Run the plan-vs-implementation delta.** Find the original plan (in a tracking ticket, a Confluence page, an AI conversation, or wherever it lives) and the merged PR. Compare them.

Look for divergences:

* Scope you added during execution that was not in the plan
* Steps from the plan you dropped or modified
* Refactor branches the AI took that were not planned
* Anything where the plan was wrong but you only realized mid-execution

Write down **one** divergence. In one sentence each, name:

* What changed between plan and execution
* Whether the plan was wrong, the execution was wrong, or both
* Whether the divergence correlated with anything downstream (review revisions, incidents, extended review time)

> 💡 **Hunch worth checking against your own work.** High plan-vs-implementation delta tends to correlate with worse outcomes. If your divergence ended in a clean merge with no revisions, that is data too. The point is calibrating whether AI-assisted plan-fidelity matches your intuition.

---

## 4. The review-finding-to-rule pipeline

The pipeline works for any source: an AI-flagged finding you accepted, a human reviewer's comment, a delta from the exercise above, a production incident, anything. Take one finding and walk it up these five steps. **Do this for one real finding from your own recent work, not a hypothetical.**

1. **The raw finding**: the reviewer's comment or your own observation, in its original form. ("This silently swallows the exception.")
2. **The pattern**: stripped of PR-specific detail, what is the recurring class of mistake? ("Using `except Exception` to make a flaky test pass instead of fixing the test's actual failure mode.")
3. **The trigger**: what specific code shape (string, function call, configuration value) should the AI catch on the next attempt? ("Any new `except Exception:` in a test file, especially when added to make a failing test pass.")
4. **The rule sentence**: one sentence. Concrete trigger. No escape hatch. No "when appropriate." ("`except Exception` is banned in new code. Use the narrowest exception class that names the actual failure mode.")
5. **The placement**: personal `CLAUDE.md`, team `.claude/rules/*`, or somewhere else? Personal is the default for the first instance. Promotion to team-level needs at least one other engineer wanting the same rule.

---

## 5. The takeaway artifact

A "Review findings I've codified" section in your personal `CLAUDE.md`. Each entry is one sentence. Each entry traces to a specific real finding.

> 💡 **Shape:**
>
> ```
> ## Review findings I've codified
> - PR #8585 (type-narrow-vs-delete): A reviewer pushed back on AI code that added a runtime `if x is None` guard for a value the production type system already proved was non-None. CI's type checker flagged the new branch as unreachable. The right fix was deletion of the guard, not narrowing it. Rule: when a code reviewer flags a runtime guard, check the production type signature before responding. If the type rules out the protected case, delete the guard, do not narrow it.
> - PR #8140 (empty-string defaults on required Settings): AI used empty-string defaults (`= ""`) on required Settings fields (DynamoDB table names, SQS queue URLs). The service started successfully and crashed on the first request because the validator never ran. Rule: required Settings fields must have no default value. Pydantic raises ValidationError at startup, which is the correct fail-fast behavior.
> - PR #8517 (broad except Exception in test fixture): AI used a broad `except Exception` to make a flaky test pass. Three independent signals (Copilot inline, Sentry production trace, a human reviewer) converged on the same finding. The narrowing fix was `except RequestError` plus an explicit check on the response shape. Rule: `except Exception` is banned in new code. Use the narrowest exception class that names the actual failure mode.
> ```

The PR numbers are anchors; the real value is the failure mode each rule encodes. A reader without access to the codebase still gets the lesson because the failure mode is named inline.

Verify each new rule the same way [Spotting AI Failure Patterns](./spotting-failure-patterns.md) does:

* Start a new AI session
* Trigger the scenario that would have produced the wrong output
* Confirm the AI catches it

If the AI does not catch it, the rule is not specific enough. The fix is almost always specificity. Soft language ("consider", "when appropriate", "evaluate") gives the AI permission to skip. Hard rules ("banned", "always", "never") with concrete triggers do not.

This section is also a memory aid. When you context-switch back to AI-assisted work after a few days off, reading this section recalibrates you faster than re-reading the AI's general training defaults.

---

## 6. If you want to share what you made

Same lightweight pattern as the prior page: when a rule survives the verification step, send it to one teammate in DM. Just the rule, the PR it came from, and one sentence on why you wrote it. Two responses are both useful:

* "I have hit this too." Now the rule is a candidate for promotion to `.claude/rules/*`. Open a PR adding it.
* "I have not hit this." Your personal version still earns its keep.

If you would rather not initiate, the reverse works too: ask a teammate to share one rule from their personal `CLAUDE.md` with you. The horizontal sharing is the whole engine. It does not need a meeting.

---

## 7. Where to Go Next

* **Don't have a personal** `CLAUDE.md` yet? [Personalize Claude for Your Context](./personalize-claude.md) is the foundation: who you are, how you want the AI to communicate, where you diverge from team defaults. This page assumes that foundation exists and adds the rule-growth pipeline on top.
* **Rules file growing past 20 entries?** [Teaching AI to Remember](./teaching-ai-to-remember.md) covers context persistence across tools and the progressive-disclosure pattern for when one file gets too long.
* **Rule has graduated past one sentence and wants to become a reusable workflow?** [Build Your First Skill or Command](./build-first-skill.md).

> 💡 **Try This Today**: Look at the last PR comment you received that taught you something. If the next AI-assisted task you do could violate that same lesson, codify it now. The 30 seconds of writing the rule is the entire investment.
