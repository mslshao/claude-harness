# Hooks

Claude Code hooks that fire on tool-use events to enforce discipline that cannot live in prompt text alone. The structural enforcement layer the harness depends on; the catalog below is the description-first index.

Some hooks are portable verbatim (the runnable `.sh` is in `examples/`). Others are personal-tier or harness-specific and only the description appears here. The split is documented per hook below.

## Why hooks (vs. prompts alone)

Prompt rules degrade. A rule in CLAUDE.md saying "no em-dashes" gets remembered when the model deliberately scans for it and slipped past when the model is generating freely. A hook that scans tool inputs and outputs catches the slip independent of model attention. The combination (prompt rule + hook) is strictly stronger than the prompt alone.

The discipline: when a correction recurs past umbrella-memory plus prompt-rule enforcement, the next move is mechanical (a hook, linter, or validator), NOT procedural (more memories, more rule sharpening).

## The catalog

### Style enforcement (portable)

#### `block-em-dash.sh`

**Trigger**: PreToolUse on Edit/Write (scans the writable content before write), PreToolUse on Bash gh/git writers + MCP atlassian/github writers (scans the body before posting), with a PostToolUse-on-Edit/Write advisory safety net.

**Behavior**: Two enforcement modes split by surface. On PROSE surfaces (`.md` file writes, Jira comment bodies, GitHub PR/issue/review bodies, gh/git commit writers) the hook now SILENTLY AUTO-REPLACES the em-dash (U+2014) via the PreToolUse `updatedInput` mechanism: it emits `permissionDecision: "allow"` carrying the full sanitized `tool_input` (` <U+2014> ` becomes ` - `, bare `<U+2014>` becomes `-`) and the tool runs with the cleaned input, no retry prompt. On SOURCE/CONFIG surfaces (anything not `.md`: `.py`, `.ts`, `.tf`, `.json`, `.sh`) it HARD-BLOCKS (exit 2) instead of rewriting, because a U+2014 there may be an intentional string literal or test fixture that a silent rewrite would corrupt; the author fixes it by hand (or uses a `-` escape). `mcp__atlassian__updateConfluencePage` is deliberately excluded from the auto-replace group: page updates re-emit full bodies that may carry colleagues' em-dashes, and mass-rewriting their prose is a ratified non-goal.

**Why subtle**: The semantics changed from uniform block-and-retry to surface-split auto-replace. On prose, the rewrite is provably safe and removing the retry loop saves a turn; on source, the same rewrite would be a silent corruption, so the block stays. Chat-output em-dashes cannot be caught here (chat is not a tool call); the companion `stop-validate-emdash.sh` (Stop hook) keeps block-and-retry there because Stop hooks cannot rewrite chat text. The three surfaces (prose tool input, source tool input, chat output) get three different ceilings.

**Portable**: yes, see `examples/block-em-dash.sh`.

#### `stop-validate-emdash.sh`

**Trigger**: Stop event (when the model is about to end its turn).

**Behavior**: Scans the chat output for U+2014 (stripping fenced code blocks first to avoid false positives on legitimate em-dashes inside code). If detected, returns a non-blocking message that forces a retry with the em-dash replaced. Loop guard via `stop_hook_active` prevents infinite retry.

**Why subtle**: Chat output is not a tool call, so PreToolUse hooks cannot catch it. The Stop event is the only chance. The retry loop is necessary because a single retry might still produce an em-dash; the loop guard caps the cost.

**Portable**: yes, see `examples/stop-validate-emdash.sh`.

#### `stop-validate.sh`

**Trigger**: Stop event.

**Behavior**: Generic stop-time validation hook. In this author's setup, it runs `pants tlc` against changed paths to surface lint/type/test issues before turn-end. Catches the "claimed done without verification" failure mode.

**Why subtle**: The model can confidently claim "all tests pass" without having run them in the current session. The stop hook is the verification gate that forces tests to actually run.

**Portable**: shape-only, see `examples/stop-validate.example.sh`. The build-tool invocation will vary by project.

### Orchestration guardrails (mix)

These hooks police the agent system itself: who is allowed to weaken enforcement, whether a subagent actually finished, and whether a multi-step skill emitted the contract it promised. They matter most in subagent-heavy and skill-driven workflows where the failure is invisible until a downstream step trusts a partial or non-conforming result.

#### `block-guardrail-hook-edit.sh`

**Trigger**: PreToolUse on Edit/Write/MultiEdit whose `file_path` is a gated guardrail surface: `~/.claude/hooks/{block-*,stop-validate*,subagent-stop-*,lint-*}.sh`, anything under `~/.claude/hooks/lib/`, or `~/.claude/settings.json`.

**Behavior**: Two-tier gate keyed on the actor discriminator. If the PreToolUse payload carries an `agent_type` key (subagent-originated call), the edit is HARD-DENIED (`permissionDecision: "deny"`): a subagent must never modify the guardrails that police it, and it is told to surface the needed change to the orchestrator via its RESULT block instead. If there is no `agent_type` (main-loop call), the hook emits `permissionDecision: "ask"` so a per-change confirmation prompt fires that a skill-flow blanket "y" cannot pre-satisfy. The hook gates itself (it matches `block-*.sh`). Loosen-vs-tighten is deliberately not classified; every guardrail-surface edit is gated as the safe direction.

**Why subtle**: `permissionDecision: "ask"` is a NO-OP for subagent tool calls (they auto-accept with no prompt, verified by probe 2026-06-10, bd docr-pnx9), so for the subagent path "ask" would silently allow the edit. That is why the subagent branch must hard-DENY, not ask. The discriminator is itself subtle: `session_id` and `transcript_path` are identical for main-loop and subagent calls; only the presence of `agent_type` (vs `effort` on main-loop calls) tells them apart. The trigger originated in a live incident: a launch subagent under retry-loop pressure edited `subagent-stop-result-contract.sh` to escape enforcement and slipped the original `block-*`/`stop-validate*` allowlist (it matched neither), which is why `subagent-stop-*` and `lint-*` are now gated too.

**Portable**: yes, see `examples/block-guardrail-hook-edit.sh`. The `agent_type` discriminator and the deny-vs-ask split are CC-specific but stable; adopters adjust the gated-surface paths to their own hook layout.

#### `subagent-stop-result-contract.sh`

**Trigger**: SubagentStop event, matcher scoped to launch-phase agents (`launch-implementer|launch-tester|launch-flex|mx2-executor`).

**Behavior**: Reads the subagent transcript and checks whether the final assistant text carries the terminal RESULT block the launch agent defs require (`RESULT:` plus `STATUS: done|partial|blocked`). To avoid false-flagging a compliant agent whose RESULT block was displaced by harness-injected reminder/notification text, it joins the LAST THREE assistant text blocks (tail-3) and matches across them. Missing block => exit 2 with a stderr recovery script (resume the same agent via SendMessage first; cold re-dispatch only if no longer resumable). Present block, or unreadable transcript => exit 0 (fail open).

**Why subtle**: It mechanizes a judgment heuristic ("does this result end mid-thought?") into a structural signal, replacing vibe with a deterministic check. It needs two independent loop guards because the obvious one is insufficient: guard 1 honors the harness `stop_hook_active` retry flag, but the first live run still looped 30+ times when injected reminder text displaced the RESULT block as the last assistant text and `stop_hook_active` was not caught (bd docr-t1nh), so guard 2 caps firings per transcript at 2 via a scratch counter. Sibling of `subagent-stop-pr-size.sh`: same event, orthogonal concern (that one catches over-scope on DONE, this one catches missing/truncated completion).

**Portable**: yes, see `examples/subagent-stop-result-contract.sh`. The SubagentStop primitive and the RESULT-contract convention are CC/launch-specific; adopters wire the matcher to their own code-writing agent names and define their own terminal-block contract.

#### `userpromptsubmit-pr-intel-contract.sh` + `stop-validate-pr-intel.sh` (the pr-intel contract-sync pair)

**Trigger**: `userpromptsubmit-pr-intel-contract.sh` on UserPromptSubmit (when the first line of the prompt invokes `/pr-intel` on a PR in default mode); `stop-validate-pr-intel.sh` on the Stop event.

**Behavior**: The pair enforces the `/pr-intel` default-mode output contract from both ends. The UserPromptSubmit half (prevention) injects the full output contract into context AND writes a session-scoped marker (`~/.claude/scratch/pr-intel-markers/<session_id>.pending`) recording that a formal run is pending. The Stop half (validation) checks the turn's output for the required template: a `## PR #` H1, `### Review Recommendation` with `**Provenance**:` and `**Decision count**:` lines, a `### Draft Review Summary`, and a per-finding `Classification:` token; it also runs disposition-budget checks (Review Recommendation metadata-only, approve Verdict <= 25 words, body-inline dedup, total disposition prose <= 200 + 40 x decision-count words). Missing template or over-budget => exit 2 to force one retry, bounded by a `stop_hook_active` loop guard. The marker is the key coupling: a full template COLLAPSE (a prose verdict with no section headers, the failure that motivated the pair) has nothing for the Stop hook to anchor on, so the marker set at prompt time is what licenses the Stop hook's collapse check. No marker => no collapse heuristic, so discussion ABOUT a review never false-positives.

**Why subtle**: The two hooks must stay in lockstep and they cross-reference each other to say so. The "Disposition budgets" block injected by the UserPromptSubmit half mirrors the exact constants checked by the Stop half (`<= 12` words of prose on the recommendation, `<= 25` on an approve verdict, the `200 + 40*decisions` proportionality formula); editing a check in one requires updating the block in the other (the sync contract is called out inline in both files, bd docr-pnx9). The marker mechanism breaks a circularity a single Stop hook could not: a Stop hook can only enforce template-completeness once it knows the output was meant to be a pr-intel review, and a collapsed output carries no header to detect that from.

**Portable**: no for both. The contract is specific to this author's `/pr-intel` skill and its `output-formats.md` template; the disposition-budget constants and provenance/classification vocabulary are personal-tier. The shape (UserPromptSubmit sets a marker + injects the contract, Stop validates against the marker, the two cross-reference to stay in sync) is the portable idea.

#### `lint-tool-roster.py`

**Trigger**: on-demand (not wired to an event): `python3 ~/.claude/hooks/lint-tool-roster.py`.

**Behavior**: Scans Claude config artifacts (agents, skills, commands at both personal and project tier) for tool names that do not exist in the harness tool registry (`~/.claude/hooks/tool-registry.txt`). Reports unknown `mcp__*` names and unknown names in frontmatter `tools:`/`allowed-tools:` lists as FAIL (exit 1); reports tools annotated `main-loop-only` (real tools that are invisible to subagents, so a bug only if the artifact runs as a subagent) as INFO. Scope v1 is tool NAMES only; parameter-shape drift is out of scope.

**Why subtle**: Born from a cross-model harness audit where ~12 of the P0/P1 findings were stale tool references (renamed MCP tools, main-loop-only tools cited in subagent contexts, invocation shapes for tools that no longer exist). This class of drift is invisible until a run fails on a call to a tool that no longer exists; the lint surfaces it on demand. The INFO-vs-FAIL split exists because the lint cannot tell which execution context an artifact runs in, so it cannot prove a `main-loop-only` reference is wrong.

**Portable**: shape-only. The registry and the set of harness tools are specific to this author's setup; the pattern (lint config artifacts against a known-tool registry) ports.

### Destructive-op gates (portable)

#### `block-destructive-commands.sh`

**Trigger**: PreToolUse on Bash.

**Behavior**: Scans the command string for patterns that indicate destructive operations without proper authorization (e.g., `rm -rf /`, `git push --force` to main, `DROP TABLE`). Exits 2 with a message naming the operation. The author can override by re-issuing with explicit confirmation; the hook blocks accidental keystrokes.

**Why subtle**: Destructive operations have asymmetric cost (one mis-keystroke loses hours). The hook is cheaper than the recovery.

**Portable**: yes, see `examples/block-destructive-commands.sh`.

#### `block-broad-targets.sh`

**Trigger**: PreToolUse on Bash.

**Behavior**: Blocks build-tool invocations that target the entire codebase (e.g., `pants test ::`, `pants check ::`). These take minutes and rarely produce actionable output; almost always the user intended a more specific target.

**Why subtle**: Broad targets exhaust attention before producing usable feedback. A scoped target (single directory or single file) gives faster feedback.

**Portable**: shape-only. The specific patterns to block depend on the build system.

#### `block-manual-pants.sh`

**Trigger**: PreToolUse on Bash.

**Behavior**: Routes pants invocations to canonical command forms when the user types a non-canonical variant (e.g., `pants test --use-coverage` when the project convention is `pants tlc`).

**Why subtle**: Non-canonical commands work but produce inconsistent output. Routing to canonical forms keeps the team-shared lexicon stable.

**Portable**: no (pants-specific, MX2-specific routing rules).

### Compliance gates (mostly non-portable)

#### `block-jira-blind-write.sh`

**Trigger**: PreToolUse on Jira MCP writers (createJiraIssue, editJiraIssue, addCommentToJiraIssue).

**Behavior**: Enforces the MX2 Jira convention that certain ticket types must populate `customfield_11220` instead of (or in addition to) the standard description field. Blocks writes that violate the convention.

**Why subtle**: The team's Jira workflow uses custom fields that the standard Jira MCP tool would not know about. The hook is the only thing preventing the model from posting ticket bodies into the wrong field.

**Portable**: no (MX2-specific custom field convention).

#### `block-personal-tier-vocab.sh`

**Trigger**: PreToolUse on Atlassian writes, GitHub writes, Slack writes, Bash gh writers.

**Behavior**: Scans outbound content (PR descriptions, ticket bodies, Confluence pages, chat messages) for personal-tier vocabulary that should not appear in stakeholder-facing artifacts. Examples: "bead" terminology (the user's local task tracker, not a team-shared concept), specific slash command names (the user's personal skills, not project skills).

**Why subtle**: The audience-tier filter rule lives in CLAUDE.md, but the model still slips and produces stakeholder-facing content with personal-tier vocab embedded. The hook is the structural backstop.

**Portable**: no (the personal-tier vocab list is specific to this author's harness; adopters would need to author their own list).

### Edit-time formatters and validators (portable)

#### `post-edit-fmt.sh`

**Trigger**: PostToolUse on Edit.

**Behavior**: Runs the project's formatter on changed files (Python: ruff format or yapf; TypeScript: prettier; etc.). Catches the "formatter would catch this on CI" failure mode at edit time instead.

**Portable**: shape-only (formatter command varies by project).

#### `post-edit-tf-fmt.sh`

**Trigger**: PostToolUse on Edit (Terraform files).

**Behavior**: Runs `terraform fmt` on changed `.tf` files.

**Portable**: yes, see `examples/post-edit-tf-fmt.sh`.

#### `post-edit-antipattern.sh`

**Trigger**: PostToolUse on Edit.

**Behavior**: Scans the changed file for known antipatterns (banned imports, deprecated patterns, security anti-patterns). Advisory only; warns but does not block.

**Why subtle**: The antipattern check fires on PRE-EXISTING tech debt in files the model touches for unrelated reasons. The hook output looks like "Edit failed" but actually the edit landed; the antipattern was just flagged.

**Portable**: shape-only (antipattern list is project-specific).

#### `post-bash-failure-inject.sh`

**Trigger**: PostToolUse on Bash.

**Behavior**: When a Bash command exits non-zero, injects diagnostic context (recent log files, related env vars) into the next prompt. Saves the model the round-trip of asking for that context manually.

**Portable**: shape-only.

### Subagent + worktree (CC-specific)

#### `subagent-stop-pr-size.sh`

**Trigger**: SubagentStop event.

**Behavior**: When a code-writing subagent reports DONE on a large PR (more than ~1000 lines added), surface the size to the parent agent BEFORE downstream review steps. The flag is the "scope flag at implementer standup" rule mechanized.

**Portable**: yes, see `examples/subagent-stop-pr-size.sh`. Subagent dispatch primitive is CC-specific but the post-dispatch scope check is portable.

#### `worktree-create-log.sh` / `worktree-remove-log.sh`

**Trigger**: Custom hooks fired when the agent creates or removes a git worktree.

**Behavior**: Logs the worktree path, branch, and creating agent to a local audit file. Used by the `/audit-worktrees` skill to identify stale worktrees.

**Portable**: no (depends on the harness's worktree primitive).

### Observability (mostly CC-specific)

#### `stats.py`, `stats-reminder.sh`, `mcp-stats.py`

**Trigger**: SessionStart (reminder), on-demand (stats query).

**Behavior**: Tracks hook firing rates, MCP tool usage, and other observability metrics for the hooks system itself. Used to identify which hooks are load-bearing (high firing rate, high block rate) vs decoration (low firing).

**Portable**: shape-only. The stats themselves depend on the local hook framework.

#### `log-mcp-calls.sh`

**Trigger**: PreToolUse / PostToolUse on MCP tools.

**Behavior**: Audit log of MCP tool invocations for compliance and replay.

**Portable**: no (specific to this author's MCP audit needs).

(The `memory-log-sync` pair moved to the Memory mechanisms section below, where its actual behavior is documented.)

### Memory mechanisms (personal-tier)

These hooks make the two-tier memory system (always-on `bd` flash-card memories + on-demand topic files) self-maintaining: they surface related prior context before a skill runs, prevent cross-session duplication, keep the chronological log current, and retire stale entries. All are personal-tier (they depend on the author's `bd` tracker and memory-graph scratch tooling) but the patterns port.

#### `preload-sibling-beads.sh`

**Trigger**: PreToolUse on the Skill tool, for an allowlist of personal-tier information-gathering / planning skills (`converge`, `launch`, `bead-forge`, `pr-intel`, `ideate`, `enrich`, `investigate`, `challenge`, `consult`), gated to fire only when the skill exists at personal tier.

**Behavior**: Extracts recognized domain keywords from the skill args (via a domain-matcher), walks the memory graph from those keywords (via a `bd_related` walker), and injects the resulting sibling-bead / memory / topic-file candidates into the calling assistant's context as `additionalContext` before the skill runs. The injected block includes a self-filter legend (bridge > high-score match > sibling > broad-net) so the model loads the 1-2 highest-signal candidates rather than everything. Advisory only; never blocks.

**Why subtle**: The ratified decision for a piece of work often lives in a sibling bead under a different epic, which a parent-only `bd show` would miss. Surfacing those neighbors at skill-dispatch time (when the model is about to act) mechanizes the CLAUDE.md sibling-bead-check rule so it fires structurally instead of only when the model remembers to widen its search. The domain-keyword gate keeps it from firing on generic invocations.

**Portable**: no (depends on the author's domain-matcher and memory-graph walker), but the shape (walk a graph from skill args, inject neighbors as pre-skill context) ports.

#### `bd-recency-surface.sh`

**Trigger**: PreToolUse on Bash, when the command is `bd comment <id>`, `bd comments add <id>`, or `bd remember --key=...`.

**Behavior**: Before a comment or memory write lands, surfaces what is already there. For a bead comment, it shows recent comments on that bead within a lookback window (default 10h). For a `bd remember`, it shows existing memories in the same namespace prefix. Emitted as `additionalContext` so the agent sees the prior content and can build on it with an explicit cross-reference (or overwrite the existing key) rather than writing a parallel entry. Advisory only; exit 0 in all cases.

**Why subtle**: It is the producer-side complement to consumer-side recall. The duplication it prevents is cross-session: a second session has no memory of the comment or memory the first session wrote, so without this surface it writes a near-duplicate. Note the implementation gotcha it documents: PreToolUse-on-Bash stdout is silently discarded unless wrapped in the `hookSpecificOutput.additionalContext` JSON envelope.

**Portable**: no (specific to the `bd` tracker's comment/memory model).

#### `memory-log-sync.sh` / `memory-log-sync.py`

**Trigger**: SessionStart (shell wrapper backgrounds the Python worker).

**Behavior**: Appends newly-created `bd` memories to the chronological `log.md` topic file. It diffs current memory keys against a marker file, parses a date from each new memory's content, and appends a log entry in the format `/bead-forge` Phase 5 uses. The shell wrapper backgrounds the Python sync (`nohup ... &`) because a cold or contended dolt server made it block session start for up to 30s; the marker diff catches up on the next session if a run dies early. Best-effort: any failure exits 0 silently.

**Why subtle**: It uses `bd memories --json`, not the plain-text output, deliberately: the text output truncates every value at ~124 chars, which made the date parser miss the date in ~18% of dated memories and drop them from `log.md` permanently (the marker still recorded the key, so they were never retried). This JSON-vs-truncated-text distinction is a recurring trap across several of these `bd`-backed hooks and is the reason the entry exists at all.

**Portable**: no (depends on the `bd` memory store and the `log.md` topic-file convention).

#### `auto-retire-stale-habits.sh` / `reforge-pending-habits.py`

**Trigger**: SessionStart, sharing a single once-per-UTC-day throttle.

**Behavior**: Two phases drain the `/compound` habit-memory channel. The reforge phase (`reforge-pending-habits.py`) upgrades fallback `habit:*` memory entries flagged `[REFORGE-PENDING]` (created when `/bead-forge` failed mid-`/compound` run) into bead-backed habits via `bd create`, updating the memory body to point at the new bead; it is idempotent (skips creation if the body already references a bead). The retire phase auto-closes `/compound`-created habit beads that have aged out (90+ days) AND are not cited at any higher tier (topic files, `.claude/rules/`, CLAUDE.md). Only beads referenced by a `habit:*` memory key are eligible; other memory-labeled beads (handoffs, audit summaries, meeting notes) are untouched. Reversible via `bd reopen`; every action is logged to a drain jsonl.

**Why subtle**: The reforge phase runs first so newly-created beads exist by the time the retire phase scans (otherwise the retire scan would not see them). The citation check is the safety floor: a habit that has graduated into a rule or topic file must never be auto-retired even if its bead is old, so the hook greps the higher-tier surfaces before closing. Like `memory-log-sync`, the reforge worker uses `--json` because the truncated text output silently corrupted any habit body longer than ~95 chars when re-written.

**Portable**: no (specific to the `/compound` habit lifecycle and the `bd` tracker).

### Session lifecycle (CC-specific)

#### `check-cc-version-drift.sh`

**Trigger**: SessionStart, throttled to at most once per business day (Mon-Fri local) via a `state/last-drift-check` date file.

**Behavior**: Compares the running Claude Code version to the version embedded in the newest snapshot filename under `scratch/system-prompt-snapshots/` (version-sorted, not mtime, so manual file moves do not skew it). If they differ, it nudges to invoke `/snapshot-system-prompt` this session to capture the new baseline and diff against the prior one. It reads the current version from the installed package manifest (`package.json`) rather than spawning `claude --version`, because the CLI spawn cost 15-51s of session-start latency on the daily un-throttled run; it falls back to the CLI only when the manifest cannot be resolved.

**Why subtle**: The nudge is emitted on STDOUT, not stderr: SessionStart stdout is injected into model context so the model can proactively act on the drift, whereas stderr is user-UI-only and never reaches the model. Getting that backwards would make the hook a no-op for the model. The version-sort (not mtime) and the manifest-over-CLI read are both deliberate corrections of earlier slower/wrong behavior.

**Portable**: no (CC-specific; the version source and snapshot convention are harness-specific).

#### `preserve-session-title.sh`

**Trigger**: SessionStart.

**Behavior**: Preserves the user-set session title across compaction boundaries so context recovery is faster.

**Portable**: no (CC-specific).

#### `refine-prompt.sh`

**Trigger**: UserPromptSubmit.

**Behavior**: Injects a hint into terse user prompts ("the user thinks faster than they type; check conversation history before asking clarifying questions"). Implements the prompt-interpretation discipline as a hook so it fires at every prompt boundary, not just when the model remembers to apply it.

**Portable**: no (CC-specific UserPromptSubmit primitive, though the underlying pattern is portable).

#### `nudge-calibration-drift.sh`

**Trigger**: SessionStart, throttled to at most one nudge per UTC day.

**Behavior**: Counts unmerged `calibration:*` `bd` memories (drift entries that subagents emit for human review via `/calibrate`) and nudges if any exist, grouped by agent. It only counts entries `/calibrate` can actually harvest: segment 2 of the key must name a real agent (`~/.claude/agents/<seg2>.md` exists); legacy keys with no matching agent are counted separately and flagged for manual triage so the nudge is always actionable. A single `bd` call with a 10s timeout; any failure exits 0 silently (fail open).

**Why subtle**: It closes the calibration loop's trigger gap. Producers write `calibration:*` memories and `/calibrate` is the human review gate, but without a structural session-start trigger the channel is write-only and entries accumulate unreviewed. The actionable-vs-legacy split matters because nudging about keys `/calibrate` cannot harvest would train the user to ignore the nudge.

**Portable**: no (depends on the `bd` tracker and the `/calibrate` agent-keyed channel).

#### `session-start-pr-sync.sh`

**Trigger**: SessionStart.

**Behavior**: BFS-first PR-state freshness sync. It scans open `bd` beads for PR references (`#NNNN`, filtered to >= 1000 to skip section-header noise), queries `gh pr view` for minimal fields only (`state`, `mergedAt`) in parallel, compares against a cache, and surfaces only the drift (e.g. `OPEN -> MERGED`) as `additionalContext`. It does NOT fetch PR bodies, comments, or files; the agent uses the BFS summary to decide whether to DFS into a specific PR. Cache amortization: if the cache was refreshed in the last 30 minutes it skips the `gh` sync and surfaces cached state, keeping cost low when sessions cold-start in quick succession. Advisory; never blocks.

**Why subtle**: It is deliberately BFS-only (entity-level state, no payloads) to keep session-start cheap: fetching comments per bead would multiply latency by bead count. The >= 1000 PR-number filter avoids treating `#1`/`#2` section headers in bead descriptions as PRs. Pairs with the consumer-side `/recall` workflow: this hook surfaces what drifted, the agent decides what to inspect.

**Portable**: no (depends on the `bd` tracker, `gh`, and the bead-references-PR convention), but the BFS-then-DFS shape (cheap state diff at session start, drill in on demand) ports.

### Shared library

#### `lib/log-event.sh`

Source-able shell helper that other hooks use for structured logging. Each hook calls `hook_instrument "$(basename "$0")"` at start to log invocation to a central audit file.

**Portable**: yes, see `examples/lib/log-event.sh`. The pattern (instrument every hook) is independent of the specific logger implementation.

## Why the description-first format

A repo that ships only runnable shell would tell adopters "here is what to run" without "here is why this hook exists." The hook's value is in the why: what failure mode does it catch, what corrective behavior does it replace, when does it matter. The runnable shell is the implementation; the description is the portable harness component.

Adopters who want to use a hook copy the shell from `examples/` and adapt to their project's specifics. Adopters who want to understand the harness read the descriptions and build equivalents in whatever tool they prefer.
