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

#### `userpromptsubmit-voice-wedge.sh`

**Trigger**: UserPromptSubmit, unmatched (fires on every prompt), unless the prompt contains the opt-out token `no-voice-check`.

**Behavior**: Emits a four-line `<voice-check>` block on stdout, which UserPromptSubmit injects into the assistant's context at the top of the turn: no em-dash (U+2014) in chat output (use a colon, comma, parentheses, or a sentence break), open with the answer, cut preamble and hedging, and match depth to the ask rather than length to the input. Nothing else: no state, no scanning, no branching. Always exit 0, never blocks.

**Why subtle**: This is the PREVENTIVE half of a style-enforcement pair whose other half is purely reactive. `block-em-dash.sh` rewrites tool inputs and `stop-validate-emdash.sh` block-and-retries chat output, so the user never sees a slip, but every catch costs a retry round-trip; the baseline at ship time was 787 chat slips since 2026-06-03, roughly 17/day and flat. The rules already live in CLAUDE.md, but CLAUDE.md is read once at session start and then sits far up-context, so the model's default token priors (em-dash connectors, throat-clearing, hedging) reassert themselves on long sessions. Recency is the active ingredient: a strong prior bends to a fresh instruction, not a buried one. Two design constraints keep it from becoming banner-blindness: scope is deliberately limited to the two recurring mechanical failures instead of restating the whole style guide, and the depth-not-length clause exists so the wedge never argues the model into over-compressing a thorough answer (which would fight the match-output-to-intent rule). Effect is measured with no new telemetry, by diffing `stop-validate-emdash.sh` block counts per day in the shared hook log before and after ship.

**Portable**: yes: the entire hook is a static heredoc plus one opt-out token, with no project, tracker, or path dependency (no runnable copy in `examples/` yet).

#### `stop-validate-slack-draft.sh`

**Trigger**: Stop event, reading the final assistant text block from the transcript.

**Behavior**: Scans the current turn's assistant chat output for a Slack/DM draft and checks it against the three rules a regex can judge without reading intent: a comma-run list of targets where a numbered list belongs, a volunteered-offer closer ("Happy to open the PR myself"), and a thread reply to a specific person with no lead @-mention. A hit blocks (exit 2) with the violated rule quoted so the assistant re-emits; a loop guard on `stop_hook_active` prevents an infinite retry, and the literal opt-out token `no-slack-check` anywhere in the turn suppresses the check.

**Why subtle**: It is the output-side backstop to a companion UserPromptSubmit hook that injects the same checklist, but only when the user's own prompt signals an upcoming draft. A prompt that merely asks to read a thread carries no such signal, so a draft the assistant volunteers unprompted slips past the input-side hook entirely; this hook is the only thing that still sees it, because it reads the turn's actual output rather than the prompt that preceded it. Scope is deliberately narrow: everything on the full checklist that needs judgment (register, hedging, audience tier, recipient-cost framing) stays the assistant's job, and only the three mechanically-checkable rules are enforced here.

**Portable**: shape-only. The specific checklist rules are this author's Slack conventions; the input-side-producer-plus-output-side-validator pairing for a chat-drafted artifact ports generally.

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

#### `guard-shared-config-writes.sh`

**Trigger**: PreToolUse on Bash AND on Edit/Write/MultiEdit (wired into both matcher groups).

**Behavior**: Blocks a write to a shared personal-tier config surface (`~/.claude/settings.json`, `settings.local.json`, `CLAUDE.md`, `hooks/*.sh`, `agents/*.md`, `skills/**/*.md`, `commands/*.md`, and memory topic files) when the target's mtime is NEWER than this session's recorded touch, or when this session has never read or written the file at all. Tool-path targets come from `tool_input.file_path`; Bash targets are recovered by a Python shlex parse covering `> f`, `>> f`, glued `>f`, `tee f`, `mv`/`cp`/`install` destinations, and `sed -i` / `truncate` / `dd` file arguments, with heredoc bodies stripped first so their contents are not mistaken for write targets. Blocks at most once per (session, file); the stamp advances at check time so re-running the identical command proceeds. Fails open on any error.

**Why subtle**: The Bash half is the entire reason the hook exists. The tool-level Edit/Write case is the easy one; the shape that actually races is `jq settings.json > tmp && mv tmp settings.json`, which the harness has no read-tracking for at all, so write targets must be parsed back out of the command string. The blast radius is what justifies a block rather than an advisory: two sessions colliding on a task tracker leave a visible mess someone can reconcile, whereas a clobbered `settings.json` silently DISABLES a guardrail hook, with no error, no diff anyone reads, and nothing downstream that notices. The never-touched-this-session branch also blocking looks over-eager until you notice that from inside one session, "I never read it" and "someone else changed it" are indistinguishable states. It operationalizes an already-written habit (check mtime before touching a shared artifact) rather than inventing policy; the near-miss that prompted it was a concurrent session adding a hook to `settings.json` while this one was mid read-modify-write, and only the interleaving order saved it.

**Portable**: shape-only. The guarded path list is this author's `~/.claude` layout, but the mtime-watermark plus Bash-write-target parsing is the portable core for anyone running multiple concurrent sessions against one config tree.

#### `bd-parallel-session-guard.sh`

**Trigger**: PreToolUse on Bash, self-filtering to `bd` write commands (`bd create`, `bd remember`, `bd comment` / `bd comments add`, `bd update`).

**Behavior**: Four independent guards, each firing at most once per (session, target), each with the same escape hatch: re-run the identical command to proceed. (1) `bd create` extracts `--title`, reduces it to at most three distinctive terms (bracketed tags, stopwords, and short words dropped), runs `bd search` per term, and blocks with the candidate beads when either two terms converge on one bead or a single matched term is at least 12 characters. (2) `bd remember` calls `bd recall` on the exact key and, if it already exists, blocks while printing the current value. (3) `bd update` with a wholesale field flag (`--description` / `--notes` / `--acceptance` / `--design` / `--title`) fetches `bd show --json`, diffs it against a per-session watermark file, and blocks showing only the unseen delta. (4) Any first touch of an already-`closed` bead blocks once. `bd comment` is deliberately NOT blocked. Fails open on any query error.

**Why subtle**: Start with why the advisory sibling was insufficient: `bd-recency-surface.sh` delivers its context WITH the tool result, meaning after the write has already landed, so the agent cannot revise. On one bead that produced 43 comments carrying 12 correction/supersede markers from four sessions, including two sessions independently superseding the SAME comment minutes apart. Only a block prevents that. The scope was then corrected by measurement in BOTH directions, which is the part worth copying: append-only `bd comment` was un-blocked after a test showed two concurrent comments both retain (nothing to lose) and blocking cost five fires in twenty minutes on a hot bead, while `bd create` was added after this guard fired six times protecting comments during a session that minted a duplicate P1 entirely unguarded. Two implementation traps: every comment is authored under the same name, so the delta cannot distinguish a peer session's write from this session's own (mitigated by a self-log of the guard's own pre-write timestamps, subtracting delta entries landing within 180s of one of our own checks, after a block told the author "ANOTHER SESSION wrote" while citing a comment this same session posted 90 seconds earlier), and the create-duplicate threshold needs two converging terms or one long term because `bd search` is title-only and single generic words produced spurious blocks.

**Portable**: no. It is built on the `bd` tracker's exact command surface and its lack of any CAS token or append primitive; the per-session watermark, block-once, re-run-to-proceed shape is what ports.

#### `subagent-stop-decision-gates.sh`

**Trigger**: SubagentStop, matcher `mx2-decision-maker` (15s timeout), with a redundant internal `agent_type` check that re-verifies the same thing.

**Behavior**: Validates the decision agent's terminal verdict from the last three assistant text blocks. First it requires a well-formed token (`DECISION:` or `VERDICT:` followed by `PROCEED`, `ITERATE`, `ESCALATE`, `ESCALATE-QUESTIONS`, or `ESCALATE-ROUTE`). If the verdict is PROCEED it additionally requires a `GATES:` block containing all 12 named criteria as `- <NAME>:` lines (INTENT, CHALLENGE, CONSULT, RULES, EVIDENCE, OBSERVABILITY, BOT-LENS, SIBLING-BEADS, MECHANISM, RESOURCES, RIGHT-SIZED, INDEPENDENT), no gate marked FAIL, and a `CALIBRATION:` line. Any violation exits 2 with instructions to RESUME the agent via SendMessage for a clean re-emit rather than inferring a verdict from prose. Fires at most twice per transcript via a scratch counter with a 12-hour GC, plus the `stop_hook_active` guard; an unreadable transcript or an unrecognized agent fails open.

**Why subtle**: The internal agent-type guard is the finding worth copying. The `settings.json` SubagentStop matcher does NOT reliably filter events: 2026-07-20 telemetry showed this hook and `subagent-stop-result-contract.sh`, whose matchers are DISJOINT, block-firing as a pair seven times, including on a compaction summarizer, so any non-decision agent lacking a verdict token was being flagged. Never trust the matcher alone on this event. The contract itself exists because this agent is the quality gate that REPLACES human judgment in the autonomous pipelines, and its old PROCEED was a three-line block: a rubber-stamped PROCEED and a genuinely checked one were textually identical, so there was nothing for the orchestrator (or a later audit) to distinguish. Requiring 12 gates with one line of evidence each converts the verdict into a checkable artifact, and the FAIL reconciliation check closes the obvious loophole where the agent walks the gates honestly, records a FAIL, and still returns PROCEED. The recovery instruction says resume, not re-dispatch, because a resumed agent still has its analysis context and a cold one would re-derive the verdict from scratch.

**Portable**: shape-only: the 12-gate roster and verdict vocabulary are personal-tier, but the internal agent-type re-check (matchers on SubagentStop are advisory, not a filter) and the per-transcript fire cap are lessons any subagent-heavy harness needs.

#### `nudge-handrolled-review.sh`

**Trigger**: PreToolUse on Bash.

**Behavior**: Detects an attempt to POST review feedback on a PR (`gh pr comment <N>`, `gh pr review <N> --approve|--comment|--request-changes`, or a `gh api` write to `/pulls/<N>/comments` or `/pulls/<N>/reviews` carrying a write flag such as `--method POST`, `-f`, `--field`, `--input`) when no `/pr-intel` run is logged for that (session, PR) pair in `~/.claude/logs/pr-intel-contract-inject.jsonl`. The first such attempt exits 2 with a routing nudge (dispatch `/pr-intel <N>` if this is substantive feedback on a high-stakes PR: infra, cross-account or hardcoded endpoints, multi-PR stack, security-sensitive) and stamps a one-shot marker; re-running the identical command passes. Exempt: an explicit `--method GET`, reads of the same endpoints, subagent-originated calls (`agent_type` present), and any command with no extractable PR number. Markers GC after 24h.

**Why subtle**: The failure it catches is drift from reviewer to coordinator, and every earlier interception point is blind to it. A prompt rule saying "rigor tracks the work's stakes, not the interaction's tempo" cannot fire at the moment it is needed, because by the time the model is composing the comment it has already concluded that hand-rolled `gh` spot-checks were enough; the posting call is the last point where that routing decision is still reversible. The one-shot design is what makes exit 2 tolerable: hard-blocking every review post would make trivial thread replies unworkable, so the hook lets attempt two through and spends its entire budget on forcing one conscious re-decision. The subagent exemption matters for the same reason: a dispatched reviewer posting under explicit orchestrator instruction is the correct flow, so nudging there would fire loudest precisely when the routing was right.

**Portable**: no (depends on the author's `/pr-intel` skill and its inject log). The shape ports: detect the write to a review endpoint, check for evidence that the structured flow ran, advise once.

#### `pretooluse-pr-create-dup-check.sh`

**Trigger**: PreToolUse on Bash, acting only on commands containing `gh pr create`.

**Behavior**: Extracts every ticket ID (`MX2-NNNNN`) from the command (title or head branch) and runs `gh pr list --search <ticket> --state all --limit 10` for each. Any hit exits 2, listing the matching PR numbers, states, and titles, and instructs the caller to verify and then re-run prefixed with `DUP_CHECK_OK=1` to override. No ticket in the command, no hits, or any `jq`/`gh` failure passes (fail-open with a stderr warning). `DUP_CHECK_GH_BIN` lets tests stub the `gh` binary.

**Why subtle**: The failure is a race between the author's OWN parallel sessions, which no single session can observe. Several windows working the same fresh ticket each check their local state, each find nothing, and each build; the duplicate surfaced only after one had already merged. That is why the search is `--state all` rather than `--state open`: the dangerous precedent is the already-merged sibling, which an open-only query reports as clean, so the obvious implementation misses the exact case that motivated the hook. Fail-open is right here (a missing `gh` must not stop PR creation) but it makes the guard best-effort by design, and the escape hatch is an env-var prefix rather than a plain re-run so the override is an explicit statement instead of something a retry loop stumbles into.

**Portable**: shape-only. The ticket-ID regex and `gh` are specific; "before creating an artifact, search the tracker across ALL states for one already referencing this ticket" ports.

#### `block-raw-gh-pr-create.sh`

**Trigger**: PreToolUse on Bash, matching an actual `gh pr create` invocation (stripped of quoted prose first, so a command that merely mentions the phrase does not fire).

**Behavior**: Blocks a raw `gh pr create` and redirects to the author's `/pr` skill, which resolves the ticket id from the branch and commits, runs the language-appropriate checks, and creates as a draft by default. Two allowances keep the skill itself unaffected: the skill's own known temp-file signature for its PR-body flag, and an explicit `PR_SKILL_OK=1` prefix for any other legitimate raw call.

**Why subtle**: The rule already existed in prose (a global instruction plus a prior recorded correction) and was violated again in the same session it was supposedly internalized in, which is what moved it from a memory to a mechanism. The escape hatch is deliberately easy to use rather than easy to forget: a guard with no bypass gets disabled instead of obeyed, so the goal is to redirect the default path, not to make PR creation hard.

**Portable**: shape-only. The specific checks the skill runs are this setup's; "detect the raw form of a multi-step workflow and redirect to the skill that does the steps" ports generally.

#### `block-state-plus-blockable.sh`

**Trigger**: PreToolUse on Bash.

**Behavior**: Blocks a single command that both creates state (a heredoc, an output redirect, or `mkdir`) and also runs something a sibling hook might block (`bd`, `gh`, `curl`, `terraform`, `pants`). Advises splitting the state-creating step into its own call.

**Why subtle**: A PreToolUse block kills the WHOLE invocation, not just the half that tripped it, so if the blockable half fires, the state-creating half never ran. The sanctioned re-run then executes against state that silently does not exist, and can succeed while producing a corrupted result (a tracker item minted from an empty file) rather than failing loudly. The risk is invisible until measured: it looks like ordinary command-chaining, and only surfaces at the exact moment another guardrail's block turns a compound command into a partial one.

**Portable**: yes: the shape (never bundle a state-creating step with anything a sibling hook might block) generalizes to any hook ecosystem where a PreToolUse block is all-or-nothing on the invocation.

#### `nudge-state-summary-dispatch.sh`

**Trigger**: PreToolUse on Agent and Workflow, main-loop dispatches only (subagent-originated calls are exempt, since subagents cannot fork and so are not the orchestration surface this guards).

**Behavior**: Fires when a dispatch prompt asks an agent to describe the CURRENT STATE of a tracked item without instructing it to read the comment history. Three conditions must all hold: a state-intent phrase, a tracked-item reference, and the absence of a read-the-comments guard. Advisory one-shot per session: it exits 2 with the missing prompt clause, stamps a marker, and passes on an identical re-run. Markers age out after 24 hours.

**Why subtle**: An agent asked for the current state of an item reads the description and skips the comments, every time, unless told otherwise. A description records the state at the moment it was written; the comments carry what happened since. A 26-item handoff sweep produced five wrong state paragraphs on that default, all understating progress, the worst of them telling an inheritor that no fix existed on an item whose fix had merged six days earlier and was recorded in four comments directly above it. It was caught by luck, not by design. The reason this is a hook and not a memory is the compounding failure underneath it: the dispatching session had hit the identical trap itself hours earlier, written it up, and then shipped the sweep that repeated it 26 times. A retrieval-tier memory only helps if something recalls it, so this fires at the dispatch instead.

**Portable**: shape yes, implementation nearly. The tracked-item regex is local; the state-intent and guard-phrase matching are not. The clause it injects is documented as clause 1 of `../../dispatch/dispatch-prompt-contract.md`.

#### `nudge-handrolled-ci-poll.sh`

**Trigger**: PreToolUse on Bash, when a CI poll loop over the check rollup is being hand-rolled instead of calling the SHA-pinned gate script that already exists. Advisory, exits 0 always, once per session.

**Behavior**: Prints the three projection bugs a hand-rolled loop hits, plus the path to the script that handles them, and gets out of the way. It never blocks, because a genuinely custom condition is a legitimate reason to write the loop.

**Why subtle**: The three bugs are all real and all silent. An in-progress check returns an empty-string conclusion rather than null, so the usual null-coalescing fallback never fires and the loop exits on its first poll treating running checks as settled (this produced a false "CI is done" read). A superseded run stays in the rollup as cancelled next to the real result, so a naive not-equal-to-success filter reports phantom failures. Bare commit statuses have a different shape from check runs and project as nulls. The placement is the point: the rule was already written in a memory file and a session-start hook already surfaced that file, and both fired on the day two loops were hand-rolled anyway. A nudge delivered hundreds of turns before the decision is not an enforcement layer for that decision.

**Portable**: shape yes. The specific projection bugs are properties of the platform's check-rollup API and would transfer to any consumer of it; the script path is local.

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

#### `ask-destructive-dispatch.sh`

**Trigger**: PreToolUse on the subagent-dispatch tools (matcher `Agent|Task`), reading `tool_input.prompt`.

**Behavior**: Greps the dispatch prompt for destructive git verbs (`force-push`, `--force` / `--force-with-lease`, `push -f`, `reset --hard`, `branch -D`, `push --delete`). A negation guard drops lines where the verb is preceded by `do not` / `don't` / `never` / `no` on the same line, so a prohibition ("do not force-push") passes silently. Any surviving match emits `permissionDecision: "ask"` quoting the matched line (first 160 chars) alongside the pre-dispatch self-check: did the USER authorize this destructive op in their message THIS round?

**Why subtle**: The rule being enforced is not mechanically checkable, and the hook is honest about that. It cannot see the user's message, so it cannot decide whether the verb was authorized; it converts an unanswerable check into the one question a human can answer in one keystroke. The failure mode is authorization drift across rounds: "address these comments" does not carry a prior round's force-push permission forward, and that exact slip recurred six times inside one PR's iteration rounds. The `ask` decision only works on this surface: `permissionDecision: "ask"` is a silent no-op for subagent-originated calls (they auto-accept with no prompt, which is why `block-guardrail-hook-edit.sh` must hard-DENY on its subagent branch), but `Agent`/`Task` dispatches always originate in the main loop and subagents cannot nest them, so the prompt reliably renders here.

**Portable**: shape-only. The verb list ports verbatim; the dispatch-tool matcher and the `ask` permission decision are Claude Code primitives.

#### `block-worktree-branch-in-main.sh`

**Trigger**: PreToolUse on Bash.

**Behavior**: Blocks `git switch -c|--create` and `git checkout -b` when the effective git directory is the main checkout (`/workspaces/main`) or any subdirectory of it. The effective directory is resolved from an explicit `git -C <path>`, else a leading `cd <path> &&`, else the payload `cwd`; a relative target resolves against the payload cwd (where the command actually runs), not the hook process's own cwd. Paths under `.launch-worktrees/` and `.claude/worktrees/` are exempt. Fails open with a loud stderr warning if `jq` is missing.

**Why subtle**: Two parsing decisions carry the whole hook. The verb match runs on a QUOTE-STRIPPED view of the command (newlines flattened, then single- and double-quoted substrings deleted), so a branch-create verb fires only when it sits outside quotes; without that, a tracker write whose description quotes `git switch -c` as prose would block. And matching subdirectories is not defensive padding: `git switch -c` run from a subdirectory switches the ENTIRE checkout's branch, so a root-only match would miss most real invocations. The harm it prevents is not a lost commit but a hijacked workspace: the main checkout is the user's live window, and a branch create silently moves them off whatever they were on. Residuals are documented instead of papered over (a branch-create nested wholly inside quotes such as `bash -c "git switch -c"`, and non-leading or quoted `cd` paths, fall through to the payload cwd; tracked in docr-ufbkq).

**Portable**: shape-only. The checkout path and worktree conventions are local, but the quote-stripped second view and the effective-directory resolution ladder are the transferable parts.

#### `block-pkill-dolt-server.sh`

**Trigger**: PreToolUse on Bash, matching a `pkill`/`killall` invocation naming the tracker's SQL server process at a command position (not merely quoted in prose).

**Behavior**: Blocks a direct kill of the process backing the beads tracker and redirects to the tracker's own lifecycle subcommands (stop, start, killall, status), which keep its PID bookkeeping consistent.

**Why subtle**: Killing the process out from under the tracker leaves its bookkeeping file empty and latches an internal circuit breaker open, which then short-circuits AHEAD of the tracker's own auto-start path, so the normal recovery setting does not save you. With many concurrent sessions sharing one store, every window's tracker commands fail until a human manually restarts the server, so the blast radius of one bad kill command is the whole fleet, not just the caller. The underlying `pkill` is separately blocked by the platform's own destructive-command classifier, so this hook's real job is turning an opaque permission denial into an actionable redirect to the correct subcommand.

**Portable**: shape-only. The specific process and subcommands are this tracker's; "a shared backing process has its own lifecycle commands, so block a direct kill and redirect to them" ports to any tool with the same shape.

#### `block-stale-force-push.sh`

**Trigger**: PreToolUse on Bash, matching a `git push` invocation carrying a force flag.

**Behavior**: Blocks a force-push whose HEAD commit did not exist yet when the user last authorized a force-push in that conversation. Resolves the current branch's HEAD commit time from git and the most recent human turn that named the force-push verb (within a length ceiling that excludes long pasted text merely discussing the topic, and excluding turns with an explicit negation) from the session transcript; if HEAD was committed after that authorization, the push is stale and blocks. A confirmed non-destructive case (the remote tip is still an ancestor of HEAD, meaning nothing would be lost) passes regardless. The block clears only when the user names the verb again in a new human turn, which necessarily postdates the current HEAD.

**Why subtle**: The rule it enforces ("authorization is per-round, not standing") was already written down and was violated anyway: a user approved a force-push for one commit, the agent amended to a different commit, and force-pushed the new one under the old approval while an external reviewer was still reading the original SHA. The gate is intentionally self-clearing through a channel an agent cannot forge, since it compares commit timestamps rather than checking for a marker file or environment variable an agent could set on its own. It is scoped narrowly to STALE authorization (an approval that predates the current commit), never to ABSENT authorization, because measurement showed the common "rebase and update the PR" flow has no verb-naming human turn at all, and gating that case would cost a false block roughly once a day.

**Portable**: shape-only. The transcript-parsing details are specific to this harness; "compare the mutation's timestamp against the authorizing human turn's timestamp, not just its presence" generalizes to any per-round destructive-op authorization.

#### `block-mcp-shell-substitution.sh`

**Trigger**: PreToolUse on MCP write tools only (wiki page updates, tracker writes, chat sends).

**Behavior**: Blocks any top-level string argument whose entire trimmed value is a single-line shell substitution expression (`$( ... )` or a backtick command). Content that merely contains a substitution is allowed, and so is any multiline body, even one that opens with `$(`. The discriminator is substitution intent: one line, one expression, nothing else. Fails open with a loud warning when `jq` is missing.

**Why subtle**: MCP arguments are JSON, not shell, so `$(cat FILE)` is never expanded; it ships as a literal string. The failure is silent and destructive rather than noisy: a page-update call whose body argument was a `$(cat ...)` expression published that literal string as the entire page body, wiping a runbook until another session restored it from the staged file. Nothing errors, the tool returns success, and the damage is only visible to a human looking at the rendered page. The known accepted false positive is a chat message that is exactly one inline code span; the fix is to add a word outside the backticks.

**Portable**: yes in shape, and nearly so in implementation: the check is on argument shape, not on which MCP server is being called. The tool-name list is the only local part.

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

#### `block-jira-transition.sh`

**Trigger**: PreToolUse matched on `mcp__atlassian__transitionJiraIssue`.

**Behavior**: Splits Jira transitions into agent-owned and human-owned. Non-terminal transition ids (ToDo, In Progress, Awaiting Sign Off, Blocked) are allowed; ids on the terminal list (Completed, No longer required) are denied with no override path, because the human verifies the work before anything reaches a done-class status. Any id outside the embedded map denies fail-closed, with instructions to resolve the target via `getTransitionsForJiraIssue`, confirm `statusCategory.key != "done"`, and add the id to the allowlist. It began as a blanket deny on all transitions and was later loosened to this split.

**Why subtle**: The MCP tool payload carries only an opaque numeric `transition.id`, no status name and no category, so a hook that wants "allow non-terminal, deny terminal" has no semantic field to branch on and must carry a workflow map resolved out-of-band. That map is fragile in exactly one named way: the observed transitions were all `isGlobal=true` (one shared workflow), so id reuse is safe today, but a second non-global workflow reusing an allowlisted id for a terminal transition would slip through. Fail-closed on unknown ids is what bounds that fragility instead of pretending it away. The extension path is the neat part: adding an id means editing this file, which is itself a gated guardrail surface, so map growth inherits a human confirm for free rather than needing its own approval mechanism.

**Portable**: no. The transition ids and the terminal-state policy are specific to this Jira workflow and this MCP tool; the fail-closed-on-unmapped-opaque-id shape is the portable idea.

#### `nudge-pr-jira-link.sh`

**Trigger**: PostToolUse on Bash.

**Behavior**: Classifies the just-run command as a PR PUBLISH event (`gh pr ready`, `gh pr create` WITHOUT `--draft`, or `gt submit`/`gt ss` without `--draft`) and, when it is, prints a three-step follow-up to stdout: identify the ticket (from the PR title, the body's `Jira issue link:` line, or the branch name), post a ready-for-review comment carrying the PR URL to that ticket, or state explicitly that the link already exists or that the PR has no ticket. Draft creations deliberately do not fire; the nudge lands later, when the draft flips ready. Advisory: always exits 0, and fails open if `jq` is unavailable.

**Why subtle**: PostToolUse stdout is injected into model context, which is the only reason an advisory works here; the same text on stderr would be user-facing UI and the model would never act on it. The draft carve-out is the non-obvious half: firing on `gh pr create --draft` would train the model to post a "ready for review" ticket comment on work that is not ready, so the trigger is bound to the publish TRANSITION rather than to PR existence. And it is a Post hook rather than a Pre hook because the artifact the follow-up needs (the PR URL) does not exist until the publish command has succeeded.

**Portable**: shape-only. The publish-command set and the ticket-comment convention are this setup's; "detect the publish transition and inject the step that is chronically forgotten after it" ports to any tracker.

#### `project-oversized-jira-search.sh`

**Trigger**: PostToolUse on `mcp__atlassian__searchJiraIssuesUsingJql`.

**Behavior**: Inspects the tool response for the harness's oversized-result redirect (`Error: result (N characters) exceeds maximum allowed tokens... saved to <path>`), regex-extracts the saved-file path out of that prose message, reads the file itself, and emits a compact key / status / assignee / summary projection of every returned issue back to the model via `hookSpecificOutput.additionalContext`. Inline (non-oversized) results pass through untouched, since the model already has them. Any uncertainty (no path, missing file, unexpected JSON shape, `jq` failure) no-ops and leaves the harness redirect in place.

**Why subtle**: Without it, a search that returns too much hands the model an error string instead of data, and the model's next move is to `jq` the saved file by hand, usually across several attempts because the payload shape is unfamiliar. Three mechanics had to be established empirically before this could work at all: the PostToolUse stdin field carrying tool output is `.tool_response` and it is a STRING (not `.tool_result`, not an object); the saved-file path exists only inside that prose message, with no structured field to read it from; and `additionalContext` reaches the model while `systemMessage` does not, so getting that last one wrong yields a hook that runs cleanly and changes nothing. The scoping to SEARCH only is equally deliberate: applying the same compaction to a single-issue fetch would strip exactly the body the caller wanted.

**Portable**: no (specific to the Atlassian MCP response shapes and this harness's oversized-result redirect). The shape (intercept a truncated tool result, read the spilled file, re-inject a compact projection) ports to any MCP tool with the same overflow behavior.

#### `block-unattributed-review-comment.sh`

**Trigger**: PreToolUse on Bash, cheap-prefiltered to `gh api` commands whose URL contains `/pulls/`.

**Behavior**: Extracts the payload (from `--input <file>`, a stdin heredoc, or `-f body=@file`) and hands it to a Python checker that applies two rules to the endpoints carrying authored findings: `POST .../pulls/N/reviews` (each `comments[].body`), `POST .../pulls/N/comments`, and `PATCH .../pulls/comments/ID`. Rule one: no posted body may @-tag a person, since GitHub notifies every handle; only `@claude` (the review-loop trigger) is allowed. Rule two: every INLINE comment must OPEN with an explicit tooling-attribution lede, because every finding came from a specialist pass rather than the author's unaided reading. The review SUMMARY body is exempt (reviewer voice is allowed there), as are reactions and replies. Any finding exits 2.

**Why subtle**: The attribution check anchors at the START of the body, after stripping leading markdown and up to two severity qualifiers ("Minor, ", "Nit: "), because the naive implementation (does this body mention a tool anywhere?) passes text that is still squarely in the author's own voice. The checker goes further and distinguishes a bot name used as the SUBJECT with an attribution verb ("Copilot flagged ...") from the same name as a possessive object ("Your decline of Copilot's suggestion ..."), which is exactly the false negative a keyword match produces. The other deliberate choice is what it declines to do: payloads it cannot parse are NOT blocked, because the documented posting path uses `--input <file>` and hard-blocking every unparseable inline string would convert a voice guard into a workflow blocker. This is the structural backstop for a rule that a pre-output checklist kept failing to hold.

**Portable**: shape-only. The @-mention guard ports verbatim; the attribution-lede opener list encodes this author's specific review-voice convention.

#### `block-unattributed-review-comment-file.sh`

**Trigger**: PostToolUse on Edit/Write, self-filtering to `.json` files that exist on disk.

**Behavior**: The backup capture point for its PreToolUse(Bash) sibling. It runs the same checker in `--payload-file` mode against any written JSON file whose shape looks like a review payload, then flags at write time with a note to fix the file before posting (exit 2). The shape gate is conservative by design: only payloads with an `event` review enum, a `comments[]` array of `{path/line, body}` objects, or a single `{"body": ...}` blob whose filename hints at a review payload are checked at all.

**Why subtle**: The Bash sibling only ever sees a direct `gh api` command string. A payload written to a file and then posted through a path the Bash hook cannot inspect (a Python subprocess shelling out to `gh ... --input <file>`, for instance) bypasses it completely, so the rule needs a second capture point at the surface where the content is AUTHORED rather than where it is transmitted. That is the transferable idea: for any content rule, ask whether the write path and the send path are the same surface, and if not, hook both. The conservative payload-shape gate is what makes the second point affordable, since a broad "any JSON with a body field" match would fire on unrelated writes and train the author to ignore it. The residual is stated rather than hidden: a payload both built and posted entirely inside one subprocess is seen by neither hook, which is why the convention is to author review payloads with the Write tool.

**Portable**: shape-only. The two-capture-point pattern ports; the review-payload heuristics and the attribution rules are this author's.

#### `block-bare-monitor-id-alert-query.sh`

**Trigger**: PreToolUse on the Datadog events/aggregation query tools, reading `tool_input.query`.

**Behavior**: Blocks a Datadog event query that pairs a bare `monitor_id:` tag filter with `source:alert`. That combination is provably always zero rows, because monitor ALERT events carry the monitor id only as an ATTRIBUTE (`@monitor_id:`), never as a searchable TAG; only monitor AUDIT events (created/modified) carry it as a tag. A bare `monitor_id:` without `source:alert` is the correct form for reading audit history and gets an advisory note instead of a block.

**Why subtle**: A query that always returns zero rows for a structural reason, rather than because the monitor is actually quiet, is a false clean: it reads as "nothing fired" when the real answer is "the query cannot see this event class at all." The underlying gotcha was already written down in a memory file and did not prevent a real investigation from reaching a wrong conclusion off the bare-tag form, which is why this became a mechanical gate rather than another memory. Every other memory-surfacing guard in this catalog matches on Bash or a skill invocation, so an MCP tool call carrying the same risky query shape was previously invisible to all of them; this hook closes that one gap at the point of use.

**Portable**: shape-only. The specific Datadog tag-vs-attribute distinction is this author's; "a filter combination that is provably always empty for a structural reason, not a data reason, deserves a block rather than a silent zero" generalizes to any query surface with the same trap.

#### `block-bead-id-in-repo-file.sh`

**Trigger**: PreToolUse on Edit/Write, scoped to files under the shared team repo checkout.

**Behavior**: Blocks an Edit or Write whose new content introduces a bead ID (the author's personal task-tracker identifier) into a committed repo file. The pattern is deliberately tight so real infrastructure identifiers that merely share the prefix do not false-positive. Removing a bead ID (the cleanup direction) is never blocked, only introducing one.

**Why subtle**: A sibling hook already scans stakeholder-facing writes (Jira, Confluence, GitHub) for personal-tier vocabulary, but it models "stakeholder-facing" as those specific write calls and never sees an Edit into a source file. A bead ID landing in a committed repo file is more durable and more teammate-visible than a Jira comment (it survives in git history and is visible to every future reader of that file), so it belongs under the same audience-tier discipline even though the write mechanism is completely different. A real prior incident showed the class recurs and persists once it lands, since a repo file has no equivalent of a Jira comment's "just don't read the thread" escape.

**Portable**: shape-only. The bead-ID pattern is this author's tracker; "a personal-tier identifier belongs behind an audience-tier filter regardless of which write mechanism introduces it" generalizes to any personal/shared split.

#### `block-gh-api-raw-field-atfile.sh`

**Trigger**: PreToolUse on Bash, matching a `gh api` invocation.

**Behavior**: Blocks `gh api ... -f`/`--raw-field key=@file` invocations. `gh`'s raw-field flag treats its value as a literal string, so `@filename` is never expanded to the file's contents; the field silently becomes the short literal path text itself, with no error. Points to the typed `-F`/`--field` flag, which does read from file, as the fix.

**Why subtle**: The failure produces a technically-successful API call with a payload that is quietly wrong (a PR body collapsing to a twenty-character path string instead of its intended content), and nothing in the response signals that anything went awry. The distinction between the two nearly-identical flags was already documented in a memory file before this hook existed and still got hit, which is the same escalation pattern behind several of this catalog's mechanical gates: a documented gotcha that keeps recurring becomes a hook rather than another memory entry.

**Portable**: yes. The `-f`/`-F` distinction is a `gh` CLI behavior, not specific to this author's setup; the pattern generalizes to any CLI with a similarly-named pair of literal-vs-file-reading flags.

#### `block-hard-wrapped-pr-body.sh`

**Trigger**: PreToolUse on Bash, on the commands that publish a PR body, PR comment, or review body, resolving the body file the command reads from disk rather than enumerating flags.

**Behavior**: Blocks a body that has been hard-wrapped to a column width. One paragraph must be one unwrapped line, however long it runs. Fails open on any internal error.

**Why subtle**: GitHub and the tracker both render a single literal newline as a visible line break, so a body reflowed to 80 or 100 columns arrives as a ragged wall of short lines with mid-sentence breaks, and the author gets asked to redo it. The interesting part is the enforcement history: the rule was already written in six memory files and four skill files, and one earlier recurrence had been declared resolved by adding prose to a skill. It shipped hard-wrapped again anyway. This hook is the ladder's next rung after prose failed twice, which is exactly the escalation the reflection-trigger convergence rule prescribes.

**Portable**: shape yes, implementation mostly. The rendering behavior it guards is a property of GitHub and the tracker, not of this setup; the body-file resolution is shared with the personal-tier vocabulary guard and would need porting alongside it.

#### `block-bad-require-reviewers.sh`

**Trigger**: PreToolUse on Bash, narrowed to PR-body writes only (never comment or review posts, whose bodies legitimately carry no directive). Same surface and body resolution as the hard-wrap guard; the two are kept in sync.

**Behavior**: Blocks a PR body whose reviewer-requirement directive cannot be satisfied on this repo, including the case where the directive is absent and the checker therefore defaults to requiring everyone.

**Why subtle**: This is the clearest case in the catalog of a hook existing because two artifacts disagree. The rule is written in a memory file with its mechanism explained on the next line, and the project-tier PR command says the opposite in two places. Prose lost three times in one week against a command file that authors the body. The underlying mechanic is unforgiving: the repo's reviewer checker expands a requested team to every member and drops nobody for authorship, and the platform forbids self-approval, so requiring all of a team that contains the author can never pass. An absent directive parses as "require all, reviewers empty" and waits on every still-requested reviewer. Both shapes leave a red check the author has to notice, diagnose, and re-push. The hook is explicitly a holding layer until the project-tier default is flipped by PR.

**Portable**: no. It encodes one repo's reviewer-checker semantics. The transferable idea is narrower and worth naming: when a generated artifact keeps coming out wrong, check whether the generator disagrees with the rule before writing more prose at the rule.

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

#### `post-edit-log-safety.sh`

**Trigger**: PostToolUse on Edit/Write.

**Behavior**: On a `.py` file inside the project checkout (`/workspaces/main/...`), it computes the lines this branch ADDED (`git diff --unified=0` against `merge-base origin/main HEAD`, parsing `@@` hunk headers into a line list) and runs `lib/log_safety_scan.py` scoped to exactly those lines. The scanner is an AST pass flagging two shapes: a log/logger/exception sink whose arguments reference a content-bearing name (`reason`, `payload`, `.body`, `page_text`, `.stdout`/`.stderr`, `response.text|json|content`, `document_text`, and similar), and a dict literal assembling an error/response record that is almost certainly about to be logged. Findings print to stderr with a "classify each as SAFE (id/status/count) vs PII/document content, fix only what YOUR edit added" instruction and exit 2 (advisory: PostToolUse cannot block and the edit has already landed). A clean scan exits 0; if the diff base cannot be computed it falls back to a whole-file scan and labels the output as possibly pre-existing.

**Why subtle**: The diff scoping is the difference between a usable hook and noise. Logging is ubiquitous in a mature service, so a whole-file scan on every edit buries the one new leak under dozens of pre-existing calls and gets ignored inside a week; scoping to added lines makes every hit actionable and lets the message say so explicitly. The hook exists because the security lens is a review-time AGENT and reviews are conditional, whereas a build that writes content-bearing logging ships the leak before any reviewer runs. It is also deliberately name-heuristic and model-free: a false positive costs a two-second "is this scrubbed?" glance, so the floor holds identically no matter which model or agent tier authored the edit.

**Portable**: shape-only. The scanner's field-name list encodes this domain's PII and document-content vocabulary, but "AST-scan only the added lines for content-bearing values reaching log sinks" ports.

#### `post-edit-tf-antipattern.sh`

**Trigger**: PostToolUse on Edit/Write.

**Behavior**: On a `.tf` file under the project's service-Terraform tree (`/workspaces/main/app/...`), greps for three specific failure shapes and reports them with line numbers on stderr, exit 2 (advisory; the edit already landed). (1) A list-coercing function over a collection: `distinct|tolist|toset|sort|reverse(values(...))`. (2) A ternary that unifies a list literal with a `values(...)` branch. (3) A Datadog monitor query whose METRIC NAME (everything before the `{`) contains a hyphen. Comment lines are filtered out of every match, each finding carries its explanation and its fix, and scratch files live in a per-invocation `mktemp -d` whose trap chains cleanup into the instrumentation logger.

**Why subtle**: All three are silent at edit time and expensive later, in different ways. The list coercions look fine locally and only fail at plan/apply with "element types must all match for conversion to list", and only when the collection is heterogeneous (a remote-state output emitting null-typed members while its siblings are typed), so they pass every local check and break the deploy. The Datadog one never errors at all: the metrics provider normalizes service hyphens to underscores on ingestion, so a hyphenated metric name matches nothing and the monitor is SILENTLY BLIND, alerting on nothing indefinitely. That is the class a hook is uniquely good at, because the only deterministic backstop is a real plan run, which nobody does per-edit. The per-invocation `mktemp -d` instead of a fixed `/tmp` path is deliberate: fixed paths cross-contaminate concurrent sessions.

**Portable**: shape-only. The three patterns are HCL-plus-Datadog-specific; the shape (grep the edited IaC file for coercion and naming traps that only fail at apply time) ports.

#### `lint-memory.py`

**Trigger**: PostToolUse on Edit/Write (15s timeout), self-filtering to the memory index `MEMORY.md` and the sub-index READMEs under `initiatives/`, `1on1s/`, `meetings/`, `dms/`, and `<service>/`. Also runs standalone as `lint-memory.py --report [PATH]`.

**Behavior**: Checks the edited index for file size against the truncation limit (ERROR at 24400 bytes or more, WARN at 22000), per-entry line length (ERROR over 200 chars, WARN over 150), stable clusters (three or more `Initiative:` / `1:1` / standup / TL Sync rows still sitting in the flat index, which should move to a sub-index), and broken relative file links. Report mode adds the two slow checks: sub-index orphan detection and validation of every referenced bead id against `bd list --json`. ERROR findings exit 2; WARN and INFO exit 0; any internal failure prints one line and exits 0 so the lint never breaks an edit.

**Why subtle**: The size limit is a hard functional cliff, not a style preference, and every other check serves it. The index is loaded into every session, and past the truncation limit it loads only PARTIALLY, silently: an entry that scrolls past the cap is an entry the model never sees again, with no error surfaced anywhere. That is why a cosmetic-looking 200-character line limit is an ERROR rather than a nit, and why the stable-cluster nudge exists at all: entry-length caps push detail down into topic files and cluster detection pushes stable groups into sub-indexes, and those are the only two levers that keep the index under the cliff. The hook-vs-report mode split is a runtime budget decision with a real consequence: the bead-link check shells out to the tracker and is too slow to run per edit, so the hook can flag a broken FILE link immediately but will never catch a dead bead reference. One more detail worth stealing: being Python, it cannot source the shared bash logging helper, so it hand-rolls a matching JSONL row to stay visible to the hook-stats tooling.

**Portable**: no. The memory-index convention, the sub-index directory list, the specific byte limits, and the bead-id check are all this author's memory layout.

#### `lint-skill-summary-sync.sh`

**Trigger**: PostToolUse on Edit/Write, scoped to files under `~/.claude/skills/` or `~/.claude/agents/`.

**Behavior**: Enforces explicitly MARKED copy relationships between agent and skill spec files. A canonical block is wrapped `<!-- summary key: KEY -->` ... `<!-- /summary -->` in the owning file; a copy is wrapped `<!-- summary-from: SRC key: KEY -->` ... `<!-- /summary-from -->`. On any in-scope edit it rescans every `.md` in the edited file's directory, resolves each copy's SRC (absolute path as-is, `~/.claude`-relative when it contains a slash, otherwise same-directory), and compares the two texts whitespace-normalized but otherwise exactly. A missing source file, a missing key in the source, or divergent text exits 2 with a source-vs-copy excerpt and a re-copy instruction.

**Why subtle**: The scope restriction IS the design, not a limitation. Skill bodies and agent definitions restate canonical blocks (output contracts, shared protocols) constantly and the copies drift independently, but a heuristic duplicate-detector over prose is unusable here: a source-read of these files found that grep-level "this duplicates that" claims overstate real duplication by roughly 4-7x, so an unmarked-text lint would bury the author in false positives and get switched off. Requiring an explicit marker pair turns the copy relationship into a deliberate declaration, which lets the check be exact instead of fuzzy and means it can never fire on ordinary prose. Worth noting what PostToolUse can and cannot do here: the write has already landed, so exit 2 is a fix-it-now signal to the editing session rather than prevention. The value is that drift surfaces in the same turn that caused it instead of at the next reader.

**Portable**: shape-only. The marker grammar and the verbatim whitespace-normalized comparison port directly; the scoped directories are this author's config layout.

### Subagent + worktree (CC-specific)

#### `subagent-stop-pr-size.sh`

**Trigger**: SubagentStop event.

**Behavior**: When a code-writing subagent reports DONE on a large PR (more than ~1000 lines added), surface the size to the parent agent BEFORE downstream review steps. The flag is the "scope flag at implementer standup" rule mechanized.

**Portable**: yes, see `examples/subagent-stop-pr-size.sh`. Subagent dispatch primitive is CC-specific but the post-dispatch scope check is portable.

#### `worktree-create-log.sh` / `worktree-remove-log.sh`

**Trigger**: Custom hooks fired when the agent creates or removes a git worktree.

**Behavior**: Logs the worktree path, branch, and creating agent to a local audit file. Used by the `/audit-worktrees` skill to identify stale worktrees.

**Portable**: no (depends on the harness's worktree primitive).

#### `worktree-remove-log.sh`

**Trigger**: WorktreeRemove event, unmatched. Symmetrical counterpart to `worktree-create-log.sh` on WorktreeCreate.

**Behavior**: Despite the name, this hook TEARS DOWN rather than merely logs (the joint worktree entry above understates it). It resolves the worktree path from the payload, trying `worktree_path`, `worktreePath`, and `path` in turn, and if none is present derives it as `<cwd>/.launch-worktrees/<agent name>` the same way the create hook did. It reads the branch before removal, runs `git worktree remove --force`, and deletes the branch ONLY if it matches `agent/*`. It then appends a `[LAUNCH_EVENT type=WORKTREE_REMOVED ...]` note to the current in-progress launch bead. Every step is best-effort (`|| true`); it always emits a `WorktreeRemove` acknowledgement JSON and exits 0.

**Why subtle**: Two deliberate hedges. The multi-key path resolution plus the derive-from-agent-name fallback exists because schema drift between the create and remove payloads is plausible and a remove hook that silently no-ops on a renamed field leaks worktrees indefinitely, which is exactly the mess the `/audit-worktrees` skill later has to clean up. The `agent/*` prefix check is the safety floor on the one genuinely destructive line: `git branch -D` is a force delete, so it is scoped to the throwaway namespace the launcher owns and leaves anything else (a human's feature branch that happened to be checked out in that worktree) alone. Removing the worktree is `--force` and unconditional, but that is recoverable since the branch survives; deleting an unmerged non-agent branch would not be.

**Portable**: no: it depends on the harness's WorktreeCreate/WorktreeRemove primitives, the `.launch-worktrees/` layout, and the `bd` tracker for the audit note.

#### `warn-stale-checkout-read.sh`

**Trigger**: PreToolUse on Bash, scoped to source-reading commands (`grep`, `git grep`, `sed`, `cat`, `head`, `tail`, `awk`) targeting a repo source path, unless the command already pins an explicit ref.

**Behavior**: When the main checkout is behind `origin/main`, prints a one-time-per-session advisory naming how many commits behind it is and how to pin the read to a specific ref instead. Never blocks.

**Why subtle**: A stale checkout produces a confidently WRONG answer rather than an obviously missing one: a grep against the pre-merge tree "proves" a function has one consumer when the merged tree has a different answer, and nothing about the read looks unusual. The tell in both real instances was indirect (line numbers disagreeing with a traceback, a grep result contradicting something already read), which is a hard signal to build a precise detector around; the hook instead accepts a lower-precision, always-available proxy (is the checkout behind at all) and trades detection precision for coverage.

**Portable**: shape-only. The specific checkout path is this author's; "advise once per session when the working tree is behind the remote before a source-reading command runs" generalizes to any git-backed harness.

#### `warn-worktree-main-checkout-path.sh`

**Trigger**: PreToolUse on Bash, Edit, and Write, reading the payload's cwd alongside the command or file path.

**Behavior**: Warns (non-blocking) on two mirror-image drifts. Case A: the session's cwd IS a worktree, but a target path is an ABSOLUTE path pointing at the main checkout instead of the worktree's own copy. Case B: the session's cwd has itself drifted to the main checkout while sitting on its default branch, so a RELATIVE path silently resolves against main; this case is gated on the checkout being on the default branch specifically, since legitimate mechanical edits happen on a checked-out feature branch and must never be flagged.

**Why subtle**: Both roots typically share the same path prefix, so a wrong absolute path looks correct at a glance in Case A, and in Case B the drift has no visible trigger at all: a skill invocation resets the shell's working directory as a side effect, so an edit can land on the default branch and the verification command that follows it, run in the same now-drifted cwd, reports a clean pass for a branch it never touched. That silent double failure (wrong target, followed by a green check that appears to confirm the wrong target) is what makes Case B worse than Case A despite being the same underlying class of mistake.

**Portable**: shape-only. The specific worktree directory layout is this author's; the two-case drift detection (absolute path pointing at the wrong root; cwd itself drifted onto the wrong root) generalizes to any harness that runs work in an ephemeral checkout alongside a persistent one.

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

#### `mcp-stats.py`

**Trigger**: on-demand (present on disk but NOT wired in `settings.json`): `python3 ~/.claude/hooks/mcp-stats.py [--days N] [--by-tool] [--server X]`.

**Behavior**: Reads `~/.claude/logs/mcp-calls.jsonl` (the audit log written by the PreToolUse `log-mcp-calls.sh` hook on the `mcp__.*` matcher), filters events by an optional recency window and an optional server name, and prints either a per-server call-count table or a per-tool breakdown within each server. Malformed JSON lines and events whose `ts` will not parse are skipped rather than counted. A missing log file prints one note to stderr and exits 0.

**Why subtle**: It is the consumer half of a producer/consumer pair, and without it the MCP audit log is write-only: `log-mcp-calls.sh` accumulates events forever and nothing answers the question they were collected for. The `--by-tool` mode is the load-bearing one, because a server-level count hides that a single chatty tool drives an entire server's footprint, and that is the fact that decides whether to keep a server connected at all (every connected MCP server costs tool-schema tokens on every request, whether or not it is called). Dropping events with an unparseable timestamp instead of counting them keeps a windowed query honest; the naive version silently folds undated rows into whatever window you asked for.

**Portable**: shape-only. The jsonl schema (`ts` / `server` / `tool`) is this author's `log-mcp-calls.sh` format, but the aggregation runs against any harness that logs MCP invocations.

#### `stats-reminder.sh`

**Trigger**: SessionStart.

**Behavior**: Emits up to three independent staleness nudges on stdout. (1) Hook stats: if `logs/hooks.jsonl` exists and the `hooks-stats-last-run` marker is missing or 7+ days old, prompt to run `stats.py --days 7`. (2) Invocation index: if `logs/invocation-index.jsonl` is 21+ days old, prompt to re-run the transcript miner. (3) Tool registry: if `tool-registry.txt` is 30+ days old, warn that `lint-tool-roster.py` is rotting toward false-clean; if the file is MISSING, say plainly that the lint will fatal and how to reseed it. Each check is computed independently; none may return early.

**Why subtle**: The "none may exit early" constraint records a bug that actually shipped: an earlier version returned after the first nudge decision, so a freshly-run stats marker silently suppressed every later nudge and the invocation-index warning was dead for weeks with no symptom. That is the general hazard of a multi-nudge session hook, where a suppressed nudge is indistinguishable from a satisfied one. The thresholds encode real decay rather than taste: 21 days for the invocation index because transcripts retain only ~35, making a monthly miner run the last safe cadence; 30 days for the tool registry because it is a hand-refreshed snapshot with no writer, so the lint reading it gets QUIETER as it rots, and a stale registry produces a passing lint. Note the consumer-side caveat that goes with any such hook: these lines are computed once at fire time and can go stale during a long session, so they are pointers to re-verify, not current facts.

**Portable**: shape-only. The three artifacts are personal-tier; the independent-checks constraint generalizes to any hook emitting multiple nudges.

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

#### `memory-log-sync.py`

**Trigger**: SessionStart, invoked by the `memory-log-sync.sh` wrapper, which backgrounds it with `nohup ... &` so session start never waits on it.

**Behavior**: Diffs the current set of `bd` memory keys against a marker file (`~/.claude/logs/memory-log-sync.keys`). For each new key it regex-extracts a `20\d\d-\d\d-\d\d` date from the value, strips a leading date prefix off the first line, truncates at 140 chars, and appends `## [<date>] memory-fact | <key-prefix> | bd-mem <key> | <summary>` to the chronological `log.md` topic file, matching the format `/bead-forge` Phase 5 writes. On the first-ever run (no marker) it BOOTSTRAPS: it records the current key set and emits nothing, so it never replays the whole corpus into the log. Each run appends telemetry (`duration_ms`, `new_entries`, `total_keys`) to a jsonl, and any exception exits 0.

**Why subtle**: Two ordering traps decide whether this is durable or lossy. The marker is rewritten only AFTER the append succeeds, so a failed write retries next session instead of being silently marked done; but a value with no parseable date is dropped from `log.md` permanently while the marker still records the key, so it is never retried. That is exactly why `bd memories --json` is mandatory here: the plain-text output truncates every value at ~124 chars, which pushed the date out of range for ~18% of dated memories and lost them for good. The JSON-vs-truncated-text distinction recurs across every `bd`-backed hook and is invisible at write time, because both paths report success.

**Portable**: no (depends on the `bd` memory store, the `--json` output shape, and the `log.md` topic-file convention).

#### `regen-memory-graph.sh`

**Trigger**: SessionStart.

**Behavior**: Spawns `scratch/scripts/memory-graph/regen_graph.py` fully DETACHED (double-fork plus `setsid`, all fds off the hook's pipes, then `disown`) under `flock -n`, and exits 0 immediately. The rebuilt index and bridge files are what `preload-sibling-beads.sh` and the `/bd-related` skill read. A missing script exits 0. Build health (last successful duration and counts) is written to `.regen-state.json`, because the hook log now only times the spawn.

**Why subtle**: The obvious inline version cost a median of 4s and a p95 of 47s of pure session-start latency, dominated by two `bd` fetches against a cold or contended Dolt server, and multiple windows cold-starting together stampeded the same rebuild. Three fixes stack and each covers a different axis: detach so the harness never waits, `flock -n` so a concurrent window's attempt becomes a no-op rather than a queued duplicate, and a corpus fingerprint inside the worker so an unchanged corpus skips the rebuild entirely. Detaching is only legitimate because the consumers tolerate staleness by design: they read the previous graph for the few seconds until the new one lands atomically, and they already accepted per-session staleness. A SessionStart hook that must inject context into THIS session cannot use this pattern at all, which is the line to check before copying it.

**Portable**: shape-only. The graph builder and `bd` corpus are personal-tier; the detach-plus-`flock`-plus-fingerprint recipe for any expensive session-start rebuild ports directly.

#### `reforge-pending-habits.py`

**Trigger**: SessionStart, called by `auto-retire-stale-habits.sh` after its once-per-UTC-day throttle gate; it is the drain's reforge phase and runs before the retire phase.

**Behavior**: Scans `bd memories habit: --json` for entries whose body carries a bracketed `[REFORGE-PENDING ...]` marker (written when `/bead-forge` failed mid-`/compound` run). For each it strips the marker, derives a title and label domain from the key's colon segments, creates a `memory`-labeled bead in ONE `bd create` call (title, description, acceptance placeholder, type, priority, and labels together), then rewrites the habit memory body to `<clean body> (see <bead-id>, reforged <date>)`. If the body already names a `docr-XXXX` bead it only strips the marker and creates nothing. Every outcome, success or failure, appends to the shared `compound-drain-log.jsonl`.

**Why subtle**: Three failure modes a naive version gets wrong are handled explicitly. `--json` is mandatory rather than stylistic: an earlier version re-wrote each memory using the truncated plain-text preview and silently CORRUPTED any habit body longer than ~95 chars past the marker. Bead creation and labelling go in a single call because a two-call version strands a bead with no labels whenever the second call fails. And when the bead is created but the pointer-write back into the memory fails, the script logs `reforge-partial` instead of claiming success, because that state is genuinely unrecoverable automatically: the next session finds no bead ID in the body, re-enters the create branch, and mints a duplicate, so the log entry IS the recovery surface. The marker regex is tight (bracketed form only) so a habit that documents the `/compound` system and merely mentions the literal string is not reprocessed daily.

**Portable**: no (specific to the `/compound` habit lifecycle and the `bd` tracker).

#### `surface-github-api-memory.sh`

**Trigger**: PreToolUse on Bash, on the first `gh api`, `gh run`, or `gh pr` invocation of a session (matched with a negative lookbehind so the token `gh` inside a quoted argument does not count).

**Behavior**: Greps the live `## ` heading list out of the `github-api.md` topic file and injects it, plus a short "read this before hand-rolling an approach to endpoint choice, token capability, CI-status interpretation, or re-running workflows" instruction, via `hookSpecificOutput.additionalContext`. A per-session marker under `scratch/gh-memory-markers/` enforces once-per-session; markers GC after 24h. A missing memo file exits 0; the hook never blocks.

**Why subtle**: This is a RETRIEVAL hook, not a rules hook, and that distinction is the whole design. The knowledge was already written down and correct; what failed was that nothing prompted a lookup, and a full session re-derived two documented gotchas (a token missing an `actions:write` scope, and a CI rollup reporting stale same-name runs) at a cost of 31 rejected calls and a user-visible correction. Injecting the SECTION LIST rather than the file body is the calibration: a few lines that tell the model what is knowable, leaving the Read as the model's call. Because the headings are grepped live, the injected index cannot drift from the file, which is the usual rot mode for a hardcoded "see also" blurb. One thing to know before copying the envelope: this hook returns `permissionDecision: "allow"` alongside the context, so it also auto-approves the call it fires on, which is fine for a read-shaped `gh` family and would not be for a mutating one.

**Portable**: shape-only. The memo path and its contents are personal-tier; "on first use of a tool family in a session, inject the live heading index of the doc that covers it" ports to any docs layout.

#### `preload-workflow-gotchas.sh`

**Trigger**: PreToolUse on the Workflow tool.

**Behavior**: Unconditionally prints three workflow-authoring rules to stdout (which becomes assistant context) and exits 0. The rules: define fan-out lists as an in-script `const ITEMS = [...]` rather than deriving them from `args` (and never give an args-derived value a silent `|| default`; hardcode it or `throw`, because a silent fallback burns the whole run on the wrong target); avoid backticks and escaped apostrophes inside script template literals, using concatenated double-quoted strings and staging large context into files agents Read; and give review-verifier prompts an asymmetric burden plus an instruction to enumerate ALL candidate evidence files rather than inspecting one named file. No parsing, no gating, no state.

**Why subtle**: It is the deliberate inverse of the retrieval-first memory design, and the inversion is the point. The depth lives in a topic file that only loads when someone searches for it, and the args-shape failure recurred a third time precisely because the author was mid-authoring and never thought to search. When a gotcha's blast radius is "the entire multi-agent run executes against the wrong target," unconditional injection at the tool call beats conditional retrieval: three lines of tokens against a run worth thousands. Binding the trigger to the TOOL rather than to a keyword also removes the matching heuristic that would otherwise be the thing that misses.

**Portable**: shape-only. The Workflow tool and these specific gotchas are harness-specific; the portable move is recognizing when a gotcha is too costly for searchable memory and belongs hardcoded at its tool call.

#### `record-shared-file-read.sh`

**Trigger**: PostToolUse on Read/Edit/Write/MultiEdit (its own matcher group).

**Behavior**: The companion writer for `guard-shared-config-writes.sh`. When a Read or a completed write touches a file in the same guarded set (`settings.json`, `CLAUDE.md`, `hooks/*.sh`, `agents/*.md`, `skills/*.md`, `commands/*.md`, memory topic files), it stamps the file's current mtime into the same per-session stamp directory under the same key scheme. Never blocks: always exit 0.

**Why subtle**: Without the Read case, the guard blocks the FIRST write to every guarded file, including the correct read-then-write flow, which trains the author to reflexively re-run past the block and hollows out the signal within a day. The write case is the less obvious half and was found by being bitten twice: stamping only on Read leaves the guard holding the PRE-write mtime, so every SECOND write to the same file in a session blocks spuriously against the session's own change. The pair only works because both halves derive the stamp key from the path identically, so the recorder and the checker can never disagree about which file they are discussing; a paired-hook design like this fails silently the moment the two key schemes drift.

**Portable**: no. It is meaningless without its specific partner hook and stamp directory, though the read-stamps-then-write-checks pairing ports to any mtime-based collision guard.

#### `block-bd-unsafe-value.sh`

**Trigger**: PreToolUse on Bash, self-filtering to `bd remember|comment|create|update`.

**Behavior**: Three deterministic checks, each exiting 2 with the safe shape. (1) Any backtick anywhere in the command blocks, and `$(...)` is permitted only for the documented composition helpers (`printf`, `cat`, `date`, `echo`, `bd`); a backslash-escaped `\$(` is exempt so that writing ABOUT command substitution stays legal. (2) `bd create ... | grep ... docr-` blocks, because grep captures whichever bead id appears first. (3) `bd update --acceptance` or `--notes` fed `"$(cat FILE)"` where FILE is empty or missing blocks.

**Why subtle**: Each check encodes a realized corruption, not a hypothetical. A code identifier written as `handler()` inside a double-quoted value was EXECUTED by the shell before the tracker ever saw it and was silently gutted from the stored text. The grep-for-id shape clobbered two unrelated beads with wrong updates, because the id it captured was one merely REFERENCED in the description rather than the one just created. Check 3 exists specifically because the tool's own native guard is incomplete in a way that reads as complete: `--body-file` and `--design-file` reject an empty file and demand an explicit override, but `--acceptance` and `--notes` have no file variant, so `"$(cat FILE)"` is indistinguishable from a deliberate inline clear. An upstream command that fails and leaves FILE empty therefore wipes the field and still prints "Updated issue" (that is how docr-txnew lost its acceptance criteria). Two smaller traps the source documents inline: the exemption for escaped `\$(` was added because the hook's own close-out note was its first false positive, and grep patterns beginning with `--` need a `--` terminator or they are parsed as options, loudly under some greps and silently under others.

**Portable**: no. The flags, the id format, and the tool's empty-value semantics are `bd`-specific; the general shape (block the shell-quoting patterns that silently mutate stored text before the tool sees it) ports to any CLI that takes prose as an argument.

#### `block-bd-unbounded-json.sh`

**Trigger**: PreToolUse on Bash, self-filtering to commands containing `bd list` with `--json`.

**Behavior**: Allows the call only when it carries an explicit result cap, accepting `-n` or `--limit` in any getopt spelling (`-n 2000`, `-n=2000`, `-n2000`, `--limit 100`), including `-n 0` for unlimited since that is an explicit choice. Anything else exits 2 with the safe shapes in stderr. `bd create --json | jq -r .id` is deliberately out of scope: it is the documented safe id-capture form.

**Why subtle**: The default is a silent-truncation trap, not a performance one. `bd list --json` defaults to `-n 50` against a corpus of roughly 1,287 beads and orders closed-first, so an unbounded call returns about 4% of the corpus (in practice all closed) with NO truncation marker anywhere in the output. Every `jq` filter downstream is then a filter over an arbitrary slice, and absence claims read false-clean: in one session this produced three separate wrong answers, a forge collision check ("does a bead for this exist?"), a P0/P1 sweep ("no P1s"), and a label query, all returning empty against a corpus that contained matches. The counterintuitive part is that filtering for ONE known bead is equally unsafe, because the cap is applied before the filter, not after. And the reason it is a hook at all rather than another note: the gotcha was written into a memory topic file the same day it was discovered and violated anyway, because that file is not loaded at session start. Documented-but-not-loaded is precisely the promote-to-mechanical trigger.

**Portable**: no. The default limit, the ordering, and the corpus size are `bd`-specific; the shape (block unbounded reads from any list API whose JSON truncates without a marker) generalizes to plenty of CLIs.

#### `surface-deploy-memory.sh`

**Trigger**: PreToolUse on Bash, self-filtering to a real `aws codepipeline`, `aws codebuild`, or `terragrunt` command. Fires at most once per session via a marker file, and the marker directory self-reaps after 24 hours.

**Behavior**: Injects the deploy-architecture memory keys as `additionalContext` before the deploy command runs, alongside the two facts they encode: that a pipeline run is scoped to one `(Project, Service, Environment)` tuple rather than deploying everything, and that a `Succeeded` pipeline proves the apply ran rather than proving a given artifact is live. The key list is read live from the tracker so a newly written deploy memory is surfaced without editing the hook, falling back to two hardcoded keys when the tracker is slow or unavailable. Advisory only, exits 0 in all cases.

**Why subtle**: This is a retrieval failure, not a knowledge failure, and the distinction is the whole point. Both facts were already written down as memories, and the global instructions already carried a rule to consult them before asserting deploy behavior. A session still gave correct per-stack deploy-ordering advice and then REVERSED it to "one pipeline run covers all four stacks" after seeing the console showed two stages, never checking the execution variables that state the scope plainly. A wrong correction layered on top of right advice is worse than no advice, because it spends the user's trust to move them away from the correct answer. Documented-but-not-retrieved is the promote-to-mechanical trigger, so the fix is a hook that fires at the moment of use rather than another rule. The command match is deliberately anchored to a command position rather than run over the whole command string, because whole-string matching is a known false-positive source on sibling hooks (a tracker reference quoted inside an unrelated argument fires the guard and kills the entire invocation).

**Portable**: no (depends on the `bd` tracker and this author's AWS deploy topology), but the shape ports: when a rule keeps getting violated despite being written down, bind the retrieval to the tool call that needs it instead of to session start.

#### `bd-health-check-daily.sh`

**Trigger**: SessionStart, gated to run at most once per UTC calendar day via a state-file stamp.

**Behavior**: Runs the tracker's own drift detector against the underlying database and prints the result only when it reports a problem; silent when the store is healthy. Fails open unconditionally: a missing detector script, a timeout, or any error is treated as nothing to report rather than as a reason to block session start.

**Why subtle**: A prior real incident left a large fraction of the tracker's historical comments and events undecodable for the better part of an hour with every routine health signal (the tool's own doctor command, a basic list, a row count) reporting green the whole time; one read path was worse than silent, dropping an entire section rather than erroring, so the tracker simply looked like it had no history. With many concurrent sessions sharing one store, a silent read-path failure of that kind can run for a long time before anyone notices by accident. The daily cadence is a deliberate cost trade: the check itself takes several seconds and opens a database connection, and the failure mode it targets is triggered by version changes rather than by continuous drift, so checking more often would not catch it any sooner.

**Portable**: no (depends on the specific tracker's internal drift-detection script). The shape ports: a periodic, fail-open, silent-when-healthy health check for a shared backing store whose ordinary health signals can all read green during a real failure.

#### `block-bd-computed-field-write.sh`

**Trigger**: PreToolUse on Bash, matching a tracker update command that writes a shell-expanded value (a command substitution) into a long-text content field (title, description, design, acceptance, or notes).

**Behavior**: Blocks the write and points to two safer forms: a fetch-assert-write helper script that verifies the prior value before replacing it, or the tracker's own file-based flags, which reject an empty file outright. A literal inline value is never blocked, only a computed one.

**Why subtle**: The tracker replaces the WHOLE field on a content write rather than patching it, so if the command that produced the substituted value silently failed or returned empty, the field becomes empty with no error and the prior content is gone. The near-miss that motivated this hook involved a JSON query that returned an empty string because the tracker's own show command returns a single-element array rather than a bare object, which is exactly the kind of shape surprise that produces an empty value while looking like ordinary plumbing. The underlying rule already existed in prose and had been violated multiple times in a single session before this became a mechanical gate.

**Portable**: shape-only. The specific tracker and its flags are this author's; "block a whole-field-replacing write when the new value is computed rather than literal, since a silent empty result destroys the prior content" generalizes to any store with replace-not-patch write semantics.

#### `verify-bd-content-field-write.sh`

**Trigger**: PostToolUse on Bash, matching a tracker update command that targets a long-text content field (acceptance, design, or notes).

**Behavior**: Re-reads the field immediately after the write and warns (advisory only, cannot undo the write) when the tracker reported success but the field is actually empty.

**Why subtle**: A documented, supported flag on the tracker's own update command can report success and print a normal confirmation line while silently storing nothing, which was confirmed by writing the flag, observing the success message, and then reading the field back as empty. It is the write-side sibling of a companion PreToolUse hook that blocks a computed value going IN to a content field; this one catches the narrower and sneakier case where a plain, well-formed write still does not land, so the next turn at least knows to distrust the success message instead of building on a false completion claim.

**Portable**: shape-only. The specific tracker and its flag set are this author's; "verify a content write actually landed rather than trusting the tool's own success signal" generalizes to any store where a documented write path can silently no-op.

#### `nudge-supersede-description.sh`

**Trigger**: PostToolUse on Bash, matching a tracker comment or a notes-appending update whose body reads like a correction (case-insensitive markers such as "corrected," "superseded," "stale," "no longer true").

**Behavior**: Emits a one-shot-per-(session, item) advisory reminding the author to also patch the READ-FIRST surface (title, description, acceptance criteria), not only the append-only comment or notes trail. Never blocks; makes no additional tracker call to check whether the fix is already reflected there, to avoid the cost and risk of an extra database connection per comment.

**Why subtle**: The tracker's own read order prints the description before the comments and its search indexes titles only, so a correction filed as a comment does not reach the surfaces a cold-start session actually reads first or searches by. The append-only instinct that produces this pattern is itself correct, since it preserves a record of what was believed and when; the gap is specifically that nobody also goes back and patches the now-stale claim sitting above it. A structured audit of a batch of recently-created items found this exact shape repeatedly, including on the very item that was tracking the failure mode itself, and one instance of it reached a PR review as a false finding because a reviewer read the superseded top-level text as current.

**Portable**: shape-only. The specific tracker's read order and search behavior are this author's; "when a correction lands on an append-only surface, nudge the author to also patch the surface a reader sees first" generalizes to any tracker with the same read/write asymmetry.

#### `lint-memory-after-bash.sh`

**Trigger**: PostToolUse on Bash, gated to commands that look like they wrote something under the memory tree.

**Behavior**: Runs the memory linter against memory files rewritten through Bash and surfaces its error lines. Advisory by construction: PostToolUse cannot block, so the edit has already landed. Exits 0 when clean, when `jq` is missing, or when nothing memory-shaped was touched.

**Why subtle**: This closes a matcher gap rather than a behavior gap. The memory linter was wired PostToolUse on Edit and Write only, so a memory file rewritten through Bash (a Python heredoc, `sed -i`, `tee`, a redirect) skipped it entirely. That is how one memory file reached roughly 30KB and silently truncated its own tail past the load cap: every edit to it that day went through Python-in-Bash, and the overflow was found only by running the linter by hand. The general lesson is worth more than the hook: a validator wired to a tool matcher is only as complete as the set of tools that can perform the write.

**Portable**: shape yes, implementation no (it invokes this setup's memory linter against this setup's memory path).

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

#### `inject-live-date.sh`

**Trigger**: SessionStart.

**Behavior**: Emits up to two blocks on stdout. Always: an authoritative LIVE DATE block giving both the user's local day with weekday and the UTC day, explicitly labelled to be trusted over any older `currentDate` already in context. Conditionally, when the payload's `source` is `resume` or `compact`: a SESSION CONTINUITY BREAK block declaring every pre-boundary live reading unverified and enumerating what to re-check (PR `headRefOid` above all, plus draft/merge/review/check state, bead status and gap-window comments, live infra state, and file contents planned for exact-string edits). The payload read is bounded by `timeout 1` and skipped entirely if `timeout` is unavailable.

**Why subtle**: Three separate traps in one small hook. The harness-provided `currentDate` is stamped at the ORIGINAL session start and goes stale across resume and multi-day sessions, while the container clock runs UTC, which in the evening is a full calendar day ahead of the user's local day, so emitting either clock alone trades a stale date for a confidently wrong one. The defensive stdin read is not paranoia: no other SessionStart hook here reads stdin, so nothing locally proves the harness closes it, and a bare `cat` on a pipe that stays open would hang every single session start, on the highest-traffic surface in the harness. The continuity block covers a blind spot the "injected status claims are pointers, never evidence" rule explicitly does not: that rule scopes to INJECTED claims (a pasted handoff, a hook status line), whereas a first-party reading the model took ITSELF earlier in the same session is exactly the one that feels current. The grounding incident: a session verified a PR at 23:00 UTC, was suspended, resumed at 03:19 UTC, and wrote those pre-gap readings into a tracker comment as "re-verified live" after concurrent sessions had force-pushed the branch twice during the gap.

**Portable**: shape-only. The local timezone and the `source: resume|compact` payload field are Claude Code specifics; the two-clock anchor and the continuity-break-invalidates-your-own-readings framing port anywhere sessions can be suspended.

#### `inject-slack-checklist.sh`

**Trigger**: UserPromptSubmit.

**Behavior**: Detects that the turn is likely to produce a Slack, DM, or message draft via three signals: a pasted thread timestamp (`HH:MM` followed by AM/PM), draft-intent phrasing ("draft a message", "what should I say", "reply to", "how do I word"), or a read-precursor ("read the DMs/thread"), which reliably precedes a reply draft. On a hit it extracts the live `## Pre-output checklist` section from the Slack-style memory topic file (`memory/feedback_slack-messages.md`) with awk and emits it as injected context, tagged with which trigger fired and pointing at the full file for situational nuance. Explicit opt-out on `no-slack-check`, plus a per-skill opt-out for `/capture-transcript`. Appends one JSONL telemetry row per firing. Never blocks.

**Why subtle**: The checklist is extracted from the source file at runtime rather than pasted into the hook, so the injected copy cannot drift from the file that owns the rules. Copying it in would have recreated exactly the duplication problem the summary-sync lint exists to police elsewhere. The detector is deliberately tuned to over-fire on an explicit cost asymmetry: a false positive injects around 25 lines the model ignores, while a false negative is the precise failure the hook exists to prevent, so borderline signals fire on purpose. The single carve-out proves the tuning is cost-based rather than vibes: transcript-ingest prompts paste long conversations full of incidental "respond to" and "reply" phrases, and dumping a drafting checklist onto a capture task is pure noise, so that one skill is suppressed by name. Underneath all of it is the general lesson: a "load this file before drafting" instruction in a prompt is never self-enforcing, and the fix is to put the content in context AT draft time rather than hoping the model remembers to go fetch it.

**Portable**: shape-only. The checklist file and the intent regex are this author's; runtime extraction of a named section from a source-of-truth file at prompt time is the portable mechanism.

#### `userpromptsubmit-coordination-refresh.sh`

**Trigger**: UserPromptSubmit, unmatched (20s timeout). Skips prompts that begin with `/`, and requires two gates: coordination-state phrasing (`reviews owed`, `waiting on`, `blocked on`, `needs/pending/awaiting/requested review`, `untriaged`, `re-review`) AND at least one 4-to-6-digit `#NNNN` PR reference (up to 12).

**Behavior**: Fetches live state for the referenced PRs (`number,state,updatedAt,author,reviews`) behind a 15-minute per-PR TTL cache, then injects a block only when live state CONTRADICTS the prompt's framing. Two concerns: (A) an OPEN PR the user did not author but has already submitted a non-pending review on, which makes a "new"/"untriaged"/"owed-review" label stale; (B) an OPEN PR untouched for >= 14 days (possibly abandoned, author possibly departed). Each concern is warned at most once per session per PR. A corrupt or empty cache file is repaired to `{}` rather than allowed to silently disable the check, and cache entries predating the review-state schema are refetched. If `gh api user` returns nothing (unauthenticated or offline) only concern A is disabled; the staleness check still runs. Advisory, exit 0 always.

**Why subtle**: The failure is that a handoff prompt or a pasted status block ASSERTS coordination state that was true when it was written, and the model treats those assertions as current facts. Three realized instances motivated it: a PR described as "deploying now" long after it was not, two PRs carried as reviews-owed for 20+ days after their author had left the company, and a PR labeled "NEW, untriaged" in a handoff when it already carried the user's own posted review from six days earlier. Note what the hook does NOT do: it never summarizes the PRs or injects their content. It fires only on a contradiction, so a prompt whose framing is accurate costs nothing and produces no output, which is what keeps it from becoming ignorable noise. The two-gate design (phrasing AND refs) means ordinary prompts never pay the `gh` round-trip. The documented scope limit is honest about the boundary: person-only commitments ("X said they would ship it") have no queryable surface and remain a behavioral concern, not a mechanized one.

**Portable**: shape-only: it needs `gh` and this repo's PR-number range, but the pattern (when a prompt asserts stale-able coordination state and names queryable entities, verify those entities and surface only contradictions) ports to any tracker.

#### `nudge-scratchpad-artifact.sh`

**Trigger**: PreToolUse on Bash.

**Behavior**: Fires when a command write-redirects (`>`, `>>`, `tee`, `tee -a`) into the ephemeral SESSION scratchpad (`/tmp/claude-*/.../scratchpad/`) targeting a document-shaped extension (`.md`, `.json`, `.txt`, `.yaml`, `.yml`), AND the same command does not also write under the persistent `~/.claude/scratch/`. It prints a durability check on stdout naming the target file and asking whether a later turn or session could need it. Reads of the same paths, non-document writes, and commands already dual-homing to persistent scratch stay silent. Always exits 0.

**Why subtle**: The session scratchpad is age-reaped within about a day, so a file staged in one turn can be gone before the turn that consumes it, and the failure surfaces as a confusing missing-file error far from the write that caused it (it landed twice: once on a review re-cut, once on a PR body staged and reaped before the round-2 patch needed it). The narrow trigger is the entire design: most scratchpad writes are legitimately ephemeral, so blocking would be wrong and a broad advisory would be tuned out within a day. Restricting to document-shaped extensions plus the dual-home exemption keeps the nudge rare enough to still get read. One consequence is easy to miss: because reaping is time-based rather than session-based, the copy has to happen in the SAME turn, so "I will move it at session end" is already too late.

**Portable**: shape-only. The `/tmp/claude-*` scratchpad layout is CC-specific; the ephemeral-vs-durable artifact split is universal.

#### `stop-validate-stale-state-claim.sh`

**Trigger**: Stop event, reading the final assistant text block from the transcript.

**Behavior**: Flags a turn-ending claim that something is still pending or outstanding (a person's action, a deploy, a review) when the same turn made no live-state read at all to refresh that claim. Re-verifying the claim anywhere in the turn is the whole exemption; blocks (exit 2) only on the conjunction of an outstanding-state assertion AND zero refreshing reads that turn, which keeps the false-positive rate near zero.

**Why subtle**: A rule already existed in prose naming the exact tell (words like "still," "has not," "no reply yet," "unsent" about someone else's action) and it fired anyway, twice: once calling a message unsent off a stale read, once telling the user two of three deployments still needed action after the user had already shipped all three. A rule stated precisely and still not firing is what moves the fix from another sharpening pass to a mechanical gate. The scope is deliberately narrow to a single failure shape (an outstanding-state claim with no same-turn refresh) rather than a general staleness detector, which is what keeps it usable without constant false blocks.

**Portable**: shape-only. The specific trigger phrases are this author's; "block an end-of-turn claim of unresolved external state unless the same turn re-checked it live" generalizes to any agent that can act on stale reads.

#### `stop-validate-unrecorded-nonactions.sh`

**Trigger**: Stop event, reading the final assistant text block from the transcript.

**Behavior**: Flags a turn-ending message that names something the assistant is deliberately NOT doing (a deferred fix, a known gap being left as-is) when the same turn made no durable write recording it anywhere. A non-action that is explicitly tied to an existing tracked item passes silently, since that is the correct and common case; only the unrecorded variant fires (exit 2).

**Why subtle**: A deliberate non-action reads as commentary rather than as work, so it skips the recording reflex that an actual code change or file write naturally triggers, even though chat is the least durable surface available. A real session wound down declaring all durable state recorded, then listed several such items in chat only; the user had to ask whether they had been logged, and most of them turned out to need real follow-up. The conjunctive trigger (a non-action marker AND zero durable writes that turn) is deliberately narrow for the same reason the sibling stale-claim validator is: false positives on ordinary commentary would make the check worse than useless.

**Portable**: shape-only. The specific marker language is this author's; "a stated intention to skip something is itself a claim that needs a durable record" generalizes to any agent whose chat output is not itself persisted.

#### `userpromptsubmit-correction-contract.sh`

**Trigger**: UserPromptSubmit, matched conjunctively: the first line is an explicit contradiction of prior output (e.g. "that is not what I asked," "I wanted X, not Y"), the prompt is not itself a slash-command invocation, and the session has not already fired this hook once.

**Behavior**: Injects the retrieval-before-acting protocol (search prior corrections, consider whether the topic recurs) as additional context at the start of the turn, once per session, advisory only (never blocks).

**Why subtle**: A controlled comparison ran an intentionally correction-shaped prompt against both an older and a trimmed version of the always-loaded instructions and found the retrieval protocol fired in neither: zero mentions of the search step, the reflection skill, or the correction-tracking convention across every run, even with the relevant tool explicitly allowed. That ruled out the trim itself as the cause and pointed at the mechanism instead: a prompt-only instruction for "search before acting on a correction" needs to be surfaced at the START of the turn to change anything, and by the time a Stop-event validator could check for it, the turn's approach is already set. Correction detection is inherently fuzzy and correction-shaped language is common in ordinary conversation, so the trigger is deliberately conjunctive (an explicit contradiction pattern, not a slash command, not already fired this session) to bound the false-positive cost to a single extra paragraph rather than a constant interruption.

**Portable**: shape-only. The specific correction-detection patterns are tuned to this author's phrasing; "inject a protocol at prompt-submit time when the prompt looks like a correction of prior output, since a post-hoc validator is too late to change the turn's approach" generalizes to any harness with an equivalent always-loaded-but-inert instruction.

### Skill-contract validators (personal-tier)

These come in producer/consumer pairs. A UserPromptSubmit hook detects that a turn is about to run a specific skill and drops a per-session marker plus the output contract; the matching Stop hook fires only when that marker exists and checks that the promised structure actually got emitted. The marker is what makes the check safe: without it a Stop hook cannot tell a collapsed render apart from ordinary discussion about the skill, so it would either false-fire on conversation or stay silent on the collapse it exists to catch. Each pair caps itself at one forced retry.

#### `userpromptsubmit-investigate-contract.sh`

**Trigger**: UserPromptSubmit, unmatched, matching only the first line of the prompt: a leading `/investigate`, or a leading imperative `investigate ...` (optionally after `please`).

**Behavior**: Producer half of the `/investigate` pair. Writes `~/.claude/scratch/investigate-markers/<session_id>.pending` (6-hour age-GC on the directory) and injects an `<investigate-output-contract>` block stating that the deliverable is the skill's Phase 4 template verbatim, that all six sections are unconditional (`### Investigation Questions`, `### AWS Evidence`, `### Datadog Evidence`, `### Findings`, `### Blast Radius`, `### In-Flight Fix?`), that the two evidence sections are either populated from live queries or carry a single explicit `Not queried: <mechanical reason>` line, that no fix proposals belong in the output, and that a Stop hook enforces this post-hoc. Advisory, exit 0 always.

**Why subtle**: Detection is deliberately NARROWER than the skill's own trigger surface, and the asymmetry is the design. The `/investigate` skill also fires by description on a pasted stack trace or a "why is X failing" question, but arming hard output enforcement on any pasted error would over-fire on casual debugging chat and force a full six-section template onto a two-line question. So the marker (the thing that licenses a block-and-retry at Stop time) is set only on an unambiguous formal invocation; the description-triggered paths stay advisory through the skill text alone. Telling the model the contract at prompt time is also cheaper than catching the violation at Stop time: the injected block exists to prevent the retry, not to justify it.

**Portable**: no: the Phase 4 section list, the AWS/Datadog evidence surfaces, and the marker path are specific to this author's `/investigate` skill.

#### `stop-validate-investigate.sh`

**Trigger**: Stop event, unmatched (15s timeout). No-ops unless `~/.claude/scratch/investigate-markers/<session_id>.pending` exists.

**Behavior**: Consumer half of the `/investigate` pair. On a turn carrying a `## Investigation:` header it requires all six Phase 4 sections, then goes one level deeper on the two evidence sections: it slices each section body with awk and requires either a populated field (a `**Label`-style bold key) or a literal `Not queried:` line, so an empty `### AWS Evidence` heading does not satisfy the check. Missing pieces exit 2 with each gap named. Without the header, a collapse floor fires on terminal investigation prose (`leading hypothesis`, `contributing factors`, `blast radius`) and forces one re-emit. `stop_hook_active` bounds it to a single retry and clears the marker.

**Why subtle**: The header-presence check is the easy half and it is not what this hook is for. The measured failure (2026-07-15 benchmark) was a SILENT skip of live-state queries: the model renders `### AWS Evidence` and `### Datadog Evidence` as empty or hand-waved headings, the output looks structurally complete, and a reader cannot distinguish "queried and found nothing" from "never queried". Forcing an explicit `Not queried: <mechanical reason>` line converts that silence into a stated decision the reader can weigh, which is the same honesty-by-enumeration trick the `/review` roster line uses. The collapse floor covers the other direction, where the model skips the template entirely and hands back a hypothesis paragraph; the pending marker is what licenses that heuristic, so investigation vocabulary in ordinary conversation never trips it.

**Portable**: no: the six-section template and the AWS/Datadog evidence contract belong to this author's `/investigate` skill. The populated-or-explicitly-declined pattern (never let an empty section pass as evidence) is the portable idea.

#### `userpromptsubmit-plan-contract.sh`

**Trigger**: UserPromptSubmit, unmatched, matching a leading `/converge`, `/ideate`, or `/launch` on the first line. `/autopilot` is deliberately NOT matched.

**Behavior**: Producer half of the plan-present pair. Records which of the three skills was invoked in `~/.claude/scratch/plan-markers/<session_id>.pending` (6-hour age-GC) and injects a `<plan-present-contract>` block naming three mandatory guarantees in the present/approval render: `### Iteration Log` covering every round including Round 0, a `### Skeptic Lens` block or an explicit `Skeptic Lens unavailable: <reason>` line, and (for converge and launch, not ideate) a `### Convergence Delta` carrying a `CATEGORY: CONFIRMED | MINOR_ADJUSTMENTS | MAJOR_REVISIONS | SCRAPPED_AND_REBUILT` tag. The block states that these render even on the ESCALATE-ROUTE branch, where the escalation section replaces the plan body but not the process-evidence sections. Advisory, exit 0 always.

**Why subtle**: The three guarantees are PROCESS EVIDENCE, not plan content, which is exactly why they are the first thing dropped when a long planning run is running out of turn. A plan without an Iteration Log cannot be distinguished from a first draft, and a plan whose Skeptic Lens section is simply absent cannot be distinguished from one where the adversarial pass silently failed to dispatch; both read as clean output. The explicit-unavailable escape hatch is what makes the requirement enforceable rather than a lie generator: a genuinely failed skeptic dispatch has a compliant way to say so. `/autopilot` is excluded on a real semantic ground, not an oversight: its Gate 1 replaces the converge skeptic and convergence-gate phases, so demanding those sections there would enforce a contract the skill does not owe. The escalate-branch clause pre-empts the obvious model rationalization ("I escalated, so the plan template does not apply").

**Portable**: no: the three skills, their templates, and the CATEGORY vocabulary are personal-tier. Requirements here are under an explicit sync contract with the three present templates and with `stop-validate-plan-present.sh`.

#### `stop-validate-plan-present.sh`

**Trigger**: Stop event, unmatched (15s timeout). No-ops unless `~/.claude/scratch/plan-markers/<session_id>.pending` exists.

**Behavior**: Consumer half of the plan-present pair. Detects which present header the turn rendered (`## Converged Plan`, `## Launch Plan`, or `## Ideate`) and requires the corresponding guarantees: `### Iteration Log` and either `### Skeptic Lens` or the explicit `Skeptic Lens unavailable` line for all three, plus a literal `CATEGORY:` tag drawn from the four-value set for converge and launch. Missing pieces exit 2 with a pointer to the specific template file for that skill. With no header, a collapse floor fires on plan-shaped terminal sections (`### Work Items`, `### Dependency Graph`, `Recommended Winner: Approach`) and forces one re-emit. One retry via `stop_hook_active`, marker cleared on success or on the guard.

**Why subtle**: The CATEGORY check matches the literal enum values, not the presence of a Convergence Delta heading, because the failure being caught is a plan that DISCUSSES how much it moved without committing to a classification: prose is unauditable, the four-value tag is. Detection also has to route per header, since ideate legitimately owes no CATEGORY (it ranks approaches rather than converging one), and a uniform check would either fail every ideate render or let converge slip. The collapse floor anchors on structural sections a plan cannot fake its way around: if `### Work Items` or a recommended winner appears without the present header, the model produced the plan body and skipped the process-evidence wrapper, which is precisely the drift the pair exists to catch.

**Portable**: no: skill names, present templates, and the CATEGORY enum are personal-tier.

#### `userpromptsubmit-review-contract.sh`

**Trigger**: UserPromptSubmit, unmatched, self-scoping to the FIRST LINE of the prompt: a leading `/review`, the token `self-review`, or an imperative "review my/this/our/the changes|branch|diff|code|working tree" (optionally prefixed by please/go/now or can/could you). A `#NNNN` or `pr N` token on that line DISQUALIFIES the match.

**Behavior**: Producer half of the `/review` contract pair. On a match it writes a session-scoped marker (`~/.claude/scratch/review-markers/<session_id>.pending`) and injects a `<review-output-contract>` block naming the required render: the `## Self-review:` header, the `{N} findings across {M} files.` count line, an `Agents:` line enumerating all 13 roster agents each with an explicit `ran` / `skipped (<reason>)` / `n/a (<reason>)` state, and the severity buckets (Front Door, Critical, Important, Suggestion, Advisory, Open questions, Positive) with empty ones omitted. It ONLY sets markers, never heuristically clears them; the Stop half clears on a valid render or after its one forced retry, and a 6-hour age-GC here covers abandoned runs. Also appends an injection record to `logs/review-contract-inject.jsonl`. Advisory, exit 0 always.

**Why subtle**: The `Agents:` enumeration is the whole point, and it is a forcing function rather than a report. `/review` fans out to 13 agents on computable dispatch signals, most of them conditional, and a weak orchestrator can dispatch a subset and produce output that looks complete: silence about an undispatched agent is indistinguishable from a correct skip. Requiring a state for EVERY agent mechanically requires evaluating every dispatch signal, so the formatting rule buys dispatch honesty. The PR-number disqualifier matters because `/pr-intel` owns PR-numbered review asks and has its own contract pair; without it the two producers would both arm on the same prompt and the model would get contradictory templates. First-line scoping is the same defense the sibling producers use: pasted blocks, handoffs, and task notifications carry review vocabulary on later lines, and matching those would arm hard output enforcement on discussion.

**Portable**: no: the 13-agent roster, the severity buckets, and the render are specific to this author's `/review` skill. The shape (arm a marker plus front-load the exact contract the Stop half will check) ports, and the roster is under an explicit three-way sync contract with `SKILL.md` and `stop-validate-review.sh`.

#### `stop-validate-review.sh`

**Trigger**: Stop event, unmatched (15s timeout). Self-gated: does nothing unless `~/.claude/scratch/review-markers/<session_id>.pending` exists, which only `userpromptsubmit-review-contract.sh` creates.

**Behavior**: Consumer half of the `/review` pair, cloned from the proven `stop-validate-pr-intel.sh` model. It extracts the assistant text emitted since the last real user prompt and takes one of three paths. If the turn carries a `## Self-review:` header, it slices the region from the `Agents:` line to the next `###` and requires all 13 roster agents to appear by name; a missing line or any missing agent exits 2 with the specific gaps named. If there is no header but the turn carries terminal review-verdict prose (`ready to push`, `findings across N files`, or a bare `### Front Door|Critical|Important|Suggestion` bucket), that is the collapse floor and it exits 2 to force one re-emit. Otherwise (an intermediate turn: questions, partial work) it keeps the marker and allows. `stop_hook_active` caps enforcement at exactly one forced retry, clearing the marker on the way out.

**Why subtle**: The marker coupling is what makes the collapse check safe. A Stop hook can only demand a template once it knows the turn was SUPPOSED to be a `/review` render, and a collapsed render carries no header to infer that from; the prompt-time marker breaks that circularity, so discussion ABOUT a review (no marker) can never false-fire. Two live corrections are baked in. The `Agents:` anchor is `^\**Agents:` rather than the bare form, because a bold `**Agents:**` label is a natural markdown rendering with identical semantics and anchoring on the bare form produced a formatting-only failure (2026-08-06). The roster check uses substring grep, so a bare `silent-failure-hunter` in the list also matches the `mx2-`-prefixed form the producer's contract names, which keeps a cosmetic prefix drift between skill and hook from failing an otherwise valid render. The roster is under a three-way sync contract (`skills/review/SKILL.md`, the producer's injected block, this array); changing it in one place silently weakens or over-fires the other two.

**Portable**: no: the roster and output template are this author's `/review` skill. The producer/marker/consumer shape with a one-retry guard and an explicit collapse floor is the portable idea.

#### `stop-validate-pr-intel.sh` (validation half, beyond the pair entry)

**Trigger**: Stop event, unmatched (15s timeout). Paired with `userpromptsubmit-pr-intel-contract.sh`; the pair's marker mechanism is described in the contract-sync-pair entry above, and this entry documents the checks that entry leaves implicit.

**Behavior**: Beyond the template-presence checks, the hook runs four layers. (1) Structured-render detection anchors on the two stable section headers plus a RELAXED PR-number-bearing H1 (`^## .*#<digits>`), not the exact `^## PR #` prefix. (2) Required-line checks add a `Specialists:` roster line (dispatched, comma-separated, plus `skipped: <name (reason)>`) to the Provenance and Decision-count lines, and compare the count of `**Briefing context**` blocks against the count of `Classification:` tokens so a per-finding gap is reported numerically. (3) An embedded Python pass does body-inline dedup: it extracts the fenced Draft Review Summary body and every fenced Draft Inline Comment, computes stopword-filtered token containment per sentence, and flags any summary sentence at >= 0.70 containment against an inline, exempting the `@claude` trigger sentence and short `see inline on line N` pointers. (4) A second Python pass runs four verbosity budgets: Review Recommendation prose beyond its metadata lines <= 12 words, an approve/Ready Verdict <= 25 words, total disposition-surface words <= `200 + 40 * DecisionCount`, and each inline comment body <= 60 words. Every structured render appends one line to `logs/pr-intel-verbosity.jsonl` recording which checks fired, so the false-positive rate is reviewable.

**Why subtle**: Three of the tuning decisions here are scar tissue from specific false fires. The relaxed H1 exists because the strict first-line check made `IS_STRUCTURED=false` on every real render (a lead-in sentence or a `## PR Intel: #NNNN` token deviation was enough), which both skipped validation AND left the marker uncleared, so a stale marker from one PR misfired a collapse on the next PR in the same session. A bare `/post-review` mention was removed as a collapse signal after it false-fired on a downstream `/compound` turn that merely referenced the skill. The header-deviation branch clears the marker and exits 0 precisely so a later same-session turn containing verdict prose cannot be read as a collapse. The verbosity constants were adversarially verified against 42 red-team cases at 0 false positives before shipping, and their known residual gaps (cross-surface paraphrase, recaps trimmed to exactly the ceiling, bloat relocated into uncounted Briefing-context blocks) are documented in the source rather than pretended away: the hook is the backstop, the injected contract is the teacher.

**Portable**: no: the template, the provenance and classification vocabulary, and the disposition budgets are personal-tier. The transferable pieces are the telemetry line per render and the practice of recording a check's known blind spots next to the check.

#### `stop-validate-overwatch.sh`

**Trigger**: Stop event, unmatched (15s timeout). Self-gated on transcript evidence; no marker involved.

**Behavior**: Triple-gated check that a standing watcher loop re-armed itself. Gate 1: a Bash `tool_use` this turn whose command references `cycle.py` (the overwatch loop driver). Gate 2: a tool RESULT this turn carrying both `"arming_due": true` and `"action": "run"`. Gate 3: no `ScheduleWakeup` or `CronCreate` `tool_use` in the turn. All three true means the turn is ending with the loop dead, so it exits 2 telling the model to schedule the next wakeup with the same loop prompt, or to call `ScheduleWakeup` with `stop:true` and say so if the loop is intentionally ending. One retry via `stop_hook_active`.

**Why subtle**: Two independent things make this hook interesting. First, the failure is silent BY DESIGN of the thing it protects: overwatch exists so the user does not have to poll, so a watcher that quietly stops re-arming produces no symptom at all; the user simply never hears from it again and cannot tell that from "nothing needed attention". Re-arming was an agent-side prose contract, which is the weakest possible place to put a step whose omission is invisible. Second, the extraction discipline is load-bearing and was learned on the very turn that authored the hook: a raw grep over the turn's JSONL matches META-CONTENT, including test fixtures written through the Write tool, bead comments, and documentation that merely mentions the trigger patterns, so the hook false-fired on itself. Each gate therefore reads a specific structured field (Bash `tool_use` commands, `tool_result` text, `tool_use` names) and the source carries an explicit "never grep the raw transcript slice in this hook" instruction. The gates are also chosen so that discussion ABOUT overwatch cannot satisfy gates 1 and 2 together: talking about the loop does not run it, and does not produce an armed plan in a tool result.

**Portable**: no: it depends on the `/overwatch` skill's `cycle.py` plan schema and on the `ScheduleWakeup`/`CronCreate` primitives. The shape (when a turn observably entered a self-perpetuating loop, require the re-arm call before letting the turn end) ports to any scheduled-agent setup.

#### `stop-validate-post-review-memory.sh`

**Trigger**: Stop event, unmatched (15s timeout). Unlike its marker-gated siblings, it self-gates on transcript evidence: it fires only when the turn actually posted a PR review.

**Behavior**: Extracts every Bash command issued since the last user prompt, base64-encoded one per line, and classifies each INDIVIDUALLY. A posted review is a single command that either `gh api`-writes to `/pulls/<N>/reviews` (URL lookahead excludes paginated `?per_page` reads) with a write indicator in the SAME command, or runs `gh pr review <N>` with a verdict flag; both forms are anchored to command position (line start, shell separator, or `$()`). If a review was posted and no `bd remember --key="review:pr-..."` ran in the same turn, it exits 2 with the exact command to run, including the PR number it parsed. Inline comment posts and replies (`/pulls/<N>/comments`) are deliberately not gated.

**Why subtle**: Nearly every line of this hook is a false-positive fix, and each one names a real misfire. Evaluating commands individually (rather than grepping the concatenated turn) exists because a READ of `/reviews` in one command plus a `-f` flag in a different command composed into a phantom posted review. Anchoring on command position exists because prose inside a bead comment or memory value that merely mentions `gh pr review --approve` matched, and the hook false-fired on its own bead trail. The turn-boundary extraction counts user messages with STRING content (hook feedback, task notifications) as boundaries, not just array-content prompts, because string-content messages never reset the boundary and the hook re-fired on every subsequent stop in the session. The underlying concern is a quiet data loss: the `review:pr-<N>:<date>` memory is the primary prior-review channel for the next re-review, the alternate channel is best-effort and SSO-dependent, and a turn that ends on a successful posting report looks complete while leaving that channel empty. The stderr also tells the model NOT to write the memory if the POST actually failed, which keeps the retry from manufacturing a record of a review that never landed.

**Portable**: no: it depends on the `bd` tracker's memory model and this author's `/post-review` skill. The per-command isolation and command-position anchoring are the transferable lessons for anyone grepping a transcript for evidence that an action occurred.

#### `userpromptsubmit-cold-review-nudge.sh`

**Trigger**: UserPromptSubmit, unmatched (20s timeout), matching a leading `/review` or a leading `/pr-intel --mine` on the first line. A plain `/pr-intel` (reviewing someone else's PR) is deliberately excluded, since that is already an external review.

**Behavior**: Detects a SECOND same-session self-review pass against an UNCHANGED target and nudges toward `/cold-review` instead. Target identity is a PR number from the first line, else the current branch. Content fingerprint is the PR head OID, or for a branch the sha256 of the merge-base diff with `index` lines stripped (matching `/review`'s own default scope, uncommitted work included). Every pass is appended to `logs/self-review-pass.jsonl`; a prior entry for the same `(session, target, fingerprint)` triple older than 180 seconds emits the nudge once, guarded by a marker file with a 24-hour GC. The nudge explains the framing-correlation argument, cites the evidence, and explicitly permits continuing if the second pass adds a named new signal. Advisory, exit 0 always.

**Why subtle**: The fingerprint condition is the whole hook. A re-review after the author changed the code is legitimate and common (this harness ran three passes on one PR in a day, and the first two were real delta re-reviews), so a nudge keyed on "you already reviewed this" would be pure nuisance and get trained away; keying on "the content has not changed since your last pass" isolates the actual anti-pattern. When the fingerprint cannot be resolved the hook stays SILENT rather than guessing, because a wrong nudge costs more than a missed one. The 180-second dedup window exists for a harness artifact: a skill invocation re-submits the prompt as `skill-invoked /review ...`, so one user action reaches this hook twice within seconds and would otherwise self-trigger. The underlying claim is structural, not effort-based: `/review` and `/pr-intel --mine` subagents get fresh context windows, but the session that wrote the code also writes their prompts and frames the diff, so a second pass re-finds what the first found. The measured cost was a 7-lens same-session review that missed or killed 8 findings a human reviewer and a review bot caught.

**Portable**: shape-only: the surfaces, repo, and skill names are personal-tier, but the mechanism (fingerprint the review target, log passes, nudge only on a repeat pass against unchanged content) ports to any self-review workflow.

### Shared library

#### `lib/log-event.sh`

Source-able shell helper that other hooks use for structured logging. Each hook calls `hook_instrument "$(basename "$0")"` at start to log invocation to a central audit file.

**Portable**: yes, see `examples/lib/log-event.sh`. The pattern (instrument every hook) is independent of the specific logger implementation.

## Why the description-first format

A repo that ships only runnable shell would tell adopters "here is what to run" without "here is why this hook exists." The hook's value is in the why: what failure mode does it catch, what corrective behavior does it replace, when does it matter. The runnable shell is the implementation; the description is the portable harness component.

Adopters who want to use a hook copy the shell from `examples/` and adapt to their project's specifics. Adopters who want to understand the harness read the descriptions and build equivalents in whatever tool they prefer.
