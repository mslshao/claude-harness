# Assumption Taxonomy

## Categories

Eight categories. Use the trigger phrases to extract assumptions from plans,
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
