# Debugging Discipline

## The Iron Law

No fixes without root cause investigation. Proposing a solution before understanding the failure is not debugging, it is guessing. Trace backward from the error through the call stack before writing any fix.

For bugs where the cause is immediately visible (typo, wrong variable, missing import), fix directly. This process applies when the cause is not obvious.

## Process

1. **Read the error.** The full error, not just the last line. Include stack traces, logs, and upstream context.
2. **Reproduce consistently.** If you cannot reproduce it, you cannot verify a fix.
3. **Trace backward.** Start at the failure and work backward through the data flow. In multi-component systems (Lambda, SQS, DynamoDB, Salesforce), gather evidence from each layer before forming theories.
4. **Find working reference code.** Locate similar code that works. Compare completely, not skimming. Identify every difference between working and broken.
5. **One hypothesis at a time.** Write it down. Test with the smallest possible change. Do not stack multiple fixes in one attempt.

   When a parameterized operation fails on a specific input (a query, a payload, a record), vary the input to a trivial known-good value to isolate input-specific from systemic failure BEFORE mutating its environment (config, permissions, connectors, infra). Changing the environment while the input is uncontrolled conflates two variables and burns rounds; the cheaper bisection is almost always the input.
6. **Failing test first.** Before implementing the fix, write a test that fails for the current bug and will pass when the root cause is addressed.

## Circuit Breaker

If three fix attempts fail, stop. Do not try a fourth. Instead:

- Reassess whether the root cause diagnosis is correct
- Question whether the architecture supports what you are trying to do
- Surface the situation to the user with what you have tried and what you have learned

Three failed fixes means you are patching symptoms, not addressing the cause.

**Architectural failure pattern.** When each fix reveals a new problem in a different place, or each fix requires "massive refactoring" to land, the pattern itself is wrong. This is not a sequence of failed hypotheses, it is the architecture rejecting the change. Stop and discuss with the user before attempting more fixes. The right question is not "what fix do I try next?" but "is this pattern fundamentally sound, or am I sticking with it through inertia?"

## Red Flags

Before proposing a fix, name the specific line where the failure originates and confirm the pattern matches this call path (not just the error message). Never retry after failure without new information.

Swapping one interchangeable component for another (connector A for connector B, region X for region Y) without a hypothesis that predicts a different outcome is a no-new-information retry: if you cannot say why the swap would behave differently, isolate the variable instead.

## Multi-Component Debugging

When the failure spans services, identify which component owns the failure first. Check contracts between components (request/response shapes, event schemas) before checking internal logic.

**Diagnostic instrumentation pattern.** Before forming theories about which component fails, log at every component boundary in one diagnostic run:

- Safe identifiers and metadata about what enters each component (for example: IDs, schema/version, counts, sizes, status flags), not raw payload contents
- Safe identifiers and metadata about what exits each component, not raw payload contents
- Whether environment and config propagated across the boundary, logging variable names, presence/absence, or an explicitly allowlisted subset of non-sensitive values, not secret values
- State at each layer, limited to non-sensitive diagnostic metadata

Never log secrets, credentials, tokens, full env var values, PII, or full request/response/document payloads. Mask or redact sensitive fields, and prefer logging shapes, counts, IDs, and other safe metadata. This rule is enforced by `rules/security.md`; diagnostic instrumentation does not relax it.

The output of one instrumented run shows WHICH component fails, often eliminating two or three layers from suspicion. THEN investigate that specific component. Skipping this step trades 15 minutes of instrumentation for hours of guessing across layers.

Example shapes (concrete commands depend on the system):
- Lambda → SQS → consumer: log message ID/correlation ID before publish, message attributes after publish, and payload schema/version or size in consumer
- API → service → DB: log request ID, route, validated input shape, query parameters that are safe to record, and query result metadata such as row count/status
- Build pipeline: log env var names, presence/absence, or an allowlisted subset of safe config values at each stage boundary

The instrumentation is throwaway. Do not commit it.
