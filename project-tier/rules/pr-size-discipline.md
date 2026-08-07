# PR Size Discipline (promoted rule)

The **rules-tier** exhibit in this directory. The other entries here are components (agents and skills); this is a `.claude/rules/` rule that was authored personal-tier-first, proved out, and merged into a team's project-tier rule corpus via a team-reviewed PR.

It earns a place here because its promotion path is unusually legible, and because it did not stop moving after promotion. Three stages:

1. **The original.** The rule nested the one-concern principle inside the size discussion, so a reader walking top-down met a ~250-line trigger first and the concern test as a clause beneath it.
2. **The promoted fix.** A literal-reading model, driving a planning session, took the contrapositive ("under the size trigger, bundling concerns is fine") and rubber-stamped a multi-concern PR as a single one. The restructure pulled the one-concern principle OUT of the conditional scope, stated it unconditionally, and marked the threshold as one-way: exceeding it forces the split questions, staying under it answers none of them. That story is told in full in `evidence/2026-06-11-rules-as-executable-specs.md`, and the generalized authoring rule it produced is `patterns/contrapositive-proof.md`.
3. **What the team did next.** Under team ownership the rule went further than the promoted version did: the numeric threshold was deleted outright rather than kept and qualified, and an explicit counter-claim was added in its place ("a small diff is never evidence a PR is well-scoped, only that it's short"). The rule also stopped being a standalone file and now lives as a section of the team's `code-style.md`.

Stage 3 is the part worth noticing. The promoted fix kept the number and tried to fence it with careful wording; the team's version concluded that a number a reader can cite as reassurance is a liability no amount of fencing repairs, and removed the citable thing. That is the same contrapositive lesson applied one step harder, arrived at by the team rather than by the original author, which is what a promotion is supposed to make possible.

The text below is the current project-tier (team-adopted) version, carried over as-is apart from em-dash substitution to match this repo's writing convention. It carries no personal or proprietary identifiers.

---

## PR Size Discipline

Large pull requests impose a disproportionate cost on reviewers. AI-assisted
authoring tends to produce larger PRs touching more files at once, concentrating
review burden rather than distributing it. Default to small, single-purpose PRs,
merged frequently.

**One concern per PR, this is the rule, not diff size.** Ask: does this work
map to one design decision or two? If the work satisfies two separate Jira
tickets, two separate acceptance criteria sets, or two independently shippable
behaviors, it should be two PRs, even when the combined diff is small. The test
is not "can these changes be merged together" (they usually can) but "does
reviewing them together force the reviewer to context-switch between unrelated
concerns?" A small diff is never evidence a PR is well-scoped, only that it's
short, so don't cite a line count as reassurance that a PR is fine to combine or
ship as-is.

Multi-thousand-line refactors should be extremely rare and warrant additional
scrutiny even when they map to a single coherent concern: at that size, a
reviewer cannot hold the full diff in working memory and bugs hide in the
volume. Prefer to extract prerequisite refactors into their own smaller PRs.

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

The failure the restructure fixed was structural, not informational. A human reader supplies the missing intent ("of course the concern test still applies") and never notices the nesting. A model reading the rule corpus as an executable spec takes the contrapositive: if the size trigger gates splitting, then under the trigger nothing gates it. The fix added no new content; it moved an unconditional principle out of a conditional scope.

The team's later deletion of the threshold extends the lesson rather than replacing it. Marking a number as one-way stops a model from reading it as permission, but it does not stop a human from citing it in review as reassurance, which is the same failure with a different reader. Removing the number closes both. The generalizable form, written up in `patterns/contrapositive-proof.md`: author principles unconditionally, and be suspicious of any threshold a reader can quote back at you as a reason not to think.
