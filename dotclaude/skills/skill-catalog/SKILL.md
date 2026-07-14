---
name: skill-catalog
description: Reference catalog of available skills. Preload into agents that need escalation awareness. Claude loads this automatically when determining which skill to recommend.
user-invokable: false
---

# Skill Catalog

These skills can be recommended to the user when the current task would benefit from them.
Phrase recommendations as: "This would benefit from `/skill-name`; it provides [specific value]."

## /consult
Parallel multi-specialist analysis run from the main conversation (the orchestrator dispatches 2+ specialist agents simultaneously; subagents cannot fork further). Deduplicates findings, resolves conflicts, and returns a unified report.
**Recommend when**: Code review findings span multiple domains (security + style + structure), large-task AGENT REVIEW pass needs parallel specialist depth, or findings need cross-specialist deduplication and conflict resolution in one report.
**Not for**: Single-domain questions that one specialist can answer.

## /test-forge
Behavioral test generation with iterative quality review. Runs `test-generator`, then `test-quality-reviewer` in a feedback loop.
**Recommend when**: A module needs tests written, especially when the risk of generating framework-testing or mock-saturated tests is high.
**Not for**: Reviewing existing tests only (use `test-quality-reviewer` agent directly).

## /bead-forge
Crafts well-bounded beads (work items) from feature descriptions. Front-loads refinement so beads are ready in 1-2 rounds.
**Recommend when**: Creating beads with design decisions, unclear scope, or multi-bead breakdown. Use checkpoint mode to preserve accumulated context before compaction.
**Not for**: Lightweight well-understood items (use `bd create`).

## /refine
Interactive prompt refinement with full conversation and codebase context.
**Recommend when**: The user has a rough idea and wants it shaped into a precise, actionable prompt.
**Not for**: Prompts that are already clear.

## /challenge
Assumption-challenging for plans, designs, and decisions. Extracts unstated assumptions, scores by fragility, stress-tests against codebase evidence.
**Recommend when**: A plan has been produced and needs assumption validation. Embeds automatically in bead-forge (Phase 2.5).
**Not for**: Code review (use /consult). Prompt refinement (use /refine).

## /synthesize
Combine N disparate inputs into structured, handoff-ready output. Pure synthesis: no opinions, no recommendations.
**Recommend when**: Multiple sources need to be merged into one artifact (review prep, decision documentation, checkpoint).
**Not for**: Trade-off analysis (use /challenge). Multi-specialist review (use /consult). Bead creation (use /bead-forge).

## /converge
End-to-end planning pipeline that chains refine, forge, challenge, consult, and synthesize into one invocation. Output is a converged, stress-tested PLAN (no code).
**Recommend when**: Rough idea or feature needs production-quality plan; medium-to-large features with assumptions to challenge and multiple specialists to weigh in.
**Not for**: Well-scoped tickets ready for hands-off implementation (use /launch). Reviewing existing plans (use /challenge). Code review (use /pr-intel or /consult).

## /launch
Execution launcher: takes a Jira ticket or bead, enriches context, converges on a plan, then dispatches an agent team in a shared worktree to BUILD it; produces real commits and a draft PR. Distinct from /converge: launch writes code; converge writes a plan.
**Recommend when**: Ticket is well-scoped and you want hands-off implementation. Multiple invocations run in parallel via worktrees.
**Not for**: Ambiguous scope (use /converge first). Single-file mechanical changes (direct edit per routing rule 7 carve-out; mx2-executor only for a fully-specified few-file change outside a PR iteration).

## /autopilot
Autonomous pipeline: converge on a plan or build a feature without human approval gates. Uses mx2-decision-maker as quality gate at each checkpoint. Modes: plan (converge only, output = beads) or build (converge + launch, output = draft PR).
**Recommend when**: User wants to kick off work and walk away; lower-stakes work where decision-maker calibration is sufficient.
**Not for**: High-stakes architectural decisions (use /converge with explicit signoff).

## /pr-intel
PR intelligence briefing for human reviewers. Gathers full PR context and produces a structured briefing with summary, scope, risk analysis, test coverage, open threads, and a readiness verdict. Three modes: reviewing others' PRs (default), self-review (`--mine`), and quick triage (`--quick`: one-shot, no specialist dispatch).
**Recommend when**: About to review a PR and want context + analysis to inform critical opinion. Also for self-review before publishing.
**Not for**: Automated code review that posts to GitHub. Author-facing specialist review swarm (use `pr-review-toolkit:review-pr`).

## /post-review
Takes /pr-intel output from conversation context and posts it as an atomic GitHub review with inline comments.
**Recommend when**: After /pr-intel run, user indicates readiness to post.
**Not for**: Drafting reviews from scratch (use /pr-intel first).

## /babysit-pr
Autonomous polling loop for an open draft PR. Classifies incoming review comments (bot vs human, mechanical vs substantive), auto-remediates mechanical bot suggestions via a pre-staged worktree with force-push, replies inline, and escalates human reviewer feedback. State persists in a tracking bead so the loop survives compaction.
**Recommend when**: Operator opens a draft PR, expects bot feedback (Copilot, PR Metrics, Vercel, Lighthouse, SonarQube, etc.), and wants to step away while bot noise gets handled hands-off.
**Not for**: Foreign-authored PRs (skill amends; requires authorship). Published (non-draft) PRs without `--allow-published` (auto-merge mid-loop risk). Operators who want every finding adjudicated (use /pr-intel on a cadence instead).

## /overwatch
Standing work-queue watcher: a self-paced ScheduleWakeup loop that watches the user's beads, GitHub PRs, and Jira on a backing-off cadence (15 -> 30 -> 60 min) and surfaces only time-sensitive DELTAS (a bead newly unblocked, a new review request, an in-progress item going stale). Read-only and surfacing-only; quiet on a healthy no-op cycle. State persists in a tracking bead's notes so it survives compaction. Chat-only output for v1.
**Recommend when**: The user is heads-down and wants to be told when something newly needs their attention across beads/PRs/Jira without polling by hand ("watch my work queue", "what should I pick up next" as a standing request).
**Not for**: Watching one specific PR and acting on it (use /babysit-pr, which mutates); a backward-looking one-shot summary of past work (use /standup-prep); a single current-state check (use `bd ready` / `gh search prs` directly).

## /enrich
Context loader for Jira tickets, beads, PRs, or topics. Gathers ticket details, related beads, codebase references, and domain knowledge into a structured briefing.
**Recommend when**: User asks about a ticket, wants context before /challenge or /consult, needs briefing for meeting prep, or pastes a Jira ID/bead ID without other instructions.
**Not for**: Producing plans (use /converge). Producing beads (use /bead-forge).

## /investigate
Structured investigation of production errors. Traces call path backward, checks git history for the introducing PR, looks for in-flight fixes, estimates blast radius. Surfaces contributing factors and a leading hypothesis (does not assert a single "root cause"). Investigation only (no fixes).
**Recommend when**: Investigating production error, Lambda failure, unexpected behavior, silent regression, or when error message/stack trace is pasted in.
**Not for**: Fix planning (use /bead-forge after the investigation). Multi-specialist review (use /consult).

## /reflect
Invoked when a user correction matches a prior correction in beads memory (two-strike pattern). Reads the target artifact, checks for existing coverage, proposes a single targeted edit. Handled by behavioral trigger in CLAUDE.md.
**Recommend when**: Do NOT invoke directly; the trigger handles it.
**Not for**: First-time corrections (save as bd memory and continue).

## /handoff
End-of-session two-phase ritual: audits personal configs (CLAUDE.md, hooks, agents, skills, memory files) against the session's learnings, then produces a copy-paste-ready cold-start handoff prompt for the next session.
**Recommend when**: Session is winding down on a substantive topic; user asks for a "handoff prompt", "cold-start prompt", or "what to tell the next session"; user pastes a long audit-style prompt asking to review configs against session learnings.
**Not for**: Mid-session prompt refinement (use /refine). Bead checkpointing (use /bead-forge in checkpoint mode).

## /audit-worktrees
Audit and clean up stale agent/autopilot worktree branches in `/workspaces/main`. Identifies orphaned launch agents, merged-and-shipped branches, and other-authored /pr-intel staging areas. Confirms before any deletion.
**Recommend when**: Worktree count grows past comfort threshold; user mentions "stale branches" or "clean up worktrees"; periodic cleanup after heavy /launch or /autopilot use.
**Not for**: Cleaning up main-checkout state (use git directly). Removing in-flight agent worktrees (the skill protects those by design).

## /calibrate
Review and merge calibration drift entries that subagents have emitted via beads memory. Reads `bd memories calibration:<agent>:*`, presents each entry alongside the current calibration file state, lets the user keep/merge/reject per entry, and writes accepted merges to the agent's calibration file.
**Recommend when**: SessionStart hook nudges about unmerged entries; periodic review of accumulated drift.
**Not for**: Authoring calibration files from scratch (write directly). Tuning agent behavior in-session (edit the agent file).

## /snapshot-system-prompt
Capture the current Claude Code system prompt's behavioral sections to a versioned snapshot file, then diff against the prior snapshot to surface drift.
**Recommend when**: The version-drift SessionStart hook nudges that the current Claude Code version no longer matches the latest snapshot; proactively after a new Claude Code version is installed.
**Not for**: Capturing project rules or memory files (those live in git and `~/.claude/projects/`).

## /codility-review
Two-pass evaluator for Codility Legal Document Management API submissions: authorship authenticity gate, then level calibration. Produces a scored Pass 1 read, a level recommendation if Pass 1 cleared, and an optional draft recruiter reply.
**Recommend when**: User pastes a Codility submission (timeline + Cody transcript + code) or asks to review a candidate assessment.
**Not for**: Non-Codility code review (use /pr-intel or mx2-code-reviewer). Interview-loop debriefs (no rubric defined here).

## /ideate
Divergent approach generation: produces 3-5 ranked candidate approaches with a mandatory skeptic pass and a decision-maker gate, then hands the winner to /converge.
**Recommend when**: A problem has 3+ plausible mechanism shapes and no clear winner yet ("what are my options for X", "tradeoffs between X and Y").
**Not for**: One obvious approach (go straight to /converge); stress-testing a single existing plan (/challenge).

## /review
Local self-review fan-out for uncommitted or branch-relative changes: dispatches up to thirteen review agents in parallel, deduplicates, and presents a grouped severity report. Read-only, local-only, no GitHub posting.
**Recommend when**: Before opening or pushing a PR; "review my changes / this branch / self-review".
**Not for**: Reviewing someone else's PR (use /pr-intel); posting comments to GitHub (use /post-review).

## /compound
Improvement loop: scans a just-completed work unit for friction signals and builds the concrete improvement (with a present-and-confirm gate), falling back to habit-memory capture when none exists.
**Recommend when**: After a PR merges, a /launch ships, a bead closes, or a substantial work unit wraps ("what did we learn from that", "capture this workflow").
**Not for**: A cold-start prompt for the next session (use /handoff); a single fact (use bd remember).

## /recall
BFS-first cross-corpus search over beads, memories, and topic files for information another session produced.
**Recommend when**: The user references past work without a current-session referent ("what we discussed about X", "remind me about Y", vague pronouns after a session gap); a SESSION HANDOFF prompt is pasted at cold start (run with its seed line, or derive seeds from its CONTEXT section).
**Not for**: Information already in the current conversation; live external-system lookups.

## /capture-transcript
Ingest a pasted meeting/standup/1:1 transcript and route it: a scannable action breakdown for a standup, or a durable memory file + recall bead + index row for a sync/1:1.
**Recommend when**: The user pastes a transcript with capture intent ("capture this standup", "capture this 1:1", "here is the transcript").
**Not for**: Generating an outbound standup from your own activity (use /standup-prep); a cold-start prompt (use /handoff).

## /standup-prep
Generate your OWN spoken-standup talk-track from your engineering activity (git, PRs authored + reviewed, PR/issue comments, Jira, Confluence, beads, plus a Slack sweep for unanswered asks), binned by your local timezone. Outbound status generation, not transcript capture.
**Recommend when**: "prep my standup", "verbal standup", "what did I do yesterday/Friday", "what did I ship"; a bare "help me with standup" when recent context is code/PR/Jira work.
**Not for**: Capturing a pasted transcript of a meeting that already happened (use /capture-transcript); a Slack-only message built from just your Slack activity (use the slack plugin /standup).

---

## Skill Catalog Discipline

When new skills are added to `~/.claude/skills/`, this catalog must be updated. The catalog is loaded into agents that need escalation awareness; missing entries cause silent under-recommendation. To verify completeness:

```bash
# Skills that should appear in this catalog: user-invokable personal skills
EXPECTED=$(grep -L 'user-invokable: false' ~/.claude/skills/*/SKILL.md | wc -l)
ACTUAL=$(grep -c '^## /' ~/.claude/skills/skill-catalog/SKILL.md)
echo "expected $EXPECTED, catalog has $ACTUAL"
```

Skills with `user-invokable: false` (e.g., `skill-catalog` itself) are intentionally absent.
