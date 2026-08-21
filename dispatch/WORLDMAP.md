---
component: dispatch
type: directory-map
status: V1 complete (all 5 dispatch docs have entries)
authored_by: Claude Opus 5
---

# WORLDMAP: Dispatch

AI-authored commentary on each routing doc in `dispatch/`. The dispatch directory captures the IF-THEN rules that drive specialist selection, model selection, and PR review routing. Entries below are pointer-shaped: each one names when the routing doc applies and the failure mode it prevents. Read the doc for the actual rule table.

The first four docs together answer "who runs this work and on what model." Dispatch heuristic answers "which agent." Agent tiers answers "which copy of that agent and at what trust level." Model selection answers "Opus or Sonnet, and where does the supervision happen." PR review routing answers the special case where the work is itself review-shaped and the surface is GitHub. The fifth, dispatch prompt contract, answers a question the other four do not touch: given the right target, what must the prompt actually say. Routing and prompting fail independently, and a correctly routed dispatch with an underspecified prompt is the more common of the two.

---

```yaml
---
component: agent-dispatch-heuristic
type: dispatch-rule
status: active
ref: agent-dispatch-heuristic.md
fires_when: "deciding whether to handle work directly or dispatch to a specialist"
prevents:
  - "Opus-main-conversation token spend on mechanical work that mx2-executor handles"
  - "default-to-main-conversation for tasks where the right agent is obvious"
  - "specialist invocation when the work would not survive the round-trip overhead"
related: [model-selection, cost-via-delegation, pr-review-routing]
---
```

When this fires: every time work could go either way (direct vs dispatch). The doc is a numbered checklist ordered by frequency of use; first match wins.

The two highest-friction calls in the heuristic are entry #1 (rough idea → /converge vs well-scoped ticket → /launch) and the carve-out at entry #9b (PR-iteration mechanical fixes under ~20 lines go direct, not via executor dispatch, because the 200-400s dispatch overhead exceeds the 30s direct edit). Both came from observed missteps codified into rule form.

---

```yaml
---
component: agent-tiers
type: dispatch-rule
status: active
ref: agent-tiers.md
fires_when: "choosing which copy of an agent runs (personal, project, or plugin) and understanding promotion direction"
prevents:
  - "personal-tier experiments shipping to team-shared infrastructure without scrubbing"
  - "audits flagging personal-vs-project content differences as drift"
  - "broken cross-tier references after a promotion (personal-only agent referenced from project file)"
related: [lab-to-production, agent-dispatch-heuristic]
---
```

When this fires: any reference to an agent by name, any promotion decision, any divergence audit. The doc names the three tiers (user, project, plugin) and the unidirectional promotion path (personal-leads-project, scrubbed and PR'd).

The name-overlap convention is the doc's most operational rule: a promoted artifact uses the SAME `name:` frontmatter at both tiers so personal takes precedence and the richer / more-recent personal version is what runs locally. Pre-merge of a promotion PR, audit the new project-tier file for references to personal-only agents and replace with role-neutral phrasings.

---

```yaml
---
component: model-selection
type: dispatch-rule
status: active
ref: model-selection.md
fires_when: "starting a session, deciding whether to escalate mid-conversation, deciding whether to dispatch to a Sonnet specialist"
prevents:
  - "starting on Sonnet for work that needs Opus synthesis (architectural decisions, ambiguity, security)"
  - "switching the main conversation down to Sonnet and losing oversight quality"
related: [cost-via-delegation, agent-dispatch-heuristic]
---
```

When this fires: at every dispatch decision and at session start. Default is Opus; cost optimization happens via delegation, not via downgrading the main conversation. Stay on Opus (or escalate mid-conversation with `/model opus`) for synthesis, architecture, security/compliance, or when acceptance criteria are not writable upfront.

The Sonnet Mode section is the operational guide for when `/model sonnet` is appropriate: bounded categories (style fixes, test generation, PR triage, single-file bug fixes with known root cause) plus explicit escalation triggers (architectural decisions, ambiguity that won't resolve from context, security-sensitive changes).

---

```yaml
---
component: pr-review-routing
type: dispatch-rule
status: active
ref: pr-review-routing.md
fires_when: "any PR-related work (reviewing someone else's, self-reviewing before push, triage, post-publish iteration)"
prevents:
  - "ad-hoc PR review tooling choice that misses specialist concerns"
  - "self-reviews missing AC compliance, CI status, or pre-submission checks"
  - "manually polling a draft PR for bot feedback when /babysit-pr handles it"
related: [agent-dispatch-heuristic, multi-window-discipline]
---
```

When this fires: any PR review surface. The doc is a trigger-to-tool table: reviewing someone else → /pr-intel; own PR pre-publish → /pr-intel --mine; quick triage → /pr-intel --quick; pre-commit on own code → mx2-code-reviewer; comprehensive multi-agent on own PR → pr-review-toolkit:review-pr; hands-off post-publish iteration → /babysit-pr.

The split is precisely shaped: each tool produces a different output format optimized for its audience (reviewer vs author vs CI debugger). The routing prevents the friction of using the wrong tool for the case.

---

```yaml
---
component: dispatch-prompt-contract
type: dispatch-rule
status: active
ref: dispatch-prompt-contract.md
fires_when: "writing the prompt for any dispatch: subagent, workflow stage, or peer session"
prevents:
  - "state summaries sourced from an item's description while its comments carry the actual state"
  - "cross-boundary verification silently scoped to code because the rule says 'check the diff'"
  - "sweep briefs that specify a filter and no value bar, returning a triage problem"
  - "destructive operations performed on an earlier round's conditional permission"
  - "an agent told its own approval gate is unnecessary because the dispatcher already has approval"
related: [agent-dispatch-heuristic, multi-session-orchestration, self-review-protocol]
---
```

When this fires: after routing is settled and before the dispatch is sent. Seven clauses, each traced to a measured defect rather than a style preference.

The load-bearing one is clause 1. An agent asked for the current state of a tracked item reads the description and skips the comments unless told otherwise, and a description records the state at the moment it was written. A 26-item handoff sweep produced five wrong state paragraphs, all understating progress, the worst of them telling an inheritor that no fix existed on a ticket whose fix had merged six days earlier and was recorded in four comments directly above it. The dispatching session had hit the same trap itself hours earlier and written it up, which did not prevent the sweep: the clause has to be in the prompt, not in a memory file, which is why the harness also backs it with a pre-dispatch hook.

Clause 5 (approval gates belong to the acting agent) is the subagent-facing half of the peer-session rule in `patterns/multi-session-orchestration.md`. Both say the same thing: the dispatcher's approval is not the acting party's approval, because the gate belongs to whoever holds the specific mutation.
