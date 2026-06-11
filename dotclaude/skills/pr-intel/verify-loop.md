# @claude Verify Loop (default mode)

Default `/pr-intel` does not stop at the briefing. When synthesis produced one or more
bot-invoked `@claude` questions (the falsifiable-assertion or trace trigger fired in
synthesis.md step 5b rule 10), default mode posts them, waits for the GitHub `@claude`
bot to answer, reconciles the answer against the local findings, and presents a final
verdict recommendation. Motivation: the bot reads repo HEAD with fresh context and
reliably catches confident-but-wrong local assertions a code-only pass ships (canonical:
PR 9451 Q4, the wrong "Starlette default TestClient is loopback" claim that drove a false
test-gap finding).

## Mode applicability

| Mode | Loop? |
|------|-------|
| default (no flag) | Full loop when `@claude` questions exist. No questions: degrade to one-shot briefing. |
| `--once` | No loop. One-shot briefing (the pre-2026-05-29 default); `@claude` questions are drafted but not posted or awaited. |
| `--mine` | No loop, no `@claude` bot-routing. One-shot self-review, unchanged. An unverified falsifiable claim surfaces as a pre-submission item to check. |
| `--quick` | No loop. Triage only. |

The loop is conditional, not unconditional: if Phase 1 produced zero bot-invoked
`@claude` questions there is nothing to verify, so default behaves exactly like
`--once` (present the briefing, stop). The user then posts via `/post-review` as today.

On M+ PRs the collaborative-routing floor (synthesis.md "Bot-Invoked Comment Form" third
consideration / step 5b rule 11) biases synthesis toward at least one question when
substantive net-new findings exist, so a larger PR degrading to zero questions is a signal
to recheck that no substantive finding was asserted directly when routing it for the author
to engage would have served better. A genuinely clean M+ PR still degrades to zero; the
floor never manufactures a question.

## Phases

### L1: Analyze
The standard pipeline through Output. The briefing includes the Draft Review Summary,
any direct inline comments, and the bot-invoked `@claude` questions with their
briefing-context (the local expected answer for each, preserved per output-formats.md).

### L2: Gate + post (outward action 1)
Posting an `@claude` comment on someone else's PR is an outward action under the user's
identity. REQUIRE explicit user OK before posting; never post autonomously.

1. Present the draft review (summary + `@claude` questions + any direct comments).
2. On the user's OK, invoke `/post-review` to post the review as a **Comment-state**
   review (verdict withheld pending the bot): the `@claude` questions as inline comments
   plus any direct comments. The review body MUST contain the literal token `@claude` or
   the GitHub Claude Code workflow will not fire (synthesis.md "Bot-Invoked Comment Form"
   posting-side note; 9325 failure). Do NOT post Approve or Request-changes here; the
   verdict is L4.
3. Record in the tracking bead: posted review/comment IDs, the PR `headRefOid`, the list
   of `@claude` questions, and each question's local expected answer.

If the user declines to post, stop: hand them the one-shot briefing (equivalent to
`--once` output) and exit the loop.

### L3: Wait
Poll for the `@claude` bot's response. The bot posts as `morgan-and-morgan-claude[bot]`
(an issue comment, e.g. "Claude finished ...", or a review-comment reply).

- Cadence: ~270s per poll (the bot ran ~3 min on 9451; 270s stays inside the prompt-cache
  window per ScheduleWakeup guidance). Use the same polling primitives `/babysit-pr` uses
  (ScheduleWakeup + a tracking bead); this is the pattern, not an invocation of that skill.
- Detection: the bot posts a `Claude Code is working…` placeholder within seconds, then
  EDITS THAT SAME comment in place through a `Working on it...` task-checklist stage, and
  finalizes by replacing the body with `**Claude finished ...**`. Poll the placeholder
  comment's BODY (by id), not the existence of a new bot comment (which fires immediately
  on the placeholder). Done-condition: body contains `Claude finished` (or `finished @`).
  Do NOT key on absence of `working` (the checklist stage still says "Working on it..."
  with unchecked `- [ ]` boxes, so an absence-of-working check passes prematurely).
- Timeout: after ~3-4 polls (~15 min) with no bot response, fall back. Do not block
  indefinitely. Fallback = present the local read, mark the `@claude` questions
  UNANSWERED, hand the verdict decision to the user with that caveat.

### L4: Reconcile + recommend (outward action 2 = user approval)
Read the bot's response and reconcile each answer against the local expected answer held
in the tracking bead:

- **Agreement**: the assertion is validated on the record (bot-attributed). Fold it into
  the recommendation.
- **Disagreement**: surface as a calibration signal; do NOT silently adopt either side.
  The bot read repo HEAD (often right, e.g. 9451), but the bot can also be wrong. Present
  both reads and flag for the user.

Then present a final recommendation (Approve / Comment / Request-changes) plus a drafted
approval-or-comment message. Apply the posted-voice provenance rule (pr-template.md
"Copy-paste block formatting"; bead `feedback:the engineering lead:pr-review-bot-vs-human-2026-05-26`):
bot-surfaced verifications lean on the bot's on-record answer, the user's own judgment
stays in the user's voice. The user makes the final approval call as a SEPARATE review
action (Approve / Comment / Request-changes) posted after reconciliation, i.e. a second
review on the PR following the L2 Comment-state review; NEVER auto-approve under the
user's identity.

**Posted-summary discipline.** The L4 review summary and approval message are
outward-facing to the PR author: state the verified conclusion directly, do NOT narrate
the verify-loop mechanism ("I posted an `@claude` question to check X", "I asked `@claude`
and it confirmed Y"). The bot's exchange is already on the PR record for anyone who wants
the provenance, so the summary folds the conclusion into the finding in the reviewer's
voice (write "the DST fix only corrects the spring-forward off-by-one" not "I asked
`@claude` to verify the DST fix"). Recurrence: 2026-06-04 PR 9671, the `@claude` callout
was removed from the round-2 summary on request.

Output-format note: the L4 recommendation is a continuation of the same review, not a
fresh briefing. Validate on the first live run that `stop-validate-pr-intel.sh` tolerates
it; carry the `Provenance:` / `Decision count:` header forward onto the L4 message if the
hook requires it.

## State and compaction
The tracking bead (created at L2) holds posted IDs, `headRefOid`, poll count, the
`@claude` questions, and the local expected answers. A cold-start agent can resume at L3
(wait) or L4 (reconcile) from the bead alone (resume detection: no bot response yet for
`headRefOid` -> resume L3; a response exists -> resume L4). Follow the same tracking-bead
pattern `/babysit-pr` uses.

## Failure modes
- **Bot never responds / errors**: L3 timeout fallback (present local read, mark
  unanswered, user decides).
- **PR updated mid-wait**: the `headRefOid` changed; the bot's answer may be stale. Note
  it and re-evaluate against the new HEAD before recommending.
- **Bot disagrees with the local pass**: L4 calibration signal; surface both, user
  adjudicates.

## Non-interactive (agent) caller path
When `/pr-intel` runs inside an automated pipeline (no interactive human at the gates),
the two outward actions cannot be satisfied. Do NOT post or approve autonomously.
Instead, produce the one-shot briefing (as `--once`) plus the drafted `@claude` questions
and an explicit note that the verify loop requires an interactive operator to clear the
post and approval gates. The pipeline's decision-maker handles escalation from there.
