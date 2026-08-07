# project-tier/

Promoted artifacts: components that started in the personal-tier sandbox (`dotclaude/`), proved themselves through real use, were scrubbed of personal preference, and shipped to a team's project-tier configuration via PR.

This directory documents the promotion path itself. The lab-to-production pattern is a deliberate choice: personal-tier artifacts can be sharper than team-tier artifacts because they are not under team-review smoothing pressure. The promotion exposes the right subset to the team while keeping the experimental edge in personal tier.

## How membership was decided

17 artifacts: 6 agents, 4 skills, 7 rules. All re-synced against the live project tier on 2026-08-07.

Membership is not a curated highlight reel. It was decided mechanically, by first-commit authorship across the entire live `.claude/` tree: an artifact is mirrored here if its first commit is the repo author's, and is not if another engineer wrote it first. The live tier is a shared team surface, most of it is other people's work, and that part is deliberately absent rather than overlooked.

The scan is also why the set went from 7 to 17 in a single pass. The earlier 7 were assembled from memory rather than from a scan, which is precisely the job a scan does better.

## Contents

Every row below landed in the team's `.claude/` through a team-reviewed PR. The version checked in here is the project-tier version, with the substitutions listed further down applied.

| Path | What it does | This pass |
|---|---|---|
| `agents/module-cohesion-reviewer.md` | Cross-file cohesion and coupling: which concern owns a module, name-vs-contents drift, production vs test-only helper separation, cross-service reach-in past a published boundary | added |
| `agents/mx2-security-auditor.md` | PII/PHI exposure (field types, log calls, LLM data flows) and audit-trail field completeness on existing log calls | added |
| `agents/mx2-skeptic.md` | Adversarial advisor: surfaces unstated assumptions and risks in plans and designs before a high-blast-radius call. Advisory, never blocks | added |
| `agents/observability-reviewer.md` | Instrumentation gaps in diffs: exception renames that break Datadog Error Tracking monitors keyed on `@error.type:`, error paths with no paired metric, trace context lost across SNS/SQS/EventBridge | re-synced |
| `agents/silent-failure-hunter.md` | Errors caught but not surfaced, especially where a Python error becomes a JSON response that TypeScript silently drops | re-synced |
| `agents/test-quality-reviewer.md` | Tests reviewed for behavioral meaningfulness: framework-mechanic testing, mock saturation, names that do not match what is asserted | re-synced |
| `skills/enrich/` | Context loader for a Jira ticket, PR, or topic: one structured briefing from Jira, git, AWS, and Datadog, with per-source bounds | re-synced |
| `skills/ideate/` | Divergent approach generation: 3-5 ranked approaches with a skeptic pass, stopping at presentation so the human picks the winner | added |
| `skills/investigate/` | Production-error investigation: trace backward through call path, git history, deploy state, Datadog signals. Contributing factors only, no fix proposals | re-synced |
| `skills/review/` | Local self-review fan-out to the project review agents, deduplicated into one grouped severity report. Read-only, posts nothing | re-synced |
| `rules/debugging.md` | No fixes without root cause: the process, the three-attempt circuit breaker, boundary instrumentation before theories | added |
| `rules/exemplars.md` | Pairs a ratified design decision with the canonical file to copy from and a one-line reason (auth, operational store, API scaffolding, configuration, module split) | added |
| `rules/pr-size-discipline.md` | The rules-tier exhibit, and the only entry with no live counterpart. See below | re-synced |
| `rules/python-testing.md` | Testing tenets, the mock policy (`unittest.mock` banned, fake at the infrastructure boundary), and test configuration | added |
| `rules/tenets.md` | Meta-rules for rule-vs-precedent conflicts: best practice over precedent, review in isolation, single-concern execution, verify before asserting | added |
| `rules/typescript-exploration.md` | Cross-stack guide for Python engineers reviewing or editing TypeScript: package tiers and import direction, conventions, gotchas | added |
| `rules/verification.md` | The completion gate, plus the taxonomy separating the "verify" instructions that are ceremony (self-recheck) from the load-bearing ones (external-oracle, cross-boundary) | added |

## Drift is what a mirror costs

All 7 previously mirrored artifacts had drifted from their live counterparts by this pass, and the drift was not cosmetic.

The clearest case is `agents/silent-failure-hunter.md`. The copy published here described an `MX2Error -> DocumentError -> DocumentNotFoundError` exception hierarchy and told the reader that all `MX2Error` subclasses map to specific HTTP status codes. The live version had since been corrected: there is no shared `MX2Error` base class, each service defines its own exceptions in a local `exceptions.py` or `errors.py`, and the real smell is a service-local exception that was never registered with the builder. The team found the original claim wrong and fixed it in place. This mirror went on publishing it.

That is worth naming plainly, because it is the standing hazard of this directory rather than a one-off mistake. A mirror is a snapshot, and a snapshot of a living artifact does not merely go out of date: it silently becomes a false statement about the codebase it describes, carrying exactly as much authority as the correct version did. An agent definition is the worst case, because a model loads it as fact and reasons downstream from it.

`skills/review/` drifted the same way in a different direction. The published copy described a four-agent fan-out; the live skill dispatches six. The two it gained, `mx2-security-auditor` and `module-cohesion-reviewer`, are themselves new entries in this directory, so the stale artifact and the incomplete membership set were one failure showing up twice.

The mitigation is to re-sync every artifact on each harness sync pass and to diff rather than assume, which is what this pass did. Nothing enforces it. `sync/scrub-check.sh` scans for leaked identifiers, not for staleness, and a real drift detector would have to run somewhere that has both this repo and the private monorepo checked out, which is not CI. If a future sync pass skips the diff, the mirror goes quietly stale again and nothing fails.

## The rules entries

An earlier version of this README argued that only one rule belonged here, on the grounds that the lab-to-production story reads most legibly at the component level. That was a rationalization of an incomplete sync. The authorship scan found seven author-written rules in the live tier and no principled reason to publish one and withhold six.

Two things are true of the rules that are not true of the agents and skills:

- **There is no personal-tier `rules/` directory to promote from.** The personal tier's analogue of a rule file is a section of `dotclaude/CLAUDE.md`, so promotion is a rewrite into the team's rule corpus rather than a file copy. "Promoted" for these seven means authored by this author and adopted as a team default through review, not necessarily personal-tier-first.
- **`rules/pr-size-discipline.md` has no live counterpart, on two counts.** It is no longer a standalone rule file (it is now a section of the team's `code-style.md`), and it kept evolving after promotion: the team deleted the ~250-line threshold outright rather than keeping it and qualifying it. That file's own preamble tells the three-stage story in full, including why the third stage is the interesting one, so it is told there and not repeated here. It cross-references `evidence/2026-06-11-rules-as-executable-specs.md` and `patterns/contrapositive-proof.md`; the three together form one exhibit across three layers.

## The personal version usually still exists

For most artifacts here, the personal-tier `dotclaude/` mirror in this repo holds the divergent personal version. The same `name:` frontmatter is used at both tiers (per the harness's name-overlap convention), so when both are installed, personal takes precedence.

The divergence is intentional, not drift. The personal versions carry author-specific calibration the team has not committed to: personal `/review` fans out to thirteen agents instead of six, personal `/enrich` and `/investigate` are beads-aware where the project versions route to a ticket or an SME, personal `/ideate` adds a decision-maker iterate gate. Each of those deltas is stated in the first line of the personal artifact's description, so the precedence and the difference are legible at retrieval time. When a personal-tier change has earned its keep across enough real sessions and survived team review, it lifts to project tier.

Two exceptions in the current set:

- `silent-failure-hunter` has a personal counterpart under a different name (`mx2-silent-failure-hunter`). The names do not overlap, so neither shadows the other and both are separately dispatchable.
- The seven rules have no personal counterpart at all, for the reason in the section above.

## Genericization applied during the lift to this public mirror

The live artifacts name internal systems. Those identifiers were substituted on the way here. What was actually applied to the files in this directory:

| Live value | Published as |
|---|---|
| The employer's name and its abbreviation, including in the Atlassian tenant hostname | `<company>`, `<company>.atlassian.net` |
| The Atlassian cloud ID (a UUID, in `skills/enrich/sources.md`) | `<atlassian-cloud-id>` |
| One internal service name, in Datadog service-tag and module-path examples | `<service>` |
| Specific Jira ticket numbers (three ESLint rule references, one campaign reference) | `MX2-NNNNN` |
| Em-dashes in one copied rule (`rules/typescript-exploration.md`) | Hyphens, to match this repo's writing convention |

Two substitution classes from the repo-wide scrub convention matched nothing in this directory: the workspace-path rewrite (`/workspaces/<repo>` becomes `/workspaces/main`) and the replacement of real teammate names with role-neutral phrasing. No mirrored artifact here contains a workspace path or a coworker's name.

Confluence page IDs were the one open judgment call this pass had to settle. `sync/SCRUB-SPEC.md` puts them under reviewer judgment rather than under an enforced detector pattern, so `scrub-check.sh` passes clean either way, and the repo had drifted into holding both answers at once: an earlier pass dropped one such link and said so in a parenthetical, while seven others survived across `dotclaude/` and here. This pass removed them all. The reasoning is that the reference had already lost its value before the question was asked: the tenant hostname is a placeholder, so the URL resolves nowhere for a public reader, and the page would return 403 for a non-member even if it did. Keeping the space key and page ID bought a reader nothing and disclosed two internal identifiers. Each reference now names the document and marks it as internal Confluence, which is the part a reader can actually use.

The substitutions preserve each artifact's structural shape, so an adopter can swap in their own identifiers and run it, without exposing the original team's tracking surface.
