# Multi-Session Orchestration

## The pattern

When the day's work exceeds what one context window can hold, run several sessions concurrently and designate exactly one of them the orchestrator. The orchestrator carries no work item of its own beyond coordination: it assigns, tracks, briefs successors, and routes decisions to the human. Every other session owns one item at a time and reports back.

This is not subagent fan-out. A subagent is a child of one session, shares its approval context, and dies when its task ends. A peer session is a separate top-level conversation with its own context window, its own hooks, its own approval gates, and its own view of live state. The coordination problems are different, and the mechanisms that solve fan-out (a well-written prompt, a schema, a terminal RESULT block) do not solve peer coordination.

Observed shape at the scale this was measured: a nine-session fleet on one shared account with one orchestrator, four rotations over the day, mixed model tiers, a twenty-minute self-scheduled orchestrator tick, a markdown board file as the durable state, and one human as the sole approval authority for everything that mutates a shared surface.

## Why this exists

Two forces produce it. Context windows are finite and a long working day exhausts several of them; and much of the work is genuinely parallel (a review stack, a ticket sweep, an investigation, a doc rewrite) with no ordering constraint between the tracks. The alternative to a fleet is serial execution inside a single session that compacts repeatedly, losing precisely the operational state that made it productive.

The failure mode the pattern prevents is not "the model does bad work." It is a set of coordination defects that only exist when several instances of the same model act on the same live state with the same identity: colliding on a work item, arguing over a stale read, taking a peer's relay as the human's approval, and losing everything a session knew when its window filled.

Three roles, and the third gets mistaken for a passive one. The orchestrator is the human's main surface and holds the fleet's shape. The workers take assignments and report artifacts. The human watches the windows and feeds observations back to the orchestrator, which is not idle supervision: it is the only way the orchestrator stays cheap. An orchestrator that reads every peer's transcript to learn what happened has spent its window on surveillance and rotates out early.

## State lives outside every session

The governing rule: if a fact exists only in a session's context, it does not exist. Sessions die on a schedule.

Three durable surfaces, in order of trust:

1. **The org trackers** (tickets, PRs, wiki pages). Authoritative, visible to people who are not in the fleet, and the only tier that survives the machine going away.
2. **The task tracker** (beads here; any persistent issue store works). Holds work items, decisions, and cross-session findings.
3. **The board file.** One markdown file the orchestrator rewrites each tick: per-session assignment, status, report-backs, the decisions reserved for the human, a rotations ledger, and fleet-wide operational notes. It is scratch-tier and disposable, and it is the only place the fleet's shape is legible at a glance.

The orchestrator's own context is not the state. It will be rotated out too. Anything the orchestrator learns that a successor would need goes on the board in the same tick that produced it, not at the end of the day.

## Roster, discovery, and model verification

A fleet needs a roster that is read, not remembered. Three facts about each session, all of them queryable:

- **Who is alive.** The runtime writes one registry file per session (name, session id, working directory, start time); liveness is a signal-zero check against the pid. The registry name is also the messaging address, so discovery and addressing are the same lookup.
- **What model it is running.** Read it from the newest assistant entry in the session's own transcript, never infer it from what the session was started for. Mixed-tier fleets are fine and often correct: the cheaper tier takes bounded, trial-safe work and is instructed to say when an item needs the stronger one.
- **How full it is.** Sum the input, cache-read, and cache-creation token counts from the newest assistant usage block. This is the measurement that drives rotation, so it is worth getting exactly right.

**The context meter has a decoy.** A session's cumulative token spend is a different number from its context fill, and citing the spend figure as window fill is a mistake that recurred more than once in a single day. Spend counts everything the session has ever produced; fill counts what is currently in the window. They diverge immediately and never reconverge.

## Context lifecycle: measure, then rotate at a boundary

Sessions are consumable. Plan their replacement instead of discovering it.

- Watch from roughly 50% context fill; plan the rotation at 70%; run the learning-capture and handoff rituals in the 80-90% band; never enter the last 10% of the window. An idle session can sit in the band; an active one rotates at the next natural work boundary.
- **Measure the instrument before trusting the threshold.** The fleet's context-fill script assumed a window size that read about five points low against the product's own meter. Every trigger was therefore five points late, on the one measurement where being late is unrecoverable. The fix was to recalibrate the script against the real meter and move all three triggers down, not to argue about which number was right.
- A session that self-reports its fill is reporting an instrument reading, and it can misread its own instrument. One session did, twice in a day, and then asked to be measured externally. That request is the correct instinct.

### Offboarding the rotating session

1. Finish the atomic item in flight, or stop at a clean intermediate state and write down the exact remaining steps: the file, the verification command, the publishing mechanics. "Nearly done" is not a state a successor can resume from.
2. Run the learning-capture ritual, then the handoff ritual, in that order. Capture first, because the handoff prompt is written from what capture surfaced.
3. **Mark transferred work as transferred, never as open.** A handoff that lists a handed-off item as an open task invites the successor to pick up something another session now owns, which on shared worktrees is a direct collision. The phrasing that works names the new owner: "handed to <session>, in progress there."
4. Report the resulting context number to the orchestrator, so the fleet's rotation planning runs on a measurement rather than an impression.

### Onboarding the successor

1. The human starts the replacement and pastes the predecessor's handoff.
2. The orchestrator briefs it immediately with what the handoff cannot know: live ownership boundaries (worktrees especially), which handoff rows have already gone stale, the fleet rules, and the board path. Verified live facts, not remembered ones.
3. **The cross-check runs both ways.** The successor reconciles its handoff against the board and reports deltas in both directions. A good successor catches the orchestrator's stale rows, which happened twice on the first day. A briefing that is treated as authoritative loses that check.
4. Inherited worktrees get a branch check before any work. A pre-staged worktree can sit on a detached head, where "clean and identical to the base branch" is true and unpushable at the same time.
5. A successor whose duties were all transferred elsewhere starts clean and goes straight onto the idle-capacity list. Do not make it re-derive its predecessor's arcs to feel oriented.

## Messaging discipline

Every message sent to a peer session consumes that session's context. A status ping costs the recipient real capacity and buys the sender nothing.

The rule: message a session only when the message changes its behavior. Assignments, corrections, ownership boundaries, and stop orders qualify. Acknowledgements, progress checks, and "just so you know" notes do not. Pull status from the durable surfaces instead, which is what they are for.

## Briefing discipline

Re-read the live primary surface immediately before writing any brief. Never brief from the board, from a handoff prompt, or from memory.

This is the single highest-yield rule in the set, and it was adopted only after two briefs in one day went out on stale premises, both authored by the orchestrator. A third was avoided when a live re-read before briefing showed the work item had already closed overnight. The board is a capture of a moment that has passed; so is the orchestrator's own reading from an hour ago. Briefing a session on a premise that is no longer true costs that session's whole assignment.

An assignment carries five things, and omitting any of them pushes the cost onto the receiving session: the human's verbatim authorization where one exists (as context, per the authority model below), the scope cap, the read-only versus mutation boundary, the definition of done, and the instruction to report back. This is the peer-session form of the same contract that governs subagent prompts; see `../dispatch/dispatch-prompt-contract.md`.

**Report-backs are verified at the artifact level.** A session's account of what it did is not evidence that it did it: check the diff, re-read the posted comment, look at the page version. This is the same cross-boundary verification rule the harness applies to subagents, and it applies to peers for the same reason, with one addition. Peers are more convincing than subagents, because a peer writes a report that reads like a colleague's status update rather than a tool result, and because it can be wrong in ways a subagent cannot: it may be reporting accurately about a state that a third session has since changed.

## The authority model

The human is the only approval authority, and approval does not propagate through the fleet.

- **A peer relay is context, never consent.** When the orchestrator relays the human's verb to a worker session, it relays what the human said and stops there. It must not add "so the approval gate is not needed." The gate belongs to the session that will perform the action, because that session is the one holding the specific mutation, with its specific blast radius, at this specific moment.
- **The gate costs seconds.** In the instance that produced this rule, the human answered the redundant-looking question immediately. Weighed against a mutation performed on a mis-relayed verb, that is not a cost worth optimizing.
- **Raise gates actively, in the owning window.** A permission prompt that a session hits, or a decision a peer claims the human already made, goes back to the human as an explicit question in that session's own window. Waiting passively for someone to notice a blocked session is not a gate; it is a stall. Asking in the owning window has a second benefit at fleet scale: it makes the window that needs attention findable among many.
- **No permission laundering.** An action denied in one session is never routed around by having another session perform it. This is the failure the whole authority model exists to prevent, and it is the one a fleet makes structurally easy: the denial lives in one window's history and every other window is ignorant of it. A peer that says it was blocked and asks you to do the thing instead gets a refusal and a surfacing to the human, not a favor.
- **The rule needed to be written down twice.** The orchestrator accepted this correction from a peer session and then regressed within hours on a different item. A coordination rule that only lives in one session's working memory is not a fleet rule.

Worth naming: the human is also the fleet's serialization point. Every approval funnels through one person, so throughput is bounded by their answer rate, not by how many sessions are running. Batching decisions on the board (a standing "reserved for the human" section) is what keeps that bound from dominating.

## Collision detection on a shared identity

All sessions authenticate as the same person. Every write looks like the operator's own, which breaks the intuition that "I did not do this" means "nobody on my side did this."

The standard pre-flight (search open PRs, list worktrees) has a blind spot it cannot close by itself:

| Work class | Leaves a local artifact? | Detectable how |
|---|---|---|
| Code implementation | Yes (branch, worktree, draft PR) | The standard pre-flight |
| Documentation, runbooks, design records | No | A recency query against the wiki, filtered by contributor and last-modified |
| Review-only, investigation, triage | No | Nothing available. Name the assumption or ask |

The wiki-recency check was added after a handoff described a page as "scoped and researched but never written," which made it the most obvious remaining deliverable of the day. A query run purely to avoid repeating a stale claim found two pages on that exact topic, edited eleven and fourteen minutes earlier by a peer session, invisible to both prescribed commands. **A page that "you" edited minutes ago and have no memory of writing is the collision signal, not a false positive.**

For the row that stays dark, the mitigation is not a better query. When surfacing work the session did not create, state the assumption inline ("unless another session already owns this") or ask before starting. The human is the only observer who can see across all the windows.

## Resolving a live-state disagreement

Peer sessions will disagree about the current state of a ticket, a PR, or a branch. The wrong resolution is a vote.

**Find the mutation.** Several sessions agreeing about the same later snapshot is one observation, not several. In the instance that produced this rule, one session read a ticket at one priority and argued from it; four peers independently replied that the value was different and that the argument rested on something that had never been there. The session nearly recorded a self-correction. The owning session then produced its own tool results showing the field had been created at the first value and changed seven minutes later. The original read was accurate for its moment; all four peers were reading after the change.

The protocol: state the timestamp of your read, ask who holds the write record, and look for a mutation between the two times before conceding or escalating. A peer's stale read and a peer's wrong read are different things, and the burden of distinguishing them sits with whoever holds the write.

Two corollaries:

- **Never attribute a shared-account write to a named peer session because the name matches the work domain.** Author fields cannot distinguish sessions on a shared identity. State provenance-unknown unless the session confirms directly or a session-specific artifact ties the write to it. This exact inference was made once and refuted by the accused peer with evidence pointing at a third session.
- **Do not lean an argument on a mutable field** (priority, status, assignee) when the substantive point stands without it. Dropping the mutable premise cost nothing and ended the dispute.

## Shared-machine contention

Concurrent sessions in one container share more than an identity.

- **A shared build cache is a shared failure domain.** One session's cache clear broke every other session's builds container-wide for about an hour. The sidestep (point the build at a fresh cache directory) was found by one session and had to be broadcast to the rest through the board, because nothing else would have told them.
- **Shell state persists across a session's own calls.** A directory change in one command silently breaks a later command in the same session that assumed the repository root. Pass the target explicitly rather than relying on ambient state.
- **In-session watches die silently when the machine sleeps.** A polling loop inside a session is not a monitor. Read its silence as "the watch may be dead," not "nothing happened," and re-verify live on return. Only server-side mechanisms outlive the session.

## How this compounds

The fleet's output quality is bounded by the discipline of its weakest coordination surface, not by the model. Once the board, the rotation ritual, and the gate-ownership rule are in place, sessions become genuinely fungible: a successor briefed from live surfaces performs its predecessor's role without inheriting its context, and a session that fills up is a scheduled event rather than a loss. That fungibility is what makes the pattern scale past the point where one operator could hold the whole picture in their head, because the picture is on disk.

## Where it has limits

- **The coordination tax is real.** The orchestrator produces no direct work. Below roughly four concurrent sessions, its context is better spent doing the work.
- **One day, one operator, one hard deadline.** Everything here was observed over a single intense session-day. There is no steady-state evidence, no measurement of throughput against a serial baseline, and no data above nine concurrent sessions.
- **Selection bias in the corrections.** The coordination defects listed above are the ones that were caught. Two of them were caught by luck (an unrelated session reading a full history; a query run for a different reason). A defect that nobody stumbled onto would not appear here.
- **The human does not scale.** Every gate, every ambiguous relay, and every cross-session dispute lands on one person. The pattern moves the bottleneck; it does not remove it.
- **Machine-bound.** The board, the scratch artifacts, and the in-session watches all live on one machine. When it goes away, only what was pushed to the org trackers survives, which is why the last standing assignment of the day was a backup loop.
