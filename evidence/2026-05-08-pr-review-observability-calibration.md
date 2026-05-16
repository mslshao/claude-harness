# 2026-05-08: PR review observability calibration (own-loop)

**Source**: author's own recall in a DM, 2026-05-08, describing a prior /pr-intel run. The work itself happened earlier; the slack message is the retelling. Scrubbed for public version (no PR number, service names, function names, or org-specific identifiers).

**Context.** A PR removed the project's structured-logging initialization helper from a handful of lambda services. The structural concern: that helper installs the JSON formatter Datadog ingests for log search and alerting. Removing it without replacement would cause the affected services to fall back to plain-text logging, breaking dashboards and alerts that depend on structured fields.

**What AI did.** Author invoked the harness's PR review skill (`/pr-intel`), which dispatches a panel of specialist agents in parallel against the diff. The `observability-reviewer` specialist auto-fired on the diff signal (a known helper removed from multiple files) and returned a BLOCKING finding: five lambda services would lose structured JSON logs.

Per the harness's "verify falsifiable specialist claims" rule, the author then ran a Datadog spot-check against those five services before posting the review. The Datadog data showed only two of the five services actually emit structured records today; the other three had already been emitting plain-text logs.

The review comment that landed on the PR was calibrated: not BLOCKING, but a COMMENT with per-service impact stated explicitly (which services would actually regress, which were already on plain-text). The author posted that comment as his own, with the per-service breakdown.

**Baseline.** Without the harness, the same review would have followed a different shape:

- Reading the diff manually, the author might or might not have noticed the structural concern. The signal is subtle (a function call removed in multiple files); it is the kind of thing a fast pass misses.
- If noticed, the natural first response is "this looks risky for the structured logging path, flagging." Severity calibration would come from intuition about the helper's role, not from production state.
- Per-service verification requires N Datadog round-trips (find each service's log stream, sample, classify); a tedious enough loop that the author would likely have posted the BLOCKING comment as-is and pushed verification onto the PR author.
- Result: either a generic "be careful with this removal" comment OR a blocking review based on an assumption that production state would have falsified.

**Verifiability.** The Datadog query is reproducible against current production logs; the observability-reviewer behavior on this class of diff signal is reproducible (it auto-fires on helper-removal patterns); the verify-before-asserting rule is codified in the author's CLAUDE.md and visible in this repo. The PR's review comment is a public artifact in the firm's monorepo.

**Honest read.**

1. *What this entry supports.* The combination of (parallel specialist dispatch + verify-before-asserting rule) produced calibrated review output that human-only review would not have produced on its own. Specifically: the specialist caught a structural concern a quick scan would have missed, AND the verification rule sized the concern correctly using production state. The end output (per-service-specific COMMENT) is what an ideal human reviewer would have produced after several Datadog round-trips; the harness compressed those round-trips.

2. *What this entry does NOT support.* This anecdote does not measure wall-clock time. It does not show the harness consistently calibrating BLOCKING claims down to COMMENT severity; one PR is N=1. It does not generalize beyond observability concerns in code review. It does not show what happens when the specialist is wrong in a different direction (false negatives are invisible to this anecdote).

## Caveats specific to this entry

- **Selection bias**: the author remembered this case because the verify-before-asserting step caught something. Plenty of `/pr-intel` runs produce noise that doesn't survive the verification step; this one happened to land cleanly with concrete production data.
- **Tooling-generation note**: a year ago, the Datadog MCP server did not exist; the per-service spot-check itself was AI-accelerated. Part of the compression is "tools are better," not "harness is special." The harness contribution is specifically the dispatch + verification discipline; the verification itself is downstream of MCP availability.
- **Sample-size note**: N=1. Whether the harness consistently downgrades BLOCKING claims to calibrated COMMENT after verification is a claim that needs more entries. This one supports the direction; it does not establish the rate.

## What this case actually evidences about the harness

The harness's value here is the chained mechanism, not any one component:

1. `/pr-intel` invokes specialists in parallel without the human deciding which to invoke.
2. `observability-reviewer` fires automatically on a diff signal a generalist reviewer would not have routed itself toward.
3. The harness rule "verify falsifiable specialist claims before posting" interrupts the natural path from finding to review comment, inserting a production-state check.
4. The final review output reflects production reality rather than diff-only reasoning.

Without all four steps, the output regresses to either (a) no observability finding (specialist not invoked), or (b) an over-confident BLOCKING claim (verification step skipped). The chain is the unit; pulling any link makes the output worse.

## What would strengthen this entry

A second entry where the verification step inverted the call in the opposite direction (specialist returned a COMMENT, verification escalated to BLOCKING based on production state). That would evidence the rule's symmetry. Pending.
