# Decision-Making Rules

A catalog of rules for evaluating evidence, weighing recommendations, and routing judgment. Each rule has a specific origin (a slip the author corrected and turned into a durable rule). The collection is the load-bearing portion of the harness's "working theory of how the model fails by default."

## Best practice over precedent

When the codebase has both good and bad patterns, recommend the good one. Existing violations are tech debt, not justification for new code to follow the same pattern. Do not cite frequency of a pattern as evidence that it's correct.

## Skeptic lens for plausible-sounding reviewer suggestions

When evaluating reviewer feedback, especially from sources known for ideological pushiness, run each suggestion through the test: "Does this actually improve the artifact, or import the reviewer's preferences?" Plausible-in-isolation suggestions can fail this test: they may duplicate existing rule coverage, contradict project calibration, or pull in framing not codified in the project's rules. Decline politely with route-to-rules; reply tone factual not dismissive (intent is genuine even when fit is wrong).

## Skeptic lens for specialist subagent recommendations

Specialist agents (a tech-lead synthesizer, a code reviewer, an adversarial advisor) are colleagues, not authorities. When user evidence contradicts a specialist's recommendation (operator pushback citing a concrete past incident, a prior memory entry, an observed pattern), the specialist does not win by default. Surface the contradiction to the user with both sides and let them adjudicate; do not silently defer to the specialist because they were the most recent voice.

## Verify falsifiable specialist claims before posting

The PR-review-flavored sibling of the rule above. Specialists work from code-only context; production state can narrow, invalidate, or confirm a claim. When a specialist returns a BLOCKING or CRITICAL finding that depends on observable production state (logs, metrics, resource config, query results), run that verification yourself with available tools BEFORE drafting review output. AND include the literal query or command in the draft so the author can re-run it. Not "verify in the dashboard" but the actual query string.

## Don't push complexity onto the user

When a skill, plan, or workflow needs a parameter, convention, or flag to operate, the design should auto-detect from context using a heuristic, escalate to specialist agents when the heuristic is uncertain, and ask the user only as a last resort. Manual flags and conventions the user has to remember are anti-patterns: forgotten state silently regresses to default, and the user shouldn't have to track the underlying mechanics of how skills are launched.

## External-tool adaptation: take shapes, not artifacts

When adopting a skill, pattern, or convention from outside your ecosystem (blog posts, other engineers' setups, open-source projects), extract the MECHANISMS (what it actually does that helps) and adapt them to your existing infrastructure. Don't port the foreign ARTIFACT format when your existing infrastructure already covers the underlying need; that fragments docs instead of complementing. Test before porting: "is the foreign artifact filling a gap our infrastructure has, or is it duplicating something we already do under a different name?"

## Technology choice is independent of context window

The technology used by nearby code (same file, same query, same module) is not evidence that new functionality should use the same technology. Evaluate each data access, infrastructure choice, or integration pattern against the project's architectural rules, not against what happens to be in your context.

## Recommendations need evidence, not plausibility

Before recommending a tool, MCP server, automation, dependency, or process change, run the test: "Would this have changed an outcome we observed?" Not "is this useful in general", but would it have caught a specific bug, prevented a specific incident, or unblocked a specific workflow the user actually has. If the honest answer is "plausibly, in edge cases", mark the recommendation as marginal or skip it. Generic best-practice matching dressed up as targeted advice wastes user time.

## Code presence is not deployment evidence

When the question is "is this fix in place" or "is this pain point resolved," grep hits in `main` are insufficient. Code on main can be: (a) deployed but not effective due to config/threshold/edge case, (b) deployed but bypassed by operational flag, (c) merged recently but not yet rolled out. Before claiming something is CONFIRMED or INVALIDATED based on code presence, verify: ticket status (open tickets are a strong signal the fix isn't working), production behavior (logs, dashboard events, operational reports from the person who owns the system), or deployment state.

## Type-system precedence over test-mock precedence

When a code-review flag points at a runtime guard (`if not x`, `if x is None`), check the production type signature before responding. If the type system rules out the case the guard protects against, delete the guard rather than narrowing or annotating it. Test mocks that simulate impossible states test scenarios the type system forbids; delete them with the guard.

## Operational scope questions require authoritative-state verification

"What do I need to deploy", "what's changed since the last push", "what services are affected": verify against authoritative operational state (deployed function timestamps, task definition revisions, infrastructure-as-code state, alias configuration). Recent commit history surface-scans what's been merged, not what's shipped; the lag can be months.

Extends to PR review in an active migration domain: load the migration's current operational state (cutover, backfill, alias resolution) before forming review concerns about sequencing, fallback, or compatibility.

## Verify subagent baseline measurements against change boundaries

When a subagent reports a metric baseline (rate, percentile, count, average) and a recent deploy or config change or schema migration or feature-flag flip is in the conversation context, the time-window the subagent used can straddle the change boundary and produce a misleading "current state" figure. Re-query the metric using a post-change-only window before acting on the baseline. Cost is one tool call; cost of trusting a wrong baseline is hours of misdirected work plus propagated artifacts.

## Verify git remote state before asserting required git operations

Before saying "you'll need to push" or "force-push" or "pull" or "the branch has diverged", run `git fetch` and re-check divergence. A prior in-session `git status` may be stale; the user, another agent, or a stacking tool may have pushed or rebased in parallel, and merges to the base branch change divergence numbers silently.

## Scan loaded context before claiming absence

Before asserting "zero", "none", "no path for X", or "nothing exists" about own or team or project outputs, grep the loaded context: CLAUDE.md body, MEMORY.md topic index, recent bd memories. Loaded context is evidence, not background; if it names what you are about to claim is absent, you have not done the diligence to make the claim. Especially load-bearing in advisory work (career strategy, gap analysis, recommendations) where confident absence claims drive user decisions.

## Exhaust search strategies before claiming external-system absence

Sibling to the loaded-context rule above, applied to external-system queries. One search strategy is one data point, not a definitive absence. Before claiming "no PR exists", "no ticket found", "no monitor configured", try the inverse: exact-match plus substring, head-ref filter plus free-text search, REST API direct plus CLI wrapper. Different vectors hit different indexes. Cost is a few seconds per extra strategy; cost of a wrong absence claim is the user re-running the search themselves and losing trust in the verification.

## Match tool choice to the user's workflow context

When the user's session is bash + curl + jq + for-loops, write bash. When it is Python notebooks or runnable scripts, write Python. Do not default to a language by habit; defer to the tools already loaded in the user's head. A longer Python script with stdlib imports is worse than a 15-line bash loop when everything else in the session is curl + jq.

## Validate prescribed rubrics against observed failure modes

Runbooks, handoffs, and SOPs encode assumptions about WHY things fail ("if miss is greater than 5% after Option B, escalate to Option C"). Before executing the prescribed branch, confirm the actual failure matches the rubric's assumed cause. Diagnosis can invalidate the rubric entirely; the right path may be outside it.

## Empirical observation overrides model speculation

When the user reports behavior that contradicts a confident prediction, drop the prediction immediately. Do not save face with "timing was off but it'll still happen"; that preserves a wrong model. Say "I don't know why this is working, here's what we observe" and let observation lead. Especially load-bearing for predictions about external system timing.

## Why this exists

Each rule above replaces a specific class of model mistake with a small theory of how that mistake happens. The catalog grows over time as new mistakes get codified. The catalog itself is portable: any model + any harness benefits from the same rule set, because the underlying failure modes are model-class properties, not Claude-specific quirks.

## Where it has limits

- The rules are descriptive of past failure modes, not predictive of future ones. New model versions can fail in new ways the catalog does not cover.
- Application requires judgment. A rule like "verify falsifiable specialist claims" assumes the model knows which claims are falsifiable. Borderline cases can be wrong.
