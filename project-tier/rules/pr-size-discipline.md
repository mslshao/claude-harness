# PR Size Discipline (promoted rule)

The first **rules-tier** exhibit in this directory. Everything else here is a component (agent or skill); this is a `.claude/rules/` rule that was authored personal-tier-first, proved out, and merged to a team's project-tier rule corpus via a team-reviewed PR.

It earns a place here because its promotion path is unusually legible. The rule was restructured after a literal-reading model, driving a planning session, read the old prose's contrapositive ("under the size trigger, bundling concerns is fine") and rubber-stamped a multi-concern PR as a single one. The restructure states the one-concern principle UNCONDITIONALLY and marks the size number as a one-way trigger. That story is told in full in `evidence/2026-06-11-rules-as-executable-specs.md`, and the generalized authoring rule it produced is `patterns/contrapositive-proof.md`. This file is the artifact those two describe.

The version below is the project-tier (team-adopted) text, scrubbed of nothing (the rule carries no personal or proprietary identifiers).

---

## PR Size Discipline

Large pull requests impose a disproportionate cost on reviewers. AI-assisted
authoring tends to produce larger PRs touching more files at once, concentrating
review burden rather than distributing it.

**One concern per PR, at any size.** Ask: does this work map to one design
decision or two? If the work satisfies two separate tickets, two separate
acceptance criteria sets, or two independently shippable behaviors, it should be
two PRs, even when the combined diff is small. The test is not "can these changes
be merged together" (they usually can) but "does reviewing them together force
the reviewer to context-switch between unrelated concerns?" This rule does not
depend on line count; the size threshold below adds scrutiny on top of it and
never relaxes it.

**The ~250-line threshold is a conversation trigger, not a hard cap.** When a PR
exceeds roughly 250 lines added (aligning with the team's "Large" PR tagging
convention of 100-499 LOC), pause and assess:

- Does the work still map to a single coherent concern, or has it accreted
  multiple distinct ones?
- Could any slice ship independently and be reviewed in isolation?
- Would a reviewer be able to hold the full diff in working memory?

**The trigger is one-way.** Exceeding it forces the questions above; staying
under it answers none of them. "Under 250 lines" is never a reason to combine
multiple concerns into one PR.

Multi-thousand-line refactors should be extremely rare and warrant additional
scrutiny even when they map to a single coherent concern: at that size, a
reviewer cannot hold the full diff in working memory and bugs hide in the
volume. The failure mode is worse when a large PR combines two distinct features
under one commit: reviewers can only partially review each concern, and
integration bugs between concerns hide in the seam. Prefer to extract
prerequisite refactors into their own smaller PRs.

**Mechanical enforcement is encouraged.** Consider adding size checks to CI or
pre-push hooks that surface the diff count and prompt the author to justify
oversized PRs. The specific tooling is a team decision, but automating the prompt
is preferable to relying on the author to notice at commit time.

**Author checklist:**

1. State the single concern this PR addresses. If you need an "and," it's probably
   two PRs.
2. Check whether any slice can be extracted as a prerequisite PR (refactor first,
   feature on top).
3. If the PR genuinely cannot be split, document why in the PR description so
   reviewers understand the constraint.

This discipline applies equally to AI-generated diffs. An AI agent can produce
hundreds of lines in seconds; that does not make hundreds of lines easier to
review. The discipline is about reviewer cost, not author effort.

---

## Why the structure matters (the promotion lesson)

The earlier version of this rule nested the one-concern principle inside the
size discussion, so a reader walking top-down met the ~250-line trigger first and
the concern test as a clause beneath it. A human reader supplies the intent ("of
course the concern test still applies") and never notices. A model reading the
rule corpus as an executable spec takes the contrapositive: if the size trigger
gates splitting, then under the trigger nothing gates it. The fix was not new
content; it was moving the unconditional principle OUT of the conditional scope
and marking the threshold as one-way. That structural edit is the whole lesson,
and it is why a rule, not just an agent or skill, belongs in this directory.
