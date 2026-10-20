# graveyard/

Perma-deleted components and what superseded them.

## The Keymaker principle

> Components in this harness exist for a specific purpose. When the purpose is superseded (by a more specific child or a more generic parent), the component is deleted, not archived. The harness carries no legacy maintenance burden.

The name is borrowed from the Matrix Reloaded character whose role was so narrow that, once his purpose was fulfilled, he was scheduled for deletion. The discipline cuts the same way: build for a need, retire when the need is met by something else, do not keep the artifact around "just in case."

## Reconstruction caveat

Personal-tier `~/.claude/` is not git-versioned by default, so perma-deleted personal-tier files are unrecoverable in a strict sense. Entries below are reconstructed from author recall plus project-tier git history. Reconstructed entries (memory-only) are marked `**Source: recall**`; entries with documented history (project-tier removals visible in git log) are marked `**Source: git log**`.

## Files

| File | Source | Superseded by |
|---|---|---|
| `agentcore.md` | recall | dispatch heuristic + tech-lead agent |
| `medical-legal-specialist.md` | recall | mx2-security-auditor + per-domain context |
| `project-tier-best-practices-rule.md` | git log | restructured into separate scoped rules (tenets, code-style, debugging, verification) |
| `project-tier-project-context-rule.md` | git log | absorbed into hierarchical CLAUDE.md restructure |
| `mx2-tenth-man.md` | repo history | renamed/reframed to `mx2-skeptic` (capability intact; the obscure name was the liability) |

Note: `mx2-tenth-man.md` is the one entry here that is a RENAME, not a deletion. The agent still exists as `mx2-skeptic`; the entry records why the name was retired (a retrieval-surface label that needed decoding before it meant anything). It is kept in the graveyard because the reasoning generalizes, even though the Keymaker "build for a need, retire when superseded" framing is usually about deletion.

## Pattern observation

Project-tier `.claude/` has been mostly additive over its history (only the two rule deletions above; no agent or skill deletions). This is a working signal: the lab-to-production discipline filters artifacts before promotion, so promoted artifacts tend to survive. Personal-tier `~/.claude/` is where iteration and deletion happens; project-tier is where stability lives.

The harness's "build for a need, retire when superseded" discipline is therefore primarily a personal-tier discipline. The graveyard captures personal-tier history that the file system did not preserve.

## 2026-10-20: the trim for stronger models

The user asked whether the harness had become too prescriptive for current models. An audit ranked seven cuts, each approved line by line, and the ones that removed text are below. These entries are **Source: snapshot**: every file was copied byte for byte before its edit, so each entry quotes what was removed in full, not from recall. Behaviour rules were deleted only after an A/B replay (`rules-ab.py`, two repeats per arm) showed the draft without the rule doing as well as the live file. Two of seven `CLAUDE.md` candidates failed that test and stayed.

| File | What went | Superseded by |
|---|---|---|
| `2026-10-20/claude-md-L31.md` | Scope a terse team request before assigning | Nothing; the model did it unprompted in the replay |
| `2026-10-20/claude-md-L42.md` | Written-deliverable length | Nothing; same |
| `2026-10-20/claude-md-L55.md` | Don't push complexity onto the user | Nothing; same |
| `2026-10-20/claude-md-L57.md` | Take shapes, not artifacts, from outside tools | Nothing; same |
| `2026-10-20/claude-md-L83.md` | One narration line per real step | Nothing; same |
| `2026-10-20/review-bounded-fanout-twelve.md` | `/review` fanning out to up to twelve agents | Step 4a "Cap the set": three by default, the full set with `--full` |
| `2026-10-20/review-default-fanout-all-true-signals.md` | Every agent with a true signal in the default set | The same step 4a; payments diffs still run their three agents |
| `2026-10-20/compound-failure-ledger-bullet.md` | The failure ledger on every merge | One line: it runs when a failure report is asked for |
| `2026-10-20/compound-codespace-greps.md` | Greps of paths from another machine | The surviving greps over this machine's memory and rules |
| `2026-10-20/worker-md-intro-and-worker-role.md` | The worker protocol's long opening | A 693-word core every fleet seat loads |
| `2026-10-20/worker-md-machine-purpose-and-task-tools.md` | The machine-purpose and task-tools paragraphs | The memory index and the environment rule, which said the same |
| `2026-10-20/worker-md-orchestrator-role-bullet.md` | The orchestrator's duties inside the worker file | The fleet routing skill |
| `2026-10-20/worker-md-registration-section.md` | The check-in section | The `checkin` skill, now its only specification |
| `2026-10-20/worker-md-prep-line-compound-at-250k.md` | A seat compounding itself at the 250k prep line | The SessionEnd queue compounds it after `/clear` (a trial from 2026-10-20) |

Text that only moved between files (dated history to a history file, sections to an on-demand detail file) has no entry. The snapshots themselves stay off this repository, since they include working notes.
