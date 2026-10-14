---
name: sdlc-launch
description: The SDLC bundle's phase skill for the gate act into implementation, testing refusal conditions, surfacing the ranked batch, writing the state transition on a permit.
---

# Skill: launch, the gate act into implementation

## Status

**Runs today.** A session can follow this skill now, end to end. It reads the spec record, the plan's decisions file, the state file and the predecessor's approval record, tests each refusal condition below, surfaces the ranked batch, and on a permit writes the state-file transition, the metrics row, the decision entries the approve settled, and the context handoff for the session that follows. Every step is specified, with one exception named in place: the shape of the implementation conflict record is open, so a session that meets a conflict records it under the lean in Outputs and says the shape is unsettled.

**Manual today.** The structured approve is a message in an agreed format rather than a button. The hash comparison is done by whoever runs the phase, reading the recorded hashes against the content. The handoff to the operator session is started by a person.

**Not built.** The command that writes the records. The guard that enforces the can-start rule without anyone checking. The approve button and the webhook behind it. Until those exist, the refusals below hold only because the person or session running the gate applies them.

Every rule below names where it came from, and the open questions are named rather than answered.

**The portability rule:** this skill references bundle files and application repository files only. Never a personal agent, a personal rule, or anything in one person's home directory.

## Name and purpose

`launch` is the human-gated crossing from planning into implementation for one unit of work. Decided by Michael, 2026-09-01; `decisions/0008-launch-and-cold-review.md` in the bundle folder.

It refuses or it permits, and it leaves a record either way. On a permit it also generates: the decisions the crossing itself settles, a record of any conflict between the ratified plan and the state the work is actually launching into, and the documentation the implementation session needs to start. Those are outputs of the act, not paperwork around it, and the Outputs section lists them.

What it is not responsible for: the plan, the implementation, or the review of either. It does not decide anything the plan left open; an unanswered human-class entry is a reason to stop, not a thing for this act to rule on.

## Where it runs

At the boundary after the plan summary and before execution.

The plan summary is a hard stop. `rules/record-contract.md` states it directly: plan summary never takes proceed, and it is a hard stop even where the phase reports nothing open. So the gate before implementation cannot be satisfied by the proceed verdict that other phases may take; it needs an approve, with per-decision verdicts and a named approver.

## Inputs

- The spec record for the unit, as `templates/spec-record.md` in the bundle folder. This is what the run loaded, and it is hash-bound to the ratified spec content.
- The plan phase's decisions file, as `templates/decisions-file.md`, every entry complete.
- The slice's state file, as `templates/state-file.md`: which phase is next, its status, its round.
- The predecessor phase's approval record, as `templates/approval-record.md`.
- The recorded hashes against the current content.

All of them by path. Nothing this act reads comes from a chat message, because a verdict in a chat message is not an approval (`CLAUDE.md`, the record discipline).

## Preconditions

The can-start rule in `rules/record-contract.md`: the predecessor phase is approved, its recorded hash still matches the current content, the successor is pending, and this session holds the lock. On any failure the act stops and says which part failed.

## What it refuses

Refusal is the point of the act, so the list is explicit.

- **No approval record.** A skip is a record with a reason, never an absence, so a missing record is a missing decision and implementation does not start.
- **A hash that no longer matches.** A record whose content no longer matches is treated as absent. The same rule appears everywhere in the contract and it is what stops a stale approval from carrying a run forward.
- **An approval bound to different content than the plan being launched.** The approver approved what they were shown. If the plan moved after the approval was written, the approval is for something else.
- **A proceed where an approve is required.** Per the hard stop above.
- **An unanswered human-class entry in the plan's decisions file.** Class is computed from the phase's two committed lists, and an entry matching neither list is human-class (`rules/decision-discipline.md`).
- **A batch that was truncated rather than ranked.** An entry below the batch line stays in the file with its assumption flag set. If it is missing rather than flagged, the record is incomplete.

Nothing autonomous crosses this gate. That is the constraint the whole act exists to hold.

## Steps

1. Read the spec record and confirm its hash still matches the ratified spec content. If it does not, stop: the unit being launched is not the unit that was ratified.
2. Read the plan phase's decisions file and the slice state file. Confirm the plan phase is where the state file says it is.
3. Run the two screens in `rules/decision-discipline.md` over the plan's entries: deduplicate against decisions already ratified, and check for a hidden assumption. Neither screen invents an answer; both move an entry out of the batch and into the file with its flag set.
4. Surface the ranked batch through the decision channel, in the shape `templates/slack-shapes.md` gives, tagging each entry to its owner. Ranked by dependency, then information gain, then reversibility.
5. Wait. The first reply is never the decision, and discussion is not authorization.
6. On the structured approve action, read the approval record it wrote. Verify it carries per-decision verdicts, a named approver, and hashes that match the exact plan content just surfaced. Verify it was written by a person outside the phase session; the agent that runs a phase never writes the verdict on it (`CLAUDE.md`).
7. Only then, write the state-file transition that moves the unit into implementation.
8. Write the metrics row for this gate by running `metrics/emit.sh gate`, which is in the bundle folder rather than the installed harness, with the run, unit, phase and round, passing `--phase-kind plan-summary`: this is the one gate the contract always calls an approve, whatever the plan's human-class decision count.
9. Read the second-pass vector from `rules/risk-intake-rubric.md` for this unit and carry it into the approval record, so the gate's own record says what the unit scored rather than leaving it in a separate file.
10. Write a decisions-file entry for anything the approve settled at this gate, including any entry a modified verdict replaced, with provenance ratified by a person. An entry the approval record settles is a decision, and leaving it only in the approval record hides it from every later read of the decisions file.
11. Where the ratified plan meets a state it did not expect at launch, write the implementation conflict record described in Outputs, whose shape is open. A conflict does not refuse the crossing; recording it is what the implementation session needs.
12. Write the context handoff from `templates/context-handoff.md` in the bundle folder: what was ratified, what is still open, and what to read first.
13. Hand off to the operator session that runs the implementation phase, per `controller/CONTRACT.md`.

## Outputs

Two kinds, and they are worth keeping apart. The first is the gate's own record of itself. The second is what the crossing generates for the work that follows.

**The gate's own records.**

- The state-file transition, naming the phase now in progress and its round.
- The metrics row for the gate.
- On a refusal, a record of the refusal and which precondition failed. A refusal that leaves no record is indistinguishable from the act never running.

**What the crossing generates.**

- **Decision entries for anything decided at the gate.** An approve with per-decision verdicts settles entries, and a modified verdict replaces text. Those are decisions, and they belong in the decisions file with provenance ratified by a person, not left implicit in the approval record.
- **An implementation conflict record**, where the ratified plan meets a state it did not expect at launch. Three shapes seen so far: another workstream has changed the same paths since the plan was ratified; the batch surfaced a boundary question, which is a redefinition rather than a question about behaviour inside the unit; or a domain guardrail applies that the plan did not account for. The conflict is not a reason to refuse on its own. It is a reason to record what the implementation session is walking into.
  **The shape is open.** The lean is that a conflict is an entry in the decisions file of class human, with its assumption flag set and a pointer to the record it conflicts with, so it travels the path every other decision travels. It earns its own template only if conflicts turn out to carry fields a decision entry has nowhere to put. A review of this file argued the other way and the argument is kept here rather than settled: all three shapes above fail the decisions file's required statement and alternatives-considered fields without inventing a decision this act is forbidden to take, and the second shape, written as an unanswered human-class entry, trips this skill's own refusal on an unanswered human-class entry in the plan's decisions file. The alternative on the table is carrying the conflict in the context handoff, where the session that needs it already reads.
- **The documentation the implementation session needs.** What was ratified, what is still open, and what to read first. That is the context handoff shape, so it is written from `templates/context-handoff.md` in the bundle folder rather than invented here. The gate is the last point where someone knows all three, which is why the crossing owes it rather than the phase that receives it.

Nothing autonomous crosses this gate, and that constraint is unchanged by any of the above. Generating a record is not permission to decide what goes in it.

## What it measures

The metrics row at this gate, with the fields `rules/record-contract.md` lists: minutes, decisions by class, questions asked and answered, human checks, approves against proceeds, escalations, and any review finding that reached a person with whether the outcome changed.

Two of those earn their place here specifically. **Approves against proceeds** is the number this gate exists to make honest, because a gate that never takes an approve is a gate in name only. **Minutes** is the wait, which is the cost this model pays for the guarantee, and the cost nobody has measured yet.

The row is written at the gate rather than reconstructed afterwards. A row written from memory at the end of a run is worth less than one written here.

## The handoff

This act does not spawn a team of agents. It hands the unit to the operator session described in `controller/CONTRACT.md`: one logical operator, discrete headless sessions, internal agents and worktrees permitted, sealed from local development access.

**The team shape is open.** Whether the implementation phase runs as one session or several, and how they divide work, is not decided anywhere in this bundle. `CLAUDE.md` records the operating shape being tried as one logical operator with parallel feature builds not the default, which constrains the answer without giving it.

## Model

Which model runs this act, and why. Recorded in the metrics row so the choice can be argued from evidence later. Not decided.

## Stop conditions

- Any item in "What it refuses" above.
- The can-start rule fails.
- The approval record names an approver who is the session that wrote the plan.
- The spec record's single-threaded owner is recorded as explicitly blocking (`decisions/0005-kickoff-authority.md` in the bundle folder).

## Open

- **How a refusal reaches a person.** The act stops and states the reason, and nothing defines where that statement goes or who is expected to act on it.
- **What happens to a unit that fails the gate twice.** The state file's round count halts a slice at the third round and only a human record resumes it, but nothing says whether a gate refusal increments that count.
- **Who may approve.** Settled. An approver is anyone named in the unit's spec record, in the approvers definition, or in `OWNERS.md`. Within that set the approver may be the one from the prior gate, another approver, or the workstream's single-threaded owner. Product and design never approve alone: engineering approves at every gate, and product or design approve alongside engineering at this gate, once the requirements are disambiguated and the build is under way. Decided by Michael, 2026-09-02; `decisions/0008-launch-and-cold-review.md` in the bundle folder.

  So the approver set is the same one `decisions/0005-kickoff-authority.md` in the bundle folder names, widened to any valid approver, and involvement in the project is what makes someone valid rather than a named role. Nobody has watched what happens when a non-engineering approver holds an implementation gate, and the first runs are the evidence.

  Three things are open and are not guessed here: who counts as involved with the project, whether the product or design case applies to this gate alone or to every gate, and how a decision's consequence is read. They sit under the assumption flag of the entry in `decisions/0008-launch-and-cold-review.md` in the bundle folder. Until they are answered, this act does not widen the approver set past the sentence above.
- **Whether the wait has a bound.** No response-time expectation was defined. Blocking whenever a required person is unavailable is the acknowledged cost of this model (`skills/surface-decisions.md`).
- **The structured action itself.** In the design it is a button, and the button is the part that does not exist yet.
