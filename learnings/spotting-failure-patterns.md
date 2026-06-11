# Spotting AI Failure Patterns

> **Where this fits**: This page deepens section 2 of [AI Coding Tools](./ai-coding-tools.md) (the six AI failure patterns). It is a peer subpage to [Teaching AI to Remember](./teaching-ai-to-remember.md), [AI-Assisted Debugging](./ai-assisted-debugging.md), and [Build Your Context Engine](./build-context-engine.md). Read in any order.
>
> **Format**: Solo read, any pace. The optional exercise takes about 15 minutes if you want to do it.
> **Output**: One sentence in your AI tooling config that catches a specific failure pattern.
> **If you only have 5 minutes**: read section 1, then come back later.

The parent page introduces six AI failure patterns and how to spot them in code. This page goes one level deeper on **why pattern recognition is the foundation**, walks through three real examples from this codebase, and ends with one concrete rule you can add to your AI tooling config.

If you have not used an AI coding tool yet, start with [Your First Week with AI Coding Tools](./first-week.md) instead.

---

## 1. Why pattern-recognition is the foundation

If you cannot spot an AI failure mode at authoring time, you push the catch onto the reviewer. That cost is currently underwritten by a small group of senior engineers, and it is growing.

The Faros AI Engineering Report 2026 ("The Acceleration Whiplash") quantifies the shift:

* Median PR size is up 51% year over year (page 13)
* Median files per PR is up 60% (page 14)
* Median PR review time is up 441% (pages 18-19)
* Lead time from open to merge is up 480% (pages 18-19)

The report's framing on page 21 is the load-bearing claim: **this is an authoring problem, not a review problem.** Adding more reviewer attention does not scale. Catching the pattern at authoring time does.

The skill is the same whether you are the author (prompt to avoid the pattern) or the reviewer (catch what slipped through). The two angles are not separate disciplines.

---

## 2. The patterns themselves

Section 2 of [AI Coding Tools](./ai-coding-tools.md) catalogs the six patterns with red flags for spotting each one. Read that section. (If you have already read it, the patterns are: copies-your-tech-debt, builds-for-a-future-that-does-not-exist, compounds-its-own-mistakes, flags-things-already-handled, does-not-know-what-CI-already-checks, multiple-tools-agreeing.)

You do not need to memorize the names. You need to recognize the shapes when you see them in a diff.

---

## 3. Optional exercise (15 minutes)

The exercise is solo. There is no share-back. The point is to calibrate your eye against real diffs that shipped through review in this codebase.

Pick **one** of the three PRs below. Pull up the diff in GitHub. Read the discussion.

* **PR #8585**: AI added a runtime `if not response` guard for a value the production type system already proved was non-`None`. CI mypy flagged the new branch as unreachable. The correct fix was deletion of the guard, not narrowing it.
* **PR #8140**: AI used empty-string defaults (`= ""`) on required Settings fields (DynamoDB table names, SQS queue URLs). The service started successfully and crashed on the first request. The correct fix was no default at all, so Pydantic raises `ValidationError` at startup.
* **PR #8517**: AI used a broad `except Exception` (plus linter-suppression pragmas) to tolerate an expected indexing failure during a migration, swallowing unrelated exceptions with it. Three independent signals (Copilot inline, Sentry production trace, a human reviewer) converged on the same finding. The correct fix was narrowing to `except RequestError` and adding an explicit `strict_mapping` check.

Three questions to write down (one or two sentences each):

* What did the AI-authored code do?
* Which of the six failure patterns from the parent page does it most closely match?
* What did the reviewer's correction look like in the diff?

If none of these PRs are in a service you have touched, that is fine. The exercise is pattern recognition, not domain knowledge.

> 💡 PR #8517 is a useful one to choose if you have time, because it intersects with section 2 of [AI Coding Tools](./ai-coding-tools.md)'s caution about "multiple tools agreeing." Three sources flagged the same finding. The parent page warns that AI tools can share blind spots and produce false convergence. But it also names a flip side: convergence across **meaningfully independent** angles is legitimate. Which side does #8517 land on, and why? The answer is in the diff.

---

## 4. Extending the 5-question filter

[AI Coding Tools](./ai-coding-tools.md)'s section 5 lists a 5-question filter for evaluating AI suggestions. For deeper practice, add a sixth question:

1. Does acting on this make the code better? (not just different)
2. Can I verify the claim in 30 seconds?
3. Would I have caught this myself?
4. Is this actionable, or just an observation?
5. Am I acting on too many AI suggestions at once? (2-3 per session is healthy; 10+ means you're not filtering)
6. **Is this finding worth codifying as a rule, or is it one-off?**

Question 6 is the upstream instinct. A finding worth codifying is one where the same mistake would recur on the next AI-assisted task in this codebase, and where a one-sentence rule would make the AI catch it before submission.

> 💡 **Try This Today**: Take one finding from your last AI-assisted task. Run it through the 6 questions. If question 6 lands on "worth codifying," draft the rule.

---

## 5. The takeaway artifact

One sentence in your `~/.claude/CLAUDE.md` (or `.cursorrules`, or your tool's equivalent persistent-instruction file).

The rule discipline from section 3 of [AI Coding Tools](./ai-coding-tools.md):

* Concrete beats general (name the exact code shape, not a principle)
* Explicit triggers beat soft guidance ("banned" works, "consider" does not)
* No escape hatches ("when appropriate" gives the AI permission to skip)

Examples that come from real corrections in this codebase:

* "Required Settings fields must have no default value. Empty-string defaults on hot-path config defer crashes from startup to runtime."
* "When a code reviewer flags a runtime guard, check the production type signature before responding. If the type rules out the protected case, delete the guard."
* "`except Exception` is banned in new code. Use the narrowest exception class that names the actual failure mode."

The rule has to be verified. Start a new AI session, trigger the scenario that would have produced the wrong output, confirm the AI catches it. If the rule does not change the AI's behavior, it is not specific enough.

---

## 6. If you want to share what you made

There is no group share-back. The horizontal version is lighter: when you have a rule that survives the verification step, send it to one teammate in DM. Just the sentence and the PR it came from. Two outcomes are both valuable:

* They have hit the same finding. Now you both have it covered, and it is a candidate for promotion to `.claude/rules/*` (team-level).
* They have not. You have still strengthened your own catch.

The point of telling someone is calibration, not advocacy.

---

## 7. Where to Go Next

* **Want to build the pipeline that adds the next ten rules without effort?** [Build Your Context Engine](./build-context-engine.md) is the natural next read.
* **Your AI keeps forgetting your rules across sessions?** [Teaching AI to Remember](./teaching-ai-to-remember.md). Context persistence, rules files across tools.
* **Want pattern recognition applied to debugging?** [AI-Assisted Debugging](./ai-assisted-debugging.md). Investigation mode, the circuit breaker, verification.
