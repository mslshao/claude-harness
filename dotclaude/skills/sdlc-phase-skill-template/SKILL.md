---
name: sdlc-phase-skill-template
description: The SDLC bundle's template to copy per phase; a phase runs one step of the lifecycle, writes its records, and stops at its gate.
---

# Phase skill template

Copy this per phase. A phase runs one step of the lifecycle, writes its records, and stops at its gate.

**The portability rule:** a phase skill references bundle files and application repository files only. Never a personal agent, a personal rule, or anything in one person's home directory. The acceptance test is that a new engineer runs a slice from a fresh copy with nothing from anyone else's machine.

**State rules in plain words, not in quotations.** A skill or agent file says what the rule is and points at the record: "Decided by <name>, <date>; `decisions/<file>` in the bundle folder". The exact words live in the decision record, which is where someone goes to check them. A quotation inside an installed file is noise for every reader who is not auditing provenance, and it goes stale silently when the record is amended.

---

## Name and purpose

One sentence: what this phase produces and what it is not responsible for.

## Inputs

- The artifacts the previous phase approved, by path.
- The slice's state file.
- The predecessor's approval record.
- The decisions and records in force that apply to these paths.
- The domain guardrails for the domains this phase touches (`domains/<domain>/` in the bundle folder).

## Preconditions

The can-start rule in `rules/record-contract.md`. If it fails, stop and say which part failed.

## The two decision lists

- Decisions this phase may take alone: <list>
- Decisions that require a person: <list>

Anything on neither list is human-class. These lists are committed configuration; the phase does not edit them.

While both lists are empty, as they are in this template, every decision is human-class. That is the conservative default `rules/decision-discipline.md` argues for, so an unfilled skill degrades in the safe direction rather than being broken.

## Steps

1. <the work of the phase>
2. Write the decisions file entry by entry, as `templates/decisions-file.md` in the bundle folder.
3. Run the two screens in `rules/decision-discipline.md` over the batch.
4. Surface the ranked batch through the decision channel and wait for the structured approval action.
5. Write the state-file transition, the metrics row, and the learnings stub.
6. Write the context handoff file if the work continues in another session.

## Outputs

The artifacts, the decisions file, the state-file transition, the metrics row, the learnings stub. Named by path, so the next session finds them without being told.

## Model

Which model runs this phase, and why. Recorded in the metrics row so the choice can be argued from evidence later. Not decided for any phase yet.

## Stop conditions

- The can-start rule fails.
- A decision the lists mark human-class has no answer.
- The phase would touch a path outside what it declared.
