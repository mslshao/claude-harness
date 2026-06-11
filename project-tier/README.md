# project-tier/

Promoted artifacts: components that started in the personal-tier sandbox (`dotclaude/`), proved themselves through real use, were scrubbed of personal preference, and shipped to a team's project-tier configuration via PR.

This directory documents the promotion path itself. The lab-to-production pattern is a deliberate choice: personal-tier artifacts can be sharper than team-tier artifacts because they are not under team-review smoothing pressure. The promotion exposes the right subset to the team while keeping the experimental edge in personal tier.

## Contents

The artifacts below were each promoted from personal-tier (`~/.claude/`) to project-tier in a team-reviewed PR. The version checked in here is the project-tier version: scrubbed of personal preference, reviewed by teammates, and adopted as a team default.

| Path | Promoted via | What it does |
|---|---|---|
| `agents/observability-reviewer.md` | Team-reviewed PR | Specialist that detects Datadog/CloudWatch instrumentation gaps in PR diffs |
| `agents/test-quality-reviewer.md` | Team-reviewed PR | Specialist that reviews tests for meaningful behavioral coverage (not framework-mechanic theater) |
| `agents/silent-failure-hunter.md` | Team-reviewed PR | Specialist that finds errors caught but not surfaced, especially at the Python-TypeScript boundary |
| `skills/enrich/` | Team-reviewed PR | Context loader for Jira tickets, PRs, or topics; structured briefing from multiple sources |
| `skills/investigate/` | Team-reviewed PR | Structured production-error investigation; trace backward through call path, AWS state, Datadog signals |
| `skills/review/` | Team-reviewed PR | Local self-review fan-out to project review agents; grouped severity report before push |
| `rules/pr-size-discipline.md` | Team-reviewed PR | Promoted RULE: one-concern-per-PR stated unconditionally, the ~250-line size as a one-way trigger (the lab-to-production pattern applied to a `.claude/rules/` rule, not a component) |

## The personal version still exists

For each project-tier artifact, the personal-tier `dotclaude/` mirror in this repo holds the divergent personal version. The same `name:` frontmatter is used at both tiers (per the harness's name-overlap convention), so when both exist on a developer's machine, personal takes precedence.

The divergence is intentional, not drift. The personal versions can carry author-specific calibration (the `mx2-tech-lead` feedback-reception mode, the `/launch` cold-start resume protocol, etc.) that the team has not yet committed to. When a personal-tier change has earned its keep across enough real sessions and survived team review, it lifts to project tier.

## Scrubbing applied during the lift to this public mirror

The project-tier versions in the live repo reference internal Atlassian/GitHub URLs, the team's Cloud ID, and the team's GitHub org. Those identifiers were genericized when copied here:

- `cloudId: <real-uuid>` becomes `cloudId: <your-atlassian-cloud-id>`
- `gh api /repos/<org>/<repo>/...` references use placeholders
- A Confluence link to the team's tenets page is documented but not linked

The genericization preserves the artifact's structural shape (so an adopter can swap in their own identifiers and run) without exposing the original team's tracking surface.

## A note on the one rules-tier exhibit

Most project-tier rules from `.claude/rules/` (testing tenets, code-style, verification discipline) originated in personal-tier and earned team adoption. They are NOT mirrored here as separate files; they are referenced from the personal-tier `dotclaude/CLAUDE.md` and the harness's pattern docs in `patterns/`, because the lab-to-production demonstration is most legible at the component level (agent, skill).

The single exception is `rules/pr-size-discipline.md`. It is included because its promotion path is exceptionally legible: the rule was restructured in response to a literal-reading model taking the contrapositive of a nested principle, and the restructure (state the principle unconditionally, mark the threshold one-way) is itself the lesson. The rule, the evidence entry (`evidence/2026-06-11-rules-as-executable-specs.md`), and the generalized pattern (`patterns/contrapositive-proof.md`) form one exhibit across three layers. The broader rules-promotion path stays documented in `patterns/lab-to-production.md`.
