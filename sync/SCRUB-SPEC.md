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

These are non-negotiable removals. Public artifacts naming real coworkers without their consent is an ethics line. The class covered: real first names, spaced/compound name forms, and GitHub/Slack handles of current or former teammates that appear in the live `~/.claude/CLAUDE.md` and `memory/` files, plus any other name fragment that resolves to a real coworker.

The concrete pattern list is deliberately NOT in this file or anywhere else in the committed repo: a detector must know what it detects, so making the committed repo name-free requires keeping the list out of the commit entirely. The patterns live in the gitignored local file `sync/scrub-names.local` (one extended-regex pattern per line; format documented in its header). That file is the source of truth; extend it as team composition changes. `scrub-check.sh` builds its Tier 1 scan from it and, when the file is absent, loudly disables the Tier 1 scan rather than reporting a false "clean" (Tiers 2-4 still run).

Replacement: role-neutral phrasing (`a peer reviewer`, `a teammate`, `another engineer`) or removed entirely if not load-bearing.

**Operational note: `sync/scrub-names.local` is required, not optional.** Because the file is gitignored, a fresh clone starts without it, and `scrub-check.sh` then runs with the Tier 1 scan disabled. It warns on stderr and qualifies its summary line (`Tiers 2-4 clean ... Tier 1 real-name scan SKIPPED`), but the exit code is still 0. An unattended CI run, or a quick eyeball on the last line of output, reads that as a pass. This has already happened once here: the file was absent across several syncs, so the load-bearing scan never ran and real teammate names sat in the published mirror while every check reported a qualified pass.

Before trusting any scrub-check result on a fresh clone:

1. Recreate `sync/scrub-names.local` (one extended-regex pattern per line; see the format header in an existing copy, or rebuild it from the current team roster).
2. Run `bash sync/scrub-check.sh`.
3. Confirm the summary line is the unqualified form: `scrub-check: clean (N files scanned, 0 findings)`. If it still says `SKIPPED`, the scan that matters did not run and the result means nothing about names.

Prefer over-inclusive patterns. A false positive costs one human look; a false negative publishes a real coworker's name without their consent.

### Tier 2: Specific incident references

These name an employer in a way that ties a specific incident to a specific company. Scrub even when the surrounding context would otherwise read as generic.

- "Anthropic" in contexts that reference the technical enablement role rejection
- Specific Salesforce incidents that name customer firms
- Specific PR review incidents tied to identifiable PR numbers and reviewers

Replacement: anonymize ("a vendor", "a customer firm", "a peer review incident") or remove.

### Tier 3: Internal tracking IDs

Tier 3 covers identifiers that let a reader address an internal system directly, or that pin a public claim to one specific internal ticket. It deliberately does NOT cover bead IDs; see below.

Enforced by `scrub-check.sh` (`TIER3_PATTERNS`), and this list is the whole of it:

- The internal Confluence space ID (`712020e7620f9a43fa4ea69b7a38bc2ee47ff5`)
- The Atlassian cloud ID (`f6ec428e-c64c-40d8-983b-9ac03ead43f5`)
- Specific Jira ticket numbers, `MX2-` followed by digits. Placeholder forms (`MX2-XXXXX`, `MX2-NNNNN`) deliberately do not match, so an example can keep the shape of a ticket reference without carrying a real one.

Replacement: remove, or substitute a placeholder that keeps the shape and drops the value (`a Jira ticket`, `MX2-XXXXX`, `a Confluence space`).

Two things sit under Tier 3's heading conceptually but cannot be expressed as a detector pattern, so they are reviewer judgment rather than enforced rules: PR numbers that tie a specific review incident to an identifiable individual (`#NNNN`), and Confluence page IDs in `atlassian.net` URLs. Handle those in review; do not expect `scrub-check.sh` to catch them.

**Standing decision on Confluence page IDs: remove them.** Leaving this to per-pass judgment produced both answers at once. By 2026-08-07 one such link had been dropped by an earlier pass while seven others survived across `dotclaude/` and `project-tier/`, which is the failure mode of a rule that says "decide each time." The decision is that the reference has no value left to preserve: the tenant hostname is already a `<company>` placeholder, so the URL resolves nowhere for a public reader, and the page returns 403 to a non-member regardless. Keeping the space key and the page ID discloses two internal identifiers and buys the reader nothing. Name the document and mark it as internal Confluence instead, which keeps the citation legible. This still is not detector-expressible (the shape is indistinguishable from any other URL), so it stays a review step, but it is now a rule with one answer rather than a judgment call with two.

**Bead IDs (`docr-*`) stay.** They are authentic operational flavor, not a leak. A bead ID resolves only inside the author's local beads workspace, carries no content, and reaches nothing a public reader can query, so it is opaque on its own. What it does carry is provenance: it marks a principle as having come from a specific real corrective instance rather than being invented for the writeup, and a calibration entry or a graveyard note keeps that tie legible even to a reader who cannot follow the reference. Scrubbing them would cost the whole provenance trail and buy nothing. As of 2026-08-07 the repo carries 161 bead-ID references across 42 scanned files, and `scrub-check.sh` passes clean with all of them present.

### Tier 4: Proprietary infrastructure detail

MX2 vocabulary is acceptable as authentic flavor (it tells the reader "this was a real codebase, not a hypothetical"). But specific infrastructure detail crosses into proprietary territory.

- Specific AWS resource names (DynamoDB table names, S3 buckets, Lambda function names) when they identify customer-facing or unreleased systems
- Specific Datadog dashboard IDs, monitor IDs, query strings that reveal monitoring topology
- Internal Confluence space IDs and the Atlassian cloud ID (same class of concern, but `scrub-check.sh` enforces them as Tier 3; see that section for the literal values)
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
