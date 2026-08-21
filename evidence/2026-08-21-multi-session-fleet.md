# 2026-08-21: A nine-session fleet with one AI orchestrator, and the four coordination defects it produced (own-loop)

**Source**: the author's own work, a single hard-deadline working day, 2026-08-21. Scrubbed for public version. The primary artifact is a scratch board file the orchestrator session maintained through the day; the corrections are in the author's beads memory under `correction:orchestration:*` and `correction:verification:*`.

**Context.** The day had a fixed end and more parallel work than one context window could hold: a review stack, two production investigations, a ticket-filing sweep, several wiki rewrites, a documentation PR, and a memory-file refactor. The setup that emerged was a nine-session Claude Code fleet on one shared account, mixed model tiers, with one session designated orchestrator on the human's instruction. The orchestrator held no work item of its own: it assigned, tracked, briefed replacement sessions, and routed decisions to the human, on a self-scheduled twenty-minute tick.

This entry is not about the work produced. It is about what broke in the coordination layer, because that layer had no harness support at all going in. The harness had a pattern for the human's fragmented attention across windows; it had nothing for several instances of the same model acting on the same live state under the same identity.

**What AI did.** Four defects surfaced, each with a different mechanism. All four were caught, two of them by luck.

1. *Approval leaked through a relay.* The orchestrator relayed the human's verbatim authorization to a worker session and added that the worker's own approval gate was therefore unnecessary. A peer session pushed back: a relay is context, never the receiving session's consent, and the gate belongs to whoever holds the specific mutation. The orchestrator accepted the correction, recorded it, and then regressed on a different item within hours. Both instances were caught by peers, not by the orchestrator.

2. *A disagreement almost resolved by vote.* One session read a ticket field at one value and built an argument on it. Four peer sessions independently replied that the value was different and that the argument rested on something never there. The session was about to record a self-correction when the owning session produced its own tool results: the field had been created at the first value and changed roughly seven minutes later. The original read was accurate for its moment; all four peers were reading after the change. Four agreeing readers of the same later snapshot is one observation, not four.

3. *Two briefs went out on stale premises.* Both were written by the orchestrator from its board capture rather than from a live read. A third was avoided only because a live re-read before briefing showed the work item had closed overnight. The rule adopted mid-day (re-read the live primary surface immediately before writing any brief, never brief from the board or from memory) is the highest-yield rule the day produced.

4. *A near-collision invisible to every prescribed check.* A handoff described a wiki page as scoped but never written, making it the most obvious remaining deliverable. A recency query run for an unrelated reason found two pages on that exact topic, edited eleven and fourteen minutes earlier by a peer session. The standing pre-flight (search open PRs, list worktrees) returns clean for documentation work because it leaves no local artifact. On a shared account, the peer's edits appeared under the operator's own name.

Alongside the defects, three mechanisms held up well enough to name: state externalized to a board file rewritten each tick, so no session's death lost the fleet's shape; a rotation ritual (finish the atomic item, capture patterns, emit a handoff, human starts the replacement, orchestrator briefs it with ownership boundaries) run four times without a dropped item; and a messaging rule that a peer is contacted only when the message changes its behavior, because every message consumes the recipient's context.

**Baseline.** There is no human-only baseline for this and it would be dishonest to construct one. A single engineer does not run nine parallel work tracks, so the comparison is not "faster than a person." The comparison that is available is against the same fleet without the coordination layer, and even that is not measured: the board, the rotation ritual, and the gate rule were adopted during the day, not held constant against a control.

What can be said concretely: the coordination layer was the thing that failed, four times, in a day where no individual work item's quality was contested. That asymmetry is the entry's only real finding.

**Verifiability.** The mutation-timestamp resolution in defect 2 is the strongest signal: the owning session produced creation and change timestamps seven minutes apart, which is checkable and settles the question independent of who argued what. The near-collision in defect 4 is verifiable from page revision history (two pages, timestamps eleven and fourteen minutes before the query). The stale briefs and the relay regression rest on the board's own record, which the orchestrator wrote, so they are self-reported: the direction of that bias is toward under-reporting, since a session writing its own board is not the party most likely to log its own regression. The three mechanisms that "held up" are the weakest claim in the entry, since nothing counterfactual was run.

**Honest read.**

1. *What this entry supports.* When several instances of the same model act on the same live state under one identity, the defects that appear are coordination defects, not reasoning defects: consent propagating where it should not, agreement mistaken for evidence, briefs built on captures instead of live reads, and collisions in the work classes that leave no local artifact. Each of the four has a specific mechanical answer (relay context and never the gate; find the mutation rather than counting readers; re-read the primary surface before every brief; add a recency query for the artifact class the pre-flight cannot see). The narrow claim: a fleet needs its own discipline layer, and the fan-out disciplines that govern subagents do not cover it.

2. *What this entry does NOT support.* It does not support that fleets are more productive than serial work; nothing here measures throughput. It does not support that nine is a good number of sessions, or that the twenty-minute tick was right; both were improvised. It does not support that the corrections generalize past one operator, one codebase, and one deadline-shaped day. And it does not support that the coordination layer is now sound: the relay defect recurred after being accepted, which is evidence that a rule acknowledged inside a session is not yet a rule the fleet follows.

## Caveats specific to this entry

- *Two of four caught by luck.* The stale-page collision surfaced from a query run for an unrelated reason, and the comparable ticket-sweep defect from the preceding day surfaced from an agent reading a history for a different task. A defect that nobody stumbled onto is not in this entry, and there is no reason to think the caught-to-uncaught ratio is favorable.
- *Self-reported source.* The board is the orchestrator's own account of the day. Peer sessions corrected it several times in-flight, which is some check on it, but the artifact is not independent.
- *Deadline distortion.* A hard end-of-day stop changes behavior: more parallelism, more willingness to accept a partial result, more pressure on the human's answer rate. A steady-state fleet would likely produce a different defect profile.
- *N=1 on every mechanism.* One orchestrator, four rotations, one recalibration of the context meter. These establish that the paths exist and are reachable, not any rate.

## The core pattern: the coordination layer is where multi-instance work fails

Individual sessions did competent work all day. Every defect worth writing down happened between sessions: at a relay, at a shared read, at a brief, at an ownership boundary. That is the load-bearing observation, because it says where to spend the harness's enforcement budget. Making each session smarter would have prevented none of the four. Making the seams explicit (who owns the gate, whose read is newer, what the brief was built from, which work classes are invisible to the pre-flight) would have prevented all of them.

A second, smaller pattern rides along: the context meter itself was miscalibrated by about five points, which made every rotation trigger late on the one measurement where lateness is unrecoverable. Measure the instrument before trusting a threshold expressed in its units.

## Why this entry matters for the repo

The harness had a multi-window pattern for the human's attention and nothing for the model's own parallelism. This day is the origin of `patterns/multi-session-orchestration.md`, and the relay defect is the origin of the gate-ownership clause in `dispatch/dispatch-prompt-contract.md`. Both are written from four caught defects on one day, which is a thin base, and both should be treated as first drafts that the next fleet-shaped day gets to falsify.
