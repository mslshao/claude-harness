# PR Review Routing

Routing rules specifically for PR-related work. The "review a PR" surface has multiple sub-cases (reviewing someone else's, self-reviewing before push, quick triage, post-publish iteration) each with its own optimal tool.

## The routing table

| Trigger | Tool | When |
|---|---|---|
| Reviewing someone else's PR | PR-intel skill (default mode) | Briefing format, reviewer perspective. For re-reviews, include revision context in the invocation ("rev8 just published, we reviewed rev7") to get delta-aware output |
| Self-review before publishing | PR-intel skill (`--mine` flag) | Own PR, post-submit but pre-publish |
| Quick triage of any PR | PR-intel skill (`--quick` flag) | Triage only |
| Pre-submission code quality (own code, before PR exists) | code-reviewer agent | Structural review, design judgment, pre-commit |
| Comprehensive multi-agent author review | PR review toolkit | Author wants thorough feedback before merge |
| Hands-off post-publish iteration on own draft PR | babysit-PR skill | After publishing a draft PR and stepping away; classifies incoming comments (bot vs human, mechanical vs substantive), auto-remediates mechanical bot suggestions via worktree plus force-push, escalates human reviewer comments. State persists in a tracking item so the loop survives compaction. Refuses on non-draft PRs unless explicit override flag. |

## Why this exists

A single "review this PR" command would route everything to the same tool and produce muddled output. PR-intel briefing format works for reviewing someone else's code; it does not work for self-review before publishing, where the author wants a checklist of "what to fix before push." The fanned routing produces output shaped for the specific use case.

The babysit-PR row is the operational sibling: a long-running PR loop that handles bot feedback while the author is offline. Distinct from the review tools because its trigger is "I am stepping away" rather than "I need to evaluate this code now."

## Where it has limits

- The routing assumes the author knows which sub-case they are in. New users might not distinguish "reviewing someone else's" from "self-review", and the default routing favors the most common case.
- Comprehensive multi-agent author review is heavier than most PRs need. The default is the cheaper triage tool; comprehensive is opt-in for substantive PRs.
