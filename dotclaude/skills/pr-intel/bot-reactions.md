# Bot Reactions

Top-level pr-intel phase. Constructs the `bot_reactions` list from the dedup
decisions made during Synthesis Step 2. Each bot comment that overlapped with
a synthesizer finding gets classified as either `+1` (bot finding is correct)
or `-1` (bot finding is a false positive). Reactions are the lightweight
signal layer; they ride INDEPENDENTLY of any inline comment the reviewer
decides to keep.

Runs AFTER Provenance Classification, BEFORE Verification.

This phase exists because earlier attempts to embed bot-endorsement marking
as a sub-step of synthesis.md Step 2 were systematically skipped by the
orchestrator (confirmed 2026-05-21 across 8+ PR reviews: bot_endorsements
universally 0 despite bot acknowledgment in body prose on PRs #9276, #9274,
#9271). The attention-floor failure mode is fixed by promoting the list
construction to a top-level SKILL.md phase with its own dedicated file.

## When This Phase Runs

- **default mode**: always
- **`--mine` and `--quick` modes**: skip entirely (no review being posted;
  no reactions to apply)

## Conceptual Frame

Two layers, INDEPENDENT:

**Reaction layer** (the bot's finding accuracy):
- `+1` = "the bot's finding is correct" (regardless of whether the reviewer
  also adds a comment)
- `-1` = "the bot's finding is a false positive" (regardless of whether the
  reviewer also adds a rebuttal)
- No reaction = "genuinely ambiguous; I can't form a position." Rare; when
  in doubt, default to a position.

**Comment layer** (what the reviewer adds beyond the bot):
- None = "the bot's text covers it; I have nothing to add"
- Additional context = keep my inline comment, prefix "Adding to [bot]'s
  point above:" (the bot's finding is correct AND I have material context
  the bot missed)
- Inline rebuttal = explicit counter-comment with cited evidence (the bot
  is a false positive AND the misread could mislead the author into
  fixing the wrong thing; per review-voice.md rebuttal exception)
- Body-prose mention = acknowledge in the Draft Review Summary body (the
  bot's finding is correct but deferred / out-of-scope; the action context
  belongs in the summary, not as an inline duplicate)

The reaction fires whether or not the comment also fires. They are
orthogonal decisions. Reaction signals accuracy to the bot's maintainers;
comment signals reviewer-added-value to the author.

## The Five Categories

Every bot inline comment fetched during Data Gathering falls into ONE of
these categories. Apply in order; first match wins.

**Precondition (resolved/moot gate).** Before classifying, check whether the
finding still applies to the current HEAD. A comment that was correct WHEN
POSTED but is now moot (addressed by a subsequent commit, or whose stated
failure mode no longer holds on the current diff) is NOT a category-1 `+1`:
it gets NO reaction and is noted in Open Threads as resolved. Reactions
signal finding accuracy on the CURRENT diff, so a comment with no current
synthesizer overlap has nothing to react to, even when the original catch
was valid; the author's own fix is the acknowledgment, not a `+1`. Slip this
prevents: PR #10049 (2026-06-22), where Copilot's `commit_id`-missing comment
was correct on commit 1, fixed on commit 2, and still drew an unplanned `+1`
that had to be removed at post time.

| # | Bot finding | Reviewer's position | Reaction | Comment |
|---|---|---|---|---|
| 1 | Correct, material, no further context | I agree, nothing to add | `+1` | None |
| 2 | Correct, I have additional context | I agree AND want to add | `+1` | Keep inline, "Adding to [bot]'s point above:" |
| 3 | Correct, deferred or out-of-scope | I agree it's a real concern, just not for this PR | `+1` | Body-prose mention in Draft Review Summary |
| 4 | False positive, misleading | I disagree AND author might act on it wrong | `-1` | Inline rebuttal with cited evidence |
| 5 | False positive, immaterial | I disagree AND it doesn't matter | `-1` | None |

**Calibration**:
- Aggressive `+1` on category 1/2/3: the cost is near-zero, the signal to
  bot maintainers is real, and the author benefits from seeing reviewer
  agreement.
- Aggressive `-1` on category 4/5: the cost is near-zero, the signal
  discourages noise patterns, and the author benefits from seeing
  "the senior reviewer thinks this is noise" without having to ask.
- Conservative "no reaction" only on genuinely borderline findings where
  the reviewer cannot form a position even after a quick read.

## Build the Reactions List

For each bot inline comment fetched during Data Gathering that overlapped
with a synthesizer finding during Synthesis Step 2:

1. Classify per the 5-category table above.
2. Determine endpoint:
   - Inline review comments (Copilot, Sentry, Datadog code-quality): use
     `/repos/{owner}/{repo}/pulls/comments/{comment_id}/reactions`
     → endpoint field = `pulls`
   - Issue-level conversation comments (SonarQube, Vercel, PR Metrics,
     Datadog PR-summary): use
     `/repos/{owner}/{repo}/issues/comments/{comment_id}/reactions`
     → endpoint field = `issues`
3. Construct the reaction entry:

   ```
   {
     comment_id: "<NUMERIC REST id, see gotcha below>",
     endpoint: "pulls" | "issues",
     reaction: "+1" | "-1",
     bot_name: "Copilot" | "Sentry" | "Datadog" | "SonarQube" | "Vercel" | "PR Metrics" | ...,
     finding_summary: "<one-line description of what the bot caught>"
   }
   ```

   **Comment-ID gotcha (load-bearing for `issues`-endpoint reactions).** The
   `endpoint: "pulls"` comments were fetched via `gh api /repos/.../pulls/N/comments`,
   whose `id` is already the numeric REST id the reactions endpoint wants. The
   `endpoint: "issues"` comments (SonarQube, PR Metrics, Vercel, Datadog PR-summary)
   were fetched via `gh pr view --json comments`, whose `id` is a GraphQL NODE id
   (`IC_kwDO...`), NOT a numeric REST id. Posting a node id to
   `/issues/comments/{id}/reactions` 404s. Record the NUMERIC id in `comment_id`:
   parse it from that comment's `url` field (`.../#issuecomment-<N>` -> `<N>`), or
   re-fetch via `gh api /repos/{owner}/{repo}/issues/comments`. Capturing it here
   means `/post-review` Step 3.5 posts directly with no resolution step.
   (Observed 2026-07-16, PR #10639: `IC_kwDOJRisZs8AAAABKZzavw` -> `4993112767`.)

4. Append to the `bot_reactions` list.

If a bot comment is in category 1-3 (`+1`) but the reviewer is ALSO keeping
an inline comment (category 2), the inline comment is handled by
synthesis.md Step 2's normal dedup-with-threading rule. The reaction entry
fires regardless.

## Output Rendering

The `bot_reactions` list appears in the briefing output as a structured
section under `### Bot Reactions (for /post-review)`. This section is
output-only (does NOT appear in the posted review body). Format:

```
### Bot Reactions (for /post-review)

- `<bot_name>` comment `<comment_id>` (endpoint: `<pulls|issues>`, reaction: `<+1|-1>`): "<finding_summary>"
- ...
```

Example:

```
### Bot Reactions (for /post-review)

- `copilot` comment `2843291847` (endpoint: `pulls`, reaction: `+1`): "broad except masks auth exceptions in auth.py:42"
- `datadog` comment `2843312900` (endpoint: `pulls`, reaction: `-1`): "no-console flag on the console.warn I explicitly asked for as partial-failure signal"
- `sonarqube` comment `2843312901` (endpoint: `issues`, reaction: `+1`): "python:S1192 - string literal duplicated 3 times in models/foo.py"
```

If no bot comments overlapped with findings, the section is omitted.

## Handoff to /post-review

`/post-review` Step 3.5 consumes this list. For each entry, post:

```bash
gh api -X POST \
  /repos/{owner}/{repo}/<endpoint>/comments/{comment_id}/reactions \
  -f content=<reaction>
```

`/post-review` handles error cases (404, 422 "already exists", 403) per its
own contract. It records the count of successful reactions in the bd memory
write as `bot_reaction_count` (renamed from `bot_endorsement_count` to
match this phase's name).

## Anti-Patterns

- **Do NOT skip the reaction layer to "be conservative."** If a finding has
  a clear truth value, react. Conservatism is for borderline cases only.
- **Do NOT paraphrase the bot's concern in body prose when a reaction would
  suffice.** Body-prose acknowledgment was the OLD behavior; reactions are
  the trust-signal upgrade. The 9276 review on 2026-05-21 is the canonical
  anti-pattern: bot acknowledgment landed as 4-sentence prose paragraph
  ("Re: Copilot's note about the SNS filter policy... acknowledging it
  here so we don't lose the thread") when a single `+1` reaction would
  have communicated the same agreement faster and without diluting the
  review's signal.
- **Do NOT use category 3 (body-prose mention) as a default for ambiguous
  cases.** It conflates "correct but deferred" with "correct but I can't
  decide." If you can't decide, the right move is to not react and to not
  mention; ambiguity belongs in the reviewer's editing pass, not in the
  posted artifact.
- **Do NOT use `-1` as a passive-aggressive signal.** A thumbs-down is a
  factual claim: "this finding is wrong." If the reviewer's position is
  "this finding is correct but I disagree with the priority," use `+1` +
  body-prose mention (category 3), not `-1`.

## Recurrence Context

- `bd memories feedback:bot-comment-reaction-lead-2026-05-20`: the engineering
  lead's original "thumbs-up instead of repeating" feedback
- `bd memories calibration:mx2-decision-maker:ideation:pr-intel-cross-cutting`:
  the /ideate gate that ESCALATE-ROUTE'd to instrumentation-first
- Transcript inspection on 2026-05-21 of PRs #9276 and #9146 R3 sessions
  confirmed zero `gh api .../reactions` calls and zero `bot_endorsement`
  list construction; this file is the structural fix.
