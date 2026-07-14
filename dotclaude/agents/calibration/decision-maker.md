# Decision-Maker Calibration

Last reviewed by Michael: 2026-06-10 (/calibrate merge: 4 merged, 1 rejected; see lookback log)

This file is read by the mx2-decision-maker agent before every decision.
The agent emits calibration drift via `bd remember` (key prefix
`calibration:mx2-decision-maker:`, FULL agent name per
`decision:calibration-key-full-agent-name-2026-06-04`); the `/calibrate` skill is the human review
gate that merges accepted entries into this file. Append-only audit of
merged/rejected entries lives at `decision-maker.lookback.md`.

---

## Rule Overrides

These rules extend or refine the defaults in the agent definition. Overrides
take precedence when they conflict with defaults. Each rule cites the source
authority (CLAUDE.md section) so future readers can trace it back.

### Operational scope: authoritative-state verification

When the artifact is operational ("what do I deploy", "what's changed since
last push", "what services are affected", "is this fix in place"), evidence
trail must include verification against authoritative operational state
(Lambda LastModified, ECS task definition revisions, Terraform state, alias
configuration, Jira ticket status), not just commit history grep. Recent
commit history surface-scans what's been merged, not what's shipped; the lag
can be months. Source: `~/.claude/CLAUDE.md` "Operational scope questions
require authoritative-state verification" (two-strike pattern in doc_v3
domain).

### Code presence is not deployment evidence

A grep hit on main does not confirm a fix is in place. Code on main can be
(a) deployed but not effective due to config/threshold/edge case, (b) deployed
but bypassed by operational flag, (c) merged but not rolled out. Before
PROCEEDing on a "fix is shipped" claim, the artifact must show: Jira ticket
status (open tickets are a strong signal the fix isn't working), production
behavior signal (CloudWatch logs, Datadog events, operational reports), or
deployment state. Source: `~/.claude/CLAUDE.md` "Code presence is not
deployment evidence."

### Validate prescribed rubrics against observed failure modes

When a runbook, SOP, or handoff prescribes a branching condition ("if miss
> 5%, escalate to Option C"), the plan must confirm the actual failure
matches the rubric's assumed cause before executing the prescribed branch.
Diagnosis can invalidate the rubric entirely; the right path may be outside
it. ITERATE if the artifact follows the rubric without confirming the
diagnosis matches. Source: `~/.claude/CLAUDE.md` "Validate prescribed
rubrics against observed failure modes."

### Recommendations need evidence, not plausibility

Before PROCEEDing on a recommendation to add a tool, MCP server, automation,
dependency, or process change, the artifact must answer: "Would this have
changed an outcome we observed?" Not "is this useful in general"; would it
have caught a specific bug, prevented a specific incident, or unblocked a
specific workflow that exists. ITERATE on generic best-practice matching
dressed up as targeted advice. Source: `~/.claude/CLAUDE.md`
"Recommendations need evidence, not plausibility."

### Type-system precedence over test-mock precedence

When a code-review flag points at a runtime guard (`if not x`,
`if x is None`), the artifact must check the production type signature
before adding annotation or narrowing. If the type system rules out the
case the guard protects against, delete the guard rather than narrowing or
annotating it. Test mocks that simulate impossible states test scenarios
the type system forbids; delete them with the guard. Source:
`~/.claude/CLAUDE.md` "Type-system precedence over test-mock precedence."

### Empirical observation overrides model speculation

When the user reports behavior that contradicts a confident prediction in
the artifact, the artifact must drop the prediction immediately, not save
face with "timing was off but it'll still happen." That preserves a wrong
model. PROCEED only when the artifact says "I don't know why this is
working, here's what we observe" rather than rationalizing the prediction.
Source: `~/.claude/CLAUDE.md` "Empirical observation overrides model
speculation."

### Strategy enumeration: include zero-code paths

When the artifact frames a decision space as A/B/C, all options should not
live in the code-change action space. Before PROCEEDing, the artifact must
have considered: "Is there a zero-code path that solves this via the
platform's own settings (UI toggle, permission grant, configuration in an
external system)?" If the answer is unknown, that is the FRAGILE assumption
to challenge first. Source: `~/.claude/CLAUDE.md` "Strategy enumeration:
include zero-code paths."

### Locked-target integrity and designed read events

ITERATE-refine when (a) synthesis silently re-scopes a capability target the
user explicitly locked (audience drift: half a locked 70/30 diagnosis dropped
without surfacing the change), or (b) the capability target requires a
retrieval path but the plan has no designed read event (a write-only artifact
with no read trigger does not deliver the capability). Source: 2026-05-20
/converge comprehension-anchor gate; merged 2026-06-10. The companion
lighter-alternative trigger from the same incident is covered by the standing
proportionality criterion in the agent definition.

### Unconfirmed-mechanism candidates route to instrumentation first

At ideation/launch gates, when the candidates all target an UNCONFIRMED
mechanism hypothesis (the failure mode has never been instrumented or
observed; e.g. a zero-count metric that collapses 4+ distinct failure modes
observationally), ESCALATE-ROUTE to /investigate rather than rating the
candidates. Designing solutions against a never-tested model is the
fixing-for-unconfirmed-root-cause failure; debugging.md Iron Law and the
Diagnostic Instrumentation Pattern own the next step. Source: 2026-05-21
/ideate pr-intel mutation-execution gate; merged 2026-06-10.

### Verify checkable data parameters before rating

When a top candidate rests on a CHECKABLE data parameter (a retention window,
a count, a quota, a date range), verify the parameter holds with a single
tool call BEFORE rating verifiability/consequence. Instance: a transcript-mine
plan assumed a 90-day baseline; one `find` showed ~35-day actual retention,
falsifying the window and flipping a would-be PROCEED to ITERATE. Distinct
from the unconfirmed-mechanism rule above: this is an unverified-but-checkable
DATA PARAMETER, not a mechanism hypothesis. Source: 2026-06-09 ideation gate;
merged 2026-06-10.

### Fail-closed semantics: plan must name concrete exception classes

When a plan describes fail-closed handling around an external library call
(Elasticsearch, Salesforce, boto3, third-party SDK), the plan text must
enumerate the specific exception classes the `except` clause will catch.
Phrases like "raised by the existing class contract" or "handled by the
standard wrapper" defer the contract to implementation time, where it slips:
the caught class can be a sibling (not parent) of what the plan implied, so
peer error classes escape and crash the path that was supposed to fail
closed. ITERATE at Gate 1 when the plan invokes fail-closed semantics on
an external call without naming the concrete classes. Source: 2026-05-19
`docr-5x7j` ES-rescue plan, PR #9193; `mx2-silent-failure-hunter` found
`elasticsearch.ApiError` is a sibling (not subclass) of `TransportError`,
so 401/403/400 escaped the catch and inverted the fail-closed intent.

---

## Example Decisions

### PROCEED Examples

**Single-service Lambda change with clear scope**
Plan: Add a health check endpoint to the metadata-updater service. One new
handler function, one new route, one test. No infrastructure changes. Evidence
trail shows existing health check patterns in 3 other services were read and
the pattern is being followed.
-> PROCEED because: well-scoped, follows existing pattern, no architectural
   impact, evidence trail confirms codebase was searched.

**Pydantic model addition for existing data flow**
Plan: Add a Pydantic model for the SQS message payload that is currently an
untyped dict. No behavior change; type safety improvement only. Evidence shows
the dict shape was verified from 4 call sites.
-> PROCEED because: pure type-safety improvement, no behavior change, evidence
   trail shows all call sites verified.

### ITERATE Examples

**typing.Any in model validators**
Plan: Create a new Pydantic model with `model_validator` that uses `typing.Any`
for the input parameter. Design notes say "we'll type it later."
-> ITERATE because: typing.Any is banned. The validator input type should be
   `dict[str, str]` (or whatever the actual input shape is). Revisit: decompose.
   (Source: agent-generation-pitfalls memory)

**New code path when existing pipeline serves**
Plan: Create a new Lambda function to re-index documents after metadata updates.
Evidence trail does not mention the existing metadata-updater pipeline or whether
sending a message through the normal path would accomplish the same thing.
-> ITERATE because: pipeline bypass not evaluated. Before adding a new code path,
   verify that the existing pipeline cannot serve this need. Revisit: decompose.
   (Source: converge pipeline-reuse-gate)

**Boolean parameter creating two functions**
Plan: Add an `include_deleted` boolean parameter to the document search function
that changes the query logic. When True, it queries a different index with
different filters.
-> ITERATE because: boolean parameter creates two functions in one. Split into
   `search_documents()` and `search_documents_including_deleted()` with shared
   internals. Revisit: decompose.

**Thin evidence trail**
Plan: Refactor the worker lifecycle management. Evidence trail shows 2 files
read and 0 infrastructure checks. No Terraform verification. No check of
shared base classes.
-> ITERATE because: evidence trail is too thin for a refactor touching worker
   lifecycle. Need to verify: shared base classes (mx2.worker.worker), Lambda
   module env vars in Terraform, all services inheriting from the base.
   Revisit: challenge.

### ESCALATE Examples

**Document access control changes**
Plan: Modify how document permissions are evaluated in the search API to support
a new access level.
-> ESCALATE because: security/compliance. Document access patterns affect
   attorney-client privilege and chain of custody. Human should evaluate: whether
   the new access level is authorized by the product/legal team, blast radius
   across all document-serving endpoints.

**Shared infrastructure module modification**
Plan: Add a new environment variable to the shared Lambda Terraform module used
by 15+ services. The variable controls retry behavior.
-> ESCALATE because: cross-team infrastructure change. The shared module is used
   by services owned by multiple teams. Human should evaluate: whether the
   default value is safe for all consumers, whether teams need notification,
   whether this should be opt-in rather than default-on.

**Scope expanded from bug fix to platform change**
Plan started as "fix the metadata updater throttling bug" but the converged plan
includes: new DynamoDB table, new SQS queue, modified shared library, and changes
to 3 services. The original ask was a single-service bug fix.
-> ESCALATE because: scope expansion changed the nature of the work. Original ask
   was a targeted fix; plan is now a platform-level change. Human should evaluate:
   whether this scope is justified or whether a smaller fix addresses the
   immediate bug while the larger work is planned separately.

---

## Threshold Notes

**<Service> domain**: <Service> services (metadata-updater, search-api, indexer) have
complex interactions with Elasticsearch and DynamoDB Streams. Plans touching
<Service> should have evidence of ES index structure verification and DynamoDB
Stream configuration checks. Missing these is an ITERATE, not an ESCALATE
(the information is available in the codebase).

**Salesforce integration**: Any plan touching Salesforce sync should verify retry
logic patterns. Salesforce API is unreliable; missing retry logic is an ITERATE.

---

## False-Negative Patterns

### Delta categorization: kind of change over count of changes

In confirmation-mode convergence, DELTA_CATEGORY MINOR-vs-MAJOR weighs the
KIND of change over the COUNT. Any pinned-decision REVERSAL (a previously
ratified choice flipped on new evidence) or a reopened ratified-vs-ratified
structural conflict tips the delta to MAJOR_REVISIONS, regardless of how many
tidy guard/AC additions accompany it; the count of additions does not dilute
a decision-class change. Instance: a ~10-amendment delta framed as "MINOR,
mostly added guards" was actually MAJOR (two pin reversals incl. an
arithmetically invalidated batch size, plus one reopened structural conflict).
Source: 2026-06-10 MX2-NNNNN confirmation-mode gate; merged 2026-06-10.

---

## Self-Reflection Log

Entries below are added automatically by the decision-maker's self-reflection
protocol. Each entry includes the date, trigger, and what was added.

### 2026-04-29: PROCEED checklist trim baseline (docr-blxj)

The PROCEED checklist in `~/.claude/agents/mx2-decision-maker.md` lines 80-134
was trimmed. Sub-bullets that duplicated `.claude/rules/architecture.md`,
`security.md`, `code-style.md`, and `testing.md` + `python-testing.md`
verbatim were collapsed into a single "Project rules respected" block that
references the source files. Category (b) gate-time application bullets
(Observability, Bot-lens, Epic-first, Prescribed-mechanism, Resource-existence)
and category (c) decision-maker-unique bullets (Plan addresses intent,
Challenge phase, Consult Fix Now, Evidence trail, Each decision evaluable)
were preserved unchanged.

If decision behavior shifts after this trim (a previously-flagged violation
goes through, or a previously-passing artifact gets an ITERATE on rule
grounds), evaluate whether the rule-reference block needs more explicit
restatement of the rule at the gate, or whether the project rule itself
needs a calibration entry here.

Categorization rationale captured in bead `docr-blxj`.
