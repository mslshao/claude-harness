# Agent Tiers

The harness organizes agents into three tiers. Each tier has different storage location, intended use, and degree of personal vs team customization.

## User tier (personal)

Location: `~/.claude/agents/`

Personal specialists for code quality, security, style, error detection, and thinking partnership. First choice for review tasks. Edited freely by the author, no review gate. Sharper, opinionated, sometimes idiosyncratic.

Mirrored in this repo at `dotclaude/agents/` (scrubbed of third-party names).

## Project tier (team)

Location: `<repo>/.claude/agents/`

Team-owned, codebase-specific. Reviewed by teammates, shipped via PR. Smoother, less opinionated, designed for collective maintenance.

Mirrored in this repo at `project-tier/agents/` (selected promotions).

## Plugin tier (toolkit)

Plugin-provided agents (`<plugin-name>:agent-name`). These come from packaged toolkits that install at the user or project level.

Examples in common use: PR review toolkits, beads task-management, skill creation toolkits, slack integration.

Plugin-tier agents are not customized by the author; they ship with the plugin and update when the plugin updates. The harness uses them but does not modify them.

## Lab-to-production for personal and project pairs

Personal tier is the testing ground; project tier is the vetted, scrubbed-of-personal-context production version. Promotion is unidirectional: personal-leads-project, scrubbed and shipped via PR.

Divergence between a personal artifact and its project sibling is intentional, not drift. Audits MUST NOT flag personal-vs-project content differences as duplication.

Distinct from project rule duplication: rule duplication in a personal agent (where the personal agent re-states a project rule that is already loaded into every session) IS still bloat to trim.

## Name-overlap convention for promoted artifacts

When promoting a personal-tier agent or skill that should also exist at project tier, keep the `name:` frontmatter field identical between the two so personal takes resolution precedence. The richer and more recent personal version is what runs locally; the project version is what other engineers get.

Before merging any personal-to-project promotion PR, audit the new project-tier file for references to agents that exist only at personal tier; replace with role-neutral phrasings ("out of scope", "route to <project-tier-agent>") rather than introducing broken references.

## The model-tier gate (empirically validated)

Each agent is pinned to a model tier by a deterministic gate, not by feel:

- **Haiku** iff the work is a bounded transform or extraction, the hard parts are pinned by deterministic contracts, blast radius is low, and there is no flag-vs-route or attribution judgment.
- **Opus** iff the work is multi-source synthesis across conflicting inputs, OR a high-blast autonomous gate.
- **Sonnet** otherwise.

Corollary: a stronger model does not move tiers. Judgment-vs-mechanical and blast-radius are model-independent axes; upgrading the model does not turn a judgment task into a mechanical one.

A 27-agent audit applied this gate and returned zero tier changes. The two most-mechanical-looking Sonnet agents (a provenance-classifier and a pydantic-settings reviewer) were kept on Sonnet via an untested prediction: "Haiku would miscalibrate." That prediction was then probed empirically (bead docr-k0g4), running worry-case inputs through Haiku-4.5 vs Sonnet-4.6:

- Provenance-classifier: 5/6 parity, but diverged on the safe-asymmetry default (Haiku was wrong AND overconfident).
- Pydantic-settings reviewer: 4/5 parity, but Haiku false-positived on a correctly-required no-default field.

Verdict: keep both on Sonnet, now evidence-backed rather than asserted. See `evidence/2026-06-04-agent-tier-eval.md`.

## Why this exists

The two-tier model decouples personal experimentation from team adoption. Personal tier lets the author iterate freely without team-review smoothing. Project tier propagates proven patterns to the team without forcing the author to suspend iteration during promotion review.

The plugin tier exists separately because plugins are ecosystem artifacts; the author neither owns them nor wants to fork them. The boundary is "code I write" (user + project) vs "code I install" (plugin).

## Where it has limits

- The two-tier model scales for "each engineer curates their own personal tier"; it does not scale for "the team standardizes on one canonical personal tier."
- Plugin tier opacity (the author cannot easily customize plugin agents) means some friction when a plugin's agent does not quite fit. Either fork the plugin or layer a personal-tier wrapper.
