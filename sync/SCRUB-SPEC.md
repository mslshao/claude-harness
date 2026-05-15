# Scrub Specification

This document specifies what gets scrubbed from the repo's public content, and why. `scrub-check.sh` is the CI-style guardrail that enforces these rules.

## Scope

Scrubbing applies to all files in:

- `patterns/`
- `dispatch/`
- `scaffolding/`
- `dotclaude/`
- `project-tier/`
- `graveyard/`
- `evidence/`
- Top-level `README.md`

Not scrubbed (allowed to contain personal context):

- `learnings/` (Confluence corpus was authored as generic content from day one)
- Anything in `.git/`
- `sync/` (this directory; scripts may reference patterns to detect)

## What gets scrubbed

### Tier 1: Always removed (private to third parties)

These are non-negotiable removals. Public artifacts naming real coworkers without their consent is an ethics line. Real names of MX2 teammates that appear in the live `~/.claude/CLAUDE.md` and `memory/` files:

- the engineering lead, a teammate, a team lead, a teammate, a team lead manager, a peer reviewer, a team lead, a solo-team engineer, a teammate, a teammate, a teammate
- Plus any other first-or-last name fragments that resolve to real coworkers

Replacement: role-neutral phrasing (`a peer reviewer`, `a teammate`, `another engineer`) or removed entirely if not load-bearing.

### Tier 2: Specific incident references

These name an employer in a way that ties a specific incident to a specific company. Scrub even when the surrounding context would otherwise read as generic.

- "Anthropic" in contexts that reference the technical enablement role rejection
- Specific Salesforce incidents that name customer firms
- Specific PR review incidents tied to identifiable PR numbers and reviewers

Replacement: anonymize ("a vendor", "a customer firm", "a peer review incident") or remove.

### Tier 3: Bead IDs and internal-tracking references

The harness uses `docr-*` bead IDs throughout `CLAUDE.md` and memory files. These IDs are meaningful only inside the author's beads workspace; they read as opaque references in any public artifact.

- All `docr-[a-z0-9]+` matches
- Specific PR numbers `#NNNN` when they tie to identifiable individuals
- Confluence page IDs (numeric, typically 9-10 digits, appearing in the patterns specific to atlassian.net URLs)
- Specific Jira ticket numbers `MX2-NNNNN`

Replacement: remove, or replace with anonymized placeholders (`a bead`, `a PR`, `a Jira ticket`).

### Tier 4: Proprietary infrastructure detail

MX2 vocabulary is acceptable as authentic flavor (it tells the reader "this was a real codebase, not a hypothetical"). But specific infrastructure detail crosses into proprietary territory.

- Specific AWS resource names (DynamoDB table names, S3 buckets, Lambda function names) when they identify customer-facing or unreleased systems
- Specific Datadog dashboard IDs, monitor IDs, query strings that reveal monitoring topology
- Internal Confluence space IDs (`<confluence-space-id>`, the cloud ID `<atlassian-cloud-id>`)
- Slack channel names that identify private channels

Replacement: keep the principle, remove the identifier ("a Datadog dashboard"; "a private Slack channel").

### Allowed (intentionally not scrubbed)

These stay as authentic context:

- The MX2 codebase name (used as one example among many, not a security boundary)
- Generic Python/AWS/Pants/Terraform terminology
- Class names, design patterns, framework names
- The Claude Code product and feature names
- Other publicly-named products: Datadog, Salesforce, Atlassian, GitHub, Pants, etc.
- The author's own name (Michael Shao) where it identifies authorship

## What does NOT belong in the repo at all

`.gitignore` enforces these at the repo level. They never enter the scrub pipeline because they never get added in the first place:

- The entire `memory/` directory tree (proprietary topic files)
- The entire `scratch/` directory tree
- Anything matching `*_token*`, `*_secret*`, `.env*`, `*.pem`
- Real Confluence page bodies, Jira ticket bodies, Slack thread contents

## Rationale (one paragraph)

The blast radius of a leak from this repo is bounded by what is in it. If proprietary content never enters the repo (because of `.gitignore`), scrubbing is a defense-in-depth measure rather than a primary protection. The Tier 1 and Tier 2 rules above are the load-bearing protections: real names and specific incidents must never appear in a public artifact, even by accident, because the harm there is to third parties who did not consent to being named.
