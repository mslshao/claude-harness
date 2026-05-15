---
name: refine
description: Transform rough input into a precise, actionable prompt. Use when the user asks to "refine a prompt", "improve my prompt", "shape this into a prompt", or needs help turning a terse idea into something Claude can act on.
argument-hint: "[rough prompt or idea]"
---

# Refine

The user invoked /refine to shape a rough prompt into something precise and actionable.
You have full conversation history and tool access; use both.

## Input

The user will provide one of:
- A rough, terse prompt they want to submit to Claude Code (most common)
- A partially-formed idea they want help shaping into a prompt
- An existing prompt they want improved or tightened
- A description of what they want to accomplish, without a prompt yet

## Process

### 1. Extract Intent

Read the input and identify:
- **Core goal**: What outcome do they want?
- **Implicit context**: What are they assuming is obvious? Check conversation history.
- **Scope signals**: Quick fix? Feature? Refactor? Investigation?
- **Target**: Is this for Claude Code, another agent, a different LLM?

Gather context with tools; don't guess when you can look:
- Check `git status`/`git log`/`git diff` if the prompt relates to current work
- Read agent definitions if the prompt should reference a specific agent
- Grep the codebase if the prompt mentions functionality by name
- Run `bd ready` or `bd list --status=in_progress` if the prompt relates to tracked work
- Read CLAUDE.md if the prompt involves code generation (project rules from .claude/rules/ are auto-loaded)

### 2. Shape the Prompt

**Specificity over brevity.** Name files, functions, patterns, and constraints explicitly.

**Context the LLM needs, not context the human knows.** Include file paths, architectural
constraints, expected behavior, and scope boundaries the user takes for granted.

**Ecosystem awareness.** When relevant:
- Reference which agents to use (or avoid)
- Specify plan-first vs. implement-directly
- Call out testing expectations
- Mention beads issues if tracking is relevant
- Set scope boundaries ("only change X, don't touch Y")

**Right-sized scope.** If the task is too large for one prompt, say so and suggest how
to break it up.

### 3. Present

Show the refined prompt in this format:

```
## Refined Prompt

[The complete, ready-to-use prompt]

## Changes from Original
- [Substantive changes only]

## Assumptions Made
- [Inferences the user should verify]
```

If the original was already clear: "Your prompt is clear as-is. No refinement needed."

Don't force changes. Don't pad. If it's good, it's good.

## Evaluation Criteria

A prompt is ready when all five hold:

| Criterion | Test |
|-----------|------|
| Intent clarity | Is the desired outcome unambiguous? |
| Sufficient context | Can Claude act without guessing about files, scope, or constraints? |
| Actionability | Is this a single coherent task Claude can execute? |
| Appropriate scope | Not too broad (needs breakdown) or too narrow (trivial)? |
| Explicit assumptions | Are things the user "just knows" stated? |

## Rules

- **Minimal questions, maximum output.** The user types slowly and reads fast. Present a
  complete refined prompt for scanning, don't interrogate with clarifying questions. If
  you must ask, limit to 1 essential question.
- **Don't expand terse-but-clear prompts.** "Fix typo in README" needs no refinement.
- **Don't inject your own priorities.** If the user wants a quick hack, refine for a quick hack.
- **Converge quickly.** One round of refinement is usually enough. If the user wants
  adjustments, apply them and show the updated prompt without re-explaining.
