# Two-Strike Pattern

The mechanism that turns repeated corrections into durable rules and prevents further recurrence through structural enforcement.

## The pattern

When the same correction fires twice on related topics within a recent window (typically 30 days):

1. **Save an umbrella memory** that captures the principle, not just the instance. The key takes the form `correction:<domain>:<umbrella-topic>` rather than `correction:<domain>:<specific-instance>-<date>`. Multiple specific instances feed into one umbrella entry.

2. **Add a structural enforcement layer** that catches future slips without relying on memory. Options ordered by strength:

| Enforcement layer | When it applies | Example |
|---|---|---|
| Hook (pre-tool-use, stop, post-output) | When the slip can be detected programmatically | em-dash detection on file writes and chat output |
| Linter or formatter | When the slip is in source code or formatted output | spell check, type check, lint rule |
| Gate or validator | When the slip is in a structured artifact | PR description template check, frontmatter schema check |
| Prompt wedge | When detection is harder; a CLAUDE.md rule or agent-prompt addition | "Don't mirror Michael's informal register" rule |

3. **Stop tallying further recurrences.** If the umbrella memory exists AND a structural layer exists, do NOT save more date-stamped recurrence entries. Repeated dated tallies are not corrective; they entrench an adversarial framing without shifting default behavior.

## When to add a new enforcement layer

The decision is per-recurrence:

- 1st slip: save a dated `correction:<domain>:<specific>-<date>` entry. No structural change needed.
- 2nd slip (within ~30 days, same topic): umbrella + structural enforcement now. The corrective is no longer "remember to not slip"; it is "the system catches the slip."
- 3rd+ slip past umbrella+enforcement: the existing enforcement is failing. Add a different layer (a different hook, a stronger linter, a prompt wedge in a different location). Do NOT add another umbrella memory.

## Examples observed in this harness

| Slip | Umbrella memory | Enforcement layer |
|---|---|---|
| Em-dash usage in chat output | `correction:style:em-dash` | Pre-tool-use hook + stop-validate hook |
| Gendered pronouns inferred from names | `correction:identity:a peer reviewer-pronoun` and similar | CLAUDE.md "Default to gender-neutral language" rule (prompt wedge) |
| Pasting tokens in chat | `gotcha:git-push-u-url-leaks-token` | Behavioral rule (avoid suggesting token-in-URL forms) |
| PR description template skipping | `correction:workflow:pr-description-template` | Repo PR template requirements; `block-personal-tier-vocab.sh` hook |

## Why this exists

A correction that stays in conversation context evaporates on compaction. A correction saved as a dated memory persists but does not change behavior; future sessions read the memory, "agree" to remember, slip anyway. The corrective is structural enforcement: a hook or linter that catches the slip independent of model agreement.

The two-strike threshold matters: a single slip might be a one-off. Saving every single slip as an umbrella plus enforcement would over-engineer the harness. Two strikes on related topics within a 30-day window signals a recurring pattern that warrants structural change.

The "stop tallying" rule matters because dated recurrence entries past umbrella-plus-enforcement are not progress; they are theater. The harness collects them, the author notices the collection, and the framing becomes "I keep slipping despite the rule," which is adversarial. Stopping the tally redirects attention to "the enforcement is failing, what mechanical change fixes this?"

## How this compounds

Over months of use, the umbrella memories and enforcement layers accumulate into a working theory of "where does this model fail by default, and what mechanism prevents it?" The catalog itself is portable: another model + another harness combination benefits from the same enforcement patterns, because the underlying failure modes are model-class properties.

## Where it has limits

- Some slips cannot be detected programmatically (subtle reasoning errors, mis-routed dispatch decisions). For those, the prompt-wedge enforcement is the only option, and prompt-wedges are weaker than hook-based enforcement.
- The two-strike threshold is heuristic. Some patterns warrant umbrella-plus-enforcement on the first slip (security-sensitive mistakes); others might warrant waiting for three strikes (cases where the corrective is expensive and the slip is rare).
- Enforcement layers themselves can have bugs. A stop hook that fires false positives on legitimate content costs round-trips. The discipline is "tune the enforcement; do not abandon it."
