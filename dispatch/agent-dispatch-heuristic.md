# Agent Dispatch Heuristic

Numbered routing rules for when to invoke which agent. Applied during conversation when deciding "should this be a dispatch, or do I handle it directly?"

The rules are ordered roughly by frequency of use. The first match wins.

## 1. Is this a rough idea that needs a full plan?

Route to a convergence skill that chains refine, decompose, challenge, consult, and synthesize. Presents only the converged plan for signoff. Use for medium-to-large features where you would otherwise invoke 3+ skills manually.

## 1b. Is this a well-scoped ticket ready for hands-off implementation?

Route to a launch skill: enriches context, converges a plan, gets approval, dispatches an agent team in a shared worktree, and produces a draft PR. Supports cold-start resume.

Before publishing the PR, run a structured self-review (PR-intel in self-review mode) for AC compliance, CI status, specialist dispatch, pre-submission checklist. Per-phase reviews catch issues within each phase but miss integration bugs between phases (wrong field names at call sites, dropped fields during refactor). Consolidate all post-review fixes into a single commit.

## 2. Is this a code quality concern?

Route to user-tier code reviewer agents first. If unsure which, route to the generalist code-reviewer.

## 3. Is this a domain-specific codebase task?

Route to project-tier agents (migration, scaffolding, integration-specific work).

## 4. Is this a PR review or feature development task?

Route to plugin-tier agents alongside user agents.

## 5. Do 2+ specialists need to weigh in on the same code?

Route to a consult skill: runs in a forked context, parallelizes specialists, synthesizes a unified report. Cheaper than serial agent calls in your own context.

## 6. Is the problem ambiguous, multi-source, or needs clear articulation?

Route to a tech-lead agent: sense-making, synthesis, and articulation. NOT for evaluating reviewer feedback.

**Manual orchestrator dispatch only**: do NOT wire the tech-lead into automation skills (PR-intel, consult, convergence specialist roster, autopilot, launch). For automation that needs adversarial judgment, use the adversarial advisor (the skeptic agent) which is advice-only.

## 7. Is the task iterating on reviewer feedback or satisfying PR review comments?

Do NOT use the tech-lead agent by default. Use the code-reviewer for structural evaluation, or handle directly. If tech-lead must be used, signal "feedback-reception mode" so it loads its conditional behavior. Read the receiving-PR-review memory for forbidden-response patterns and source-specific handling before drafting replies.

## 8. Is the user's request terse and you're about to dispatch to specialists?

Use a prompt-refiner agent (headless mode) to expand context before building specialist prompts. This prevents subagents from guessing at intent. Skip if you already have enough context to construct focused prompts yourself.

## 9. Did you just write or modify tests?

Route to a test-quality-reviewer: validates tests assert behavior, not framework mechanics. Invoke before committing test changes.

## 9b. Is it a well-bounded implementation task?

Known fix, pattern-matching, single-file: route to a bounded executor agent with precise instructions. Review the returned diff before committing. This saves strong-model tokens on mechanical work while keeping review quality.

**Carve-out for PR-iteration mechanical fixes**: when resolving bot feedback on an already-pushed PR and the fix is single-file and under approximately 20 lines (ellipsis-to-pass, add a constant, add `raise NotImplementedError`, rename), do the edit directly plus lint plus amend. Implementer dispatch overhead (200-400 seconds with self-review) exceeds direct-edit cost (around 30 seconds) by an order of magnitude. Reserve dispatch for first-pass implementation, multi-file refactors, or fixes that require codebase exploration.

## 10. Is it a straightforward task you can do correctly in one pass?

Just do it. Not everything needs an agent.

## 11. Challenge before consult

When a plan rests on assumptions about external state (resource existence, schema shape, API behavior), run a challenge skill to surface those assumptions before consult or implementation. Assumptions about what exists are the highest-fragility category.

## 12. Multi-reviewer convergence is a strong signal

When two or more review sources (Copilot, Sentry, human reviewers, specialist agents) flag the same concern, treat it as a legitimate finding and iterate rather than defend the original pattern. The concurrence across independent signals is load-bearing. Budget a cycle for the revision; it is almost always faster than arguing.

## Why this exists

A harness with 20+ specialist agents has a routing problem: when do you call which? Without explicit rules, the model picks based on superficial similarity (the agent's name sounded relevant). Explicit ordered rules force the model to check the first-match path before falling through to alternatives.

The "manual dispatch only" caveats on certain agents (especially tech-lead) exist because some agents have strong opinions that work well under operator supervision but produce muddled output when wired into automation. The caveats are calibration.

## How this compounds

After a few months of use, the rules accumulate carve-outs and exceptions (the "implementer dispatch overhead exceeds direct edit cost for fixes under 20 lines" rule, for example). Each carve-out is a specific case the default routing got wrong. The catalog of carve-outs is itself the harness's working theory of "when does each pattern apply, and when does it not?"

## Where it has limits

- The rules assume the model can recognize the rule's trigger condition. Borderline cases (is this "ambiguous"? is this "well-bounded"?) require judgment.
- New tasks that do not fit any rule get routed by default to direct handling or to the convergence skill. Both are sensible fallbacks but neither is optimal for every uncovered case.
