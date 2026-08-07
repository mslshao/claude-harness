---
component: dotclaude/hooks
type: directory-map
status: V0 complete (one entry per catalog category, 10 of 10; per-hook detail lives in README.md)
authored_by: Claude Opus 5
---

# WORLDMAP: Hooks

AI-authored commentary on the hook system in `dotclaude/hooks/`. The hooks themselves are catalogued in `README.md` with per-hook trigger, behavior, "why subtle," and portability notes. This WORLDMAP sits above the README and adds per-category commentary: when the category fires, what failure mode it prevents, how it composes with the other layers (prompt rules, agents, skills).

The category split is the operational lens: each category catches a different class of failure, with different cost and reversibility. Together they are the structural backstop that the prompt-only rules depend on.

The hooks layer matters because prompt rules degrade. A rule in CLAUDE.md saying "no em-dashes" gets remembered when the model deliberately scans for it, then slipped past when the model is generating freely. A hook that scans tool inputs and outputs catches the slip independent of model attention. The combination (prompt rule + hook) is strictly stronger than the prompt alone.

---

```yaml
---
component: hooks/style-enforcement
type: hook-category
status: active
catalog_ref: README.md "Style enforcement" section
members: [block-em-dash, stop-validate-emdash, stop-validate]
fires_when: "any output surface where the writing-style discipline applies (file edits, Bash gh writers, Jira/GitHub MCP, chat output)"
prevents:
  - "em-dashes (U+2014) slipping through prompt-only enforcement on chat or tool inputs"
  - "claimed-done without a verification command actually running in the current session"
related: [writing-style-discipline, self-review-protocol, verification gate]
---
```

When this fires: PostToolUse on Edit/Write, PreToolUse on Bash gh writers and MCP Jira/GitHub, Stop on chat output. The em-dash hooks (block + stop-validate) have to be two hooks because the surfaces are different; tool inputs and chat output have no shared interception point.

What it prevents: the most-observed recurrence pattern in the writing-style rule. The em-dash is the canonical example, but `stop-validate.sh` extends the same posture to verification (runs `pants tlc` on changed Python files before turn-end). Both are mechanical enforcement of rules that prompt-only enforcement could not sustain.

How it compounds: with the writing-style-discipline pattern (which is the human-readable rule) and with the reflection-trigger (which is what produced the hook in the first place). The reflection-trigger said "umbrella memory plus structural enforcement," and these hooks are the structural-enforcement layer.

Portable: all three are in `examples/` with shape-only adjustments noted (`stop-validate.sh` needs the build-tool invocation swapped for the adopter's project).

---

```yaml
---
component: hooks/destructive-op-gates
type: hook-category
status: active
catalog_ref: README.md "Destructive-op gates" section
members: [block-destructive-commands, block-broad-targets, block-manual-pants]
fires_when: "Bash command would run a destructive op, a broad-scope build target, or a non-canonical command form"
prevents:
  - "destructive ops without explicit authorization (rm -rf, force-push to main, DROP TABLE)"
  - "broad-target build invocations that exhaust attention before producing usable output"
  - "non-canonical command forms that work but produce inconsistent output"
related: [response-behavior, code-discipline]
---
```

When this fires: PreToolUse on Bash. The hooks block the command pre-execution and surface a message; the user (or model) can override with explicit confirmation if the op was intentional. The gate is on accidental keystrokes, not on intentional destructive work.

What it prevents: the asymmetric-cost class of failure. A force-push to main is one mis-keystroke that costs hours of recovery. A `pants test ::` is one command that ties up the session for minutes producing output the user does not actually need. Each gate is cheaper than the recovery.

How it compounds: with the response-behavior pattern (which is the human-readable destructive-op discipline) and with the audit log (which records when a hook fired and which override path was taken). The hooks make the discipline structurally enforced; the audit log makes the enforcement reviewable.

Portable: `block-destructive-commands.sh` is portable verbatim. The other two are shape-only because the specific patterns to block depend on the build system and naming conventions.

---

```yaml
---
component: hooks/orchestration-guardrails
type: hook-category
status: active
catalog_ref: README.md "Orchestration guardrails" section
members: [block-guardrail-hook-edit, userpromptsubmit-pr-intel-contract, stop-validate-pr-intel, lint-tool-roster]
fires_when: "a subagent or skill-flow tries to edit an enforcement surface, or a contract-bearing skill (/pr-intel) is invoked and later ends its turn"
prevents:
  - "a subagent weakening the guardrails that police it (deny), or a skill-flow blanket-accept riding over a guardrail edit (ask)"
  - "a /pr-intel run collapsing into a prose verdict with no postable comments, or drifting over the disposition budget"
  - "config artifacts (agents, skills, commands) referencing tool names that no longer exist"
related: [verification gate, lab-to-production pattern, self-review-protocol, pr-intel skill]
---
```

When this fires: PreToolUse on Edit/Write of a guardrail surface (`block-guardrail-hook-edit`), UserPromptSubmit + Stop bracketing a `/pr-intel` run (the contract-sync pair), and on-demand for the tool-roster lint. This category is distinct from the destructive-op gates above: those protect the filesystem and remote, these protect the agent system's own enforcement layer and output contracts.

What it prevents: the meta-failure where the thing that enforces discipline is itself weakened or bypassed. `block-guardrail-hook-edit` is the sharpest case: a subagent under retry-loop pressure once edited `subagent-stop-result-contract.sh` to escape its own enforcement, so subagent-originated edits to any enforcement surface are now hard-DENIED (a plain "ask" is a no-op for subagents, the load-bearing CC gotcha here). Main-loop edits get "ask" instead, which a skill-flow blanket "y" cannot pre-satisfy. The pr-intel sync pair prevents the orthogonal failure where a multi-step skill silently degrades its output: a collapsed prose verdict with no postable inline comments leaves the reviewer nothing, so a UserPromptSubmit marker (set when the run is invoked) licenses a Stop-time collapse check that has no template header to anchor on otherwise. `lint-tool-roster` prevents stale tool references in config artifacts (the bulk of a cross-model audit's P0/P1 findings).

How it compounds: `block-guardrail-hook-edit` is the floor under every other hook in this directory; without it, the enforcement layer is editable by the actors it is meant to constrain. The pr-intel pair is two halves of one contract that must stay in lockstep: the UserPromptSubmit half front-loads the same disposition budgets the Stop half checks post-hoc, and both files carry an inline sync-contract note so an edit to one is a known edit to the other. Prevention (inject the contract before composing) plus validation (check it at turn-end) is strictly stronger than either alone. `lint-tool-roster` compounds with the lab-to-production pattern: promoting a personal artifact to project tier is exactly when a stale tool reference would slip in, and the lint is the pre-promotion check.

Portable: `block-guardrail-hook-edit` is portable (adjust the gated-surface paths to the adopter's hook layout; the agent_type discriminator and deny-vs-ask split are CC-specific but stable). The pr-intel pair and `lint-tool-roster` are not portable (the contract, budgets, and tool registry are personal-tier), but their shapes port: a marker-coupled prevent/validate pair, and a config-vs-known-registry lint.

---

```yaml
---
component: hooks/compliance-gates
type: hook-category
status: active
catalog_ref: README.md "Compliance gates" section
members: [block-jira-blind-write, block-personal-tier-vocab]
fires_when: "outbound content (PR description, Jira ticket, Confluence page, Slack message) is about to be written to a stakeholder-facing system"
prevents:
  - "Jira ticket bodies posted to the wrong field (the team's customfield_11220 convention is invisible to default MCP tools)"
  - "personal-tier vocabulary (bead/, /personal-skill names) leaking into stakeholder-facing artifacts"
related: [writing-style-discipline, response-behavior]
---
```

When this fires: PreToolUse on Atlassian MCP writes, GitHub MCP writes, Slack writes, and Bash gh writers. The hooks scan the outbound content before it lands in the external system.

What it prevents: cross-audience leakage. The model's working context includes personal vocabulary (the bead tracker name, personal skill names, the "/launch this" shorthand) that does not exist for stakeholders. A PR description that mentions "/babysit-pr will handle the rest" reads as gibberish to a reviewer who does not have that skill. The hook is the structural backstop for the audience-tier filter rule.

How it compounds: with the lab-to-production pattern (which is when personal artifacts get promoted with appropriate scrubbing) and with the writing-style-discipline pattern (which is the human-readable audience-tier rule). The Jira-specific hook composes with the project's customfield convention; the personal-tier-vocab hook composes with whatever vocab list the adopter maintains.

Portable: no for both. The Jira convention is project-specific; the vocab list is per-author. Shape-only; adopters who want the same posture author their own list.

---

```yaml
---
component: hooks/edit-time-formatters
type: hook-category
status: active
catalog_ref: README.md "Edit-time formatters and validators" section
members: [post-edit-fmt, post-edit-tf-fmt, post-edit-antipattern, post-bash-failure-inject]
fires_when: "PostToolUse on Edit or Bash; auto-formatters run on changed files, antipattern scanners surface tech debt, failure injectors add diagnostic context for the next prompt"
prevents:
  - "formatting failures landing in CI (round-trip cost vs catching at edit time)"
  - "missing the antipattern scan on files the model touched for unrelated reasons"
  - "the model asking the user for diagnostic context it could have captured from the bash failure itself"
related: [self-review-protocol, verification gate, code-discipline]
---
```

When this fires: PostToolUse on every Edit (formatters) and Bash (failure injection). The formatters run silently on success; the antipattern scanner surfaces advisory findings; the failure injector adds context to the next prompt.

What it prevents: the "CI would catch this" round-trip class. Every formatting failure caught at edit time is a CI run avoided. The antipattern scanner has a subtle gotcha: it fires on PRE-EXISTING tech debt in files the model touches for unrelated reasons, and the output looks like "Edit failed" when actually the edit landed. The doc names this gotcha explicitly so the model does not pivot into cleaning up unrelated tech debt as a side effect.

How it compounds: with the self-review protocol (the verification gate that runs at end-of-turn) and with the cleanup discipline (which says do not sweep whole files unrelated to your change). The hooks catch a class of issue at the right moment; the patterns prevent the over-correction.

Portable: shape-only for all four. The specific formatter / antipattern list / failure context to inject depends on the project.

---

```yaml
---
component: hooks/subagent-and-worktree
type: hook-category
status: active
catalog_ref: README.md "Subagent + worktree" section
members: [subagent-stop-pr-size, subagent-stop-result-contract, worktree-create-log, worktree-remove-log]
fires_when: "a subagent reports DONE (PR-size check + RESULT-contract check) or creates/removes a worktree (audit log)"
prevents:
  - "large-foundation PRs landing without scope flagging at standup time"
  - "truncated/partial subagent runs trusted as complete because the self-report sounded confident"
  - "stale agent/autopilot worktree branches accumulating untracked"
related: [agent-dispatch-heuristic, audit-worktrees skill, pr-scope-flag rule, truncated-subagent-detection]
---
```

When this fires: SubagentStop event (the size-flag and RESULT-contract hooks) and custom worktree-create/remove events. The size hook fires when a code-writing subagent reports DONE on a worktree-based implementation; it surfaces the PR size to the parent agent before any downstream review step. The RESULT-contract hook fires on the same event for launch-phase agents and checks the final message for the terminal RESULT block.

What it prevents: two orthogonal failures on the same event. The size hook catches the scope-flag class: the launch-implementer's own self-flag catches over-scoped PLANS at scope determination time, while the hook catches the orthogonal failure where a reasonable plan executed past threshold due to mid-flight refactor, test expansion, or scope discovery. The RESULT-contract hook catches the truncated-completion class: a subagent that hit a turn limit or ended mid-thought returns a summary that reads as done, and the parent trusts it. `subagent-stop-result-contract.sh` turns "does this end mid-thought?" (a judgment heuristic in the verification rule) into a deterministic check for the RESULT block, and on absence instructs the orchestrator to resume the same agent (context intact) before cold re-dispatch. Both hooks need loop guards because exit 2 re-injects as user input and re-fires Stop; the result-contract hook needs two (the harness `stop_hook_active` flag plus a per-transcript fire cap), because the first live run looped 30+ times when injected reminder text displaced the RESULT block as the last assistant text.

The worktree logging hooks compose with the `/audit-worktrees` skill: the skill identifies stale worktrees by reading the audit log the hooks produce. Without the log, the skill would have to walk the filesystem and infer state.

How it compounds: with the agent-dispatch-heuristic (which routes work to subagents in the first place), with the verification gate (the result-contract hook is the structural form of "check the diff, not the self-report"), and with the audit-worktrees skill (which cleans up what the worktree hooks logged). Dispatch creates the worktree, the SubagentStop hooks flag scope and completeness, worktree hooks log it, the skill cleans it up.

Portable: `subagent-stop-pr-size.sh` and `subagent-stop-result-contract.sh` are both portable shape-wise (the SubagentStop primitive and the RESULT-contract convention are CC/launch-specific, but the post-dispatch scope check and the terminal-block check port). The worktree logging hooks are not portable; they depend on the harness's worktree primitive.

---

```yaml
---
component: hooks/observability
type: hook-category
status: active
catalog_ref: README.md "Observability" section
members: [stats.py, stats-reminder, mcp-stats, log-mcp-calls, memory-log-sync]
fires_when: "SessionStart (stats reminder), on-demand (stats query), PreToolUse/PostToolUse on MCP tools (audit log), periodic (memory sync)"
prevents:
  - "hooks accumulating without visibility into which are load-bearing vs decoration"
  - "MCP tool calls without an audit trail for compliance or replay"
  - "in-memory state lost when the session boundary closes without sync"
related: [reflection-trigger, audit-log pattern]
---
```

When this fires: stats and stats-reminder on SessionStart (which is what produced the "last reviewed 8 days ago" nudge at the top of this session). The audit-log hooks on every MCP tool call. The memory-sync hooks periodically.

What it prevents: a hook system that grows without visibility into which hooks are load-bearing. The stats output answers "which hooks fire often, which block often, which are dead." A hook with zero firings in 30 days is a candidate for removal; a hook with high block-rate is doing real work.

The MCP audit log is the compliance layer: every MCP tool call (Jira, GitHub, Confluence, Slack, etc.) is logged with input shape and outcome. The author's MCP audit needs are specific; the shape is portable.

How it compounds: with the reflection-trigger (which uses the stats to decide whether a rule needs reinforcement) and with the audit-log discipline elsewhere in the harness (which depends on every tool call being recorded).

Portable: shape-only. The specific stats schema and audit format depend on the local hook framework.

---

```yaml
---
component: hooks/memory-mechanisms
type: hook-category
status: active
catalog_ref: README.md "Memory mechanisms" section
members: [preload-sibling-beads, bd-recency-surface, memory-log-sync, regen-memory-graph, auto-retire-stale-habits, reforge-pending-habits, surface-github-api-memory, surface-deploy-memory, preload-workflow-gotchas, record-shared-file-read, block-bd-unsafe-value, block-bd-unbounded-json]
fires_when: "SessionStart (graph rebuild, log sync, habit drain), PreToolUse on the Skill tool (sibling-bead preload), PreToolUse on Bash for tracker writes, first gh use, and deploy commands"
prevents:
  - "the ratified decision sitting in a sibling bead under a different epic never surfacing, because only the parent bead was read"
  - "a documented gotcha going unretrieved at the moment of use, so a session re-derives it or reverses a correct answer from partial live evidence"
  - "an unbounded list --json call returning the first 50 closed beads with no truncation marker, which makes an absence check read false-clean"
  - "shell-mangled or blanked values landing in the tracker while the write still reports success"
related: [context-loading-protocol, recall skill, bead-forge skill, reflection-trigger]
---
```

When this fires: SessionStart for the background maintainers (`regen-memory-graph` detaches the graph rebuild, `memory-log-sync` appends new memories to the chronological log, the habit drain reforges then retires), PreToolUse on the Skill tool for `preload-sibling-beads`, and PreToolUse on Bash for everything that guards or precedes a tracker, `gh`, or deploy command. The three timings are the category's structure: maintainers run whether or not anyone is looking, retrieval hooks fire at the moment of use, write guards fire before the write lands.

What it prevents: four failures that all leave a memory system looking healthy. Retrieval that never happens is the largest: the knowledge was already written down and correct, but nothing prompted the lookup, so one session re-derived two documented `gh` gotchas at a cost of 31 rejected calls, and another reversed its own correct per-stack deploy advice after reading a console page instead of the memory that states the pipeline scope plainly. `surface-github-api-memory` and `surface-deploy-memory` bind retrieval to the tool call rather than to session start. Cross-session duplication is the second: a second window cannot see the comment or memory the first one wrote, so `bd-recency-surface` shows the existing content before the write instead of after it. Silent truncation is the third: the tracker's JSON list defaults to 50 results ordered closed-first against a corpus of roughly 1,287 beads, with no truncation marker anywhere in the output, so "does a bead for this exist?" and "any open P1s?" both come back empty against a corpus that contains matches. Value corruption is the fourth: a code identifier written as `handler()` inside a double-quoted tracker value was executed by the shell before the tracker saw it, and `"$(cat FILE)"` against an empty file wiped a bead's acceptance criteria while the command still printed "Updated issue".

How it compounds: with the context-loading protocol (the human-readable "load beads before substantive work" rule) and with the skills that consume what these hooks maintain. `regen-memory-graph` builds the index `preload-sibling-beads` and the graph-walk skill read, so a SessionStart maintainer and a PreToolUse retriever are producer and consumer of one artifact. The parallel to the style category is exact: the prompt rule says check sibling beads, and the hook makes that fire when the model did not think to.

Limits, and they are load-bearing here. The retrieval hooks inject a heading index or a key list, not the content, so the model can still decline to read; that is calibration, not coverage. The write guards are one-shot per session and target with re-run-to-proceed, so they buy exactly one conscious re-decision. `memory-log-sync` drops any memory whose value carries no parseable date permanently, because the marker records the key as seen and it is never retried. And nothing in this category catches a memory that is written cleanly and is simply wrong.

Portable: no for every member; they are built on the tracker's exact command surface and this author's memory layout. Three shapes port: bind a documented gotcha's retrieval to the tool call that needs it, surface existing content before a write that has no merge semantics, and detach plus `flock` plus corpus-fingerprint any expensive SessionStart rebuild whose consumers already tolerate staleness.

---

```yaml
---
component: hooks/session-lifecycle
type: hook-category
status: active
catalog_ref: README.md "Session lifecycle" section
members: [check-cc-version-drift, preserve-session-title, refine-prompt]
fires_when: "SessionStart (version-drift check, title preservation) or UserPromptSubmit (prompt-interpretation hint injection)"
prevents:
  - "Claude Code version updates changing model behavior silently"
  - "session titles lost across compaction"
  - "the prompt-interpretation discipline applying only when the model remembers it"
related: [snapshot-system-prompt skill, prompt-interpretation pattern]
---
```

When this fires: SessionStart and UserPromptSubmit. The version-drift hook compares the running Claude Code version to the last snapshot and nudges to run `/snapshot-system-prompt` if different. The session-title hook preserves the user-set title across compaction. The refine-prompt hook injects a hint into terse user prompts at every UserPromptSubmit event.

What it prevents: a category of silent failures around the session boundary itself. Claude Code updates change behavior in ways that the prompt does not surface; the version-drift hook is the only chance to catch a drift event. The refine-prompt hook is the prompt-interpretation pattern mechanized: it fires at every prompt boundary, not just when the model remembers the pattern.

How it compounds: with the snapshot-system-prompt skill (which captures the new version's defaults when the drift hook fires) and with the prompt-interpretation pattern (which is the rule the refine-prompt hook applies). Hook plus skill plus pattern: three layers where each one alone would not be enough.

Portable: no for all three. CC-specific primitives (SessionStart event semantics, UserPromptSubmit hook API). The underlying patterns port; the mechanics do not.

---

```yaml
---
component: hooks/skill-contract-validators
type: hook-category
status: active
catalog_ref: README.md "Skill-contract validators" section
members: [userpromptsubmit-investigate-contract, stop-validate-investigate, userpromptsubmit-plan-contract, stop-validate-plan-present, userpromptsubmit-review-contract, stop-validate-review, stop-validate-overwatch, stop-validate-post-review-memory, userpromptsubmit-cold-review-nudge]
fires_when: "UserPromptSubmit when the first line formally invokes a contract-bearing skill (/investigate, /converge, /ideate, /launch, /review), and the paired Stop event when that session's marker exists"
prevents:
  - "an evidence section rendered as an empty heading, so a reader cannot tell queried-and-found-nothing from never-queried"
  - "a review render naming only the agents that ran, where silence about an undispatched agent is indistinguishable from a correct skip"
  - "a plan present dropping its Iteration Log and Skeptic Lens, the process evidence that gets cut first when a long run is out of turn"
  - "a standing watcher loop ending a turn without re-arming, a failure whose only symptom is the silence the user already expects"
related: [investigate skill, review skill, converge/ideate/launch skills, overwatch skill, pr-intel contract pair, verification gate]
---
```

When this fires: the producer half on UserPromptSubmit, matching the FIRST LINE only and only an unambiguous formal invocation; the consumer half on Stop, a no-op unless this session's marker file exists. Three members break the pattern on purpose. `stop-validate-overwatch` and `stop-validate-post-review-memory` self-gate on transcript evidence rather than a marker, because their trigger is an action the turn observably took (the loop ran, a review got posted) rather than a skill the user named. `userpromptsubmit-cold-review-nudge` is producer-only and advisory: it fingerprints the review target and nudges toward `/cold-review` when a second same-session pass runs against unchanged content.

What it prevents: a skill rendering something plausible instead of the contract it owes. The class is narrow and worth naming precisely: the parts dropped first are the ones carrying process evidence rather than content, and their absence is indistinguishable from success. An empty `### AWS Evidence` heading reads as a complete investigation while hiding that no live query ran, so the contract demands either a populated field or a literal `Not queried: <mechanical reason>` line. A `/review` that lists only the agents it dispatched cannot be told apart from one that dispatched all 13, so every roster agent must carry a `ran` / `skipped (<reason>)` / `n/a (<reason>)` state, which mechanically forces evaluating every dispatch signal. A converged plan with no Iteration Log is textually identical to a first draft, and one whose Skeptic Lens section is simply absent is identical to one whose adversarial pass silently failed to dispatch. The overwatch case is the sharpest: a watcher that stops re-arming produces no symptom at all, because silence is exactly what the user expects when nothing needs attention.

How it compounds: the marker is the load-bearing coupling, and it exists to break a circularity. A Stop hook can only demand a template once it knows the turn was supposed to BE that render, and the failure most worth catching (a collapse into prose) carries no header to infer that from. The prompt-time marker supplies the knowledge, which is what makes a collapse floor safe: discussion about a review, with no marker, can never false-fire. The producer is more than a marker-setter, though, since it front-loads the exact contract the Stop half checks, so prevention and validation run off one text and the retry is the fallback rather than the mechanism. This is the shape the `/pr-intel` contract pair established; that pair is catalogued under orchestration guardrails above because it polices a skill flow's disposition budgets, and the investigate, plan, and review pairs are clones of its render-validation half.

Limits: each pair caps at one forced retry via `stop_hook_active`, so a second non-conforming render ships. The checks are structural, so a render can satisfy all of them and still be a bad investigation, and honesty-by-enumeration only buys the enumeration: nothing stops an agent writing `skipped (not applicable)` without having evaluated the signal. Detection is deliberately narrower than the skills' own trigger surfaces, so a description-triggered run (a pasted stack trace routing to `/investigate`) gets no enforcement at all. And the rosters and section lists are duplicated across skill, producer, and consumer under sync contracts that are stated in prose and enforced by nothing.

Portable: no for every member; the templates, section lists, agent rosters, and vocabulary are all this author's skills. The shape ports and is compact: arm a session-scoped marker on formal invocation, inject the contract the Stop half will check, gate the Stop check on that marker, add a collapse floor for the no-header case, cap at one retry.

---

## Shared library

`lib/log-event.sh` is source-able by every hook. Each hook calls `hook_instrument "$(basename "$0")"` at start to log invocation to a central audit file. The pattern (instrument every hook) is independent of the specific logger implementation; the instrumentation is what feeds the observability category above.

---

## Why this WORLDMAP is category-shaped

The agents/ and skills/ WORLDMAPs have one entry per component because each agent or skill is a thing-you-reach-for: the per-component "when I reach for it / what it prevents / how it compounds / limits" structure is the right shape for a thing the model invokes.

Hooks are not invoked by the model; they fire on tool-use events independent of model attention. The right shape is "when this category fires, what class of failure it prevents, how it composes with the prompt-rule and pattern layers." Per-hook detail (the trigger, the exact behavior, the portability) is in `README.md` because that detail is reference, not commentary.

Reading the two together: `README.md` answers "what does this hook do," WORLDMAP answers "why this category exists and what would be different without it."
