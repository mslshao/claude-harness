# AI Coding Tools: Insights, Patterns, and Practical Guidance

> **New to AI coding tools?** If you haven't started yet, or tried once and stopped, start with [Your First Week with AI Coding Tools](./first-week.md) instead. This page assumes you're already using AI tools and focuses on improving your results.

Lessons from ~3 months of daily AI-assisted development. These apply regardless of which tool you use: Claude Code, GitHub Copilot, Cursor, ChatGPT, or anything else. Tool-specific examples are labeled; everything else is universal.

---

## 1. The Trust Problem

"I don't trust AI output" is a legitimate starting point, not a skill gap. If you've used AI on code and gotten mediocre results, that's normal. Here's why, and what to do about it.

**Why general-purpose prompts reinforce distrust**: "Review my code" is vague input. Vague input produces vague output (garbage in, garbage out). The AI tries to say something about everything and ends up saying nothing useful about anything. This reinforces the feeling that AI tools are unreliable.

**The shift: scoping builds trust.** "Check this function for off-by-one errors in the loop bounds" is a narrow, verifiable question. The AI either finds one or it doesn't. You can check the answer in 30 seconds. That's a fundamentally different experience from "review my PR."

**Mental model: AI findings are leads, not conclusions.** You are the editor, not the reader. The AI generates candidates; you decide which ones are worth acting on. This isn't a limitation to work around. It's the correct operating model.

Trust isn't binary. The goal is **calibrated trust**: knowing what to verify and what to rely on.

> 💡 **Try This Today**: Next time you use AI on code, replace "review this" with a specific question about a specific function. Compare the output quality.

---

## 2. What AI Gets Wrong

Six failure patterns you'll encounter regardless of tooling. Each one has a red flag so you can spot it in practice.

### Pattern 1: It copies your tech debt

You have `# noqa` on line 42. Copilot autocompletes the next function with `# noqa` too. The AI learned that's how your codebase works. It pattern-matches against existing code, and if your codebase has linter suppressions, the AI will replicate them as "accepted convention."

🚩 **Red flag**: AI-generated code contains the same suppression comments (`noqa`, `type: ignore`, `pylint: disable`, `@SuppressWarnings`) as nearby legacy code.

### Pattern 2: It builds for a future that doesn't exist

You ask for a parser. The AI also creates a `ParserFactory`, a `ParserConfig`, and an `AbstractParserStrategy`. None of them are called anywhere. Good names, good docstrings, zero callers.

🚩 **Red flag**: New classes or types that nothing imports or instantiates.

### Pattern 3: It compounds its own mistakes

Speculative code (pattern 2) + copied suppression (pattern 1) = code that passes CI, looks intentional, and is completely wrong. The linter suppression hides the architectural violation, and the speculative type hides the fact that nothing uses it.

🚩 **Red flag**: A PR that introduces both a new type AND a linter suppression in the same change.

### Pattern 4: It flags things that are already handled

AI review says "this might throw an exception" without checking whether the caller already handles it. Or it flags the same issue a bot already flagged. It generates plausible-sounding concerns without verifying them.

🚩 **Red flag**: Finding says "callers may depend on X" without naming the caller or showing the dependency.

### Pattern 5: It doesn't know what your CI already checks

After CI passes, most lint/type/style findings are noise. The AI doesn't know what your pipeline already verified. It will re-flag import ordering, type annotations, and formatting on code that already passed pylint + mypy + your formatter.

🚩 **Red flag**: AI flags import order or type annotations on code that already passed CI.

### Pattern 6: Multiple tools agreeing doesn't mean they're right

Three automated tools flagged the same function as broken. All three were wrong. They shared the same reasoning flaw: analyzing how a type annotation *should* work instead of checking what actually happens at runtime. A 3-line test would have shown the function works exactly as intended.

This happens because AI tools share similar training data and reasoning approaches. When they agree, it feels like independent confirmation, but it's actually the same blind spot amplified. Consensus without verification is just shared speculation.

**The flip side**: when the sources agreeing are meaningfully independent (a human reviewer, a runtime error tracker like Sentry, a static analyzer reading the diff), converging on the same concern IS a legitimate signal. The distinction is where the agreement comes from. Multiple AI tools trained on similar data share blind spots; a human noticing the same issue Sentry flagged in production does not. When that kind of convergence happens, budget a revision cycle rather than defending the original pattern. Iterating is almost always faster than arguing, and the odds that three independent angles all got it wrong in the same way are low.

🚩 **Red flag**: Multiple tools flag the same issue, but none of them verified by tracing the actual execution path or running the code.

> 💡 **Try This Today**: After AI generates code, search it for comments containing `noqa`, `ignore`, `disable`, `suppress`, or `skip`. If found, that's pattern 1 in action. And when multiple tools agree on a finding, ask: did any of them actually run the code?

---

## 3. Giving AI Better Instructions

These principles apply whether you're writing a `CLAUDE.md` file, a `.cursorrules` file, ChatGPT custom instructions, or just pasting context at the top of a prompt.

### Concrete beats general

* Chat window version: *"When reviewing my code, flag any* `# pylint: disable` *as a violation. Do not add new ones."*
* Rules file version: `"# pylint: disable" is banned in new code. Existing instances are tech debt, not precedent.`

**Why this matters**: AI pattern-matches against existing code. General principles ("follow best practices") lose to concrete code examples every time. Name the exact pattern you want banned.

### Explicit triggers beat soft guidance

* "Consider whether tests are needed" produces zero tests.
* "After creating any new function, write at least one test that exercises the happy path" produces tests.

This isn't just about tests. The pattern is universal:

* "Evaluate whether error handling is adequate" → nothing changes.
* "Every function that calls an external API must have a try/except with a specific exception type" → error handling appears.

The AI treats soft language as optional because "when appropriate" is ambiguous, and ambiguity gives the AI permission to skip it. Concrete triggers remove the ambiguity entirely.

Research supports this: bright-line rules ("banned", "must", "always") are measurably more effective than hedged guidance ("prefer", "consider") when instructing LLMs (Meincke et al., 2025).

### Rules without escape hatches

* "Always use typed models instead of untyped dictionaries" works.
* "Use typed models when appropriate" means "never, because the AI decides everything is appropriate as-is."

State rules without "unless." Violations are tech debt to fix, not precedent to follow.

### Progressive disclosure for long context

Don't dump 2000 lines of instructions into one file. The AI will lose the important stuff in the middle. Pattern: short always-loaded summary that points to detailed files loaded on demand. Same principle works in chat: give a focused prompt, then provide detail when the AI asks.

> 💡 **Try This Today**: Pick one recurring AI mistake in your workflow. Write a one-sentence rule that names the exact pattern (the literal string or code shape, not a principle). Add it to your custom instructions or paste it at the start of your next prompt.

---

## 4. Two Modes of AI Review

The single most impactful workflow distinction. Same tool, different two-sentence framing, dramatically different output quality.

### Before CI (self-review)

AI catches everything: lint, types, style, logic. You WANT noise here because nothing else has checked yet.

Prompt: *"CI has not run. Flag everything: style, types, lint, naming, and logic issues."*

### After CI (reviewing others' code)

AI focuses on design judgment only. CI already caught lint/type/style. Duplicating that is the "regurgitating AI" problem: it re-flags everything the pipeline already caught, and the output feels like noise.

Prompt: *"Linting, type checking, and formatting already pass. Focus only on logic errors, design issues, and missing edge cases."*

Without this distinction, post-CI AI review produces bulk findings that add no value and erode trust.

**Testing heuristic** (useful in both modes): **"Does this test break ONLY if OUR code changes?"** If a test would also break from upgrading a library or changing a framework config, it's testing the framework, not your code.

> 💡 **Try This Today**: Next time you ask AI to review code, add one sentence: "CI has already passed for lint, types, and formatting. Focus only on logic and design." Compare the signal-to-noise ratio.

---

## 5. Reading AI Output Critically

Whether you're reading AI suggestions in your IDE, reviewing AI-generated code, or using AI to help with PR review, the same critical reading skills apply.

**Observations beat verdicts.** "This appears to drop error context" is useful. "This is wrong" usually isn't. When AI gives you a verdict, ask: what's the evidence?

**Check for false positives.** AI loves to flag removed code as "risky" without checking whether anything depends on it. Before acting on an AI finding, spend 30 seconds verifying the claim.

**Spot the duplication.** If your linter, CI, or another bot already flagged something, the AI finding adds nothing. Skip it.

**Watch for "might" and "could."** "This might throw" and "this could fail" without specifics usually means the AI is speculating. Ask: what specific exception, under what specific conditions?

### The 5-question filter

Before acting on any AI suggestion:

1. Does acting on this make the code better? (not just different)
2. Can I verify the claim in 30 seconds?
3. Would I have caught this myself?
4. Is this actionable, or just an observation?
5. Am I acting on too many AI suggestions at once? (2-3 per session is healthy; 10+ means you're not filtering)

> 💡 **Try This Today**: Next time AI flags something in your code, before fixing it, spend 30 seconds verifying whether the claim is actually true. Track your hit rate over a week.

---

## 6. Going Deeper

For developers who want to go further, the child pages branch into four tracks. All are optional and self-paced.

### Sharpen how you use AI

* [**Spotting AI Failure Patterns**](./spotting-failure-patterns.md): Deepens section 2 above with three anchor PRs from this codebase, an exercise that calibrates your eye against real diffs, and the rule-discipline that turns one finding into a one-sentence catch.
* [**Build Your Context Engine**](./build-context-engine.md): Operationalizes section 3 above. The pipeline that turns every review finding into a rule that catches the same class of failure on every future task. Includes the plan-vs-implementation delta exercise.
* [**Teaching AI to Remember**](./teaching-ai-to-remember.md): Context persistence, rules files across tools, what to save vs discard, progressive disclosure.
* [**AI-Assisted Debugging**](./ai-assisted-debugging.md): Investigation mode, the circuit breaker, verification discipline.

### Apply AI across your workflow

* [**AI Workflows: End-to-End Examples for Developers**](./workflows-developers.md): Four stages of a typical dev workflow: exploration, implementation, pre-push, and responding to PR comments. Concrete prompts, traps, and stop-criteria for each.

### Build your own AI tools

These three pages cover extending Claude Code yourself: writing skills and commands, configuring Claude for your specific work style, and graduating to advanced patterns.

* [**Build Your First Skill or Command**](./build-first-skill.md) (beginner): The entry point. Walks through writing a skill or command using an enrichment workflow as a worked example. Read first if you've never written your own.
* [**Personalize Claude for Your Context**](./personalize-claude.md) (side-door): Read when you have opinions about how Claude should behave for you specifically. Includes a structured interview prompt that populates a personal `~/.claude/CLAUDE.md`. Three trajectories covered (strong-opinions, no-opinions-yet, calibrated-taste-but-rusty).
* [**Building Skills and Commands at Scale**](./skills-at-scale.md) (advanced): Agent ergonomics, sub-agent dispatch, MCP integration, and the iteration cycle.

### Going further on agent design

* [**Agent Design Lessons**](./agent-design-lessons.md): Identity framing, mechanical checklists vs. self-critique, context injection patterns. Sibling to "Building Skills and Commands at Scale"; deeper on the philosophy, lighter on the worked examples.

---

## Appendix: What a layered AI tooling setup looks like

> **Note**: This appendix describes the shape of a deliberately-layered AI tooling configuration. It is illustrative, not prescriptive. Names and specifics will differ depending on which tools you use and what you build for yourself.

### Three tiers of agents and skills

The same layering pattern applies to both agents (specialized sub-AIs) and skills (reusable workflows):

1. **Personal tier**: things you build for yourself, in your own home directory configuration. These reflect how you specifically work. They do not need to be shared, generalized, or documented for others. The cost of writing one is low; the benefit is that the same problem does not have to be solved twice across your future sessions.
2. **Project tier**: things committed to the repo for the whole team. Examples: review fan-out workflows, ticket context loaders, error-handling and code-style enforcement agents, scaffolding and migration assistants, generated test suites. Discoverable to anyone with the repo checked out; usable without additional configuration.
3. **Plugin tier**: reusable, distributable modules. Multi-agent PR review packs, brainstorming and TDD assistants, debugging helpers. Installed via the plugin system.

### Project-tier agents in one example repo

The following agents live at the project tier of one team's repo and are available to anyone working in it. The names are illustrative; your team's set will look different depending on what you build.

* `code-reviewer`: structural and standards review against the team's `.claude/rules/`.
* `dependency-graph`: cross-service dependency analysis.
* `error-handling`: custom exception hierarchies, Pydantic error models, audit-log compliance.
* `infrastructure`: Terraform/Terragrunt scaffolding following the repo's module conventions.
* `legacy-migration`: moving code out of legacy directories into the modern layout.
* `llm-prompt`: optimizing prompts used in document extraction and analysis.
* `pydantic-migration`: converting untyped dictionaries to Pydantic models.
* `salesforce-sync`: SF integration patterns with retry logic and tracking.
* `service-scaffolding`: new Lambda service skeletons with handler, models, settings, BUILD, and tests.
* `test-generator`: pytest test generation with moto-mocked AWS, fixtures, and team patterns.
* `observability-reviewer`, `test-quality-reviewer`, `silent-failure-hunter`: review specialists that survived personal-tier sandboxing and were promoted to project tier. Reference implementations of all three live in this repo under `project-tier/agents/`.

Invoke with `@agent-name` in a Claude Code session.

### Project-tier slash commands in the same example repo

Slash commands available to anyone in the repo:

* `/pr`: open a GitHub PR with lint checks and Jira linking.
* `/jira`: create a Jira ticket using the team's field convention.
* `/confluence`: create or update a Confluence page.
* `/review`: local self-review fan-out to project review agents; produces a grouped severity report. Reference implementation in `project-tier/skills/review/`.
* `/enrich`: load context for a Jira ticket, PR, or topic into the conversation. Reference implementation in `project-tier/skills/enrich/`.
* `/investigate`: structured investigation of a production error; traces call path and history. Reference implementation in `project-tier/skills/investigate/`.

### Dispatch shapes worth wiring up

The dispatch pattern is "named need → named invocation." The list below is illustrative; your own setup will end up with its own table once you have built or installed the tools you actually use:

* Code quality review on uncommitted changes or a diff: `code-reviewer`.
* Cross-service dependency or import-graph question: `dependency-graph`.
* Production error investigation: `/investigate`.
* Self-review fan-out before pushing: `/review`.
* Loading context for a ticket or PR before analysis: `/enrich`.
* Multi-agent author review on a PR: a PR review toolkit plugin command.

Other useful shapes once you build them at personal tier: a planning workflow that converges a rough idea into a stress-tested plan, an execution launcher that takes a well-scoped ticket and dispatches an agent team in a worktree, a PR-intelligence skill that produces a structured briefing with draft review comments, a parallel-consult skill that runs multiple specialists on the same code in a forked context. These shapes are what a mature personal setup ends up with after a few months of iteration; the specific names you give them are yours.
