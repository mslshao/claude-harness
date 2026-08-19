---
name: cold-review
description: Generate a self-contained COLD REVIEW prompt so a genuinely separate reviewer (a fresh Claude session, a different model, or a human) can review a finished change without inheriting the implementing session's framing, and with explicit instructions to read the change IN CONTEXT (reuse search, sibling-path parity, reference resolution, invariant pinning) rather than diff-anchored. Targets the two measured causes of automated review missing what human reviewers catch: framing correlation and diff-anchoring. The author-side complement to /review (same-session self-review) and /pr-intel (reviewing someone else's PR). Use after finishing an implementation instead of leaning on same-session /review + /pr-intel --mine cycles, which share the author's framing and blind spots. Also emits the per-round HAND-BACK prompt that carries findings back to the implementing session (which never sees the review), so trigger on that half too. Trigger on "cold review", "/cold-review", "external review prompt", "bias-free review", "review handoff for a fresh reviewer", "hand this to a fresh session", "prompt to hand back", "hand me the prompt for the implementer", "follow-up prompt to hand back", "re-review after the implementer's changes".
---

# /cold-review

Produces a copy-paste-ready COLD REVIEW REQUEST: a prompt engineered so a reviewer with no exposure to the implementing session reviews a change from scratch.

It targets TWO distinct failure modes that both cause automated review to miss what human reviewers catch. Keeping them separate matters, because only the first is about who reviews and only the second is about how.

**1. Framing correlation.** Same-session review, including the multi-agent `/review` and `/pr-intel --mine` fan-outs, inherits the author's framing: the subagents have fresh context windows, but the implementing session writes their prompts and presents the diff the way it already sees it, so errors stay correlated with the author's blind spots. Evidence: `memory/reviewer-discipline.md` (2026-07-24) recorded a 7-lens same-session Workflow missing or killing 8 findings that a human peer reviewer and the Graphite bot caught. A reviewer given only the requirement and the raw diff has decorrelated priors. The fix is WHO reviews, which is what this skill's handoff shape provides.

**2. Diff-anchoring.** Three independent 2026-07-24 retros found this to be the larger cause, and it is NOT fixed by changing reviewers: `correction:review:context-reach-not-isolation` ("our review read the diff in isolation while the peer reviewer read it in context; gap = contextual reach, not line-reading") and `correction:review:sibling-path-parity-lens` (5-6 of 9 substantive human findings on PR #10769 were sibling-path parity divergences, "a class NO automated lens owns: all 13 `/review` agents + pr-intel are diff-anchored and the sibling code is unchanged/other-package"). A cold reviewer told only to "read the diff" inherits this blind spot exactly. The fix is HOW the reviewer reads, which is why the artifact carries the four contextual reaches as fixed template rather than optional advice. Do not trim them to shorten the prompt: they are the half of this skill that addresses the dominant observed failure mode. Whether the decorrelation in (1) pays off independently is under evaluation at bd `docr-qc87r`.

## What this is NOT

- **Not a same-session review.** This skill PRODUCES a prompt; it does not run the review in this session. Running it here (even by spawning a subagent) reintroduces the framing bias it exists to remove, because this session would author the reviewer's prompt. The artifact is meant to run in a SEPARATE context.
- **Not `/pr-intel`.** `/pr-intel` reviews someone else's PR (already external). This is the author-side handoff for your OWN change.
- **Not `/handoff`.** `/handoff` is a cold-START prompt to resume work in the next session. This is a cold-REVIEW prompt to adversarially check a finished change.

## When to use

After finishing an implementation, in place of leaning on repeated same-session `/review` + `/pr-intel --mine` cycles, especially when the change is consequential or when you notice you are the one who wrote both the code and every review of it.

## Input

`/cold-review [PR-number | branch | bead-id | ticket]`. Default: the current branch's open PR.

Resolve, in order: an explicit PR number; else the current branch to its PR (`gh pr view --json number,url,headRefName,baseRefName`); else a bead or ticket id passed directly.

## Process

1. **Resolve the artifact and its diff locator.** Capture the PR number + URL (or branch + a `git diff <base>...<head>` command) and the changed-file list (count + paths only). Do NOT embed the diff contents: the reviewer fetches the diff themselves so they read it unmediated.

   Capture the head SHA explicitly (`gh pr view <n> --json headRefOid -q .headRefOid`) and instruct the reviewer to read every file through it (`git show <sha>:<path>`). Never read through `FETCH_HEAD`: it is shared mutable state that any later fetch in the same session silently repoints, and a stale read produces confident findings about code that is not in the PR. Observed 2026-08-06 on a re-review of PR #11388, where a stale `FETCH_HEAD` nearly produced a "the doc still lists the old name" finding against content the PR had already fixed.

   The same pin applies to SEARCH, not only reads: use `git grep <pattern> <sha> -- .`, never a
   working-tree `grep -rn`. The checkout is usually on a different branch than the PR under review,
   so a working-tree grep answers the reference-resolution question (reach 3 in the template)
   against the wrong tree and returns the PRE-change identifiers. Observed 2026-08-06 on PR #11388,
   one round after the `FETCH_HEAD` near-miss above: a scoped `grep -rn` over `app infra docs`
   returned the old resource name and old monitor display name, which reads as "the rename is
   incomplete" when the head SHA had already renamed both. Two operational notes for this repo that
   make `git grep` the fast path as well as the correct one: `rg` is not installed, and an unscoped
   repo-wide `grep -r ... .` exceeds the 120s tool timeout and gets backgrounded mid-review.

   The BASE needs pinning too, not just the head. `git diff main...<sha>` silently inflates scope
   when local `main` lags `origin/main`, which it usually does in a long session: `git fetch origin
   main` first, then diff against `origin/main...<sha>`, and cross-check the file count against
   `gh pr view <n> --json files`. Observed 2026-08-06 on PR #11388 round 3: a three-dot diff
   against stale local `main` reported 33 files and 3,216 insertions for a 3-file, 129-insertion
   PR, because the branch had been rebased onto three merged MX2-XXXXX PRs. This is
   `gotcha:stale-local-main-diff-base` (2026-06-15) reaching a consumer that postdates it.

2. **Resolve the requirement from an author-independent source**, in priority order:
   a. The linked bead's acceptance criteria (`bd show <id>`, the ACCEPTANCE / DESIGN fields).
   b. The Jira ticket's acceptance criteria (the ticket the PR names in its "Jira issue link:").
   c. If neither exists, fall back to the PR's stated goal, tagged `[author-sourced requirement, treat with skepticism]` so the reviewer knows the framing came from the author.
   d. If even that is absent, use `[no requirement provided, infer intent from the diff and flag its absence]`.

   Before using (a) or (b), check whether the field was amended AFTER the implementation. An AC
   list carrying the author's own verification results ("satisfied by construction", "verified
   against live data", or a SUPERSEDED entry rewritten to match the mechanism that shipped) is
   author framing wearing a requirement's clothes; feeding it verbatim anchors the reviewer to the
   implementation it was rewritten to describe. When it is contaminated, drop to the next source
   that PREDATES the implementation, quote that verbatim, and state in the artifact which field you
   excluded and why, so the reviewer knows a source was set aside rather than missed. A
   pre-implementation source written by the author is still not fully independent: tag it so the
   reviewer discounts the parts that read as suggested mechanism. Observed 2026-08-06 on PR #11388,
   where bead docr-txnew's ACCEPTANCE field had been amended post-implementation with per-criterion
   verification claims, so the Jira defect report (13 days older, mechanism-neutral) became the
   requirement and the bead AC was excluded explicitly in the artifact.
   A requirement can be STALE rather than contaminated, and staleness survives every check above
   because the AC reads as ground truth. When the change alters a parameter (a window, a
   threshold, an interval, a page size, a timeout), grep the requirement text for the OLD value:
   acceptance criteria are written before the fix and routinely keep the pre-change number, which
   turns the AC itself into a false-clean path. Carry the stale figure into the artifact as a
   flagged question rather than silently correcting it, since judging it is the reviewer's job.
   Observed 2026-08-12 on PR #11582: the fix widened an evaluation window from 15m to 30m and AC2
   still read "at least one full 15 minute boundary then passes", so a post-apply read at 15
   minutes would have passed on a window that had not yet crossed two boundaries. Two cold-review
   rounds quoted that AC and neither checked it.
   Pull the requirement VERBATIM. Do not paraphrase, condense, or fold in the author's implementation reasoning.

3. **Assemble the COLD REVIEW REQUEST mechanically** from the fixed template below. Do NOT inject any of: the implementation approach, why choices were made, self-review results, PASS verdicts, CI status framed as reassurance, or a list of what was already checked. Each of those anchors the reviewer to the author's mental model and defeats the purpose.

   Exactly three slots carry judgment (requirement source, plus the two below); everything else is fixed template:
   - **Scope note** (include ONLY when the requirement spans more artifacts than this diff, e.g. one ticket delivered across several PRs). State the split as a bare fact with the sibling identifiers, then hand the judgment back: "Judge whether that split is sound and whether this one's half is complete; do not assume it is." Without it, a cold reviewer reads a broader requirement, sees a narrower diff, and reports a phantom requirement gap. Do NOT explain why the split was made; that is author rationale.
   - **Domain failure-mode hint** (include ONLY when the artifact's dominant failure mode is invisible in the diff text). One sentence naming how this CLASS of change fails silently, e.g. for monitors: "a monitor that never evaluates is indistinguishable from a healthy one." A reviewer with no domain priors otherwise spends the pass on generic style. Name the failure mode only: never the specific suspect line, and never whether you think it is present.

4. **Output** the assembled prompt as a single fenced block for copy-paste, followed by one line on how to run it out-of-session.

5. **Hand the findings back.** When a review comes back with findings (whether it ran in a fresh session, a different model, or a human wrote it), the deliverable is not the review: it is a prompt the implementing session can act on. Emit the HAND-BACK template below as a single fenced block, unprompted. Do not wait to be asked; the implementer session cannot see the review, so the hand-back is the only thing that crosses the boundary.

   This step repeats per round. A re-review that finds the prior round's items closed emits a hand-back covering only what is still open, plus the verdict.

   The hand-back is chat, and chat does not survive the session. When the review runs in a
   separate context its findings exist nowhere durable until someone writes them down, so the
   same round that emits the hand-back also comments them onto the bead or ticket that owns the
   work: verdict, open items, and the ALREADY VERIFIED list. Skipping it costs a full round when
   the implementer's next session re-derives what the reviewer already measured. Do NOT read that
   bead's own comment trail while writing to it, or later rounds inherit the implementer's
   framing, which is the isolation this skill exists to protect. Observed 2026-08-13 on PR #11595:
   `stop-validate-unrecorded-nonactions.sh` caught round 1's findings sitting only in chat.

   On every round after the first, check what each fix INTRODUCED, not only whether it was
   applied. A hand-back that asks for a behavior change buys a new behavior, and the round that
   requested it is the round least likely to audit it: the reviewer is checking their own ask.
   Two questions per closed item: does the new path have the observability the old one had, and
   did removing a defensive mechanism promote some other check into load-bearing duty it was not
   written for? Observed 2026-08-06 on PR #11389, where a requested tolerate-to-terminate change
   landed correctly and introduced an unmonitored terminal state plus a cardinality check standing
   in for a range guarantee the deleted code used to make structurally.

## Output template (the outbound review request; the hand-back template is below)

```
COLD REVIEW REQUEST. You did not write this change; review it with fresh eyes.

Artifact: PR #<n> (<url>). Run `gh pr diff <n>` (or `git diff <base>...<head>`) and read the
full diff yourself. Changed: <k> files (<paths>).

[Scope note, omit when the requirement and the diff cover the same ground:]
Scope note (fact, not judgment): <ticket> was delivered across <n> artifacts. This one is <id>;
the sibling(s) are <ids>. Judge whether that split is sound and whether this one's half is
complete; do not assume it is.

Requirement (verbatim from <source>): <requirement / acceptance criteria>

[Domain failure-mode hint, omit unless the dominant failure mode is invisible in the diff text:]
Note on this class of change: <one sentence naming how it fails silently>.

Your task: review the diff against the requirement as if seeing it for the first time. Assume
nothing about its correctness. Do not trust that CI, tests, or type checks pass; verify what you
can from the diff and the repo. Look for correctness bugs, missing or mishandled cases,
requirement gaps, security/PII exposure, and risk introduced by the change. Report EVERYTHING you
find, ranked by severity. Do not self-censor to "only high-severity" or "be conservative";
filtering happens in a separate pass after yours, not inside it.

Read it in context, not in isolation. The highest-value findings on changes like this one live
outside the diff hunks, in the relationship between the new code and code it did not touch. Four
specific reaches, all of which require opening files the diff does not list:
1. Reuse search: grep for an existing endpoint, function, or module that this code reimplements.
   New code that duplicates a capability the repo already publishes is a finding even when the
   new code is locally clean.
2. Sibling-path parity: if this change mirrors an existing path (look for mirror, parallel,
   same-semantics, or "same as X" language in the diff, docstrings, or PR body), open the
   canonical path and table its mechanisms against this one. Force every divergence into
   deliberate or drift. The divergent code is usually fully typed and idiomatic in isolation, so
   this class of finding exists ONLY in comparison and no line-level lens will surface it.
3. Reference resolution: every reference the change introduces (runbook links, doc URLs, function
   and monitor names, ticket IDs) must actually resolve. Check them rather than assuming.
4. Invariant pinning: name the central invariant each new test is supposed to protect, then check
   the test would actually fail if that invariant broke.

Deliberately omitted: the implementer's approach, rationale, self-review results, and what it
believes it already verified. This omission is intentional. Do not ask for them; form your own
judgment from the diff and the requirement alone.
```

## How to run it out-of-session (pick one, strongest first)

- Paste the block into a NEW Claude Code session (fresh context, no exposure to the implementing session). Strongest cheap option.
- Hand it to a different model, or to a human reviewer.
- (Future, Mechanism B) a separate top-level harness invocation runs it headless so even the reviewer's prompt is authored by a different context.

Do NOT run it as a subagent of the session that wrote the change; that is the same-session bias this skill removes.

## Hand-back template (step 5, emitted per round)

The implementing session never saw the review. Everything it needs to act must be in this block, and nothing in it should require the implementer to reconstruct the reviewer's reasoning.

```
FIX REQUEST: PR #<n> (<ticket> / bead <id>), head <sha>

<One-line verdict. On round 2+, lead with what is now closed so the implementer does not
re-litigate settled items.>

============================================================
<n>. <SEVERITY>: <one-line defect statement>
============================================================

<file:line>

<Mechanism: why it is wrong, in terms the implementer can check without trusting the
reviewer. Name the layer the original reasoning got right, so the correction lands as a
distinction rather than a contradiction.>

<Reproduction the implementer can run themselves, verbatim and copy-pasteable. This is the
load-bearing part: a finding they can reproduce needs no argument, and a finding they cannot
reproduce turns into a debate.>

<Blast radius as a table of concrete call sites / consumers, not a count.>

<Fix, if you verified one. Say that you verified it and against what.>

============================================================
ALREADY VERIFIED HERE, DO NOT REDO
============================================================

<Everything the reviewer confirmed clean, with the command or oracle. Without this the
implementer re-runs the reviewer's work, and each round costs double.>

============================================================
DEFINITION OF DONE
============================================================

<Numbered, checkable. Include "or decline it in the PR body with a reason" for anything
that is a judgment call rather than a defect: a declined item with a stated reason and a
follow-up bead is a valid close, and pretending otherwise produces theater.>
```

Rules for assembling it:

- **Reproduction over assertion.** Hand over the command, not the conclusion. The strongest hand-back this pattern produced turned "your audit checked the wrong layer" into a 20-line script the implementer ran themselves.
- **ALREADY VERIFIED is not padding.** It is what keeps round N+1 cheap. Name the oracle (`pants test`, `terraform fmt -check`, a schema dump), not just the claim.
- **Never propose a fix you have not run.** If you hand over a code suggestion, verify it against the same cases the defect broke on, and say so. An unverified fix in a review that just caught an unverified fix is self-refuting.
- **Offer the decline path.** Items that are judgment calls (missing test, deferred consolidation) close legitimately via a stated reason plus a tracked follow-up. Demanding the build on those turns the hand-back into a compliance exercise.
- **Evidence placement is a finding.** If the implementer did the work but recorded it somewhere the PR's reviewers will not look (a bead, a scratch dir), say so and name the surface it belongs on. Observed twice on PR #11390.
- **A hand-back ask that lands on a team-facing surface names the team-facing id.** PR bodies, Jira tickets, and commit messages take the tracker id the team reads (`MX2-*` here); internal bead ids are for internal surfaces. Asking for the wrong tier is not a cosmetic slip: a guardrail can refuse the edit outright, and the implementer then has to file the ticket mid-round to satisfy the ask. Before writing "name `<id>` in the PR body", check whether that id has a team-facing counterpart, and if it does not, ask for the ticket to be filed as the item rather than as the citation. The reverse direction is unaffected: the review-response template's ALREADY TRACKED line is implementer-to-reviewer, and a bead id is correct there. Observed 2026-08-11 on PR #11550 round 2, where a DEFINITION OF DONE item asking for docr-rzjwj in the PR body was refused by the gate, which named the fix itself.
- **An absence claim needs an unbounded read.** "No bead tracks this", "no ticket exists", "nothing references it" is a finding that costs the implementer a real edit when wrong, and it is the easiest finding to get wrong, because every convenient read is truncated. Before reporting a missing artifact: use `bd list --status all --json -n 0` (the default cap is 50, ordered closed-first, so a jq filter over the default reads false-clean), search more than one term shape (hyphenated and unhyphenated: `bd search "inference error rate"` misses a title reading "inference error-rate"), and read the whole artifact rather than `bd show | head -N`. Observed twice on PR #11388, 2026-08-06: a capped `bd list` plus a hyphen-blind search reported docr-dzymh missing eight minutes after it was created, which made the implementer delete a true pointer that the next round had to restore; and a `head -16` read reported docr-r8ovv as not covering a concern its line 113 covered in full. The implementer counted this as the third under-scoped-search false negative in one thread, alongside docr-9ppsn's clamp-scoped grep, so treat a negative claim from a single search strategy as unfinished work. The cap is not always the tool's: a self-imposed `| sort ... | head -N` over a correctly uncapped result is the same failure with none of the warning signs, because the `-n 0` in the command reads as diligence. Observed 2026-08-07 (CLAUDE.md trim review round 2): `bd list --status all --json -n 0 | jq ... | sort -k3 -r | head -8` over 110 matches reported a bead absent that matched on TITLE alone, and the sort key was a date identical across most rows, so which 8 survived was arbitrary. Report absence only from a read with no cap anywhere in the pipeline. The same term-shape blindness applies to the CODE tree, not just the tracker: `git grep "11 matter"` misses a docstring reading "11-matter", and a package-scoped grep misses an anchor living in a sibling package's test file. Before reporting a reference as unanchored, run the hyphen, space, and underscore variants unscoped over the SHA (`git grep -I <pat> <sha>`; `-I` skips the binary fixtures that otherwise blow past the output cap). Observed 2026-08-12 on PR #11598: a package-scoped, hyphen-blind grep reported "the stated 11-matter maximum has no in-repo anchor" when `test_doc_file_info_builder_matter_stub.py:394` carried it, and the claim had to be corrected in the hand-back.

## Review-response template (implementer to reviewer, the reverse direction)

The two templates above both flow reviewer-to-implementer. The third direction has no template
and gets improvised: the implementer answering the review so the reviewer can run their
verification round. Added 2026-08-11 after improvising it on PR #11425, where the response had
to carry two defects in the REVIEWER's own evidence, which is the case the shape exists for.

Emit this when findings have been dispositioned, whether or not every item is closed. A partial
response is correct and better than silence; say plainly what is unfinished and why.

```
REVIEW RESPONSE: PR #<n> (<ticket> / bead <id>), head <sha>, <UNCHANGED | was <old-sha>>

<One-paragraph verdict. Lead with what the reviewer got RIGHT that changed the outcome, then
what did not survive, then what is still pending and the reason. Do not lead with agreement
theater or with a defense.>

=== 1. <FINDING ID>: CONFIRMED / larger than measured / REFUTED ===
<Evidence, with the command and its output. If confirmed and worse than they measured, say by
how much and show the measurement.>

=== 2. DEFECTS IN THE HANDED-BACK EVIDENCE ===
<This section is the reason the template exists. A reviewer running round 2 with a broken query
measures the wrong thing twice. Name each defect, show the correct form, and state which of
their conclusions it invalidates. Be specific and non-scoring: the goal is that their next
round works, not that they were wrong.>

=== 3. DISPOSITION PER ITEM ===
<One line per finding: ACCEPTED (what changed), DECLINED (reason + follow-up bead), ALREADY
TRACKED (bead id, and say so plainly when their absence claim did not hold), or SKIPPED.>

=== 4. NOT YET DONE, AND WHY ===
<Blocked items with the actual blocker, e.g. branch ownership, a decision that is the human's,
a disconnected tool. Never imply closure you do not have.>

=== 5. FOR YOUR NEXT ROUND ===
<What to verify, including anything that would fail clean if they re-ran their own commands
verbatim. Point at the read-first surface, not just the comment stream.>
```

Assembly rules specific to this direction:

- **Correct the reviewer's evidence before anything else you want them to do.** A casing bug, a
  wrong metric name, or a stale ref in their hand-back will silently reproduce their wrong
  conclusion. On #11425 the reviewer's ES|QL matched an uppercase sentinel that returns zero
  against a live non-zero population, and they had read that zero as the population draining.
- **Their absence claims are the most likely to be wrong**, for the same reason the outbound
  template warns about ours. Check each "file it" / "nothing tracks this" against the tracker
  before accepting the ask; on #11425 two of them were already filed.
- **Confirmed-and-worse is the highest-value response shape.** When their finding holds and the
  real magnitude exceeds their estimate, lead with the corrected number and show the query.
- **Do not launder a decline as a deferral.** If you are not doing it, say declined, give the
  reason, and name the bead. "Tracked separately" without an id is not a disposition.
- **State the head SHA and whether it moved.** The reviewer cannot re-diff without it, and a
  response against a head they never reviewed wastes their round.

## Round N+1: verifying the claim

The implementer reports done. That is a claim, not evidence, and this skill exists
because the implementing session cannot see its own blind spots. Start the verification
round on the claim itself; do not wait to be told to check.

1. **Re-resolve the head.** `gh pr view <n> --json headRefOid`, then diff old head to
   new head and read it. Never the summary.
   For a NON-GIT artifact (a personal config file, a memory file, a scratch doc) there is
   no ref to re-resolve, so snapshot the head you reviewed at hand-back time
   (`cp <file> <dir>/heads/<name>.round<n>-<md5-prefix>`) and quote its md5 in the
   hand-back. Without that anchor, round N+1 has nothing to diff and must reconstruct the
   prior head by patching the original snapshot with a persisted diff, which only works if
   that diff was persisted. Observed 2026-08-07 (CLAUDE.md trim review, round 3:
   reconstructed the round-1 head via `patch` and checksum-verified it against the md5 the
   round-1 request had quoted, then started saving a head per round).
   Check the producer, not just the comparison: a failed `git show` still pipes cleanly into
   `md5sum`, which hashes empty input, so two broken reads compare equal and the check prints
   SAME. Observed 2026-08-07 on PR #11411, where a drift check run from the wrong cwd reported
   both config files unchanged because both reads had failed. Use `git -C <dir>` and confirm
   the hash is not the empty-input one.

   The same trap wears a second costume: a LINE-ANCHORED grep over captured tool output.
   `grep "^Plan:" <file>` matches nothing in terragrunt output because every line carries an
   `HH:MM:SS STDOUT terraform:` prefix, and the empty result reads as "the artifact does not
   contain the claim." Observed 2026-08-11 on PR #11514 round 3: an anchored grep over ten plan
   artifacts printed empty for all ten, and the unanchored form returned the `Plan: 0 to add,
   N to change` lines that CONFIRMED the implementer's evidence. Before treating an empty read
   as evidence, print one raw line and confirm the pattern could ever match it.

   Mirror case, where the read succeeds but its value is an artifact of how you took it: state
   the measurement window or scope inline on every quantitative finding. Same round, a monitor
   expression returned 5,000 at 15m, 60,000 at 4h and ~180,000 at 24h, so a bare magnitude would
   have read as reviewer and implementer contradicting each other when both were right at
   different windows. The stated window turned a standoff into a diagnosis.
2. **Classify every finding**: fixed / documented-but-not-guarded / declined-with-reason
   / untouched. "Documented" is often the right outcome, but say so plainly: prose in a
   docstring is not a guard, and the residual belongs on a tracked bead.
3. **Mutation-verify every NEW guard test the round added.** A guard that has only ever
   been green proves nothing. Break the invariant it claims to protect; confirm it reds.
   Always run the mutation with `pants test --force`. A content-hash cache hit prints as
   `✓ ... succeeded`, indistinguishable from a fresh green, and a mutation run is the case
   it corrupts worst: re-applying an identical mutation re-serves your own earlier run, and
   on a shared machine a baseline re-serves the implementer's. Either way a green under
   mutation may mean cached rather than "the guard does not fire". See
   `memory/pants-verification.md`. Observed 2026-08-12, PR #11598 round 1: a reported "96
   targets green under the inverted guard" was mostly cache hits, and only an earlier 3-file
   run was a real first execution of that input.
4. **Use an isolating mutation: break the far side of the boundary.** For a
   producer-contract mirror, rename the field on the PRODUCER, not on the mirror.
   Renaming the mirror also breaks every hand-written fixture test, which proves
   "something broke", not "the new guard works". For a leak guard, inject the leak.
   Record the split (1 failed / N passed) and which tests stayed green: the split IS
   the evidence.

   For a leak guard whose assertion is a SUBSTRING SEARCH, injecting the leak is necessary
   but not sufficient: the mutation can come back all-green for a second reason, that the
   fragment the test searches for was never renderable in that channel for that fixture.
   Check the precondition standalone before mutating anything. Reconstruct the fixture in a
   throwaway script, render the channel the assertion reads (`str(exc)`,
   `traceback.format_exception`, the log line), and confirm the fragment IS present with the
   leak in place. If it is not, the assertion cannot fail and the guard is blind rather than
   passing. Two things make this recur:
   * **Truncated renders are fixture-order dependent.** pydantic renders a long `input_value`
     as head plus tail, so dict key order decides which field lands in the window, and a
     cosmetic-looking fixture edit flips a falsifiable assertion to a vacuous one. Such a
     fixture needs a positive control PER SHAPE (not one per site) and a docstring naming
     which key is load-bearing.
   * **It recurs inside the fix round.** Observed on PR #11583: round 2 shipped a containment
     test that could not fail while closing a round-1 item about assertions that could not
     fail. Re-run the precondition check on the round's NEW test; do not assume the lesson
     transferred.
5. **Restore and prove it.** Tree clean at the head SHA, suite green again, before you
   report.
6. **Verify the implementer's own verification, including its wording in the PR body.**
   A non-isolating mutation described as proof is a defect in the record even when the
   guard turns out fine. (Observed: PR #11392 round 2.)
7. **Grep every surface for the claim you corrected, not just the copy you cited.** A factual
   claim usually has copies: the doc, the ticket it links, the PR body, a commit message, a
   sibling runbook. Fixing the one your finding named leaves the others asserting the refuted
   version, and the survivor is often the one that costs real work, since a ticket is what
   someone implements from. Before closing a corrected-claim finding, grep its distinctive
   phrase across the diff, `gh pr view <n> --json body`, and every ticket the change links.
   Observed twice on PR #11411: the "no push-to-main trigger" cause was corrected in the doc
   while MX2-XXXXX kept it (round 3), and the "org is over its plan limit" framing was
   corrected in the doc and the ticket while the PR body kept it for three more rounds
   (round 6).

## When a round asks you to build a verification artifact

A hand-back that asks for a test suite, a repro script, or a baseline harness creates a
NEW artifact that the next round will then review. That artifact has its own failure
mode, distinct from anything above: it accretes correctness across rounds without ever
being executed, and each round's edits feel like progress because they are individually
right.

Observed 2026-08-07 on the CLAUDE.md trim: a regression suite went 5,258 -> 6,759 ->
8,151 -> 12,198 bytes over four rounds and was never run. The reviewer had to
pre-register "a fifth round of suite polish is the finding" to break the loop, and every
single edit it flagged along the way was a real defect.

Rules, both directions:

- REVIEWER: once an artifact you requested exists and is executable, stop reviewing its
  content and ask for its OUTPUT. An unexecuted artifact's defects are cheap to find and
  worth nothing; the first run reprices them. If you must flag a defect in round 2,
  attach it to the run request rather than blocking on it.
- IMPLEMENTER: after the SECOND round of edits to the same verification artifact, stop
  and either execute it or state plainly why you cannot. "Cannot" is a legitimate answer
  and is often structural (a retroactive A/B needs the old config LOADED, which a
  subagent cannot do because it inherits its parent's). Say that in round 2, not round 4.
- For a verification artifact the bar is "good enough to execute", not "correct". An
  imperfect suite that ran beats a perfect one that did not, because only the former
  produces information.

## Bounds

- Read-only. Produces a text artifact; makes no code, PR, or tracker changes.
- Assembles from a fixed template. The skill must not editorialize the requirement or summarize the diff; both reintroduce author framing.
- The requirement is author-independent by preference (bead/ticket AC); a PR-sourced requirement is flagged as such so the reviewer discounts it.
