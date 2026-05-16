# Personalize Claude for Your Context

You've used Claude Code, maybe written your first skill, and you've noticed: Claude doesn't know YOU. It knows the codebase, the project rules, the team conventions. But it doesn't know how you talk, what you care about, or where you diverge from the team default.

> **Where this fits**: This page is the foundation in the "build your own AI tools" track of [AI Coding Tools](./ai-coding-tools.md). It's a side-door entry; read it when you have strong opinions about how Claude should behave for you specifically. Once you have a personal `CLAUDE.md`, [Build Your Context Engine](./build-context-engine.md) teaches you how to grow it with codified review findings.
>
> **Format**: Solo read, any pace. The interview prompt in §2 takes 5-10 minutes.
> **Output**: A personal `~/.claude/CLAUDE.md` with sections for About Me, Communication, Autonomy, Where I Diverge, and Verification.
> **If you only have 5 minutes**: skim §1 (what personal `CLAUDE.md` does) and §2 (the interview prompt).

> **Skipped here from another page?** This page is a side door. Read it when one of these is true:
>
> * You have strong opinions and want Claude to respect them.
> * You're tired of correcting the same things every session.
> * You've been using Claude for a few weeks and noticed your style drift away from team defaults in specific places.

> **Just getting started?** If you haven't used Claude Code at all yet, [Your First Week with AI Coding Tools](./first-week.md) is a better start. If you've used it but never built your own anything, [Build Your First Skill or Command](./build-first-skill.md) is more useful first.

---

## 1. What Personal [CLAUDE.md](https://code.claude.com/docs/en/memory) Actually Does

Your project's `.claude/rules/` files codify how the org expects code to be written: testing standards, type safety rules, security requirements. Those apply to everyone working on the codebase.

A personal `~/.claude/CLAUDE.md` is layered on top. It captures things like:

* Your role and where your context is shallow
* How you want Claude to talk to you
* Your autonomy threshold (when to ask vs. act)
* Where YOU diverge from team defaults (style preferences, naming conventions, things you care about that the org doesn't enforce)

Both files load into every Claude Code session automatically. Your personal [CLAUDE.md](https://code.claude.com/docs/en/memory) is private; it's not committed to any repo.

> **The dual-purpose distinction**: Project rules describe what's true for the team. Personal `CLAUDE.md` describes what's true for you. Don't put your personal preferences in the project rules. Don't put org standards in your personal `CLAUDE.md`. The two layers exist exactly so they don't bleed into each other.

---

## 2. The Interview Prompt

Here's the fastest way to populate a useful first version. Open Claude Code and paste this in:

```
I'd like you to help me create a personal CLAUDE.md file. This file will live at
~/.claude/CLAUDE.md and Claude Code will load it into every session, so the goal
is to capture who I am and how I want to work, in a way that helps you (Claude)
be more useful to me specifically.

Please ask me the following questions, one at a time. Wait for my answer before
moving to the next. After all questions, draft the CLAUDE.md and show it to me
for review before saving.

1. Role and tenure: What's your role and how long have you been doing this kind
   of work? Are you new to this codebase, or do you have history here?

2. Domain map: What parts of the codebase or system do you own or feel
   comfortable in? Where do you have shallow context and need help?

3. Teaching vs. output: Are there areas where you want me to teach as I go
   (explain what I'm doing and why) vs. areas where you just want the output?

4. Communication style: When I respond to you, do you prefer concise answers
   (just the conclusion) or detailed answers (with reasoning shown)? Formal or
   casual register? Any pet peeves about how AI tools talk to you?

5. Autonomy and uncertainty: When I have a multi-step task, do you want me to
   ask permission at each step, or run end-to-end and report back? When I'm
   uncertain, should I guess my best answer and flag the uncertainty, or stop
   and ask? Does your answer differ for "uncertain about approach" vs.
   "uncertain about risk"? What kinds of changes should I always confirm
   (e.g., destructive git ops, deploys, deletes)?

6. Where do you diverge from team defaults? This isn't about disagreement; it's
   about things you care about that the org doesn't enforce. Examples: stricter
   type hints, no inline comments, longer test names, no bare exception handlers.
   If you're not sure yet, describe a habit from a previous job or tool that
   you'd want to carry forward.

7. Anti-patterns: What's something an AI tool has done in the past that
   annoyed you? We can write a rule to prevent it.

8. Verification habit: Before claiming a task is done, what evidence do you
   want me to gather? For example: tests passing, type-checker clean, manually
   read the diff, manually exercised the feature. If you're not sure, name what
   "done" felt like in your previous role.

After my answers, draft the CLAUDE.md with these sections:
- # About Me (role, tenure, domain map; behavior in shallow zones)
- # How I Want You to Communicate (style, register, anti-patterns; teaching mode)
- # Autonomy and Confirmation (when to ask, when to act; uncertainty handling)
- # Where I Diverge from Defaults (personal overrides)
- # Verification Before Claiming Done

If I gave tentative or "I'm not sure yet" answers to several questions, mark
the file as a first draft at the top and add: "Revisit after 30 days of use."
```

It takes 5-10 minutes. Save the output to `~/.claude/CLAUDE.md`. Done. You can edit it whenever you want; it's just a markdown file.

> 💡 **Try This Today**: Run the interview. Even if your answers are vague the first time, the act of having Claude prompt you is what makes the gaps visible.

---

## 3. Starter Defaults

If you don't want to do the interview yet, or you want a baseline to edit instead of build from scratch, here's a reasonable starter:

```markdown
# About Me

[Your role, tenure, codebase history]

Strong context: [areas you own]
Shallow context: [areas you need help in]

When I'm working in shallow zones, surface assumptions explicitly before acting.

# How I Want You to Communicate

Concise. Lead with the conclusion. Show reasoning only if I ask.
No filler ("Great question!", "Certainly!", "Of course!"). No unnecessary hedging.

# Autonomy and Confirmation

For bounded, reversible work, run end-to-end and report back.
Always confirm before:
- Destructive git operations (push, force-push, reset, branch delete)
- Deploys
- Deletes of files I didn't explicitly tell you to delete
- Anything touching production data

When uncertain about approach, give your best guess and flag the uncertainty.
When uncertain about risk, stop and ask.

# Where I Diverge from Defaults

[Your personal overrides. Leave empty if you're new.]

# Verification Before Claiming Done

- Linter/type-checker against changed targets is clean (or the equivalent for your stack)
- Tests pass for code I changed
- Don't claim "done" without showing me the verification output

When I ask for self-review before submission, invoke the code-reviewer agent in Author Mode.
```

Edit any line. Add or delete sections. The file is yours.

---

## 4. When to Override the Org Defaults

The "Where I Diverge" section is the most personal part of the file. Some real examples that have shown up in `CLAUDE.md` files on this team:

* Stricter type hints than `.claude/rules/code-style.md` enforces (`X | None` always, never `Optional[X]`)
* A specific test naming convention (`test_<thing>_when_<condition>_returns_<expectation>`)
* "Never generate docstrings longer than the function they describe"
* "Don't split one logical change into multiple commits"
* Preference for integration tests over unit tests in specific subsystems
* "If you notice tech debt while working on a task, mention it but don't fix it. I want to file it separately."

These are all valid. They reflect that engineers arrive with different backgrounds, calibrated tastes, and trade-off preferences. As long as your overrides don't contradict project rules (which apply to the codebase regardless of who is editing it), they belong in your personal `CLAUDE.md`.

> **One caveat**: If your personal override produces output that fails the project's CI checks or violates `.claude/rules/`, the project wins. Personal preferences operate within the boundary of what the team has agreed to enforce.

---

## 5. The File Evolves

Your first version will be incomplete. That's correct.

You'll notice gaps over the first few weeks:

* Claude does something annoying. You add a rule.
* Claude misunderstands what you meant in a specific area. You add context.
* A rule you wrote turns out to be too rigid. You soften it.
* A rule you wrote turns out to be ignored. You make it harder.

Most engineers on this team rewrite their personal `CLAUDE.md` 2-3 times in the first month. The version you ship after one afternoon is not the version you'll have at month three. That's fine. It's the same iteration cycle as a test suite.

> 💡 **The maintenance habit**: Once a week, when something goes wrong with Claude, ask yourself "is this something I can prevent next time with a rule?" If yes, add the rule. If no, move on. When you start codifying review findings from PRs (the next-level pattern), see [Build Your Context Engine](./build-context-engine.md) for the pipeline.

---

## 6. Three Common Trajectories

People arrive at personalization from different directions, and the file looks different depending on where you start.

**Trajectory A: You arrived with strong opinions.**
You came in with calibrated tastes from a previous role, and your hands-on coding skills are current. Your interview answers were specific. Your file has 6-10 concrete divergence rules from day one. Your iteration cycle is "tighten what's already there."

Risk: some of those opinions are untested assumptions that won't survive contact with this codebase. The rule that worked at your last job may produce friction here.

If you're A: revisit your file after 30 days. Some of those opinions won't survive contact with the actual work. Delete what stopped helping.

**Trajectory B: You arrived without strong opinions.**
AI is new to you, or you're early-career and haven't yet calibrated what you want. Your interview answers were tentative. Your file is short. Your iteration cycle is "discover preferences as I work, add them as they crystallize."

Risk: the file stays empty too long. No opinions = no leverage. Claude defaults to its base behavior, which isn't tailored to you.

If you're B: every time something annoys you, write it down immediately. That's the discovery process. Don't wait until you have 10 opinions to start the file. Start with one.

**Trajectory C: You arrived with calibrated taste for outcomes, rusty on the day-to-day idiom.**
You spent enough years writing code to develop strong opinions about what good software looks like, but you've spent the last several years orchestrating, reviewing, or managing rather than typing. You know "done well" when you see it, but you're rusty on current idioms, modern tooling, and the texture of well-named-this-week patterns. Your interview answers were specific about WHAT the output should be, vague on HOW it should be written today.

Your iteration cycle is "lean on the AI for current technical fluency; validate against my senior judgment about outcomes."

Risk: two failure modes. Trusting the AI's idiomatic suggestions without your outcome-level validation (it ships code that compiles but doesn't fit). Or dismissing the AI's idiom because it doesn't match the patterns you remember from your hands-on era (you ship a 2020 solution to a 2026 problem).

If you're C: invest heavily in the autonomy section. You probably want the AI to run end-to-end and then walk you through the design decisions it made, so you can validate at the outcome layer rather than the keystroke layer. "Run, then explain what you did and why" gives you more leverage than step-by-step permission.

---

## 7. Where to Go Next

* **Ready to grow your** `CLAUDE.md` from real review findings? [Build Your Context Engine](./build-context-engine.md) teaches the pipeline that takes one review comment and turns it into a one-sentence rule that catches the same class of failure on every future task.
* **Want to extend Claude with reusable workflows?** [Build Your First Skill or Command](./build-first-skill.md).
* **Ready for advanced patterns (sub-agents, multi-step, MCP integration)?** [Building Skills and Commands at Scale](./skills-at-scale.md).
* **Want concrete patterns for specific situations?** [AI-Assisted Debugging](./ai-assisted-debugging.md) or [Teaching AI to Remember](./teaching-ai-to-remember.md).
