---
component: patterns
type: directory-map
status: V0 complete (all 12 pattern docs have entries)
authored_by: Claude Opus 5
---

# WORLDMAP: Patterns

AI-authored commentary on each pattern doc in `patterns/`. These docs are the tool-agnostic philosophy: rules the harness applies, with each rule's origin in a specific failure mode the model produces by default.

Entries below are pointer-shaped, not full-explanation. Each pattern doc is itself the explanation; this WORLDMAP names when the pattern fires, the failure mode it prevents, and which other patterns it composes with. Read the doc for depth.

The patterns split loosely into three layers: process discipline (context loading, self-review, reflection trigger), output discipline (writing style, code discipline, response behavior), and meta-rules (decision-making, lab-to-production promotion, cost-via-delegation, multi-window discipline). Multi-window discipline is the load-bearing one because it grounds the others; the rest exist because attention is fragmented and the harness has to survive that.

---

```yaml
---
component: lab-to-production
type: pattern
status: active
ref: lab-to-production.md
fires_when: "deciding whether a personal-tier artifact (agent, skill, rule) is ready to promote to project tier"
prevents:
  - "personal-tier experiments shipping to team-shared infrastructure without vetting"
  - "audits flagging personal-vs-project divergence as drift when it is intentional"
related: [reflection-trigger, decision-making-rules]
---
```

When this fires: any artifact lives at two tiers (personal `~/.claude/`, project `.claude/`). The promotion path is unidirectional and explicit; divergence below the promotion line is intentional. The pattern's structural enforcement is the name-overlap convention (same `name:` frontmatter, personal takes precedence) and the project-PR review step.

The doc names the audit-mistake failure mode specifically because the audit rule is easy to write but easy to apply too aggressively (treating personal-only content as duplication of project content it has not yet been promoted from).

---

```yaml
---
component: reflection-trigger
type: pattern
status: active
ref: reflection-trigger.md
fires_when: "user corrects the model's approach or a tool call fails non-trivially"
prevents:
  - "the same correction recurring across sessions without a durable artifact"
  - "umbrella memories bloating with dated tally entries instead of structural enforcement"
related: [two-strike-pattern, decision-making-rules, self-review-protocol]
---
```

When this fires: a correction lands. The pattern enforces a two-step search-then-classify protocol (search memory for prior corrections on the topic; if a match exists within 30 days, escalate to /reflect; otherwise save and continue). The convergence rule (when umbrella memory plus structural enforcement are both in place, stop tallying) is the load-bearing part.

The doc's "rationalization-refusal table" is the discipline layer: a list of plausible-sounding reasons to skip the reflection step, paired with rebuttals. Useful when the model's default is to gloss past a correction.

---

```yaml
---
component: self-review-protocol
type: pattern
status: active
ref: self-review-protocol.md
fires_when: "after writing or modifying code or executable specifications"
prevents:
  - "shipping unverified work (the verification gate in verification.md is the structural backstop)"
  - "missing class-of-issue gaps that a multi-pass review would catch"
related: [code-discipline, decision-making-rules]
---
```

When this fires: after every code change. Two passes for small tasks (correctness, style), four passes for large tasks (correctness, clarity, edge cases, agent review). Stop early on convergence (a pass that produces no changes).

The pattern explicitly extends to executable specifications (agent definitions, skills, slash commands); these are instructions agents follow literally and require the same rigor as code. Naming this extension is the doc's contribution beyond a generic "review your work" rule.

---

```yaml
---
component: contrapositive-proof
type: pattern
status: active
ref: contrapositive-proof.md
fires_when: "authoring a rule, skill, or agent definition that a model will read literally as an executable spec"
prevents:
  - "a principle nested inside a conditional being read as licensing the contrapositive (under the threshold implies the opposite)"
  - "numeric thresholds read backward as two-way gates when they were meant to fire in one direction only"
related: [self-review-protocol, decision-making-rules, two-tier-doctrine]
---
```

When this fires: authoring any rule a model reads literally. State unconditional principles OUTSIDE conditional scopes; mark numeric thresholds as one-way triggers (over implies the action; under implies nothing). The corpus is the program the agent executes, so an ambiguous branch is a behavioral bug, not a typo.

The doc's concrete instance is the load-bearing part: a PR-size rule nested an unconditional one-concern-per-PR principle inside a ~250-line size conditional, and a literal-reading model took "under 250 lines" as a license for multiple concerns in one PR. The fix stated the concern principle unconditionally and marked the size number one-way. `evidence/2026-06-11-rules-as-executable-specs.md` carries the full case plus the honest bound (verified forward in replay; the original red was N=1 and not reproducible on demand).

---

```yaml
---
component: multi-window-discipline
type: pattern
status: active
ref: multi-window-discipline.md
fires_when: "designing any agent output, skill, or harness component that surfaces information to the user"
prevents:
  - "blockers buried in prose where a multi-window user will scroll past them"
  - "outputs that assume undivided attention from a user who is sampling 30-second slices"
related: [writing-style-discipline, response-behavior, decision-making-rules]
---
```

When this fires: every design decision about output shape. Lead with the highest-impact information; end-of-turn summaries scannable in under 30 seconds; visual signals (severity tags, code blocks for IDs) to direct attention; never bury blockers in prose.

The pattern is grounding for many of the others. Writing-style discipline (terse, calibrated), response-behavior (don't reconfirm within a directive's scope), decision-making (lead with current state) all serve the multi-window reality. The `mx2-skeptic` agent exists explicitly as the safety net for this failure mode.

---

```yaml
---
component: cost-via-delegation
type: pattern
status: active
ref: cost-via-delegation.md
fires_when: "deciding whether to handle work in the main conversation or dispatch to a subagent"
prevents:
  - "strong-model token spend on mechanical work that a smaller model handles"
  - "switching the main conversation to a smaller model and losing oversight quality"
related: [agent-dispatch-heuristic, model-selection]
---
```

When this fires: any bounded implementation task with a known root cause and small surface area. Dispatch to `mx2-executor` (Sonnet); review the returned diff; commit. The main conversation stays on Opus for dispatch and review.

The doc names the asymmetry explicitly: switching the main conversation to Sonnet means Sonnet self-assesses when it needs Opus help, which is unreliable. Delegation keeps Opus as the supervisor and Sonnet as the executor; the cost saving comes from the supervisor doing less typing, not from downgrading the supervisor.

---

```yaml
---
component: prompt-interpretation
type: pattern
status: active
ref: prompt-interpretation.md
fires_when: "user prompt is brief, ambiguous, or context-dependent"
prevents:
  - "round-trips of clarifying questions on prompts where context already resolves them"
  - "missed scope-probe questions (\"what did you X exactly?\" surfacing an underbuild)"
related: [multi-window-discipline, decision-making-rules]
---
```

When this fires: the user types tersely because they think faster than they type. The pattern says infer intent from conversation context, git state, active task tracker, and recent decisions before asking. Make one focused question if you must clarify; never multiple.

The scope-probe sub-rule is the doc's sharpest contribution: a retroactive "what did you X exactly?" is not a status request, it is a probe for missing scope. Default response: state what was done, identify the coverage gap, propose how to close it.

---

```yaml
---
component: writing-style-discipline
type: pattern
status: active
ref: writing-style-discipline.md
fires_when: "any prose output (chat, PR body, ticket comment, Slack draft, Confluence page)"
prevents:
  - "em-dashes (U+2014) slipping through prompt-only enforcement"
  - "gendered pronouns inferred from names or context"
  - "catastrophizing language on findings that don't warrant it"
  - "end-of-turn summaries that re-explain work already shown"
related: [multi-window-discipline, response-behavior]
---
```

When this fires: every output. Each constraint has structural enforcement (block-em-dash hook + stop-validate-emdash hook for em-dashes, post-output sanitizer for pronouns when calibrated, calibrated-language and HTTP-verb-caution rules for tone). Prompt-only rules degrade; the pattern depends on the hook layer.

The doc's "personal tier vocab" rule is the most specific: a person can write "the bead" or "/launch this" to the model but those terms should not appear in stakeholder-facing output. The `block-personal-tier-vocab.sh` hook is the structural backstop.

---

```yaml
---
component: code-discipline
type: pattern
status: active
ref: code-discipline.md
fires_when: "writing or modifying code (separate from prose-style discipline)"
prevents:
  - "default over-commenting (the model's instinct is to narrate)"
  - "premature abstraction (a helper for one caller, an interface for one implementer)"
  - "defensive validation against impossible states inside type-narrowed code"
  - "backwards-compatibility hacks for code that has no active consumers"
related: [self-review-protocol, decision-making-rules]
---
```

When this fires: every code change. Default to no comments; only add one when the *why* is non-obvious and not derivable from identifiers. Scope discipline (YAGNI) means three similar lines is better than a premature abstraction. Cleanup discipline means delete unused code completely instead of leaving rename / re-export / removed-comment hacks.

The doc names the model's specific failure modes (decision-history comments, ticket-reference comments, journey narration in code) so the rules have concrete teeth instead of vague "be tasteful."

---

```yaml
---
component: decision-making-rules
type: pattern
status: active
ref: decision-making-rules.md
fires_when: "evaluating recommendations, weighing evidence, routing judgment between specialists, user, and self"
prevents:
  - "deferring to specialist subagents when user evidence contradicts them"
  - "asserting absence claims without scanning loaded context first"
  - "recommending tooling/automation without proving it would change observed outcomes"
  - "code presence in main being treated as deployment evidence"
related: [reflection-trigger, self-review-protocol, verify-before-asserting]
---
```

When this fires: any time a recommendation, evaluation, or routing decision happens. The catalog is large (the doc is the longest in patterns/) because each rule has a specific incident origin; together they form the working theory of how the model fails by default in decision-making.

Three rules in this catalog are load-bearing across the harness: best-practice-over-precedent (do not justify new code by frequency of existing violations), verify-before-asserting (claim work complete only with fresh evidence from the current session), and skeptic-lens-for-specialists (specialists are colleagues, not authorities; user evidence overrides them when concrete).

---

```yaml
---
component: response-behavior
type: pattern
status: active
ref: response-behavior.md
fires_when: "structuring any response, especially destructive-op confirmations and end-of-turn summaries"
prevents:
  - "running destructive git operations without explicit user authorization"
  - "re-confirming within the scope of an already-granted directive (treating one go-ahead as scoped to each substep)"
  - "ambiguous confirmation keywords (\"go\" instead of the specific verb \"push\" or \"merge\")"
related: [multi-window-discipline, writing-style-discipline, prompt-interpretation]
---
```

When this fires: every response, with the highest leverage on destructive operations. No `git reset`, no `git push --force`, no `git stash` without explicit user request. Destructive-op confirmations use unambiguous keywords that name the verb (`push`, `merge`, `publish`, `drop`); generic `go` is fine for non-destructive confirmations.

The "don't re-confirm within scope" sub-rule is the operational corollary of multi-window discipline: a user who says "publish all these" is not asking to be re-prompted on each substep. Re-confirm only when a substep crosses into destructive scope the original directive did not authorize.

---

```yaml
---
component: context-loading-protocol
type: pattern
status: active
ref: context-loading-protocol.md
fires_when: "starting substantive work (implementation, analysis, dispatching to specialists)"
prevents:
  - "duplicating in-flight work across parallel sessions (one session creates a bead another already authored)"
  - "PR review concerns that misread a migration's current state"
  - "subagents producing findings that ignore prior decisions captured in beads"
related: [reflection-trigger, two-tier-doctrine, agent-dispatch-heuristic]
---
```

When this fires: every session start, every dispatch to a specialist, every implementation kickoff. Run `bd list --status=in_progress`, `bd ready`, and `bd show <id>` on relevant beads. Pass relevant bead context into specialist prompts; otherwise the specialist starts cold.

The doc's "epic-first check for domain-familiar work" rule is the sharpest: in active migration domains (a doc-indexing pipeline, Folio, doc_v3, classifier rewrite), `bd show <epic-id>` plus its children is the prerequisite to convergence or PR review. Skipping costs one re-planning cycle. The cost of one `bd show` is near-zero.
