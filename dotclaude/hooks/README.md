# Hooks

Claude Code hooks that fire on tool-use events to enforce discipline that cannot live in prompt text alone. The structural enforcement layer the harness depends on; the catalog below is the description-first index.

Some hooks are portable verbatim (the runnable `.sh` is in `examples/`). Others are personal-tier or harness-specific and only the description appears here. The split is documented per hook below.

## Why hooks (vs. prompts alone)

Prompt rules degrade. A rule in CLAUDE.md saying "no em-dashes" gets remembered when the model deliberately scans for it and slipped past when the model is generating freely. A hook that scans tool inputs and outputs catches the slip independent of model attention. The combination (prompt rule + hook) is strictly stronger than the prompt alone.

The discipline: when a correction recurs past umbrella-memory plus prompt-rule enforcement, the next move is mechanical (a hook, linter, or validator), NOT procedural (more memories, more rule sharpening).

## The catalog

### Style enforcement (portable)

#### `block-em-dash.sh`

**Trigger**: PostToolUse on Edit/Write (scans the file after write), PreToolUse on Bash + MCP atlassian/github writers (scans the body before posting).

**Behavior**: Detects the em-dash character (U+2014) and exits 2 with a directive message: replace with hyphen, comma, or parenthesis. The hook is the structural backstop for the "no em-dashes" writing-style rule.

**Why subtle**: The model's default prose heavily uses em-dashes. Catching them in tool inputs alone is not enough because the model also uses em-dashes in chat output. The companion `stop-validate-emdash.sh` (Stop hook) catches the chat-output case.

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

#### `memory-log-sync.py` / `memory-log-sync.sh`

**Trigger**: Periodic (cron or session-start).

**Behavior**: Syncs in-memory state of the memory store back to disk to survive session boundaries.

**Portable**: no (depends on the memory store's sync semantics).

### Session lifecycle (CC-specific)

#### `check-cc-version-drift.sh`

**Trigger**: SessionStart.

**Behavior**: Compares the running Claude Code version to the last snapshot stored in `scratch/system-prompt-snapshots/`. If different, nudges to run the `/snapshot-system-prompt` skill to capture the new version's defaults.

**Portable**: no (CC-specific).

#### `preserve-session-title.sh`

**Trigger**: SessionStart.

**Behavior**: Preserves the user-set session title across compaction boundaries so context recovery is faster.

**Portable**: no (CC-specific).

#### `refine-prompt.sh`

**Trigger**: UserPromptSubmit.

**Behavior**: Injects a hint into terse user prompts ("the user thinks faster than they type; check conversation history before asking clarifying questions"). Implements the prompt-interpretation discipline as a hook so it fires at every prompt boundary, not just when the model remembers to apply it.

**Portable**: no (CC-specific UserPromptSubmit primitive, though the underlying pattern is portable).

### Shared library

#### `lib/log-event.sh`

Source-able shell helper that other hooks use for structured logging. Each hook calls `hook_instrument "$(basename "$0")"` at start to log invocation to a central audit file.

**Portable**: yes, see `examples/lib/log-event.sh`. The pattern (instrument every hook) is independent of the specific logger implementation.

## Why the description-first format

A repo that ships only runnable shell would tell adopters "here is what to run" without "here is why this hook exists." The hook's value is in the why: what failure mode does it catch, what corrective behavior does it replace, when does it matter. The runnable shell is the implementation; the description is the portable harness component.

Adopters who want to use a hook copy the shell from `examples/` and adapt to their project's specifics. Adopters who want to understand the harness read the descriptions and build equivalents in whatever tool they prefer.
