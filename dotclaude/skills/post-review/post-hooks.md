# Hook Interactions When Posting

Five hook gotchas that fire on the Step 3 `gh api .../reviews` POST. Each names
the hook, why it fires, and the avoidance pattern. The SKILL.md Step 3 points
here; the canonical avoidance defaults (flat scratch path, write-then-post as
separate commands, --input file) are summarized at the Step 3 pointer.

> **Em-dash guard**: `~/.claude/hooks/block-em-dash.sh` scans the review body
> and all inline comments in the `gh api -X POST /repos/.../pulls/N/reviews`
> payload for U+2014 (in both inline heredoc and `--input <file>` forms) and
> blocks the call on match with exit 2. Sanitize the drafted prose before
> building the JSON payload: replace em-dashes with hyphens, commas,
> semicolons, or parentheses. This guard fires regardless of which skill or
> agent invoked the post.

> **Backticks for code identifiers**: GitHub Markdown parses `__text__` as bold
> and `*text*` as italic. Code identifiers without backticks render mangled in
> the posted review: `__init__.py` becomes "**init**.py", `__all__` becomes
> "**all**", `__str__` becomes "**str**". There is no hook for this (GitHub
> accepts the post regardless), so the discipline is at draft time. Wrap in
> backticks: paths (`libs/models/__init__.py`), dunders (`__all__`, `__str__`),
> class/function names (`Activities.RUNNING`, `update_item`), imports
> (`from foo import *`), config files (`pyrightconfig.json`).

> **Destructive-commands false positive**: `~/.claude/hooks/block-destructive-commands.sh`
> scans the bash command for an `rm <path>` pattern combined with a `-X-r-Y`
> substring and a trailing `*` or path. Review bodies that mention a deletion
> ("rm libs/models", "rm -rf the package") and include any `*` (e.g. quoting
> `from foo import *`) can satisfy the regex when posted via stdin heredoc,
> because the body text becomes part of the bash command. The hook does NOT
> scan file contents passed via `--input <path>`. **Default to `--input <file>`
> for review posts**: write the JSON payload to
> `/home/vscode/.claude/scratch/<pr>-review-<YYYY-MM-DD>.json` first (flat path,
> no subdirectory, date-suffixed per round; see personal-tier-vocab note below), then
> `gh api -X POST .../reviews --input <that-file>`. This sidesteps THIS hook
> (which reads only the command text) without changing the API call shape. It
> does NOT sidestep content gates: the attribution and personal-tier-vocab hooks
> both read the payload file, by design. Treating `--input` as general-purpose
> hook avoidance is how the 2026-08-13 bead-ID leak happened; see the
> personal-tier vocab note below.

> **Personal-tier vocab hook scans the command AND every file it references**:
> `~/.claude/hooks/block-personal-tier-vocab.sh` blocks personal-tier vocabulary
> (the word bead, a `bd` subcommand, a personal slash command like `/pr-intel`,
> and a `docr-` bead-ID slug) on stakeholder surfaces. It scans the bash command
> text and, since 2026-08-13, the CONTENT of every command token that resolves to
> an existing file, not just the first `--input` / `--body-file` match.
>
> CORRECTION (2026-08-13): this note previously said the hook scans "the bash
> command (not file contents)". That was wrong even before the change (it always
> read `--input` files), and the belief is load-bearing: it is why the posting
> pattern drifted toward payload files as a way to sidestep scanners, and seven
> `docr-` slugs reached public PR comments on #11598, #11390 and #11388 as a
> result. The hook ran on every one of those posting commands and returned allow,
> because the body lived in a file it did not open. Do not treat `--input` as a
> way around a content gate.
>
> Two consequences for path choice, both measured:
> - An EXISTING file's path is stripped before the command scan, so a payload
>   filename containing personal-tier vocab no longer blocks on the name alone
>   (`.../scratch/pr-intel/9025-review.json` with clean content now passes).
> - A path to a file that does NOT yet exist is still scanned as prose and WILL
>   block on `/pr-intel`. So the flat-path default still matters, for the
>   same-invocation write-then-post case and for typo'd paths.
>
> **Default to a flat scratch path**:
> `/home/vscode/.claude/scratch/<pr>-review-<YYYY-MM-DD>.json`. No subdirectory
> named after a personal slash command. Coverage probe for which
> posting shapes the hook does and does not see:
> `~/.claude/scratch/test-vocab-hook-surfaces.sh`. Still uncovered, because
> `IS_TARGETED` never fires for them: `gh api graphql` inline mutations, a Python
> subprocess calling `gh`, and `curl`.

> **Write the payload file in a SEPARATE step before the post command.** The
> `block-unattributed-review-comment.sh` PreToolUse hook reads the `--input
> <file>` payload at PreToolUse time, i.e. BEFORE the Bash command runs. If one
> command both writes the file and posts it (`python build.py && gh api --input
> f.json`, or a heredoc that writes then posts), the hook reads the file's
> STALE content from a prior run, not what the current command is about to
> write. The date-suffixed path (`<pr>-review-<YYYY-MM-DD>.json`) makes each
> round a fresh file, so a normal re-review no longer collides with the prior
> round's payload and the stale-content read is avoided. Always: (1) write the
> payload file in its own tool call, then (2) post with `gh api --input` in a
> separate call, so the hook validates the fresh payload. The one residual
> collision is a same-day second round (same date suffix): append `-N`
> (`<pr>-review-<date>-2.json`) so each round keeps its own payload, matching the
> Step 5 memory-key scheme. If you do reuse the path, the Write tool blocks with
> "File has not been read yet", so Read once then overwrite.
