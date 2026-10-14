---
name: workgroup
description: >
  Slice off a working group from one sentence of Michael's. Reads the problem
  and its parallel parts out of the sentence, picks a lead and one member per
  part from the idle peers on the board by verified model, writes the lead
  brief and the member briefs with Michael's verb quoted in each, lifts a
  standing rule only where the verb needs it, ticks the board, and then hears
  from the lead three ways: a standup at most every twenty minutes, a named milestone, and one RESULT for the whole
  group. Use for "slice off a working group to <problem>", "spin up a
  subgroup for", "give it to a pair", "have them talk to each other and
  report once", "single point of contact for". Orchestrator side. It never
  dispatches outside the group's boundary and never coordinates the members
  itself once the group is formed.
argument-hint: "<Michael's sentence> [--lead <session>] [--dry-run] | milestone <lead> | result <lead>"
allowed-tools: ["Bash", "Glob", "Grep", "Read", "Edit", "Write", "ListAgents", "SendMessage", "Skill"]
---

# Workgroup

One sentence in, one group out, two messages back. The shape was set on
2026-09-09 between 14:19 and 14:22 PDT on PR 56: a Fable session took the
work, an Opus session took the conflict resolution in parallel, and Michael
asked for them to talk to each other, with the Fable as "leader of the
subgroup" and the orchestrator's single point of contact. Two briefs were
rewritten by hand to make that true. This skill writes them from the
sentence.

## Where the protocol lives

Read these before acting. Point at them in the briefs; do not copy them.

- `~/.claude/memory/fleet-dispatch-contract.md`. Clause 28 is this skill's
  contract with the lead. Clause 1 (sub-delegation), 3 (write authorization),
  5 (receipt) and 6 (model routing) shape every brief it writes.
- `~/.claude/rules/fleet-peer-protocol.md`. What a worker owes, the relayed
  verb paragraph of 2026-09-09, and the working-group paragraph once it lands.
- `~/.claude/skills/fleet/SKILL.md`, "Routing new work" (was `usage.md` rule 2). Which model takes which kind of part.
- `~/dev/claude-harness/dispatch/dispatch-prompt-contract.md`. The seven
  clauses every brief follows.
- The most recent `~/.claude/scratch/sdlc-orchestration/BOARD-*.md`. The
  fleet table with each peer's verified model, the standing rules, and the
  worked example under the 21:21Z to 21:24Z ticks of 2026-09-09.

If any of these is missing, say so and stop. Do not form a group from memory.

## Input

`/workgroup <sentence>`, with `--lead <session>` when Michael names one and
`--dry-run` to read everything, form nothing and print what would form.
`/workgroup milestone <lead>` and `/workgroup result <lead>` record the two
later messages on the board.

The sentence is Michael's, in whatever shape it arrives. Four things come
out of it, and the "Dispatching as" line says all four back before anything
is sent:

- **The problem.** One line, in Michael's words where possible.
- **The parts.** The pieces that can run at the same time. Where Michael
  lists them, take the list. Where the sentence names only the problem,
  propose a split in one line and proceed unless Michael objects.
- **The verbs.** Michael's words that authorize the group's writes, quoted
  with their time: a push to a named branch, a page, a repository. A sentence
  with no verb forms a read-and-draft group whose writes go as files through
  the lead to the orchestrator, which asks Michael in its own window.
- **The join.** Where one part needs another's output. A sha, a page id, a
  file. Today's join was commit 1's sha, which the merge waited on.

## The parallel test

Two parts are parallel when each can start now in its own clone or surface
and needs the other only at a named join. Today's merge could be prepared
in full and pushed after the sha arrived, so it was parallel up to the join.

A part that cannot start at all until another finishes, and has nothing to
prepare meanwhile, is a sequence. A sequence is one dispatch with steps, not
a group. A sentence that yields one part is one dispatch. Say which shape
the sentence produced and why, then form that shape.

## Forming the group

**Read the room.** `ListAgents` for who is idle. The board's fleet table for
each peer's model, filled from five-line replies and never from a name.
A peer marked off-limits on the board is not a candidate. A peer whose row
says it holds an instruction from Michael is not a candidate.

**Pick the lead.** The strongest model the problem needs, by the fleet skill's "Routing new work":
Fable for a problem with a judgment in it (a design call, a review that
decides, a body Michael will sign), Opus otherwise. When `--lead` names a
session, use it. If the named session's model is weaker than the problem
needs, say so in one line and proceed; the choice is Michael's.

**Pick the members.** One per part, from the idle peers, by the same rule:
Sonnet for a mechanical part (a move, a scrub, an extraction), Opus for a
part that needs the whole corpus or a draft (a merge across a tree, a page),
Fable never, unless Michael names it. A part with no idle peer of its model
takes the next model up when one is idle, and the line says so. A part with
no idle peer at all goes to the lead in sequence, and the board says so. A
peer is never replaced by a sub-agent of the lead's without the board saying so; a lead may run sub-agents by default (Michael, 2026-09-09 14:36 PDT), and the lead brief
budgets it (clause 1).

**Write the group folder.** `~/.claude/scratch/sdlc-orchestration/<slug>/`,
one `BRIEF-<session>.md` per session. Clone paths sit under the same folder,
one per session, and no two briefs name the same clone. A slug folder that
already holds briefs is a live group: report it and stop. A second group on
the same problem needs a new slug from Michael.

**Write the lead brief.** From the block below. It says four things past the
work itself. Coordinate the members directly. Own the group's write boundary
and the verbs. Send the dispatching session a named milestone and then
exactly one consolidated RESULT, with every member's COULD NOT DETERMINE
under that member's name. Escalate only when stuck. When the brief mandates
sections under a word cap, sum each section's minimum words against the cap
before dispatch and leave room for deltas (2026-09-24: CRITERIA.md measured
964 at its first complete draft against 900, and seven trims followed).
When a member is blind to another member's output, the brief names the board
ticks it may read ("ticks before <stamp>"). A blind brief that says only "read
the board" lets the other member's results in (2026-10-01: a blind Phase 1 read
two ticks that summarized the other reviewer's facts).

**Write each member brief.** From the block below. It says four things past
the work itself. Report to the lead. Message the lead by name. Escalate to
the dispatching session only if the lead is unreachable for the stated
number of minutes. Never share a clone with another member.
For a file two parts both edit, the brief names which part's diff goes first;
the second part copies the file, applies the first diff, and diffs against
that. The member brief points at the shared brief's cap and never restates the
number.
A channel-watch part opens with one broad read: every message in the
channel since the start of the working day, and every thread with replies,
named in the brief or not. A brief that names only the threads it knows
about misses the one it does not. On 2026-09-09 a third thread carried the
channel's delta analysis and a draft pull request link, and it reached the
orchestrator only when another session noticed. A fact the lead already
holds goes in the brief, never in a mid-task correction (2026-09-24: the
50-story set, the rendered column and the prompt's scope each reached dev-91
after dispatch).

**Carry the verbs.** Every brief quotes Michael's words and their time, and
states the scope they cover: this branch, this page, this repository, and
nothing wider. A relayed verb covers the scope it names, per the 2026-09-09
paragraph in the peer protocol.

**Lift a standing rule only where the verb requires it.** Today the 011
branch rule was lifted for dev-87 and dev-2b alone, for that work. The lift
names the sessions and the scope, appears in each brief it covers, and goes
on the board tick. A rule the verb does not touch stays.

**Tick the board.** One tick at formation: lead, members with their parts,
verbs, any lift, the two expected messages with their due times, and the
escalation timer. Stamps from `~/.claude/scratch/scripts/stamp.sh`.
While a member is blind to another's output, the tick for that output gives
the file, its hash and its counts, and none of its content.

**Send.** The lead brief first, then each member brief. Receipt per clause 5:
`ListAgents` about a minute later, resend once to a peer still idle with no
reply.

**Say it back.** The "Dispatching as" line names the shape, the lead, the
members and models, the parts, the verbs and the two messages. Then stop
coordinating. The lead has it.

## While the group runs

The dispatching session expects two messages from the lead and answers
nothing else about the work.

**A member messages the orchestrator.** Reply with one line pointing back to
the lead, and tick it. The exception is the escalation the member brief
allows: the lead unreachable for the stated minutes. Then `ListAgents` the
lead, resend the last message once, and if the lead stays silent promote the
member with the most of the work in hand to lead with a one-line brief
amendment. Tick the board, tell Michael in one line, and go back to waiting
for two messages.

**The milestone arrives.** `/workgroup milestone <lead>`: one tick naming it,
and one line to Michael if the milestone was for Michael ("ready to test").

**The RESULT arrives.** `/workgroup result <lead>`: one tick, then read it
the way any RESULT is read, with each member's COULD NOT DETERMINE section
present under that member's name. A RESULT missing a member's section goes
back to the lead in one line.

**The parts prove sequential inside the group.** That is the lead's to
resequence, and it says so in the RESULT. A member with nothing left to do
is released by the lead with one message to the orchestrator, which counts
as the escalation the lead brief allows, not as a third report.

## Wind-down

The lead's compound covers the group's coordination: what the join cost,
what the escalation timer caught, what a member could not determine. Each
member still writes its own candidate file per the fleet skill's wind-down
brief, from its own transcript. The wind-down message to a member names no
work list (clause 21).

## The lead brief block

```
# <lead> (<model>): lead the <slug> group

From <orchestrator>, the orchestrator. Michael, <date> <time> PDT, VERBATIM:
"<verb sentence>". That is the verb for this group: <scope, and nothing else>.
<lifted rule, if any, naming the sessions it is lifted for and the work>.

## The group
<member> (<model>) holds `<folder>/BRIEF-<member>.md` and owns <part>.
<one line per member>. Each has its own clone under <folder>; nobody shares one.
Shared reading is in `<folder>/BRIEF-shared.md`; each brief below carries
only its own part.

## Your part
<the work, in the dispatch contract's shape>

## Stop when
<what done contains, and the point past which the group stops iterating and
sends a RESULT instead of another draft: a count of drafts, a review with no
blocker, or a time. Michael's `stop-line`, 2026-10-07; on 2026-09-09 a group
with no such line ran eleven versions in eighty minutes.>

## Leading
- Coordinate the members directly, by SendMessage and by name. Questions,
  blockers and their RESULTs come to you, not to <orchestrator>.
- You own the group's write boundary and the verbs above. A member's write
  outside that boundary is yours to refuse. Writes go as files through you to
  <orchestrator>, which asks Michael in its own window.
- Send <orchestrator> a standup at most every twenty minutes: one line on progress since the last, one on what is next, one saying every member answered in that window. Then two more messages: "<MILESTONE NAME>" as the first
  line when <milestone condition>, by <time>; then one RESULT for the whole
  group by <time>, with each member's COULD NOT DETERMINE under that
  member's name. Escalate only when stuck.
  Every message opens with its kind and a handle; a standup says what it
  supersedes, if anything; raw output lives under <folder> and the message
  names the path.
- A member silent for <N> minutes: ListAgents, resend once, then reassign
  or take the part, and say so in the RESULT.
- One draft in flight per reviewer; the next goes out after the review
  lands (clause 17). Collect the signed hash and report it beside the final.
- Before answering a finding "no change", grep the repository's constitution and
  binding docs for the rule the finding touches, and quote the line in the
  answer (2026-10-01: "tolerable at three" was reversed when the third-occurrence
  rule was cited, and a round was spent).
- The reader pass is the last act before the RESULT. An edit after it re-runs
  it, and the RESULT names the hash the verdict covers (2026-09-24: the
  verdict covered b56cf1e0 and the RESULT shipped 31eca5b3). When a meeting
  is judging the same artifacts during the run, the brief budgets a second
  reader pass after the capture lands.
- A stack has one restack owner, named on the board. The owner sends `RESTACK DONE <PR> <head>` for each pull request.
- Checks on a restacked pull request start only after that push. A rebase brief names the PR's own tests first. (2026-10-01: #189's restack changed owner four times, and about thirty minutes of runs were thrown away. A rebased PR answered 401 on its contract test.)
- A standup says "every member answered" only after `~/.claude/scratch/scripts/members-answered.sh <since> <name>...` printed it. Each waiting-on line names its handle and the stamp it was last checked. (2026-10-01: a 22:53Z standup said every member answered since 22:34Z, and one had sent nothing since 22:20Z.)
- Sub-agents: <none | budget>. Never merge the pull request.

## Rules
<write boundary, verbs, checks, plain words, no self-reported stamps>
Instruction lists are bullets, one sentence each, before the first plain-check run (2026-09-24: six LENGTH and CHAIN hits across five briefs and ten in one prompt, each fixed the same way).
- A part that tests an agent file names the model its `model:` line gives, and runs the test on that model.
- A wave's pull requests draft the records their candidates earn (the repository's memory-capture step), in the same review as the code. This line stays in this local template; never put it in a repository file or a pull request (Michael, 2026-10-01 15:53 PDT: "wave-records yes but only locally").
```

## The member brief block

```
# <member> (<model>): <part>, reporting to <lead>

From <orchestrator>, the orchestrator. Michael, <date> <time> PDT, VERBATIM:
"<verb sentence>". That is your verb: <scope, and nothing else>.
<lifted rule, if any>.

<lead> (<model>) leads this group and holds `<folder>/BRIEF-<lead>.md`.

## The work
<the part, in the dispatch contract's shape, with the join named>

## Who you report to
- Report to <lead>. Questions, blockers and your RESULT go to <lead> by
  SendMessage, by name. Not to <orchestrator>.
- Message <orchestrator> only if <lead> is unreachable for <N> minutes, and
  say so in the first line.
- Your clone is <path>. Never share a clone with another member. Never push
  around <lead>'s sequencing.

## Rules
Standing rules apply. plain-check.py and pronoun-check.py clean on what you
write. Instruction lists are bullets, one sentence each, before the first plain-check run (2026-09-24: six LENGTH and CHAIN hits across five briefs and ten in one prompt, each fixed the same way). New today: <verbs, lifts, anything else>. Raw output under
<folder>/<member>/; the message names the path and keeps the verdict line.

## RESULT, by SendMessage to <lead>
Standard shape, first line a fact with a handle. Specific to this part:
<what it must show>. COULD NOT DETERMINE one line per item that changes
what <lead> does next; "none, after checking X" counts.
Sign a draft you review on the file's hash, and name that hash in the
RESULT, so the group can say which text was signed.
```

## When it goes wrong

| Case | What the skill does |
|---|---|
| No idle peer of the needed model | The part takes the next model up if one is idle, named in the line. No idle peer at all: the lead takes the part in sequence, and the board says so. Never a sub-agent in a peer's place without a budget in the lead brief. |
| Michael names the lead | `--lead` wins. If the named model is weaker than the problem needs, one line says so and the skill proceeds. |
| The parts are not parallel | Say so and form the other shape: one dispatch with steps for a sequence, one brief for one part. No group is formed. |
| A member goes silent | The lead's job: ListAgents, resend once, reassign or absorb, deviation in the RESULT. The orchestrator hears of it in the RESULT, not before. |
| An item is reassigned | Whoever reassigns sends the old holder one line: stop, write nothing more under that item, name what you wrote and where. A session that looks dead may still be writing (Michael's `stand-down`, 2026-10-07). |
| The lead goes silent | Members escalate after the stated minutes. The orchestrator resends once, then promotes the member with the most work in hand, ticks the board, tells Michael in one line. |

## What this never does

Dispatch outside the group's boundary. Let a member report to the
orchestrator while the lead answers. Let two members share a clone. Let the
lead merge a pull request. Lift a standing rule wider than the verb. Guess a
model from a session name. Coordinate the members itself once the group is
formed.

## The report

After forming:

```
## Workgroup <slug>, <stamp>

Shape: group | sequence | single dispatch, and why
Problem: <one line>
Lead: <session> (<model>, verified from the board)
Members: <session> (<model>) owns <part>; ...
Join: <what waits on what>
Verbs: <quoted words, time, scope>
Lifted: <rule, sessions, scope> | none
Expect: <milestone> by <time>; RESULT by <time>; escalation after <N> min
Briefs: <paths>
Board: <tick stamp>
```

## Rules

Every stamp comes from `stamp.sh`. Plain words; `plain-check.py` and
`pronoun-check.py` clean on every brief. No em or en dashes. Michael's verbs
are quoted verbatim, with their time, in every brief that relies on them.
A dry run that would form nothing is a finding to explain, never a group
already formed.

## Michael's answers that override the text above where they differ

Michael, 2026-09-09 14:36 PDT, VERBATIM: "The lead can run sub-agents, and the escalation timer should be maximum 20 minutes before a forced checkin ("standup"?) just so we know that (1) it's making forward progress and (2) they're both not dead."

So: a lead may run sub-agents without a budget line in its brief, and says in its RESULT what they did. The escalation timer is at most twenty minutes, never more. And the lead sends the dispatching session a standup at least every twenty minutes while the group runs. Three lines.
- Progress since the last standup.
- What is next.
- Every member answered a message in that window. A standup more than twenty minutes late is the lead going silent, and the table under "When it goes wrong" applies. The standup is short and never carries the RESULT's content.

Michael, 2026-09-09 15:18 PDT, on approvals, VERBATIM: "This is the part that may get hard to scale - I have to go FIND the session to go approve something. It's fine if I'm on my computer, but if I'm on my phone, I'll have to literally peek into each and every session (which, if you look at this fleet size - it's not like it's 2 or 3 sessions, we're at like 10+). It may continue to work \"for now\", but we'll really need to think of a way to be able to delegate an update downstream such that if I tell you (maybe the workgroup does the file edits, and you do the push?), then YOU can ask for permission, and that way I don't have to scramble around to find the right blocked session?"

So a group never asks Michael in a member's or the lead's window. The lead collects every outward write the group needs as a prepared file: a push, a body, a comment, a page, a rule edit. It sends the orchestrator the path and the one line to put to Michael. The orchestrator asks in its own window and relays the answer as a verb with its scope, and the lead acts on it. The lead brief template says so; "escalate only when stuck" includes this.

Michael settled this routing on 2026-09-10 at 11:00 PDT: "Approvals should go through orchestrator - let's try that path for now." (`CLAUDE.md`, Response Behavior, and clause 29 of the dispatch contract).
