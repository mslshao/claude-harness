# Assumption Taxonomy

## Categories

Nine categories. Use the trigger phrases to extract assumptions from plans,
then filter through the relevance gate (see Extraction Discipline below).

### Codebase
Assumptions about existing code, patterns, or architecture.

**Triggers**: "We'll extend...", "There's already...", "The existing X handles...",
any reference to code that hasn't been Read/Grep'd in this conversation.

**Example**: "We can reuse the qualifier engine's operator dispatch pattern."

### Domain
Assumptions about business rules, legal requirements, or user needs.

**Triggers**: "The client needs...", "Users expect...", "The legal requirement is...",
"The workflow assumes...", any business logic assertion without a cited source.

**Example**: "Batch processing is sufficient; real-time sync isn't needed."

### Technical
Assumptions about technology capabilities, performance, or compatibility.

**Triggers**: "X can handle...", "Performance will...", "This is compatible with...",
"DynamoDB supports...", capability claims without documentation reference.

**Subtrigger - Serialization Safety**: "model_dump()", "json.dumps()", "put_events()",
"send_message()", any data crossing a serialization boundary (Python object to JSON,
API response, EventBridge event, SQS message). Challenge: "Does this data survive
serialization? Are there Enum values, datetime objects, or custom types that
`json.dumps()` can't handle without `mode='json'`?" Sentry catches these routinely.

**Subtrigger - Identity/Uniqueness Key**: any work item that gathers, stores,
diffs, merges, or deduplicates a collection of items/records/entities sourced
from 2+ upstream systems, feeds, or namespaces (cross-repo, cross-tenant,
cross-service). Challenge: "What is the uniqueness/identity key for these
items? Is the raw identifier unique only within its source namespace, and if
so does the plan's key include a namespace qualifier (e.g. `<repo>#<number>`
rather than a bare `<number>`)? Could two distinct real-world items from
different sources collide under the stated key?" Added 2026-07-10: a plan
that said a gather step "returns items" for a cross-repo GitHub PR search
never specified the key; a bare PR number collides across repos and would
have silently dropped a genuinely new review request.

**Subtrigger - State-Ownership (the WHERE)**: any work item that introduces a
new piece of persistent or coordinating state (a table, queue, lock, claim,
flag, cache, index) without naming which service/worker OWNS it and which
component is its FIRST consumer. Treat unnamed ownership as FRAGILE + HIGH by
default. Challenge: "Which component acquires/writes this state first, at what
point in the pipeline does that happen (before or after fan-out, at the
document or the chunk level, per-request or per-run), and does the named owner
actually possess the concepts the state is keyed on (does the proposed owner
have a run_id at all)? If the design says only WHAT the state is and not WHERE
it lives, the implementer's guess gets baked into every downstream item."
Added 2026-07-17: a multi-PR pilot's design said "IAM grant for the workers"
without naming which worker owns a dedup claim; the implementer bound it to
the chunk worker (a defensible reading), but the claim runs at the document
level before chunks exist. A reviewer's ownership question had already
surfaced the problem and was read past as advisory; the fix cost a mid-run
design amendment across the remaining items.

**Subtrigger - Control-Verb State-Transition Completeness**: item text
contains an operator control verb (stop/start/pause/resume/restart/cancel)
applied to a recurring, scheduled, or background mechanism. Treat the
claimed control guarantee as FRAGILE by default. Challenge: "Enumerate every
{prior-state} x {action} combination this item implies (e.g. ACTIVE+stop,
ACTIVE+resume, STOPPED+resume, STOPPED+stop). For each, does the underlying
tool's actual cancellation/queuing semantics support it, or only appear to
because the plan's prose reads as complete?" Verify against the tool's real
behavior (does it cancel an in-flight scheduled action, or only suppress
future scheduling?), not against a codebase pattern citation. Added
2026-07-10: a plan's "resume path" conflated two different meanings of
resume (a fresh session cold-starting into an ACTIVE loop, vs. restarting a
STOPPED loop) under one word; the tool in question queues rather than
cancels, so the naive reading would have let a stopped loop silently
un-stop itself.

**Example**: "DynamoDB can handle this query pattern efficiently at our scale."

### Scope
Assumptions about what's in or out of scope.

**Triggers**: "That's out of scope", "Auth is handled by...", "We don't need to...",
"This PR only covers...", boundary assertions.

**Example**: "Authentication is already handled by the upstream API gateway."

### Dependency
Assumptions about other teams, services, timelines, or external state.

**Triggers**: "Team X will...", "The schema won't change...", "By the time we...",
"The API provides...", any claim about external actors or systems.

**Example**: "The Salesforce schema won't change before we ship this feature."

### Precedent
Assumptions that a past decision still applies or that historical context is current.

**Triggers**: "We chose X in sprint N...", "The ADR says...", "We've always...",
"Last time we...", references to past decisions without checking if they're still valid.

**Example**: "We chose separate operator enums per module, so we should continue that."

### Reasoning Chain
Assumptions about logical dependencies between plan steps, where step N depends
on step N-1 being correct.

**Triggers**: "because X, therefore Y", "this enables...", "once X is done, we
can...", "X handles Y, so we don't need to...", any multi-step logic where one
conclusion builds on another.

**Example**: "Because we're using Pydantic models, validation is handled
automatically." (The "therefore" may not follow if the models lack validators
for the specific constraints that matter.)

**Subtrigger - Mechanism-Homogeneity**: item text names 2+ cases, categories,
or triggers as producing one outcome via one described mechanism ("category
X/Y/Z each produce a named alert via mechanism M"). Challenge: "Tag each
named case with its actual detection algorithm shape (membership-diff /
threshold-crossing / rate-of-change / other). Does every case's real shape
match the others, or does the plan gloss a structurally different case as
uniform prose?" A case that needs its own state machine (e.g. "alert once
per item when it crosses an age threshold, without re-alerting every cycle
it stays over") is not a diff, even when the plan describes it in the same
sentence as two cases that are. Added 2026-07-10: a plan named "aged
in-progress item" alongside two membership-diff categories with no
distinction; the aged case actually needed a non-trivial state machine
(seed only already-aged items at baseline, union newly-aged into the known
set, intersect against current membership to stay bounded) that the plan
never specified.

### Pipeline Bypass
Assumptions that new code is needed when an existing pipeline or mechanism
already provides the behavior. The most expensive assumption category: it
leads to reimplementation bugs that the existing, tested path doesn't have.

**Triggers**: "We'll construct a...", "Send a synthetic...", "Build a new method
to...", any new code path that duplicates what an existing pipeline does end-to-end.
Also: new infrastructure (settings, IAM, topics, env vars) for a code change.

**Challenge question**: "What happens if we just use the existing pipeline?
What's the cost of running one message through the normal path vs building
a shortcut?"

**Example**: A document processor needs to trigger completion for already-processed
chunks. Plan builds a synthetic CompletionRequest. Challenge: the normal doc_chunk
pipeline already handles this - re-sending one chunk through the existing path
triggers completion via the existing finally block. The shortcut had 3 bugs;
the pipeline had 0.

### Scope/Completeness
Assumptions that the plan covers everything needed. Unlike other categories,
this is detected by probing for what's NOT in the plan, not by scanning what
IS there.

**Triggers**: absence of error handling discussion, no mention of rollback or
migration path, no observability/monitoring, "this is all we need", implicit
completeness. Ask: "What does this plan NOT address that a production deployment
would require?"

**Subtrigger - Infrastructure Completeness**: When a plan includes Terraform or
infrastructure changes, probe for: missing environment configs (CD exists but no
beta/prod), missing variable pass-through to child modules, EventBridge subscription
gaps (Lambda has SQS but no EventBridge rule routing events to it), and duplicate
HCL keys that silently overwrite. Sentry catches these as CRITICAL on nearly every
infra PR. Ask: "Does this Terraform config work in all environments, or just the
one being tested?"

**Example**: A plan for a new DynamoDB table that doesn't mention GSIs, capacity
mode, or TTL. The plan is correct about what it states; it's incomplete about
what it omits.

## Extraction Discipline

**Target 3-7 assumptions per plan.** After scanning with trigger phrases, apply
a relevance gate before scoring: "If this assumption is wrong, does the plan
change in a way that matters?" If the inversion test produces "no meaningful
change," the assumption is SOLID by definition - drop it from the report.

If you extracted 10+, you're scanning too broadly. Re-read the list and cut
assumptions that don't pass the relevance gate. The goal is to surface the
3-7 that actually carry risk, not to catalog every implicit belief.

This is not mechanical pattern matching. Extraction requires judgment about what
matters, constrained by the inversion test (if wrong, does the plan change?),
not by opinion about code quality or best practices.

## Scoring

Each assumption gets two independent ratings: **fragility** (how likely to be wrong)
and **impact** (how much breaks if it is wrong). These are separate axes; a
well-verified assumption can still be high-impact, and a shaky assumption can be
low-impact.

### Fragility (SOLID / SOFT / FRAGILE)

Determined by two tests:

#### Inversion Test
"What if the opposite were true? What changes in the plan?"
- No meaningful change → SOLID
- Approach changes but direction holds → SOFT
- Plan direction invalidated → FRAGILE

*Example*: Plan assumes "DynamoDB can handle this query pattern." Inversion: "DynamoDB
cannot handle this query pattern." If true, the entire data layer changes → FRAGILE.

#### Staleness Test
"When was this last validated? Could it have changed?"
- Verified this conversation via Read/Grep → SOLID
- Verified in a recent session (referenced in beads/memory) → SOFT
- Unverified or from an old conversation → FRAGILE

*Example*: Plan says "The qualifier engine uses operator dispatch." Agent Read the
file this conversation and confirmed → SOLID. Plan says "The client prefers batch."
No one checked recently → FRAGILE.

#### Fragility Score
One FRAGILE on either test → FRAGILE overall. One SOFT without FRAGILE → SOFT.
Both SOLID → SOLID.

### Impact (HIGH / LOW)

Determined by coupling: how many plan elements depend on this assumption.

- **HIGH**: 3+ plan elements depend on it. If wrong, significant rework.
- **LOW**: 0-2 plan elements depend on it. If wrong, localized fix.

*Example*: "We'll use Pydantic models for all DTOs"; every bead references this
pattern → HIGH. "The log level should be INFO"; only the observability config
references it → LOW.

### Combined Classification

Report both: `[FRAGILE | HIGH]`, `[SOFT | LOW]`, `[SOLID | HIGH]`, etc.

- **FRAGILE + HIGH**: Top priority. Unverified and load-bearing. Must resolve.
- **FRAGILE + LOW**: Worth verifying but won't derail the plan if wrong.
- **SOFT + HIGH**: Monitor. Reasonably current but load-bearing.
- **SOLID + HIGH**: No action needed, but note as load-bearing for future reference.
- Anything + LOW with SOLID/SOFT fragility: omit from report unless user asks.

The bar is intentionally conservative: FRAGILE assumptions should be rare (1-3 per
plan), not common. If you're scoring 50%+ as FRAGILE, recalibrate; you're likely
being too aggressive with inversion tests on well-established patterns.
