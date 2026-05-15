# Grounding Rules

Every finding must be traceable to the diff or verifiable against the codebase.

## Two-Phase Verification

### Phase A: Evidence category triage

Each specialist finding should include an evidence category (VERIFIED, DIFF-VISIBLE, or
QUESTION). If a finding lacks one, infer it:
- Findings with a `verification:` field describing what the agent checked → VERIFIED
- Findings quoting only diff code → DIFF-VISIBLE
- Findings phrased as questions → QUESTION

### Phase B: Mechanical confirmation

For each VERIFIED or DIFF-VISIBLE finding, run a quick confirmation:
Use the Grep tool to confirm the quoted code actually exists in the file. The
specialist's worktree should already be at the PR's HEAD commit. If verifying
in a context where the worktree is unavailable, use the inline diff as the source
of truth instead. If the search fails (quoted code not found), demote the finding
to QUESTION.

## Additional Grounding Checks

Apply to all findings:

1. **Diff line check.** Is the finding about code on `+` lines (additions) or `-` lines
   (meaningful deletions)? Findings about diff context lines (unchanged code) move to
   Review Summary as "pre-existing, not introduced by this PR." They do not become
   inline comments. Findings about code not visible in the diff at all (e.g., a file
   not in the changeset, stacked branch interactions, downstream breakage) also go in
   the Review Summary with enough context for the reviewer to verify independently.
   Inline comments require a navigable line in the GitHub diff view.

   **Line targeting rule for inline comments**: When a finding is about a concept (e.g.,
   a banned import pattern), target the line where the concept is *used in new code*
   (a `+` line within a diff hunk), not where it is *defined* in pre-existing code.
   Example: if `from unittest.mock import create_autospec` is a pre-existing import at
   line 5 but `create_autospec(MyClass)` appears in new code at line 167, target line
   167. GitHub's review API returns 422 "Line could not be resolved" for lines outside
   diff hunks. The `/post-review` skill catches this during verification, but pr-intel
   should not generate unpostable line numbers in the first place.

2. **Already-on-main check.** Files flagged as `already_on_main` during Merge Base
   Freshness (Data Gathering) must not receive inline comments. Findings about these
   files move to the Draft Review Summary with note: "This file's content is already
   on main (merged via a sibling PR). The diff shows it due to a stale merge base."
   Do not escalate severity for stale-file findings.

3. **Cross-reference check.** Only reference other PRs/issues if the PR's own description,
   comments, or linked issues mention them. Drop fabricated cross-references.

4. **Identifier check.** All referenced identifiers (class names, functions, variables)
   must be present in the diff or confirmed via grep. If fabricated, drop the finding.

5. **Stateful script check.** When reviewing shell scripts, Makefiles, or other
   sequential execution files, track cumulative state changes (especially `cd`) before
   making claims about later lines. A command like `pants tailor ::` has different
   scope depending on the working directory at that point in the script. Read the
   script top-to-bottom and resolve state before analyzing any individual line.

## Disposition

- Findings with fabricated identifiers or cross-references → **drop**
- Findings that fail mechanical grep → **demote to QUESTION** (may still be valid concerns)
- Findings about unchanged context lines → **move to Review Summary** with pre-existing note

## Evidence Categories in Output

- **VERIFIED** (✓): Agent confirmed by reading/searching the codebase
- **DIFF-VISIBLE** (○): Apparent from the diff; reviewer should verify wider context
- **QUESTION** (?): Plausible concern that could not be confirmed; framed as a question
- Cross-verification: "Also flagged by X" is noted but doesn't define the category

## Stale Comment Detection

Inline comments fetched via `gh api /repos/X/Y/pulls/N/comments` do not include a
pre-computed `is_outdated` flag. To detect staleness, compare each comment's
`original_commit_id` against the PR's current `headRefOid` (from metadata).

```bash
gh api /repos/<owner>/<repo>/pulls/<number>/comments \
  --jq '[.[] | {id, path, line, body, original_commit_id, commit_id}]'
```

If `original_commit_id` differs from the current head, the comment was written against
an older revision; the code at that file:line may have changed. Treat as potentially
stale and present under Open Threads with a staleness note.

If all comments share the current head, no staleness check is needed.
