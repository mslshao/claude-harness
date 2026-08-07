# Implementation Tenets

Meta-rules that govern how we apply standards when the codebase contains conflicting
patterns. These resolve "should I follow what the codebase does or what the rule says?"
without escalation.

## Core Tenets

### Best Practice Over Precedent

Existing violations are tech debt, not evidence that a rule is wrong.

The codebase contains hundreds of `unittest.mock` occurrences, deferred imports,
f-string log calls, and `typing.Any` usages. These predate current standards. They
are the backlog, not the bar. When a rule file says "X is banned," the presence of X
in existing files does not weaken that ban; it shows how much cleanup remains.

**Practical effect for new code:** Write to the rule, not to the pattern you see
nearby. When a reviewer cites frequency of a pattern as justification ("this is how
we do it everywhere"), point to the relevant rule. The tenet gives engineers license
to push back in code review.

**Practical effect for existing code:** When you touch a file for another reason,
migrate violations in the lines you're already editing. Do not sweep whole files
unrelated to your change (that expands PR scope); do clean up what you're walking
past.

### Review in Isolation

Each PR should map to one coherent concern, reviewable without holding the rest of
the codebase in working memory.

When evaluating whether a change is appropriately scoped, ask: does this work map to
one design decision or two? If the PR satisfies two separate Jira tickets, two
separate acceptance criteria sets, or two independently shippable behaviors, it is
two PRs. The test is not "can these changes be merged together" (they usually can)
but "does reviewing them together force the reviewer to context-switch between
unrelated concerns?"

Multi-thousand-line PRs are extremely rare justified cases. At that size, a reviewer
cannot hold the full diff in working memory and bugs hide in the volume. Prefer to
extract prerequisite refactors into their own smaller PRs.

### Single-Concern Execution

Execute the single concern you were assigned. Do not expand scope mid-task.

"Review in Isolation" (above) governs how to slice a PR at build time. This tenet
governs how you behave during execution: while implementing one assigned concern,
you will often notice an adjacent issue (a nearby bug, a refactor opportunity, an
untyped dict next door, a missing test). Record it as a follow-up (a tracking ticket
or a noted observation in your output) and keep working on the assigned concern. Do
not offer to expand the current change to cover it, and do not steer the author
toward unassigned work.

Why this is a default, not a preference: less-experienced engineers may over-weight a
"want me to also tackle X?" suggestion over the task they were actually assigned, and
mid-task scope expansion is how a one-concern change accretes a second. Early-career
growth comes from intentional execution on narrowly-scoped work; breadth and autonomy
follow from a track record, so the default keeps every contributor on the assigned
concern and routes the rest to a follow-up.

The discipline: finish the assigned concern, then list adjacent findings as
follow-ups. Surfacing an adjacent issue as an observation is correct; pitching a
scope expansion or redirecting the author to it is not.

### Verify Before Asserting

Do not claim work is complete without fresh evidence from the current session.

Before reporting a test passes, run it. Before reporting a type error is fixed, run
`pants check`. Before reporting a subagent completed work, check `git diff`. A prior
run, a prior session, or reasoning from first principles is not evidence. Only output
from a command run in the current session counts.

This applies equally to "the build is broken" assertions: confirm with a command
before escalating. Misdiagnosed failures waste more time than the verification
would have.

See `verification.md` for the full gate and common failure modes.

## Tenet Hierarchy

When two rules appear to conflict, resolve using this order:

1. **Security and compliance** (see `security.md`): non-negotiable.
2. **Architecture rules** (see `architecture.md`): structural decisions that
   affect multiple services are hard to reverse. Err toward compliance.
3. **Code style and testing rules**: important for long-term health but more
   locally contained. Migrate on contact when the cost is low.
4. **Precedent**: not a tenet. Existing code that violates a rule is tech debt.

## Scope

These tenets apply project-wide. For testing-specific tenets (assert outcomes not
mechanics, fake at the boundary, tests as spec), see `python-testing.md`.
