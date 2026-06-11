# Building Skills and Commands at Scale

You've shipped a few skills or commands. They work. Now you want them to be durable: usable by teammates, robust to edge cases, and worth keeping after the first afternoon's enthusiasm wears off.

> **Where this fits**: This page is the advanced sibling of [Build Your First Skill or Command](./build-first-skill.md) in the "build your own AI tools" track of [AI Coding Tools](./ai-coding-tools.md). The companion philosophy page is [Agent Design Lessons](./agent-design-lessons.md): same audience, "why agents are designed this way" angle.
>
> **Format**: Solo read, any pace. The DLQ live-build worked example in §2 is short; the rest are patterns you'll apply when your current skill outgrows a single file.
> **Prereq**: You've written at least one skill or command (see [Build Your First Skill or Command](./build-first-skill.md)).
> **Output**: A durable, promotable skill (or set of related skills) with an explicit iteration cycle and clear promotion path from personal to project tier.
> **If you only have 5 minutes**: read §1 (the heuristic for when to build a skill) and §2 (the DLQ live-build worked example). The rest are patterns to apply when you hit specific scaling needs.

> **Too advanced?** If you've never written a skill, start with [Build Your First Skill or Command](./build-first-skill.md).

> **Want the personalization angle instead?** See [Personalize Claude for Your Context](./personalize-claude.md).

---

## 1. The Heuristic

The first principle is unglamorous: **anything you do more than once per day, build a skill for it.**

Not "should I build a skill for this someday." If you've typed the same shape of prompt three times this week, the skill should already exist. The cost of writing the markdown file is lower than the cost of typing the prompt for a fourth time.

Patterns that show up repeatedly on this team:

* "Brief me on service X" (became `/enrich`)
* "Review this PR against project standards" (a multi-agent review skill)
* "Trace why this document didn't get indexed" (became `/investigate`)
* "Show me the DLQ status for my team's services" (was built live during a pairing session; see Section 2)

The shape: a question or task you keep retyping. The output: a markdown file that captures the prompt, the steering, and the success criteria, so Claude does it consistently every time.

---

## 2. The DLQ Live-Build: A Worked Example

This is a real session, paraphrased. The skill it built took 15 minutes start to finish.

**Setup**: A teammate asked Claude in a chat session: "Can you give me an overview of the DLQs for the court reporting downloader service?" Claude looked up the service in code, found the input queue, and reported its status via the AWS MCP server.

**The realization**: The teammate noticed they'd want this for every service their team owned. Multiple times per week.

**The build prompt**:

```
I want to create a Claude Code skill to look at all DLQs for my team. Team is
"<team-name>". Walk me through what the skill would do, then create it.
```

**What Claude did:**

1. Searched for skills directory (`~/.claude/skills/`).
2. Drafted a skill `SKILL.md` that listed all DLQs tagged for the team, sorted by depth, with optional filters.
3. Asked for confirmation before writing.
4. Wrote the skill.
5. Suggested invoking it: `/list_team_dlqs`.

**The first run failed.** Claude misplaced the skill in the wrong directory. It noticed, removed the file, recreated it in the right location, and tried again. Second run worked. Output: 92 DLQs found, 16 non-empty, sorted by depth.

**The iteration**: The teammate asked, "Can it also show message counts?" Claude updated the skill in-place, re-ran, and the next invocation showed counts.

**The point**: The skill wasn't designed up front. It was extracted from a working session, refined through use, and self-corrected when it hit edge cases. Total elapsed time: under 20 minutes including the iteration round.

> 💡 **Try This Today**: Pick a thing you do every few days. Walk through it once with Claude in a chat session. At the end, ask: "Turn this into a Claude Code skill I can invoke with a slash command." Watch what it produces. Iterate. You'll have a working skill before lunch.

---

## 3. Agent Ergonomics: Writing for Bots, Not Humans

The skills you write are read by Claude, not by people. That changes how you write them.

Behavioral principle: **Claude takes the shortest path to accomplishing the task.** If your skill instructions are vague ("consider checking X"), Claude will skip the check. If your instructions are bright-line ("ALWAYS check X before Y"), Claude will follow.

Concrete patterns that work:

| Vague | Bright-line |
| --- | --- |
| "Consider whether tests are needed" | "After every new function, write at least one test" |
| "Be careful about deletes" | "Before any `rm` or `git reset`, ask the user to confirm by typing the word DELETE" |
| "Use existing patterns" | "Read 3 example files in the same directory before writing a new one. Match their structure." |
| "Verify the output" | "Run `pants check {target}`. If it returns errors, fix them before claiming done." |

This is the opposite of how you'd write for a human teammate (where "consider X" is polite). Treat the skill as instructions to a literal-minded contractor who bills by the minute. The clearer the spec, the better the output.

> **The "agent behavioral economics" framing**: Agents are incentivized to do whatever most easily accomplishes their task. They don't have your taste, your context, or your sense of what counts as "done well." Specificity in your skill is the only way to communicate those things.

---

## 4. The Iteration Cycle

Skills don't ship once. They evolve.

**The cycle:**

1. Use the skill in real work.
2. Notice where it fails (wrong output, missed edge case, misunderstood intent).
3. Open the skill markdown file.
4. Add or sharpen the rule that prevents the failure.
5. Re-run.

The fastest way to do this is to let Claude self-correct in the same session. After a failed invocation, ask: "What went wrong, and what should the skill say differently?" Claude usually edits the skill itself, then re-runs. (This is exactly what happened in the DLQ build above.)

**Wrong fast > wrong slow.** A skill that fails immediately and visibly is better than a skill that drifts incorrectly across many invocations before you notice. Bias toward making your skills opinionated and brittle: they should refuse to operate when their assumptions don't hold, not silently produce mediocre output.

> 💡 **The disagreement test**: When Claude tells you "you're absolutely right" or "great catch," that's the failure mode you're optimizing against. Add a rule to your skill: "If the user is wrong, say so directly. Do not validate incorrect claims." Skills that flatter you are skills that don't catch your mistakes.

---

## 5. Promotion Path

Skills evolve through three locations:

**Personal (**`~/.claude/skills/`): Where new skills are born. Only you have them. Use this for skills that haven't earned their keep yet, or that capture preferences nobody else shares.

**Project (**`.claude/skills/`): When the skill works for your use case AND you can articulate why it'd help teammates, promote it. Open a PR, get review, ship. Now the whole team gets it.

**Advanced (sub-agents, multi-file skills, MCP-driven)**: When the skill needs to do work big enough that a single invocation isn't enough, decompose. Split into multiple files, dispatch sub-agents, integrate MCP servers. This is where the depth lives.

**Decision rule**: Don't promote a skill to the project before you've used it for a week personally. The version you ship after one afternoon is not the version your teammates should depend on. Use it, find the edges, sharpen the rules, then promote.

---

## 6. Multi-File Skills

A `SKILL.md` alone is sufficient for ~80% of cases. When it isn't, here's the pattern:

```
~/.claude/skills/<name>/
  SKILL.md           # Entry point: when to fire, high-level instructions
  workflow.md        # Step-by-step procedure
  examples.md        # Reference outputs for calibration
  rules.md           # Bright-line constraints
  output-format.md   # Structured output spec
```

The `SKILL.md` references the other files. Claude loads the relevant ones based on the work it's doing. This is "progressive disclosure": don't load the rules file unless you're enforcing rules, don't load examples unless you need them.

Real example: a multi-file PR review intelligence skill that dispatches specialist sub-agents (security, style, structural review), aggregates findings, and produces a single review report. Each component lives in its own file.

---

## 7. MCP Integration in Skills

When your skill needs external data (Datadog logs, AWS resource state, Jira tickets), reference the MCP tools directly in the `SKILL.md` instructions:

```markdown
## Step 1: Get the current SQS queue depth

Use the AWS MCP server. Call `aws sqs get-queue-attributes` for each queue.
Group results by team tag. Sort by `ApproximateNumberOfMessages` descending.
```

Claude resolves the MCP tools at runtime. You don't need to write MCP plumbing yourself; you just name the tool and Claude figures out the rest.

The MCP servers commonly configured for a Claude Code session are: Atlassian, Datadog, AWS, plus the Claude-Code-internal ones. To check what's available in a given session, run `/mcp` in the Claude Code window.

---

## 8. Sub-Agent Dispatch

Some skills are too big for one invocation. A sub-agent is a separate Claude instance with its own fresh context, launched mid-task to do a bounded piece of work and report back. The pattern: dispatch sub-agents to do specialized work in parallel, then aggregate.

**When to use sub-agents:**

* The work needs more context than fits in one session.
* Multiple independent perspectives are useful (security, style, structure).
* The work is parallelizable.

**When NOT to use sub-agents:**

* The work is sequential.
* The output of step N depends on step N-1.
* The total work is small enough to fit in one session.

A PR review intelligence skill, for example, can dispatch a security auditor, a style reviewer, and a code reviewer in parallel against the same diff, then synthesize the findings into one report. The skill itself is the conductor; the agents are the orchestra.

In the `SKILL.md`, the dispatch is plain instructions, the same as any other step:

```markdown
## Step 2: Dispatch reviewers in parallel

Launch the security-auditor agent and the code-reviewer agent on the same diff.
Wait for both to finish. Merge findings into one report, deduplicating overlaps.
```

> **The cost calculus**: Sub-agents are not free. Each one starts a fresh context. Loading the sub-agent's instructions, the relevant code, and the task description costs tokens. Use sub-agents when the parallelism is worth it; don't use them as a default just because they exist.

---

## 9. Verification and Self-Review

When your skill is complex enough to need its own review, treat it like code. Before shipping to project-level:

```
@code-reviewer review the changes I'm about to commit. Treat this as
pre-submission. Flag style, types, lint, naming, and design issues. Be
specific about what would fail CI.
```

For executable specifications (skills, commands, agents), additional checks:

* Walk every decision branch in the skill. For each "ask the user" point, verify there's an explicit non-interactive path.
* Verify any tool names, MCP endpoints, or API field names against actual schemas. Don't write from memory.
* Run the skill in a fresh session before merging. Skills that work in your dev session may fail in a clean one due to assumed context.

---

## 10. Where to Go Next

* **Want to revisit fundamentals?** [Build Your First Skill or Command](./build-first-skill.md).
* **Want to personalize Claude further?** [Personalize Claude for Your Context](./personalize-claude.md).
* **Want the deeper "why" behind agent design?** [Agent Design Lessons](./agent-design-lessons.md).
