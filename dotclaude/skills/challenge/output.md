# Output contract

The last thing a challenge run emits, whether it ran in this session or in a
fork. A forked run has no dispatch to answer and no conversation to lean on, so
the block has to stand alone: a reader who saw none of the work should be able
to act on it without asking a question first.

Emit the sections below in this order, after the Phase 6 report. Nothing else.

## 1. Headline

One line, and the first line, so a reader who expands nothing still knows what
happened:

    CHALLENGE <plan name> <fragile count> fragile of <total> <CONFIDENCE>

`CONFIDENCE` is one word on the main claim of the verdict: HIGH, MEDIUM or LOW.
HIGH means the adjudications rest on commands run in this run. MEDIUM means the
verdict turns on at least one assumption nothing could verify. LOW means the
plan itself was read at second hand, or most assumptions came back UNVERIFIABLE.

## 2. Handles

The things a reader needs to reopen the work:

- The plan, by path, or the first line of its text when it arrived as text.
- Any file the adjudication rests on, by `path:line`.
- The repository and the commit or branch the greps ran against, when code was read.

## 3. Counts

Assumptions extracted, and the split by fragility. Every number comes from the
table in the report above, not from memory of it.

## 4. Deviations

Where this run departed from the skill as written, and why. A phase skipped, a
specialist not reached, a score overridden. `none` when there were none.

## 5. Sub-agents

Named, with what each returned in one line. `none` when the run did it all
itself. A forked run that spawned nothing writes `none`.

## 6. COULD NOT DETERMINE

Never empty. One line per item that would change what the reader does next: an
assumption no command could settle, a decision that needs a person, a plan
element outside what was handed over. When a run really settled everything it
looked at, the line reads `none, after checking <what>`, and names the check.

## 7. Gaps

What could not be read, as distinct from what could not be decided. A file that
was not there, a repository not on this box, a tool that returned nothing, a
permission that stopped a command. Name the thing and the reason. A silent gap
reads to the next session as a clean pass.

## 8. STATUS

One word plus a clause: `done`, `done, with the gaps above`, or `stopped`, and
what would unblock a stopped run.

## What this block never carries

A self-reported send time, which is stale before it is read. A restatement of
the findings table. An offer to do the next thing. A claim that the run verified
something no command in it touched.
