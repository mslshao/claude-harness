# learnings/

The AI Learning Track corpus. Originally authored as a Confluence series for team-internal knowledge sharing on Claude Code adoption. Generic content (not company-specific); migrated here for public access.

## Status

V0 placeholder. The full 12-page corpus was enumerated during a V1 prep session (2026-05-16). The sanity-check pass found that NO page is a clean lift-as-is candidate: every page needs at least URL rewriting (cross-page Confluence links), and several have editorial scrub items (real teammate names, internal Jira ticket IDs, org-specific examples). The per-page recommendation table lives in the author's session scratch and is pending review.

After review, the migration order will be (easiest first, to land cross-references cleanly):

1. Agent Design Lessons (cleanest, philosophy fit)
2. AI-Assisted Debugging
3. Personalize Claude
4. Your First Week
5. Build Your Context Engine
6. Spotting AI Failure Patterns (anonymize teammate)
7. AI Coding Tools (parent, lifts LAST so sibling cross-links resolve)
8. Building Skills at Scale (anonymize teammate)
9. Build Your First Skill (genericize a worked example)
10. Teaching AI to Remember (restructure appendix)
11. AI Workflows for Developers (genericize service paths)
12. AI Workflows for PMs (deferred entirely; heavily org-specific, audience mismatch with rest of corpus)

## Corpus shape (when populated)

The 12 pages divide into four tracks:

| Track | Pages |
|---|---|
| Foundation (one-page on-ramp) | Your First Week |
| Sharpen how you use AI | Spotting AI Failure Patterns, Build Your Context Engine, Teaching AI to Remember, AI-Assisted Debugging |
| Apply AI across your workflow | AI Workflows for Developers (+ deferred AI Workflows for PMs) |
| Build your own AI tools | Personalize Claude, Build Your First Skill, Building Skills at Scale, Agent Design Lessons |
| Parent (insights and patterns) | AI Coding Tools |

## Page format spec

A `page-format-spec.md` capturing the corpus's authoring conventions (header callout block: "Where this fits", "Format", "Output", "If you only have 5 minutes"; the consistent "Where to Go Next" footer; parent-page bidirectional navigation) is planned. The spec is portable harness content beyond just the corpus, and the V1 lift will follow it for each lifted page so the corpus reads consistently.

## What lifts cleanly vs what needs editorial work

Mechanical scrubs (caught by `sync/scrub-check.sh`):

- Real GitHub org name in code blocks
- The Atlassian cloud ID and personal Confluence space ID
- The internal `/workspaces/main` path

Editorial scrubs (NOT caught by scrub-check; require human pass):

- Real teammate first names (the engineering lead, a teammate) used in worked examples
- Internal Jira ticket references (MX2-NNNNN) used as anchor examples
- Internal Confluence cross-page URLs (about 80 across the corpus)
- Org-specific terms (Litify, Jacksonville, LibreChat incident) in the PM-focused page
- Internal service paths (`src/python/mx2/<service>`, `dec_page/extr`) in code-flow examples

The editorial scrubs are why every page is "lift-with-edits" rather than "lift-as-is."

## Open decisions (deferred to author)

- PR-anchor pattern: keep PR numbers (#8585, #8140, #8517) as concrete anchors or strip and replace with abstracted descriptions? The PRs themselves are not public; the numbers tell readers "this came from a real codebase," not where.
- <service> ramp anonymization in "Build Your First Skill or Command": preserve the worked example with the service name genericized, or replace with a synthesized example that conveys the same lesson?
- Teaching AI to Remember appendix: keep the "What a Mature Setup Looks Like" appendix (marked MX2-Specific with a disclaimer) or rewrite as a generic "what mature setups tend to look like" framing?
- AI Workflows for PMs: defer entirely, or do the editorial work? The audience is fundamentally different from the rest of the corpus.
