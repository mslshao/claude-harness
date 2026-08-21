# Judgment Scrubs

`scrub-check.sh` catches leaks it has a pattern for. This file lists the scrubs it structurally cannot catch, because they are rewrites rather than substitutions. Read it before running any mechanical re-sync of `dotclaude/` or `project-tier/` from live, and re-check these lines afterward.

Established 2026-08-21, after a scrub-aware re-sync overwrote seven of them and the detector reported clean anyway.

## Why the detector cannot catch these

`scrub-check.sh` greps for known strings: a name, a cloud ID, a ticket key. Three classes defeat that:

1. **Orphan surnames.** The Tier 1 list matches full names (`Firstname Lastname`) and a subset of standalone tokens. Substituting only the first name leaves the surname, and the full-name pattern no longer matches. `Vineet Kumar's guide` becoming `the engineering lead Kumar's guide` is clean by the detector and still names a real person.
2. **Bare first names.** Several roster entries appear in the pattern list only in full-name form. A live file that says just `Logan` or `Beth` passes.
3. **Case.** The detector greps case-sensitively, so a name inside a lowercase memory key (`design:vineet-...`, `correction:identity:tomi-pronoun`) passes.

The general shape: a leak that survives is one where the *mechanical* scrub already ran and made the residue unrecognizable to the pattern.

## The standing rewrites

These are prose decisions, not substitutions. A re-sync that takes the upstream line wholesale will undo them.

| Class | Upstream shape | Mirror shape |
|---|---|---|
| Named reviewer | `<first> <last>'s Code Review Guide` | `the engineering lead's Code Review Guide` (possessive, not `the engineering lead Guide`) |
| Reviewer list | `(<name>, <name>, ...)` in an audience description | `(the peer reviewers, ...)` |
| Ratifier | `<name>-ratified decision` | `lead-ratified decision` |
| Name-in-key | `bd memories design:<name>-code-review-alignment-...` | `design:lead-code-review-alignment-...` |
| Name-in-key | `correction:identity:<name>-pronoun` | `correction:identity:reviewer-pronoun` |
| Same-first-name rule | names both people to make the point | states the rule without naming the teammate |
| Transcript-garble examples | real garbled names and the real entries they missed | describes the shape (`one teammate's first name can surface as three spellings`) |
| Confluence citation | `[Title](https://<host>/wiki/.../pages/<id>)` or `Confluence <id>` | `Title (an internal Confluence page)`; page IDs are removed per SCRUB-SPEC Tier 3 |
| Gendered pronoun about a real person | `She had the fix queued` | `They had the fix queued` |
| Em-dashes | team-authored project files use U+2014 | replaced, because the repo bans U+2014 on every surface |

## Re-sync checklist

A mechanical merge is fine as the first pass; it is not sufficient on its own. After one:

1. `bash sync/scrub-check.sh` and confirm the summary is the unqualified `clean (N files scanned, 0 findings)`. A `Tier 1 ... SKIPPED` line means the scan that matters did not run.
2. Diff the newly-introduced capitalized tokens against the previous commit and eyeball the list for anything person-shaped:
   `git grep -h '' HEAD -- dotclaude project-tier` versus the working tree, extracting `\b[A-Z][a-z]{2,15}\b`. This is what catches bare first names.
3. Grep case-insensitively for the roster first names, which the detector misses inside lowercase keys.
4. Grep for orphan surnames whose first name the scrub would have removed.
5. Grep for `Confluence [0-9]{9,}` and for `atlassian.net/wiki` URLs.
6. Count U+2014 across `*.md`; the repo's steady state is zero.
7. Re-read every line the merge rewrote in the table above.

Steps 2 through 4 are the ones with no automated equivalent. They are the reason this file exists.
