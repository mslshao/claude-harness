# Agent Design Lessons: Advanced AI Tooling Patterns

> **Where this fits**: This page is the philosophy companion to [Building Skills and Commands at Scale](./skills-at-scale.md) in the "build your own AI tools" track of [AI Coding Tools](./ai-coding-tools.md). Same audience, different angle: this page is "why agents are designed this way," that page is "how to build skills that follow these principles."
>
> **Format**: Solo read, any pace. No exercises.
> **Prereq**: You should be comfortable with the concepts in [AI Coding Tools](./ai-coding-tools.md) (scoping, two modes, critical reading) and have written at least one skill (see [Build Your First Skill or Command](./build-first-skill.md)) before these lessons land.
> **Output**: Six structural lessons that change how you write agent definitions, with concrete patterns for each.
> **If you only have 5 minutes**: read lesson 1 (identity framing backfires) and lesson 3 (caller-injected context over agent-internal branching). They are the load-bearing principles; the rest apply them.

Advanced patterns for developers building custom AI agents or specialized tools. These lessons come from ~3 months of building and iterating on a suite of specialist agents for code review, assumption challenging, and multi-agent coordination.

---

## 1. Identity Framing Backfires

**The problem**: An agent prompt said "You are [the author]'s engineering mind operating at full capacity." The agent pushed back on valid reviewer feedback, treating external criticism as something to debate rather than address. Same failure mode appeared in two completely different role framings (coordinator and thinking-partner).

**Root cause**: Possessive identity patterns ("[Author]'s X", "act as a senior engineer who...") create advocacy. The agent identifies with the persona and resists anything that challenges it, regardless of the role noun you choose. This is structural, not a prompting mistake you can fix with better wording.

**Fix**: Pure-function tools with no persona. Instead of "You are an expert code reviewer," try "Given this diff, identify logic errors. For each: state the error, the evidence, and the impact. Do not recommend, interpret, or editorialize." The agent follows an algorithm, not an identity.

**The insight**: Identity framing is structurally adversarial to external input. If your agent needs to receive and act on feedback from others (reviewer comments, user corrections, contradicting evidence), strip the identity.

---

## 2. "Critique Yourself" Doesn't Work

**The problem**: Asking an agent to "review your own output for mistakes" or "challenge your assumptions" produces weak, self-congratulatory results. The agent has no incentive to find its own errors.

**Fix**: Mechanical checklists that separate extraction from scoring.

The pattern that works:

1. **Extract** assumptions from the plan (mechanical: scan for trigger phrases like "assumes", "depends on", "requires")
2. **Score** each assumption on two independent axes: fragility (how likely to be wrong) and impact (how much breaks if wrong)
3. **Gather evidence** for high-risk assumptions (grep the codebase, read the docs)
4. **Report** findings with evidence, not opinions

The agent follows an algorithm. It doesn't need to *want* to find mistakes. The algorithm finds them mechanically.

**Why two axes**: Fragility and impact were initially combined into one score. This caused verified high-coupling assumptions to score as FRAGILE (they're not likely to be wrong, they just matter a lot if they are). Separating the axes fixed the false positives.

---

## 3. Caller-Injected Context Over Agent-Internal Branching

**The problem**: An agent needs to behave differently in two contexts (e.g., self-review before CI vs. PR review after CI). The instinct is to add mode parameters or if/else branches inside the agent definition.

**Why that's wrong**:

* Mode parameters bloat the definition with branching logic and violate separation of concerns
* Separate agent variants double the file count for a 2-sentence difference
* Internal branching makes the agent harder to test and reason about

**Fix**: Keep agent definitions mode-agnostic (full capability). The caller injects a 2-sentence preamble that sets expectations:

* Self-review caller injects: "CI has not run. Flag everything: style, types, lint, naming, and design issues."
* PR review caller injects: "CI has passed. Focus on design judgment that static analysis cannot catch."

Same agent, different context, different behavior. The agent definition stays clean and testable.

**The principle**: Agents are functions. Context is a parameter. Don't bake context into the function definition.

---

## 4. Agents That Decide, Not Explain

**The problem**: You want an agent to approve or reject something (a plan, a diff, a change to production). You write a reviewer prompt: "Assess this against our quality bar." The agent returns three paragraphs of analysis, a long list of observations, and a soft "this generally looks reasonable with some concerns worth considering." You wanted a decision, you got a book report.

**Why this happens**: Reviewer-framed agents optimize for explaining what they see. Commentary is the safest output because a clear verdict commits to something, and observations don't. The agent hedges because nothing in the prompt rewards it for committing.

**Fix**: Constrain the output shape to a small set of verdict tokens. Three-token verdicts work well: proceed (meets the bar), iterate (specific issues + what to revisit), escalate (outside the agent's authority, needs a human). In practice these often show up as PROCEED / ITERATE / ESCALATE. The agent still has to reason about evidence, but the reasoning funnels into one of three outputs, not prose.

**What changes**: The agent stops hedging. It either greenlights the change, sends back a specific list of fixes, or flags that the decision is too important to automate. Narrative disappears. The next step is obvious from the token alone: proceed moves forward, iterate loops back with actionable feedback, escalate pauses for a human.

**When this works**: The agent has a clearly defined bar (security, correctness, specific quality criteria) and the caller has a plan for each verdict. Without a defined bar, you'll get "ITERATE" on everything because the agent has no reference point for "meets the bar."

**The insight**: Decisions are smaller than opinions. Pick the smallest output that lets you act.

---

## 5. Multi-Agent Orchestration: Caller Owns Context, Agents Own Execution

**The problem**: One task needs multiple agents working in parallel. The obvious design is several specialist agents, each with a carefully crafted system prompt encoding its role, its scope, its boundaries, its communication protocol. The system prompts diverge. Two agents develop subtly different ideas of what "done" means. Outputs don't compose. You spend more time reconciling their work than they saved you by running in parallel.

**Why this happens**: Role information lives in the wrong place. If every agent has its own identity baked into its prompt, you have N drift surfaces. When the task changes, you edit N files. When you want a role the team doesn't have, you write a new agent from scratch.

**Fix**: Role-specific parallel agents that share one execution protocol. The protocol (how to report progress, when to stop, what to hand off) is identical across the team. The role (implementer for this module, tester for that module, generalist for whatever's left) is injected by the caller as a preamble when the agent is spawned. The agent definitions themselves stay close to mode-agnostic.

**What changes**: Adding a new role is one preamble, not one new agent definition. Tuning the protocol happens once and applies to every role. A caller orchestrating three agents can reason about their work as one team with three assignments, not three independently specified bots.

**The caller's job**: Decide what each agent works on, inject the role, handle the reports. The caller is where context lives, because the caller is the only component that sees the whole picture.

**The agent's job**: Execute against the assignment, report against the protocol, stop at the boundary. No scope expansion, no reinterpreting the assignment, no synthesizing across siblings. The caller synthesizes.

**The principle**: This is Section 3 applied at team scale. Context is a parameter. It enters each agent through the call site, not the definition.

---

## 6. Calibration That Only Grows

**The problem**: Your agent has a quality bar. You encode it in the system prompt as rules (never approve without a test; reject plans that add complexity without addressing the stated goal). Over time, the agent misses cases the rules didn't cover. You add rules. Then you notice some rules are over-triggering, creating false positives. You tighten them. Six months in, the system prompt is a dense, contradictory policy document nobody wants to touch.

**Why this happens**: You're maintaining rules in the wrong place. System prompts are read every call; edits to them need full review. Mixing accumulation (what the agent learned) with pruning (what's no longer needed) means every edit touches both concerns and nothing is safe to change quickly.

**Fix**: A separate calibration file that the agent loads. Self-reflection can add to the calibration file; it cannot remove from it. Removal is a deliberate human pass, done periodically, with full context about what each rule was originally added to catch. Accumulation is fast and frictionless (a rule or example goes in the moment a miss is identified); pruning is slow and reviewed (you evaluate whether a rule's trigger conditions still match reality).

**What changes**: The agent's core definition stays stable. The calibration file grows additively. Pruning is a task someone schedules, not an accidental side effect of "I'll tighten this rule while I'm in here." You can tell at a glance what the agent has learned, because the calibration file is an append-only record.

**The parallel to persistence**: The [Teaching AI to Remember](./teaching-ai-to-remember.md) page warns that rules files need maintenance to avoid staleness. This pattern is the operational counterpart: separate the "new rule goes here" surface from the "let's audit what still applies" surface, so maintenance happens on purpose rather than by accident.

**The principle**: Learning is cheap. Unlearning is expensive. Build the mechanism that reflects that asymmetry.

---

## 7. Where to Go Next

* **Want the operational sibling to this philosophy?** [Building Skills and Commands at Scale](./skills-at-scale.md). Same audience, "how to build skills that follow these principles" angle. Worked example: a live DLQ skill build with self-correction, agent ergonomics, and sub-agent dispatch.
* **Haven't built a skill yet?** [Build Your First Skill or Command](./build-first-skill.md) is the entry point. The lessons on this page only land once you've felt the failure modes they address.
* **Apply Section 3 at the user level?** [Personalize Claude for Your Context](./personalize-claude.md). Your personal `CLAUDE.md` is caller-side context for every session.
* **Apply Section 6 to your own rules?** [Build Your Context Engine](./build-context-engine.md). The "Review findings I've codified" section is the calibration-that-only-grows pattern at user scale.

The common principle across all of this: agents are functions. Context is a parameter. Identity is a liability. Decisions are smaller than opinions. Build the smallest output that lets you act.
