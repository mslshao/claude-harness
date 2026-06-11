# Contrapositive-Proof Authoring

## The pattern

A model reads the rule corpus, the skill spec, and the agent definition as an executable specification, and it follows the structure literally. A human reader supplies intent the prose omits; the model does not. So when you author a rule that a model will read:

1. **State unconditional principles outside conditional scopes.** A principle that always applies must not sit nested inside an `if` clause. A reader walking the rule top-down sees the condition first and the principle as a clause under it, which makes the principle look conditional on the very thing it was meant to be independent of.
2. **Mark numeric thresholds as one-way triggers.** A threshold gates an action in one direction only: over the threshold implies the action; under the threshold implies nothing. Write the threshold so the contrapositive is closed off. "Over N lines, split the PR" must not be the only sentence, because a literal reader takes "under N lines" as a license to do the opposite (bundle freely).

The failure these prevent is the same shape: a principle nested inside a conditional invites the contrapositive. A literal-reading model treats "below the threshold" as license for the opposite of what the principle requires.

## Why this exists

The concrete instance: a PR-size rule carried two distinct ideas, an unconditional one-concern-per-PR principle and a size heuristic (a ~250-line trigger above which a PR should split). The prose NESTED the concern principle inside the size conditional. A planning session driven through a more literal rule-reading model (a Fable-class model) read "under 250 lines" as licensing multiple concerns in one PR, and a verify-and-refine pass rubber-stamped the sizing claim because the rule prose, read literally, allowed it.

The fix was structural: state the concern principle UNCONDITIONALLY, outside the size scope, and mark the size number as a one-way trigger (over the threshold implies split; under the threshold does NOT imply bundle). The contrapositive license is removed because the principle no longer sits inside the conditional. A forward-verification replay shows the model explicitly REJECTING "under the trigger" as a justification and re-grounding on concern-mapping, where the old text had licensed it.

The asymmetry is the point. A human reading the old rule applies intent ("of course the concern test still applies") and never notices the nesting. The gap is invisible from the human side precisely because the human supplies the intent the prose omits. A literal model takes the contrapositive instead. The rule corpus is the program the agent executes; an ambiguous branch in it is not a typo, it is a behavioral bug that ships silently.

See `evidence/2026-06-11-rules-as-executable-specs.md` for the full write-up, including the honest bound: the fix is verified forward (the rewrite demonstrably moves the model in the intended direction in replay), but the original red was N=1 and not reproducible on demand, so the claim is "the rewrite changed the model's reasoning," not "the old text reliably caused the failure."

## How this compounds

Every rule authored this way removes one latent contrapositive from the corpus. Because the corpus is read literally and applied across every session, the payoff is not one avoided slip; it is the closing of a branch that would otherwise license the wrong behavior every time a literal-reading model walks that rule. The discipline also transfers: once you see rules as a program, you start auditing existing rules for nested principles and unguarded thresholds the same way you would audit code for an unhandled branch.

## Where it has limits

- The failure mode is partly a property of which model reads the spec. A more literal generation takes the contrapositive where a less literal one supplies the missing intent. Authoring unconditionally is cheap insurance regardless, but you cannot assume every model would have slipped.
- Closing the contrapositive removes a license; it does not encode a standard that was never written down. In the concrete instance, the rewrite removed the under-threshold bundling license but did not capture the reviewer's unwritten "shared-module changes ship as their own stacked PR" standard. Structural clarity is not a substitute for ratifying the standard itself.
- Not every threshold is one-way. Some genuinely gate in both directions (a value that must be between a floor and a ceiling). The rule is to mark the directionality explicitly, not to assume it is always one-way.
