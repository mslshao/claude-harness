---
component: dotclaude/hooks
type: directory-map
status: V0 complete (per-category commentary; per-hook detail lives in README.md)
authored_by: Claude Opus 4.7
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

## Shared library

`lib/log-event.sh` is source-able by every hook. Each hook calls `hook_instrument "$(basename "$0")"` at start to log invocation to a central audit file. The pattern (instrument every hook) is independent of the specific logger implementation; the instrumentation is what feeds the observability category above.

---

## Why this WORLDMAP is category-shaped

The agents/ and skills/ WORLDMAPs have one entry per component because each agent or skill is a thing-you-reach-for: the per-component "when I reach for it / what it prevents / how it compounds / limits" structure is the right shape for a thing the model invokes.

Hooks are not invoked by the model; they fire on tool-use events independent of model attention. The right shape is "when this category fires, what class of failure it prevents, how it composes with the prompt-rule and pattern layers." Per-hook detail (the trigger, the exact behavior, the portability) is in `README.md` because that detail is reference, not commentary.

Reading the two together: `README.md` answers "what does this hook do," WORLDMAP answers "why this category exists and what would be different without it."
