# AI Workflows: End-to-End Examples for Developers

> **Where this fits**: This page is the workflow application of [AI Coding Tools](./ai-coding-tools.md)'s principles across the full ticket-to-merge lifecycle. The "sharpen how you use AI" pages teach individual skills (pattern recognition, persistence, debugging); this one shows where those skills land at each stage of a real dev workflow.
>
> **Format**: Solo read, any pace. The "Try This Today" callouts run during your next real task, not as standalone exercises.
> **Prereq**: You should have read [AI Coding Tools](./ai-coding-tools.md) (or at least tried AI tools a few times). When something breaks mid-workflow, the [AI-Assisted Debugging](./ai-assisted-debugging.md) page covers the investigation workflow.
> **Output**: A four-stage workflow with concrete prompts, traps to avoid, and stop-criteria for each stage.
> **If you only have 5 minutes**: read §1 (just-got-assigned exploration) and §4 (responding to PR comments). Those are the two stages where AI most consistently saves time.

**One practical note**: Stages 1 and 2 (planning and implementation) flow naturally in one conversation. Start a fresh session for Stage 3 (the pre-push review): an AI that just helped write the code will tend to defend it rather than review it. Stage 4 is always a new conversation.

---

## 1. "I just got assigned a ticket"

You got assigned a Jira ticket for a feature in a service you've touched once. Maybe you've seen the directory name in a PR. Maybe you've never opened the files. Before you write a single line of code, you need to understand what exists, what needs to change, and how to approach it.

This is where most developers skip AI entirely and just start reading code. Reading code is good. But AI can compress the "where do I even start?" phase from an hour to ten minutes, if you scope the question.

### Example prompts

**Explore the system:**

`"Walk me through the request lifecycle in [service name], from the handler entry point to the database write. Skip the auth middleware."`

This models scoping: you're asking for a specific path through the code, not "explain everything." The explicit exclusion ("skip auth middleware") prevents the AI from spending 200 words on something you don't care about right now.

What good output looks like:

> **Request lifecycle in extract-pipeline:**
>
> 1. Handler entry: `handler.py:lambda_handler`        *starts with a specific file and function*
>
>     * Parses SQS event, extracts document ID
>     * Creates `MessageProcessor` instance
>
> 2. Processing: `message_processor.py:run()`           *follows the path you asked about*
>
>     * Loads document from DynamoDB
>     * Calls OCR API for text extraction
>     * Runs LLM extraction for relevant identifiers
>
> 3. Output: `message_processor.py:submit_to_queue`  *ends at a clear boundary*
>
>     * Publishes result to SQS for downstream sync
>
> Not covered: auth, logging decorators, error retry    *confirms it respected your scope*

If the output is a vague summary instead of specific files and functions, your prompt was too broad. Narrow it.

**Understand impact:**

`"I need to add [feature] to this service. What existing code would I need to touch? List files and the reason each is relevant. Don't suggest an implementation yet."`

The "don't suggest an implementation yet" constraint keeps the AI in investigation mode. Without it, the AI jumps straight to code generation before you understand the landscape.

**Pick an approach:**

`"Give me 3 approaches to implement [feature]. For each: what changes, what doesn't change, and what breaks if requirements expand to include [likely extension]. I'm constrained to [existing pattern/framework]."`

This forces the AI to evaluate approaches against your specific constraints and a realistic future, not a hypothetical one. The AI is good at generating options; it's bad at filtering them without constraints from you.

### Traps

**The broad summary trap.** The AI gives you a 500-word overview of the service architecture when you needed to know about one specific data path. Fix: name the path in your prompt.

**The premature abstraction trap.** The AI suggests approach 3 should include a factory pattern "for extensibility." Ask: "What concrete requirement would trigger that extensibility?" If the answer is hypothetical, skip it. (This is [Pattern 2](./ai-coding-tools.md) from the parent page: building for a future that doesn't exist.)

### When to stop using AI at this stage

If you're going back and forth for more than 3 rounds on a design decision, the AI is pattern-matching, not reasoning. Grab a colleague or a whiteboard. The AI helped you explore; now you need judgment that comes from context it doesn't have.

**Before moving on, verify:** You can explain the approach to a teammate in 2 sentences. If you can't, you're not ready to code.

> **Try This Today:** Pick a ticket you were recently assigned. Before writing any code, point your AI tool at the relevant service: in Claude Code, open a session in the repo and name the service's directory in your question; in Cowork, attach the two or three core files (for example the handler and main processing module). Then ask: "What are the three most important things I need to understand about this code before I change it?" Compare the answer to what you actually needed to know. The gap tells you how to write better exploration prompts.

---

## 2. "Time to write the code"

You've committed to an approach. Now you're writing code with AI assistance.

This stage is where most developers already use AI, so the advice here isn't "try using AI" but "use it better." The difference between productive AI-assisted coding and frustrating AI-assisted coding is almost always about how you direct the corrections.

### Example prompts

**Precedent-based implementation:**

`"I need to add error handling to this function. Show me how similar functions in this codebase handle errors, then apply the same pattern here."`

This prevents the AI from inventing a new error-handling style. It anchors the output to your existing conventions, which means less cleanup and fewer review comments.

**Specific test generation:**

`"Write a test for [function] covering: happy path, the null case, and what happens when [dependency] raises [specific exception]. Use the test patterns already in this directory."`

Name the cases. "Write tests" produces generic coverage. "Cover these three cases using the patterns in this directory" produces tests that match your conventions and test what matters.

**Correction (the most important skill):**

`"I asked you to implement X but you also added Y. Remove Y. I only want X."`

The AI will add abstractions, utilities, and "helpful" extras you didn't ask for. Push back immediately. Every unwanted addition you accept becomes code you maintain. This is the single most important habit in AI-assisted implementation: if you didn't ask for it and don't need it, say so.

### Traps

**The "fix this test" trap.** AI generates a test with a wrong assumption. The test fails. You ask the AI to fix the test. It patches the assertion to match the wrong behavior instead of fixing the code. Fix: ask "why does this test fail?" not "fix this test." (This is [Pattern 3](./ai-coding-tools.md) from the parent page: the AI compounds its own mistakes.)

**The silent style drift trap.** AI writes code that looks correct but uses different naming conventions, import patterns, or error styles than the rest of the codebase. CI might catch some of this; it won't catch all of it. Fix: anchor the AI with "follow the patterns in this directory."

### When to stop using AI at this stage

If the AI keeps generating code that doesn't compile or fails the same test after 2 correction rounds, you're fighting the tool. Write it yourself and use AI for review instead. Two rounds is the limit before diminishing returns.

**Before moving on, verify:** The code compiles and the tests you wrote actually test the behavior you care about, not just that a mock was called.

> **Try This Today:** After your next AI-assisted implementation session, count how many AI suggestions you accepted versus rejected. If you accepted everything, you probably weren't filtering enough. The sweet spot is accepting 60-80% and pushing back on the rest.

---

## 3. "Before I push"

Code is written, tests pass locally. Before you push, run one more AI pass. This takes 60 seconds and catches things you've gone blind to after staring at the same code for an hour.

This is the **pre-CI mode** from [AI Coding Tools](./ai-coding-tools.md) Section 4. The key difference from post-CI review: nothing has been checked yet, so you want the AI to flag everything.

### Example prompts

`"Review what I just wrote. CI hasn't run yet. Flag: type errors, missing edge cases, and style violations against this repo's patterns. Don't flag things the linter will catch."`

The "don't flag things the linter will catch" part is optional. In pre-CI mode, it's reasonable to include linter-level findings since CI hasn't verified them yet. But if your formatter runs on commit, those findings are noise.

`"Look at the test I wrote. Does it break only if OUR code changes, or would it also break from upgrading a dependency?"`

This is the testing heuristic from the parent page, applied as a self-review prompt. If the test would break from a library upgrade, it's testing the framework, not your code.

### Traps

**The "looks correct" trap.** You read the AI's review, see no findings, and conclude the code is clean. But the AI may have skimmed rather than analyzed. If the review comes back with zero findings on a non-trivial change, run it again with a more specific prompt: "Check the error handling paths. What happens when \[specific input\]?"

**Before moving on, verify:** You've addressed findings you agree with. You've consciously decided to skip findings you disagree with (not just scrolled past them).

> **Try This Today:** Add one prompt to your pre-push routine: "Review what I just wrote. CI hasn't run. Flag everything." Track how many of its flags would have actually failed CI. That hit rate is your calibration metric for how much to trust pre-push AI review.

---

## 4. "Someone left comments on my PR"

Your PR has 3 inline comments: one from a human reviewer, one from Copilot, one from Sentry. You need to understand what's being asked, decide how to fix it, implement the fix, and respond.

This is the stage where AI saves the most time per interaction, because interpreting review feedback and implementing targeted fixes is exactly the kind of focused task where AI excels.

### The screenshot workflow

One developer on our team found a workflow that handles the overhead of multiple review bots efficiently: screenshot the PR comment and paste it into an AI tool. The screenshot captures everything the AI needs: file path, line number, surrounding code, the exact comment, and the reviewer's name. Then:

1. **Interpret first:** "What is the reviewer actually asking me to change? Separate the concrete request from any stylistic suggestions."
2. **Get options:** "Suggest 1-2 ways to address the concrete request."
3. **Select and implement:** Pick an approach. Let the AI implement it and run the tests.
4. **Respond yourself.** Write the GitHub response in your own words. The AI helped you understand and fix; the communication is yours.

This works equally well for bot comments (Copilot, Sentry, SonarCloud) as for human comments. The AI interprets the comment regardless of who wrote it.

### Example prompts

`"[screenshot or paste of PR comment] What is the reviewer actually asking me to change? Separate the concrete request from stylistic suggestions. Then show me 1-2 ways to address the concrete request."`

The "separate concrete from stylistic" instruction prevents over-correction. Not every comment requires a code change; some are observations or preferences.

`"The reviewer said [quote]. I think they're wrong because [reason]. Am I missing something, or should I push back? If I push back, draft a response that's direct but collaborative."`

Using AI as a sounding board for disagreements is underutilized. The AI can often spot whether you're right, the reviewer is right, or you're talking past each other. Just don't trust its answer blindly: if it agrees with everyone, it's not analyzing, it's people-pleasing.

### Traps

**The copy-paste-fix trap.** The AI implements a fix by copying an existing pattern from nearby code. But that nearby pattern might be the exact thing the reviewer flagged. Check that the fix doesn't introduce the same problem elsewhere. (This is [Pattern 1](./ai-coding-tools.md): the AI copies your tech debt.)

**The "everyone agrees" trap.** You ask the AI if the reviewer is right. It says yes. You ask if you're right. It also says yes. AI tools agree with whatever framing you give them unless you force a specific evaluation. Ask "argue the reviewer's position" and "argue my position" separately, then compare. ([Pattern 6](./ai-coding-tools.md): agreement isn't correctness.)

**Before moving on, verify:** Run the tests after each fix. Don't batch 3 fixes and hope they all work.

> **Try This Today:** Next time you get PR feedback, paste the comment into your AI tool and ask: "What is the reviewer actually asking me to change? Separate the concrete request from stylistic suggestions." Compare the AI's interpretation to your own. If they disagree, figure out who's right before responding.

---

## 5. Where to Go Next

* **Something broke mid-workflow?** [AI-Assisted Debugging](./ai-assisted-debugging.md) covers investigation mode, the circuit breaker, and verification discipline.
* **Want to turn Stage 4 review findings into rules that prevent the same comment next time?** [Build Your Context Engine](./build-context-engine.md) is the pipeline.
* **Want concrete examples of the failure patterns this page references?** [Spotting AI Failure Patterns](./spotting-failure-patterns.md) walks three anchor PRs from this codebase.

The common thread: AI tools are powerful when directed and unreliable when given open-ended authority. At every stage of the workflow, the difference between useful and useless is how specific your direction is.

---

> **Audience note**: A PM-focused workflow page covering the equivalent lifecycle from the non-engineering side (ticket writing, ceremony design, data analysis, stakeholder translation) is planned but not yet lifted to this repo. The shape would be the same four-stage discipline applied to different inputs and outputs. The deferral reason is editorial: the original was heavily personalized to one firm's PM workflows and needs broader-audience rewriting before it earns its keep here.
