---
name: investigate
description: Structured investigation of production errors. Use when investigating any production error, Lambda failure, unexpected behavior, or silent regression, especially when an error message or stack trace is pasted into the conversation. Traces backward from the failure point through call path, git history, AWS deploy state, and Datadog signals to identify contributing factors and the leading hypothesis. Produces a structured investigation document with file:line citations ready to paste into Jira or Slack. Does NOT propose fixes (investigation only). Use before fix planning or multi-specialist review (file a Jira ticket or route to a tech lead/SME) when contributing factors are not yet known. Also trigger on phrases like "what's causing this", "prod issue", "error in Lambda", "why is X failing", "this error started after".
---

# investigate

Structured investigation of production errors. The goal is to answer specific questions about what happened before anyone proposes a fix. Proposing fixes before understanding the failure is guessing; a good guess is still a guess.

This skill ends at a structured investigation document that names contributing factors and the leading hypothesis. It does not write or propose code, and it does not assert a single "root cause" when multiple factors are at play.

## Phase 1: Parse the error

Before reading any files, extract from the error message or context:

1. **What failed**: exception type and message (verbatim, for investigation context only)
2. **Where it failed**: file and line from the stack trace
3. **What triggered it**: the specific value, field name, or behavior that caused the failure
4. **When it became visible**: was this always failing, or did a recent deploy expose it?

Write these four items down before reading anything. If any are unclear, note them as "unknown (to be determined)."

**PII boundary**: capture verbatim values in your investigation notes (chat / scratch) only. The published investigation document (Phase 4 output) must redact true PII, document content, client names, and full payloads per `.claude/rules/security.md`. Unredacted system identifiers (document ID, request ID, user ID, matter ID, job ID) are not sensitive and should appear in the published artifact; they are how the investigation is reproducible.

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

### AWS context (Lambda and ECS errors)

When the error originates in a Lambda function or ECS task, fetch the current deployment configuration before forming theories about whether a regression commit is live.

Use `mcp__aws__call_aws` with `GetFunctionConfiguration` (Lambda) or `DescribeTaskDefinition` / `DescribeServices` (ECS) to confirm:

- The `LastModified` timestamp on the function or task definition (Lambda: `LastModified` field; ECS: task definition `registeredAt`)
- The currently active alias target (Lambda: `GetAlias` for aliases like `live` or `prod`)
- Environment variable values are typically non-secret configuration in MX2 services: table names, queue URLs, region, log level, SecretsManager ARN references (the secret payloads themselves are fetched at runtime, not stored in env). Record values that bear on the investigation; redact anything that looks like a raw credential or token. `DD_VERSION` is especially useful: it holds the commit hash of the deployed build, so `git log <DD_VERSION>` lists exactly which commits are running.

**Critical note on deploy lag.** `LastModified` reflects when the function was last deployed, not when the commit was merged. The lag between a merge and the corresponding deploy can be days or weeks. Do NOT assume a recent commit is running in production unless the deploy timestamp confirms it. If `LastModified` predates the regression commit, the regression is not yet in production and the investigation focus shifts.

Example: to check a Lambda named `my-service-prod`:

```
mcp__aws__call_aws(
  service="lambda",
  operation="GetFunctionConfiguration",
  parameters={"FunctionName": "my-service-prod"}
)
```

Check the `LastModified` field against the regression commit date before concluding the commit caused the observed error.

### Datadog context (confirming current firing state)

Before concluding an error is actively causing production impact, verify it is currently firing using the `mcp__datadog__*` tool family. Checking git history tells you what code changed; Datadog tells you whether the error is actually happening now.

Relevant tools:
- `mcp__datadog__search_datadog_logs` - search for the error message in recent log windows
- `mcp__datadog__aggregate_spans` - group by service or error type to confirm active traces
- `mcp__datadog__search_datadog_events` - check for correlated deployment or alert events
- `mcp__datadog__search_datadog_incidents` - check for open incidents tied to the error
- `mcp__datadog__search_datadog_errors` (Error Tracking) - get case-level first_seen, last_seen, count

Target fields from a Datadog query:
- Error count over last 24 hours
- `first_seen` and `last_seen` timestamps
- Whether the case is currently open or resolved
- Fingerprint stability (see gotcha 3 below)

**Three gotchas - apply before forming any Datadog theory:**

1. **ECS service tag suffix.** ECS-deployed services carry an `-ecs` suffix on their Datadog service tag. Query `<service>-doc_chunk-ecs`, not `<service>-doc_chunk`. Always verify the actual service tag via `mcp__datadog__aggregate_spans` grouped by `service` before forming theories. Using the wrong tag returns zero results and incorrectly suggests the error is not firing.

2. **Flex tier retention for windows over 7 days.** Any query window greater than 7 days needs `storage_tier: "flex_and_indexes"` set explicitly. The default hot tier silently drops older data; queries that span more than 7 days will appear to show zero matches when matches exist in the flex tier. A query showing zero results for a window over 7 days cannot be trusted without confirming the storage tier parameter.

3. **Error Tracking fingerprint drift.** Error Tracking case fingerprints can drift over time. A single ET case can accumulate different stack-trace fingerprints, hijacking the case across distinct error classes. Compare `first_seen` vs `last_seen` fingerprint hashes before trusting case-level "still firing" signals. If the fingerprints differ, the case may be aggregating unrelated errors under one ID.

### Estimate blast radius

Determine whether failures are:

- **Always**: every event of this type fails (e.g., the schema rejects a field that's always present)
- **Conditional**: only when a specific field is non-null, a specific code path is taken, or a specific data shape appears

For conditional failures, identify the condition and reason about its frequency. "Only when `mass_tort_type` is non-null in the associated matter" is a useful blast radius estimate even without production query access (note: this is an estimate).

If blast radius requires production data to verify precisely, say so and provide a reasoning-based estimate.

## Phase 4: Output

Produce a structured investigation document using this format. The structure is the output; use it verbatim. Include the AWS evidence and Datadog evidence sections when those sources were relevant to the investigation.

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

### AWS Evidence

*(Include this section when the error originates in Lambda or ECS.)*

- **Function/service name**: [Lambda function name or ECS service name]
- **Last deploy timestamp** (`LastModified`): [timestamp from GetFunctionConfiguration or task definition registeredAt]
- **Current alias target** (Lambda only): [alias name and version number, if applicable]
- **Deploy lag vs regression commit**: [is the regression commit deployed? confirm by comparing LastModified to commit date]

### Datadog Evidence

*(Include this section when Datadog was queried to confirm current firing state.)*

- **Case ID** (if Error Tracking case found): [ET-XXXXX or "not found"]
- **first_seen**: [timestamp]
- **last_seen**: [timestamp]
- **Current count over last 24h**: [N errors]
- **Fingerprint stability check**: [stable / drifted - if drifted, note the distinct fingerprints observed]
- **Service tag verified**: [actual service tag used, confirmed via aggregate_spans grouped by service]

### Findings

[Lead with the leading hypothesis: the most likely chain of decisions that produced the failure, named at the specific line or PR where the chain originates. Then list contributing factors as separate bullets when more than one is at play (e.g., a missing schema update + a deploy-order assumption + a default that masked the issue in dev). Avoid framing this as "THE root cause" if the failure has multiple contributing factors. State explicitly what was changed, what was not updated to match, and why the two are now inconsistent. No fix proposals.]

### Blast Radius

[Always / Conditional. If conditional: the specific condition that triggers it, and a frequency estimate. If frequency cannot be verified without production data, state that explicitly.]

### In-Flight Fix?

[Yes / No. If yes: branch or PR name, what it changes, and whether deploy order matters. If no: state that none was found.]

### Next Steps

- If fixing: file a Jira ticket or open a follow-up with the structured investigation document attached. The investigation can also feed into team review processes (PR review, design review).
- If communicating: the Findings section above is ready to paste into a Jira comment or Slack message

---

## Hard constraint

Do not propose a fix, draft a PR, write code, or describe what a fix "would look like." If you find yourself writing "the fix is..." or "to resolve this, you should...", stop.

The reason: fix proposals made before the investigation is fully documented are guesses. Even a correct guess bypasses the verification step and makes the fix harder to explain to others. Investigation first; fixes belong in a separate skill invocation.

If asked what to do after the investigation, recommend filing a Jira ticket with this investigation attached (for fix planning), or routing to a tech lead or relevant subject-matter expert for cross-specialist review of the hypotheses.

## Confidence calibration

Answer only what the evidence supports. If a claim requires data you don't have access to (production query, live metrics, downstream service behavior), say so: "Cannot verify without production query; estimate based on [reasoning]." Calibrated uncertainty is part of a good investigation. Overconfidence is worse than acknowledging a gap.

When the evidence supports multiple plausible chains rather than one, name them as alternative hypotheses with their relative weight, instead of forcing a single conclusion.
