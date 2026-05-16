# Your First Week with AI Coding Tools

A starting point for developers who haven't started yet.

> **Where this fits**: This page is the on-ramp. If you have never used an AI coding tool, or you tried once and stopped, start here. Everything else in the series (the [parent page](./ai-coding-tools.md) and its subpages) assumes you have had at least one productive AI-assisted session.
>
> **Format**: Solo read, any pace. Each "Try This Today" callout is a 5-10 minute exercise on a real (low-stakes) task.
> **Output**: One persistent-instruction rule, verified to change the AI's behavior in a fresh session.
> **If you only have 5 minutes**: read §1 (the one insight nobody tells beginners) and skim §3 (your first rule).

> **Already use AI tools daily?** The [parent page](./ai-coding-tools.md) is the better starting point.

---

## 1. "I Should Probably Learn This"

You've seen teammates get AI-assisted productivity gains. Maybe someone mentioned Copilot helped them write a test in 30 seconds. Maybe you saw a PR description that was suspiciously well-structured. Meanwhile, you tried pasting code into ChatGPT once, got a mediocre answer, and moved on.

That's a completely normal experience. Here's the thing nobody says out loud: everyone who gets value from AI tools today went through the same "this is useless" phase first.

One developer on our team reported: "I'm giving it very little specific direction and it understands what I want it to do and does it perfectly." That didn't happen on day one. It happened after weeks of learning what to ask, how to ask it, and what to ignore in the response.

This page gets you from zero to your first productive AI-assisted session. No installation guides, no feature tours, no tool-specific instructions. Just three things to try, one habit to build, and the one insight about AI tools that nobody tells beginners.

> 💡 **Try This Today**: Open any AI tool you have access to (ChatGPT, Copilot Chat, Cursor, Claude). Pick a file you're working on right now. Paste it and ask: "What does this code do? Walk me through the logic step by step." Don't ask it to change anything. Just see how well it explains code you already understand. That calibration (seeing where it's right and where it's wrong on code you know) is the foundation for everything else.

---

## 2. Three Things to Try This Week

Don't learn "AI features." Instead, take three tasks you already do and try them with AI assistance. Each one is low-risk: you're not changing production code, you're evaluating whether the AI's output is useful.

### Explain unfamiliar code

**Scenario**: You're reviewing a PR and there's a module you've never touched.

**Prompt**: "Walk me through what this function does, step by step. What are the inputs and outputs? What could go wrong?"

**Why this works**: You can verify the explanation against your own reading. The stakes are zero because you're not changing anything. And it builds the most important AI skill: evaluating whether the output is right.

**The trap**: Accepting the explanation uncritically. AI sometimes invents plausible-sounding logic for code it misunderstands. If the explanation doesn't match what you see in the code, the AI is wrong, not you.

### Generate a test draft

**Scenario**: You need to write a test for a function. You know what it should do, but the boilerplate setup is tedious.

**Prompt**: "Write a pytest test for this function. Test the happy path: \[describe expected behavior\]. Use the existing test file \[filename\] as a style reference."

**Why this works**: Test generation is one of AI's strongest use cases because the output is immediately verifiable (run the test) and you give clear constraints (expected behavior, existing style).

**The trap**: Accepting the test without reading it. AI-generated tests often test that a mock was called, not that the actual behavior is correct. Read the assertions. Ask yourself: "Does this test break only if our code changes, or would it also break if we upgraded a library?"

### Rubber-duck a problem

**Scenario**: You're stuck. Something is wrong but you can't quite articulate what.

**Prompt**: "I'm looking at \[file/function\]. Something about \[describe the symptom\] doesn't seem right. Help me think through what could cause this. Don't suggest a fix yet. Help me understand the problem."

**Why this works**: The "don't suggest a fix yet" constraint keeps the AI in thinking mode instead of solution mode. It becomes a conversation partner that helps you articulate what you're seeing, not an oracle that guesses at answers.

**The trap**: Letting the AI jump to solutions. If it starts suggesting fixes before you understand the problem, redirect: "I'm not ready for solutions yet. Help me understand why this value is null here."

> 💡 **Try This Today**: Pick one of these three. Do it today on a real task. Track two things: (1) How long did it take? (2) Did you learn something you wouldn't have found as quickly on your own? Don't worry about whether the AI output was perfect. Worry about whether it was useful.

---

## 3. Your First Rule

If you tried any of the exercises above, the AI probably got some things right and some things wrong. The things it got wrong are likely your team's conventions, not universal programming knowledge. The AI doesn't know your line length limit, your testing framework, or your import conventions.

That's fixable. Most AI tools support some form of persistent instructions: a file or setting that gets loaded into every conversation automatically. (For a full comparison of which tool uses which file, see the sibling page on [Teaching AI to Remember](./teaching-ai-to-remember.md), Section 3.)

**The exercise**: Think of one thing the AI got wrong that it would get wrong every time. Write it as a one-sentence rule.

Examples:

* "We use pytest, not unittest. Do not generate unittest code."
* "Our line length limit is 100 characters. Do not exceed it."
* "We use 2-space indentation, not 4-space."
* "Do not add `# type: ignore` without a specific error code and justification."

Put it wherever your tool reads persistent instructions. If you're not sure where that is, just paste the rule at the top of your next conversation. It works either way.

**The verification**: Start a new conversation, trigger the same scenario that produced the wrong output. Did the rule fix it? If yes, you've just configured your AI. If not, the rule needs to be more specific (you'll get better at this with practice).

> 💡 **Try This Today**: Write one rule. One sentence. Put it wherever your tool reads persistent instructions (or paste it at the start of your next session). Verify it works. Congratulations: you are now configuring your AI, not just using it.

---

## 4. The Part Nobody Tells You

The rule you wrote in Section 3? You'll rewrite it within a week. Not because you wrote it wrong. Because you'll learn more about what the AI needs to hear.

Here's the timeline that most people go through, based on the experience of developers on our team who have been iterating on their AI configurations for the past few months:

**Week 1**: You write a few rules. They're too general. "Follow best practices" produces nothing useful. "Match the existing code style" causes the AI to replicate patterns you're trying to move away from.

**Week 2**: You rewrite them to be specific. "Never use `unittest.mock`. Use `mockito` for mocking." works. "Use best-practice mocking" does not. You start to notice a pattern: the more specific the instruction, the more reliable the behavior.

**Month 1**: You've rewritten your rules 2-3 times. You discover that soft language ("consider whether tests are needed", "evaluate error handling when appropriate") gives the AI permission to skip it entirely. You switch to hard rules ("banned", "always", "never"). Research supports this: bright-line rules are measurably more effective than hedged guidance when instructing AI.

**Month 2**: You have enough rules that they start contradicting each other. You reorganize. Some rules that seemed important turn out to be unnecessary. Some rules you thought were edge cases turn out to be the most important ones.

**Month 3**: You have a system that works. It's nothing like what you started with. Every component has been rewritten at least once.

**The key insight: treating AI configuration as a one-time setup is the single most common mistake.** It's an ongoing practice, like maintaining a test suite or a CI pipeline. Your first version will be bad, and that's correct. The iteration IS the process.

Three real moments that drove rewrites on our team:

* **Feedback from a teammate**: AI-assisted review comments felt like "regurgitating AI and passing it off as my own." Triggered a full rewrite of how the tool generates output. *Lesson: feedback from others is the strongest iteration signal.*
* **A tool that kept failing the same way**: A specialized AI tool designed to help with feedback kept pushing back on valid criticism. Three rewrites of its role definition, same failure. The fix wasn't better wording. It was removing the personality definition entirely and making it a pure function. *Lesson: sometimes iteration means deleting, not improving.*
* **The "consider" vs "always" discovery**: Rules that said "consider whether tests are needed" produced zero tests. Changed to "after every new function, write at least one test." Immediate behavior change. *Lesson: you discover what works empirically, not theoretically.*

The parallel to other skills: your first unit test was probably bad. Your first PR description was probably thin. Your first CI pipeline probably had holes. You iterated on all of them. This is the same skill applied to a new domain.

---

## 5. Three Things to Try Next Week

You've done your first AI-assisted task and written your first rule. Here are three exercises to try when you're ready for the next step:

**Add a second rule. Then a third.** Each time, follow the same pattern from Section 3: notice what the AI gets wrong repeatedly, write a rule, verify it works. Your rules file grows from lived experience, not from trying to anticipate every possible scenario upfront.

**Try the two-mode distinction.** The [parent page](./ai-coding-tools.md) explains that AI review works differently before and after your CI pipeline has run. Before CI: you want the AI to flag everything (lint, types, style, logic). After CI: you want it to focus on design judgment only, because CI already checked the mechanical stuff. This is the single highest-leverage concept in the whole series. Read [Section 4 of the parent page](./ai-coding-tools.md) when you're ready.

**When the AI starts forgetting, read the memory page.** Eventually your conversations will get long enough that the AI loses earlier context, or you'll find yourself re-explaining the same things every session. When that happens, [Teaching AI to Remember](./teaching-ai-to-remember.md) addresses exactly that problem.

> 💡 **Try This Today**: Bookmark the [parent page](./ai-coding-tools.md). When you've had 3-5 productive AI sessions and are ready for the next level, read it. Don't read it now. Use the tools first. The concepts land differently after you've experienced the problems they solve.

---

## 6. Where to Go Next

* **Ready for the next level?** [AI Coding Tools (parent page)](./ai-coding-tools.md) is the next read after a few productive sessions. Trust calibration, six failure patterns, the 5-question filter, two-mode review.
* **Your AI keeps forgetting?** [Teaching AI to Remember](./teaching-ai-to-remember.md). What to persist, rules files across tools, progressive disclosure.
* **Stuck on a bug?** [AI-Assisted Debugging](./ai-assisted-debugging.md). Investigation mode, the circuit breaker, verification discipline.
* **Ready to extend Claude with reusable workflows?** [Build Your First Skill or Command](./build-first-skill.md). The entry point for writing your own.

The common thread across every page: AI tools are powerful when directed, and unreliable when given open-ended authority. In every domain (coding, reviewing, debugging, configuring, building), the difference between useful and useless is how specific your direction is. That's not a limitation. That's the skill.
