# Code Discipline

Rules for code the model authors, separate from prose-style rules. These exist because the model's default code production has predictable failure modes: over-commenting, premature abstraction, defensive validation against impossible states, and backwards-compatibility hacks that nobody asked for.

## Comments

Default to writing no comments. Code's purpose is conveyed by well-named identifiers, function decomposition, and module structure. A comment is justified only when the *why* is non-obvious to a reader who knows the language and the surrounding code.

Comments should explain non-obvious **current** invariants: a hidden constraint the type system cannot express, a subtle invariant a future maintainer might break, a workaround for a specific external bug with a link.

Do not write:

- **Decision history.** "Bumped from 1024 to 2048 after observing OOM at p99". "Tuned to 0.3 based on April A/B". "Initially used X, switched to Y". "TODO: revisit if memory pressure returns". This belongs in the PR description and ticket, reachable through version control history.
- **Caller, ticket, or fix references.** "Used by X". "Added for the Y flow". "Fixes TICKET-12345". "Handles the case from issue #123". Identifiers and call sites belong in code search; tickets belong in commit messages.
- **Journey or rationale narration.** "We considered X but went with Y because...". "Previously this was...". "This used to handle...". The PR description and design doc are the venue.

Applies to line comments, block comments, JSDoc, and docstrings equally.

## Scope discipline (YAGNI)

- Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup; a one-shot operation doesn't need a helper.
- Don't design for hypothetical future requirements. Three similar lines is better than a premature abstraction. No half-finished implementations either.
- Don't add error handling, fallbacks, or validation for scenarios that can't happen. Validate only at system boundaries (user input, external APIs, deserialized payloads). Inside the codebase, types are the contract. A defensive `if not x` check on a type-narrowed parameter is dead code that hides architectural confusion.
- Prefer editing existing files to creating new ones. Don't proliferate utility modules for one-off helpers. A new file is justified by a clear ownership boundary (a new domain, a new public interface), not by "this didn't fit anywhere obvious."
- Don't use feature flags or backwards-compatibility shims when you can change the code directly.

## Cleanup discipline

Avoid backwards-compatibility hacks:

- Renaming unused variables to `_var` (just delete them)
- Re-exporting types from removed modules
- `// removed` or `# deprecated` comments for deleted code
- `/* @deprecated TODO */` blocks that never resolve

If you are certain something is unused, delete it completely. The git history preserves what was there; the comment in current code is decoration.

## Frontend completion criteria

For UI or frontend changes, start the dev server and verify the feature in a browser before claiming the task complete. Test the golden path AND edge cases. Monitor for regressions in adjacent features.

Type checking and test suites verify code correctness, not feature correctness. If you cannot test the UI in a browser, say so explicitly rather than claiming success.

## Why this exists

The model defaults to over-producing: more comments than needed, more abstractions than needed, more validation than needed, more file-creation than needed. Each is "helpful" in isolation but adds maintenance burden. The discipline pushes against the bias.

A more concrete framing: the question is not "could this code be useful?" but "does this code do anything that types, naming, or function decomposition would not already convey?" If the answer is no, the addition is decoration.

## Where it has limits

- "No comments" is the default; specific domains (cryptography, security boundaries, algorithmic invariants) genuinely need explanatory comments. The discipline is "default no, justify yes" not "never under any circumstances."
- Some teams have stylistic preferences for verbose documentation that conflict with this discipline. Project-tier code style rules can override personal-tier defaults.
- Defensive validation at trust boundaries is correct. The rule is "no defensive validation against impossible states inside the trust boundary," not "no defensive validation anywhere."

## Companion patterns

- `self-review-protocol.md` provides the mechanism for catching violations of these rules (a review pass that asks "is this comment load-bearing?" before the change ships).
- `decision-making-rules.md` includes the "code presence is not deployment evidence" rule, which is the orthogonal "verify what is shipped" discipline.
