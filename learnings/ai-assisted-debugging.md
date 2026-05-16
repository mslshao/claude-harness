# AI-Assisted Debugging: Why Your AI Keeps Guessing and How to Make It Investigate

> **Where this fits**: This page is the debugging companion in the "sharpen how you use AI" track of [AI Coding Tools](./ai-coding-tools.md). It is a peer subpage to [Spotting AI Failure Patterns](./spotting-failure-patterns.md), [Build Your Context Engine](./build-context-engine.md), and [Teaching AI to Remember](./teaching-ai-to-remember.md). Read in any order; this one is most useful the next time you are stuck on a bug.
>
> **Format**: Solo read, any pace. The "Try This Today" callouts are exercises to run during your next real debugging session, not standalone tasks.
> **Output**: An investigation-first habit (treat the AI as research assistant, not oracle) and a personal circuit-breaker rule for fix-spirals.
> **If you only have 5 minutes**: read §1 (the guess-and-check trap) and §2 (the five-fix spiral, including the circuit-breaker rule).

How to turn AI from a guess machine into a debugging partner that actually traces root causes.

---

## 1. The Guess-and-Check Trap

You paste a stack trace into your AI tool. The AI reads three lines, says "this looks like a null pointer issue, try adding a null check here." You add it. Same error. "Oh, try wrapping it in a try/except." Same error. "Let me suggest a different approach entirely." Now you've made three changes, the code is worse, and you still don't know what the bug is.

Sound familiar? The problem isn't the AI. The problem is how you're using it.

When you paste an error and ask "what's wrong?", you're treating the AI like an oracle: ask a question, get an answer. When the answer is wrong, you ask again and hope for a different one. That's not debugging. That's guessing with a confident narrator.

The alternative: treat the AI like a research assistant. Instead of "what's wrong?", try "help me investigate." Instead of asking for answers, ask for evidence. "Help me trace where this value comes from." "Show me every code path that reaches this line." "What's different between this function and the similar one that works?"

**The iron law of debugging applies whether a human or an AI is doing the work: no fix without root cause.** Proposing a solution before understanding the failure is guessing, and AI tools are especially prone to this because they pattern-match from error messages. They've seen millions of stack traces and learned statistical associations: "this error often correlates with that fix." But correlation isn't causation, and your bug might be the 20% case where the common fix doesn't apply.

> 💡 **Try This Today**: Next time you have a bug, resist the urge to paste the error and ask "what's wrong?" Instead, paste the error and ask "help me trace where this value comes from." Compare how different the conversation feels.

---

## 2. The Five-Fix Spiral

Here's the anti-pattern, step by step:

1. You paste an error. AI suggests Fix A. Doesn't work.
2. You say "that didn't fix it." AI suggests Fix B (often contradicting Fix A). Doesn't work.
3. AI suggests Fix C. You're now three changes deep with no idea which ones to revert.
4. AI says "let me try a completely different approach." Fix D rewires the architecture.
5. You now have a bigger mess than you started with.

**Why this happens**: The AI has no memory of *why* each fix failed. When you say "that didn't work," it hears "the previous suggestion was wrong, generate a different one." It doesn't ask "what specifically happened when you tried it?" It doesn't update its understanding of the bug. Each attempt is essentially independent. (If you've read the sibling page on context persistence, you'll recognize this: the AI is forgetting within the conversation, not just between them.)

**The circuit breaker: three failed attempts means stop.** Not "try harder." Stop. If three fixes didn't work, the diagnosis is wrong. You're patching symptoms, not addressing the cause. This is the hardest habit to build because the AI's confidence doesn't decrease with each failed attempt. Fix 5 sounds just as confident as Fix 1.

**Self-test questions** (if you answer "no" to any of these, you're in the spiral):

* "Can I name the specific line where the failure originates?" If not, you're guessing at the fix location.
* "Did I verify that this fix addresses the root cause, or does it just suppress the symptom?" Null checks and try/except wrappers are symptom suppressors, not fixes.
* "What do I know now that I didn't know before the last attempt?" If the answer is "nothing," the attempt taught you nothing, and the next one won't either.

**The rationalization trap:**

| What you're thinking | What's actually happening |
| --- | --- |
| "Let me just try one more thing" | You have no new information. The next attempt will be as blind as the last. |
| "The AI is getting closer" | The AI has no trajectory. Each suggestion is statistically independent. |
| "This fix is different enough to work" | Different isn't better without a root cause hypothesis. |
| "I'll revert if it doesn't work" | Can you actually revert cleanly after 4 stacked changes? |
| "The runbook says to do Y if X crosses the threshold" | Runbooks encode an assumption about *why* X crosses the threshold. If your failure's actual cause doesn't match that assumption, executing the prescribed branch reproduces the same failure on the same data. Verify the cause matches the rubric before following the branch. |

> 💡 **Try This Today**: Set a personal rule: after the second failed AI-suggested fix, stop and ask the AI to *explain the error* instead of *fix the error*. "Walk me through what this stack trace tells us about the execution flow." The shift from "fix this" to "explain this" changes the AI's mode entirely.

---

## 3. Making the AI Investigate Instead of Guess

The debugging process works the same whether you're debugging alone or with AI. The difference is how you use the AI at each step. The key: keep the AI in investigation mode through at least the first four steps before letting it suggest any fix.

### Step 1: Read the full error

Don't paste just the last line of a traceback. Paste the whole thing. AI tools often skim multi-line errors the same way humans do, focusing on the final exception and ignoring the chain of calls that led there.

Prompt: "Read this full stack trace. What is the outermost call and what is the innermost failure? Trace the path between them."

### Step 2: Reproduce consistently

Before any fix attempt, establish reproduction. Ask the AI: "Given this error, what's the minimal input that would trigger it?" If the AI can't articulate reproduction steps, neither of you understands the bug yet.

### Step 3: Trace backward

This is where AI shines if you direct it properly. Instead of "fix this error," try:

* "What function produces the value that's null on line 42?"
* "Show me every place where `user_session` gets assigned before it reaches this handler."
* "What are the possible states of `response.status` when this code path executes?"

The AI becomes a code search and tracing tool, not a fix generator. It's reading code and following data flow, which is exactly what it's good at.

### Step 4: Find working reference code

Ask the AI: "Find a similar function in this codebase that handles the same error correctly." Or: "Show me other places where we call this API, and how they handle the response." The AI is excellent at finding patterns across a codebase. Use that strength to find code that already does what your broken code should do.

### Step 5: One hypothesis at a time

Write down (or have the AI write down) the hypothesis before trying the fix. "The hypothesis is that `user_session` is None because the middleware doesn't run on this route. Evidence: the middleware is registered on `/api/*` but this route is `/internal/*`." Then test that specific hypothesis with the smallest possible change.

If you can't articulate the hypothesis, you're back to guessing. That's the test.

### Step 6: Verify, don't declare

After applying a fix, the AI will want to say "that should work now." Don't accept it. Run the test. Check the output. Confirm the fix addresses the root cause, not just the symptom. "Should work now" is not evidence (more on this in Section 5).

> 💡 **Try This Today**: Next time you debug with AI, don't let it suggest a fix until step 4. Keep it in investigation mode: "Don't suggest a fix yet. Help me understand the data flow that produces this error." You'll be surprised how much faster you reach the actual root cause.

---

## 4. Multi-Component Debugging (Where AI Actually Helps Most)

AI-assisted debugging gets dramatically more useful when the bug spans multiple components. A frontend error caused by a backend issue caused by a database constraint. Three services, three languages, three log formats. Tracing through manually is exhausting. The AI can hold context from all three simultaneously.

**The principle: identify which component owns the failure before investigating any component deeply.**

The prompt pattern that works:

1. "Here's the frontend error, here's the API response, here's the backend log entry. Which component produced the first anomaly?"
2. "Check the contract between the frontend and the API. Does the request match what the API expects?"
3. "Check the contract between the API and the database. Does the query match the schema?"

This is boundary-first debugging. Most multi-component bugs are contract violations: one side sends X, the other expects Y. The AI can compare schemas, request/response shapes, and event formats much faster than a human can context-switch between codebases.

**One caution**: AI will analyze how components *should* interact based on type definitions and interface contracts. But the bug might be in how they *actually* interact at runtime. The parent page's Pattern 6 applies here: three tools once analyzed type annotations instead of checking runtime behavior, and all three were wrong. Always verify with execution, not just static analysis.

> 💡 **Try This Today**: If you're debugging across services, paste the error AND the request/response from both sides of the boundary. Ask the AI: "Do these two sides agree on the contract?" before asking "what's broken?"

---

## 5. Verification Is Not Optional

After the fix, before moving on: verify. This is the discipline that separates "I think it's fixed" from "I know it's fixed."

**The gate**: Before claiming a fix is complete, (1) identify what proves the claim, (2) run it, (3) read the output, and (4) confirm it matches. This applies whether you're fixing your own bug or validating an AI-suggested fix.

**Banned phrases** (these substitute confidence for evidence):

* "Should work now"
* "Probably fixes it"
* "I believe this resolves the issue"
* "Based on the changes, this should be fine"

These are confidence statements, not evidence. The fix works or it doesn't, and the only way to know is to run it.

**The pre-existing failure trap**: The AI suggests a fix, you run the tests, a test fails, and the AI says "that failure is unrelated to our change." Maybe. But you don't know that without evidence. Run the test before your change. If it was already failing, fine. If not, your fix broke something.

| What you're thinking | What's actually happening |
| --- | --- |
| "The fix looks correct" | Looking correct and being correct are different things. Run it. |
| "That test failure is unrelated" | Prove it. Run the test on the previous commit. |
| "I've been debugging this for an hour, it's probably fine" | Fatigue is not evidence. The gate applies especially when you're tired. |
| "The AI confirmed the fix is correct" | The AI confirmed it *looks* correct. It didn't run it either. |

> 💡 **Try This Today**: After your next AI-assisted fix, ask the AI: "What test would prove this fix is correct? What test would prove it's wrong?" Write both. Run them.

---

## 6. Where to Go Next

* **Want to make this investigation discipline repeatable?** [Build Your First Skill or Command](./build-first-skill.md) is the entry point. On a mature setup, an `/investigate` skill applies this entire discipline to production errors automatically: traces the call path backward from the failure, checks git history for the regressing PR, produces a structured RCA. A reference implementation lives at the project tier in this repo's `project-tier/skills/investigate/`.
* **Same kind of finding keeps showing up?** [Build Your Context Engine](./build-context-engine.md) is the pipeline for turning a debugging finding into a one-sentence rule that catches the same class of bug next time.
* **Want to build skills that dispatch sub-agents and integrate MCP servers?** [Building Skills and Commands at Scale](./skills-at-scale.md) covers how skills like `/investigate` are built.

The common thread: AI tools are powerful when directed, and unreliable when given open-ended authority. In debugging, "fix this" is open-ended authority. "Help me trace this" is direction. The difference is everything.
