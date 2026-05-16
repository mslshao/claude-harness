# Build Your First Skill or Command

You've used Claude Code as a consumer. You've read the bot's PR review comments. You've watched it summarize a ticket. Now you want to build your own.

> **Where this fits**: This page is the entry point in the "build your own AI tools" track of [AI Coding Tools](./ai-coding-tools.md). It is paired with [Personalize Claude for Your Context](./personalize-claude.md) (which configures Claude for how YOU work) and [Building Skills and Commands at Scale](./skills-at-scale.md) (the advanced patterns once your first skill ships).
>
> **Format**: Solo read, any pace. The complex-pipeline ramp worked example in §2 is short; the hands-on exercise in §3 takes about 30 minutes if you do it.
> **Prereq**: You've used Claude Code as a consumer (read AI-generated review comments, used `/pr` or `/jira`, asked questions in the chat window). If you haven't used Claude Code at all yet, start with [Your First Week with AI Coding Tools](./first-week.md).
> **Output**: A first skill or command (in `.claude/skills/` or `.claude/commands/`) exercised against a real service you don't yet understand.
> **If you only have 5 minutes**: read §1 (skill vs command, and how to choose) and §2 (the worked example). The rest is the hands-on walkthrough.

> **Already comfortable building skills?** Skip to [Building Skills and Commands at Scale](./skills-at-scale.md) (advanced sibling).

> **Have strong opinions about how Claude should behave for you personally?** That's a different journey. See [Personalize Claude for Your Context](./personalize-claude.md). You can do that one first or come back to it after this. Both work.

---

## 1. Skill or Command? Both Are Just Markdown

A **skill** and a **command** are two ways to give Claude Code a reusable, named workflow. Both are markdown files. No traditional coding required.

**Skill** (`.claude/skills/<name>/SKILL.md`)

* Loaded automatically when its description matches what you're doing.
* Best for: workflows Claude should pattern-match into without you typing a name.
* Example: a "post a PR review" skill auto-fires when you ask Claude to post review comments on a GitHub PR.

**Command** (`.claude/commands/<name>.md`)

* Invoked explicitly with `/<name>` in the prompt.
* Best for: workflows you want to trigger on demand.
* Example: `/list_team_dlqs` shows the SQS dead-letter queues for your team.

**When to pick which:**

* If you'd type a slash to fire it, write a command.
* If you want it to fire automatically based on what you're doing, write a skill.
* When in doubt, start with a command. They're simpler. You can promote to a skill later.

> 💡 **Tip**: Ask Claude: "What's the difference between a skill and a command in Claude Code, and which fits my use case better?" then describe what you're trying to do. Official docs: [Claude Code Skills](https://code.claude.com/docs/en/skills).

> **Project vs. personal location.** Skills and commands can live at `~/.claude/` (personal, only you have them) or at `.claude/` (project, everyone on the repo gets them). For your first one, default to project-level. That way your teammates benefit too, and the file is reviewed and version-controlled. Personal ones are for opinions you hold that the org doesn't share, see [Personalize Claude for Your Context](./personalize-claude.md).

---

## 2. A First-Week Ramp Worked Example

Here's a real story from this team. The author inherited ownership of a complex document indexing pipeline after the previous owner left. The pipeline was 9 service boundaries deep: documents went in one end, embeddings came out the other, and nobody on the new team could explain what happened in between. This was the first time the author had to consider how to reach context across multiple sessions, because the pipeline's complexity exceeded what any single conversation could hold.

The author's first week looked like this:

**Day 1**: Asked Claude in the chat window: "Walk me through what happens when a document gets uploaded. Start at the API handler. Don't skip layers."

**Day 2**: Same question, but more specific: "Read the indexing service's main directory. Trace the path from the SQS consumer to the Elasticsearch write. Tell me which Lambda owns each step."

**Day 3**: Noticed Claude kept losing context partway through. Started saving its answers as markdown files in a scratch directory so the next session could pick up.

**Day 4**: Realized the pattern was repeating: "give me context about service X." Wrote a command called `/enrich` that pulled together the relevant Jira ticket, the codebase entry points, and the related documentation, in one shot. The cross-session friction (re-explaining the pipeline shape every morning) was the specific pain `/enrich` was built to remove.

**Week 2**: The output of those `/enrich` runs, plus follow-up Q&A, became a technical reference document on the pipeline. That document is now what every new contributor reads first. It did not exist before. The author did not know enough to write it. The team learned the system by getting Claude to teach them, and the teaching session became the doc.

The `/enrich` command was later promoted from personal-tier to project-tier in a team-reviewed PR. It is now available to everyone working in the repo. A reference implementation lives in this repo at `project-tier/skills/enrich/`.

This case study matters because it's the first instance where "AI as research assistant across sessions" was the load-bearing capability. A new owner with no prior context, a pipeline whose shape required multiple days to absorb, and no human teammate available to teach: the skill emerged from that constraint, not from a design exercise.

---

## 3. Try This on a Service You Don't Know

Pick a service you don't fully understand. It can be a service you're about to be on-call for, a system your team just inherited, or a module you keep meaning to read.

### Step 1: Open Claude Code

In your codespace (or local terminal), open Claude Code. If your installation shows a version older than 2.1.45, run `claude --update`.

### Step 2: Verify your model

Type `/model` in the Claude Code window. Make sure you're on a recent model. The difference between generations of the same model family is significant for harness-driven workflows; newer is generally more capable.

### Step 3: Connect your tools

Type `/mcp` and authenticate any MCP servers your project uses (Atlassian, Datadog, AWS, etc.). This is a one-time OAuth flow. Without this, the next step works on code only and misses half the picture.

### Step 4: Run /enrich

If your project has an `/enrich` skill available (or you've installed the reference implementation from this repo), type:

```
/enrich on the <service-name> service. I want to understand how a request flows
from the entry point to the final write or response. I'm going to use this to
write a technical reference.
```

If you don't have `/enrich` yet, paste the equivalent prompt directly into the chat. The skill is just a saved version of this kind of prompt.

The output should be a structured briefing: relevant Jira tickets, codebase entry points, models, settings, and any related Confluence docs gathered into one place.

### Step 5: Ask follow-up questions

Don't take the first answer as final. Probe:

* "Which step is the most likely to silently fail?"
* "What's the contract between \[layer A\] and \[layer B\]?"
* "Where would I check if a document gets stuck?"

### Step 6: Save it

When the answers stop surprising you, ask Claude:

```
Summarize what we just learned into a Confluence-ready doc. Use H2 sections.
Include code references with file paths and line numbers. Mark anything we
weren't sure about as "needs verification."
```

You now have a draft technical reference doc. Edit it for accuracy and ship it.

> 💡 **Try This Today**: Pick the service. Run the prompt. Spend 30 minutes on it. Even if you don't ship a doc afterward, you'll know that service better than you did this morning.

---

## 4. When the Conversation Gets Long: The Handoff Pattern

Long sessions hit a wall. Claude Code shows your context usage near the top of the window. When it climbs past 50%, you'll start to notice degraded responses: missed details, forgotten decisions, repeated questions.

Don't fight it. Plan a handoff.

**The handoff prompt:**

```
Summarize what we decided and what we did, in a format I can paste into a new
session to continue from here. Include: the goal, decisions made (with reasoning),
what's been verified vs what's still open, file paths I should pre-load, and the
next concrete step.
```

Save the output to a markdown file (a scratch directory works fine, e.g., `~/.claude/scratch/<topic>.md`). In the next session, paste it back as your first message. You'll resume from where you left off.

This is exactly how the `/enrich` skill itself was built: long sessions, manual handoff prompts, scratch markdown files. The skill is a more durable version of the handoff pattern.

> 💡 **When you find yourself doing the handoff pattern often**, that's the signal it's time to write a skill or command. See [Building Skills and Commands at Scale](./skills-at-scale.md) for the next step.

---

## 5. Pre-Submission Self-Review

Once you've written a skill or command and used it for a few days, you'll want to commit it to the repo so your team gets it. Before you push:

```
@code-reviewer review my changes against project standards. Treat this as
pre-submission (Author Mode). Flag everything: style, types, lint, naming,
design issues. I want to fix problems before CI sees them.
```

The `code-reviewer` agent applies the project's `.claude/rules/` against your diff. Most things our PR review bot would catch later, this catches now. Iterate until it's clean, then push.

---

## 6. What Success Looks Like

You know you're doing this right when:

* You stop typing the same long context-setup prompt every session. (You wrote a skill for it.)
* You stop opening 5 Confluence tabs to brief yourself on a service. (You wrote a command for it.)
* You start volunteering to take on services you don't know. (Because ramping is fast now.)
* A teammate asks you for help, and you point them at a skill you already wrote.

You know you're doing it wrong when:

* You're trying to make the skill solve every edge case at once. Ship the 80% version. Iterate.
* You're trying to make it polished enough to share. Don't, yet. Use it for a week first. The version you'd share with a teammate is not the version you'd ship after one afternoon.
* You're afraid to delete a skill that didn't work. Delete it. Markdown files are cheap.

---

## 7. Where to Go Next

* **Want Claude to know more about you, your style, and your preferences?** [Personalize Claude for Your Context](./personalize-claude.md).
* **Ready to build skills with multiple steps, MCP integrations, or sub-agents?** [Building Skills and Commands at Scale](./skills-at-scale.md).
* **Want to understand the deeper "why" behind effective AI tooling?** [Agent Design Lessons](./agent-design-lessons.md).
