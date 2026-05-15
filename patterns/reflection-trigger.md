# Reflection Trigger

## The pattern

When the user corrects your approach, or when a tool call fails for a non-trivial reason:

1. Extract a 2-3 word topic and classify into a domain (`testing`, `style`, `architecture`, `security`, `debugging`, `verification`, `workflow`, `skill:<name>`, `agent:<name>`).
2. Search persistent memory for prior corrections on the same domain.
3. If a match exists on the same topic and is recent (within 30 days): treat as a two-strike pattern. Invoke a `/reflect` skill (or equivalent) that reads the target artifact, checks for existing coverage of the rule, and proposes a single targeted edit.
4. If no match: save the correction as a durable memory entry (key pattern: `correction:<domain>:<specific>`, with a one-line summary and date) and continue working.
5. **Stop tallying when reflection has converged.** If a `/reflect` pass concluded "no edit needed" AND an umbrella memory plus structural enforcement (hook, linter, gate, formatter) are both already in place, do not save another date-stamped recurrence entry. The umbrella memory is sufficient. Repeated dated tallies are not a corrective action; they entrench an adversarial framing without shifting the default behavior the rule is trying to capture. If the same topic recurs past this point, the next move is mechanical (a different enforcement layer, e.g., post-output sanitizer, model-side prompt wedge), not procedural (more memories, more rule sharpening).

## Why this exists

Corrections made mid-conversation evaporate on compaction. The model adjusted its behavior for the remainder of the session, but the next session starts cold and slips on the same thing. Persistent-memory entries with a typed key namespace turn ephemeral corrections into durable rules. The compounding effect is the load-bearing benefit.

The two-strike threshold matters: a single slip might be a one-off, and saving every slip as a rule would bloat the rule set. Two strikes within a 30-day window signals a recurring pattern that warrants structural change.

## The rationalizations to refuse

The mechanism is fragile to "I'll skip it just this once" thinking. The honest answer to each rationalization:

| Rationalization | Reality |
|---|---|
| "This correction is too minor to reflect on" | You cannot judge significance without searching memory. Extract and search. |
| "I'll remember this for next time" | You will not. The conversation will compact. Save it or lose it. |
| "The current task is more urgent" | Search-and-save takes under one second. There is no urgency tradeoff. |
| "I already adjusted my behavior" | Adjusting in this conversation is not adjusting in future conversations. That requires a durable artifact. |
| "I should log this slip as a recurrence memory for the record" | Only if no umbrella memory plus enforcement exist yet. After both are in place, dated tallies are performance, not progress. |

## How this compounds

After several months of use, the memory store accumulates a typed catalog of personal anti-patterns: which mistakes the model makes by default, which rules were authored as corrections, which enforcement layers exist. The catalog itself becomes a portfolio artifact: a working theory of where the model fails by default, evidenced by the corrections that prevented recurrence.

## Where it has limits

- The corrective is conversational. Tooling failures (a tool that consistently returns wrong results) need a different intervention; reflection alone cannot fix the underlying tool.
- A correction can be wrong. If the user's correction was itself a mistake (a misread of the situation, a one-off frustration), saving it as a durable rule entrenches the wrong heuristic. The `/reflect` skill (when it runs) is the check on this: it reads the artifact and asks "is this actually a coverage gap?" before proposing an edit.
- Pattern recognition has a long tail. Very rare slips will not hit the two-strike threshold and will not get rules. Acceptable: rare slips have low aggregate cost.

## Companion patterns

- `two-strike-pattern.md` (in `scaffolding/`) describes the umbrella-memory-plus-enforcement mechanism that the trigger feeds into.
- `self-review-protocol.md` is the prophylactic counterpart: catch slips before they happen, rather than logging them after.
