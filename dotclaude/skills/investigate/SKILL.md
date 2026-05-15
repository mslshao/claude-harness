---
name: investigate
description: Structured investigation of production errors. Use when investigating any production error, Lambda failure, unexpected behavior, or silent regression, especially when an error message or stack trace is pasted into the conversation. Traces backward from the failure point through call path and git history, identifies the introducing change, looks for in-flight fixes, and estimates blast radius. Produces a structured investigation document with file:line citations ready to paste into Jira or Slack. Does NOT propose fixes (investigation only). Use before /bead-forge (fix planning) or /consult (multi-specialist review) when contributing factors are not yet known. Also trigger on phrases like "what's causing this", "prod issue", "error in Lambda", "why is X failing", "this error started after".
---

# investigate

Structured investigation of production errors. The goal is to answer specific questions about what happened before anyone proposes a fix. Proposing fixes before understanding the failure is guessing; a good guess is still a guess.

This skill ends at a structured investigation document that names contributing factors and the leading hypothesis. It does not write or propose code, and it does not assert a single "root cause" when multiple factors are at play.

## Phase 1: Parse the error

Before reading any files, extract from the error message or context:

1. **What failed**: exception type and message (verbatim)
2. **Where it failed**: file and line from the stack trace
3. **What triggered it**: the specific value, field name, or behavior that caused the failure
4. **When it became visible**: was this always failing, or did a recent deploy expose it?

Write these four items down before reading anything. If any are unclear, note them as "unknown (to be determined)."

## Phase 2: Derive investigation questions

From the parsed error, derive 4-5 questions to answer. Frame them as questions with specific, falsifiable answers, not open-ended directions.

Every investigation should include at least:

**Q-origin**: Which code path introduces [the bad value / missing field / unexpected behavior]? Trace backward from the failure point.

**Q-contract**: Is [the target schema / mapping / interface / config] supposed to accept this? Does the target need to be updated to include it, or does the source need to stop sending it?

**Q-regression**: Which PR or commit introduced this? Was it working before a recent change, and if so, which change broke it?

**Q-inflight**: Is a fix already in flight on a branch, open PR, or ticket? Knowing this changes the recommendation.

**Q-blast**: Is this always failing, or only under specific conditions? What's the scope?

Write the questions out before investigating. Answering them is the structure of Phase 3.

## Phase 3: Investigate

### Read files in parallel

When you need to read multiple files, read them all in a single batched set of tool calls, not one at a time. Reading sequentially signals that you haven't thought through what you need. Typical first-pass batch:

- The file at the failure line (with surrounding context)
- The schema, mapping, or contract that defines what's valid at the failure point
- The builder, handler, or assembler that produces the value being rejected

### Trace the call path backward

Start at the line where the error is thrown. Work backward:

- What calls this function?
- What value does it receive, and where does that value come from?
- Where is that value constructed or assembled?

Don't stop when you find "where it enters the system." Keep tracing until you find the decision that caused the mismatch between what's being produced and what's expected.

### Find the regression commit

Once you know which code introduces the bad value, check git history:

```bash
git log --oneline -- <relevant_files>
```

Look for the commit that added the field, changed the schema, altered the behavior, or removed a guard. Cross-reference with PR titles. When you find it, note the PR number and what it changed.

Check whether the change that introduced the regression also should have updated something else (e.g., added a field to Python models without updating Terraform mapping). That gap is often a contributing factor.

### Check for in-flight fixes

```bash
git branch -a | grep -i <relevant_terms>
git log --oneline <candidate_branch>
```

Also check open PRs:
```bash
gh pr list --state open --search "<relevant terms>"
```

If a fix is already in flight, note it. Deploy order often matters; code that writes new fields before the schema accepts them will reproduce the error.

### Estimate blast radius

Determine whether failures are:

- **Always**: every event of this type fails (e.g., the schema rejects a field that's always present)
- **Conditional**: only when a specific field is non-null, a specific code path is taken, or a specific data shape appears

For conditional failures, identify the condition and reason about its frequency. "Only when `mass_tort_type` is non-null in the associated matter" is a useful blast radius estimate even without production query access (note: this is an estimate).

If blast radius requires production data to verify precisely, say so and provide a reasoning-based estimate.

## Phase 4: Output

Produce a structured investigation document using this format. The structure is the output; use it verbatim.

---

## Investigation: [error type, one line]

**Error**: `[exception type and message]`
**Component**: [service or Lambda name]
**Became visible**: [when, e.g., "after PR #NNNN deployed" or "always present"]

### Investigation Questions

For each question from Phase 2, answer it with evidence. Cite files and line numbers as `file.py:N` or `file.py:N-M`. Every claim should be traceable.

**Q: [question text]**
[Answer. File:line citations for every claim.]

**Q: [question text]**
[Answer. File:line citations.]

(continue for all questions)

### Findings

[Lead with the leading hypothesis: the most likely chain of decisions that produced the failure, named at the specific line or PR where the chain originates. Then list contributing factors as separate bullets when more than one is at play (e.g., a missing schema update + a deploy-order assumption + a default that masked the issue in dev). Avoid framing this as "THE root cause" if the failure has multiple contributing factors. State explicitly what was changed, what was not updated to match, and why the two are now inconsistent. No fix proposals.]

### Blast Radius

[Always / Conditional. If conditional: the specific condition that triggers it, and a frequency estimate. If frequency cannot be verified without production data, state that explicitly.]

### In-Flight Fix?

[Yes / No. If yes: branch or PR name, what it changes, and whether deploy order matters. If no: state that none was found.]

### Next Steps

- If fixing: open `/bead-forge` with this investigation to decompose the fix into work items
- If communicating: the Findings section above is ready to paste into a Jira comment or Slack message

---

## Hard constraint

Do not propose a fix, draft a PR, write code, or describe what a fix "would look like." If you find yourself writing "the fix is..." or "to resolve this, you should...", stop.

The reason: fix proposals made before the investigation is fully documented are guesses. Even a correct guess bypasses the verification step and makes the fix harder to explain to others. Investigation first; fixes belong in a separate skill invocation.

If asked what to do after the investigation, point to `/bead-forge` or `/consult`.

## Confidence calibration

Answer only what the evidence supports. If a claim requires data you don't have access to (production query, live metrics, downstream service behavior), say so: "Cannot verify without production query; estimate based on [reasoning]." Calibrated uncertainty is part of a good investigation. Overconfidence is worse than acknowledging a gap.

When the evidence supports multiple plausible chains rather than one, name them as alternative hypotheses with their relative weight, instead of forcing a single conclusion.
