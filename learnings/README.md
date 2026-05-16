# learnings/

The AI Learning Track corpus. Originally authored as an internal Confluence series on Claude Code adoption; migrated here with editorial scrubbing applied (real teammate names, internal Jira IDs, internal Confluence URLs, and org-specific examples removed or anonymized).

## Status

V1. 11 of the original 12 pages lifted. The 12th page (PM-focused workflows) is deferred pending broader-audience editorial rewriting; an audience note in `workflows-developers.md` flags the deferral.

## Reading order

The corpus has a natural reading order. New readers start at `first-week.md` and continue based on intent.

| Page | Track | Read when |
|---|---|---|
| [first-week.md](./first-week.md) | Foundation | You've never used an AI coding tool, or tried once and stopped |
| [ai-coding-tools.md](./ai-coding-tools.md) | Parent / Insights | You've had a few productive AI sessions and want to level up |
| [spotting-failure-patterns.md](./spotting-failure-patterns.md) | Sharpen | You want to recognize the six AI failure modes at authoring time |
| [build-context-engine.md](./build-context-engine.md) | Sharpen | You're turning review findings into rules that catch the same failure next time |
| [teaching-ai-to-remember.md](./teaching-ai-to-remember.md) | Sharpen | Your AI keeps forgetting your conventions across sessions |
| [ai-assisted-debugging.md](./ai-assisted-debugging.md) | Sharpen | You're stuck on a bug and the AI keeps guessing |
| [workflows-developers.md](./workflows-developers.md) | Apply | Concrete prompts for the four stages of a real dev workflow |
| [personalize-claude.md](./personalize-claude.md) | Build (side-door) | You have strong opinions about how Claude should behave for you |
| [build-first-skill.md](./build-first-skill.md) | Build | You want to build your own reusable workflow as a skill or command |
| [skills-at-scale.md](./skills-at-scale.md) | Build (advanced) | You've shipped a skill and want the next-level patterns |
| [agent-design-lessons.md](./agent-design-lessons.md) | Build (philosophy) | Pairs with skills-at-scale; the "why agents are designed this way" angle |

## Scrubbing applied during the lift

Mechanical scrubs:

- Internal GitHub org name in code blocks
- The team's Atlassian cloud ID and personal Confluence space ID
- The internal monorepo workspace path
- All cross-page Confluence URLs rewritten to local relative paths

Editorial scrubs:

- Real teammate first names replaced with "a human reviewer" / "a teammate"
- Internal Jira ticket IDs generally removed
- PR numbers kept as authentic anchors (so readers see "this came from a real codebase"), with each one's failure mode and rule described inline so the lesson lands without access to the codebase
- Org-specific examples (firm name, office names, internal tool names) genericized
- Internal service paths replaced with descriptive shapes (e.g., "a complex document indexing pipeline" instead of the internal name)

The MX2 codebase vocabulary itself stays in places where it appears as authentic flavor (per the harness's privacy boundary decision); it tells readers "this came from a real codebase" without identifying which.

## Editorial decisions made during the lift

Four decisions were ratified by the author before this lift:

1. **PR-anchor pattern**: keep PR numbers (#8585, #8140, #8517) as concrete anchors, paired with inline descriptions of the failure mode each one teaches. The numbers say "this came from a real codebase"; the descriptions deliver the lesson without requiring access.
2. **First-week ramp worked example** in `build-first-skill.md`: keep the worked example structure (the `/enrich` origin story), describe the underlying pipeline's shape without naming it. The case study is load-bearing because it's the first instance where cross-session memory scaffolding became the operative capability.
3. **Mature setup appendix** in `teaching-ai-to-remember.md`: rewritten generic. The MX2-Specific framing is dropped; the SSO bootstrap and S3 bucket pattern descriptions stay (shape, not precise identifiers) because they document a real concrete implementation an adopter can model.
4. **PM Workflows page**: deferred. The original is heavily org-specific (firm name, office names, internal tools, an internal Jira ticket as a worked example) and the audience differs from the rest of the corpus (PMs vs. engineers). When it returns, it returns as a fresh audience-broad write rather than a heavy edit. The framing matters because broader-audience teaching is itself a portfolio claim.

## Page format

The corpus uses a consistent format across all pages:

- Header callout block with "Where this fits", "Format", "Output" / "Prereq", and "If you only have 5 minutes"
- Numbered top-level sections
- "Try This Today" callouts for exercises during real work
- A closing "Where to Go Next" section with relative links to siblings
- Bidirectional navigation: every page links back to the parent (`ai-coding-tools.md`) and to its peers

A separate format spec is not provided; the consistent structure across the 11 pages serves as the spec.
