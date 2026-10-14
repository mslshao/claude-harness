---
name: sdlc-test-forge
description: The SDLC bundle's phase skill that maps every ratified acceptance criterion to the tests verifying it, and writes the mapping as a record.
---

# Skill: test-forge

Maps every ratified acceptance criterion for a unit to the tests that verify it, and writes the mapping as a record. It does not generate tests and does not run a suite.

**The portability rule:** this skill references bundle files and application repository files only. Never a personal agent, a personal rule, or anything in one person's home directory.

## Status

**"Runs today" below means a person can follow this file and get the result. Nothing here executes; no command in this bundle runs any of it.** The skill has not yet been followed to completion on a real unit: the one rehearsal unit that exists refuses at step 2, because no stage has ratified criteria for it, which is the procedure working rather than failing.

| Part | State |
|---|---|
| Reading the ratified criteria and the plan's decisions file | Runs today |
| Building the criterion-to-test map | Runs today |
| Writing `acceptance-map.md` beside the phase outputs | Runs today, written by hand from the template |
| Reporting gaps in both directions | Runs today |
| Refusing an unratified acceptance section | Runs today |
| Deciding whether a criterion has observable behaviour | Manual today, a person rules |
| Running the suite and filling the status column from real results | Manual today |
| A coverage check that fails the gate on a missing id | Not built |
| Behaviour verification driven from the criteria | Not built, see The open destination |
| The architecture-contract check | Not built, see The open destination |

Everything marked "runs today" is a person following this file. Nothing here is automated, which is the same state as every other record in this bundle.

## Inputs

By path, all of them.

- **The ratified acceptance criteria for the unit.** Follow the spec record (`templates/spec-record.md`) to its `spec_source` for the unit's acceptance section, and then to whatever the requirements stage ratified from it. The second step is not optional; see What it refuses.
- **The plan's decisions file** (`templates/decisions-file.md`), which supplies the paths and seams the tests touch, and any decision that already binds how a criterion is verified.
- **The domain guardrails** for the domains the unit touches, `domains/<domain>/` in the bundle folder. A domain may require a kind of test this map has to account for.
- **The application repository's existing tests**, so a criterion already covered is recorded as covered rather than written twice.

## What it refuses

- **An acceptance section that is a proposal rather than ratified criteria.** The spec's acceptance list is the author's view, offered to the requirements stage rather than binding it; the requirements stage generates and ratifies the criteria that bind the work and may land somewhere different. Mapping tests to the author's list produces a map of what was suggested, which reads exactly like a map of what was approved and is not one. If the requirements stage has not ratified, stop and say so.
- **A criterion with no observable behaviour.** A criterion nothing could fail is not a criterion. Do not invent a test for it and do not quietly drop it: record it with kind `none`, status `gap`, and say in the provenance column that it needs rewording, so the requirements stage sees it rather than the map absorbing it. What a test may assert once a criterion has observable behaviour is `rules/testing-discipline.md`, which binds any test anyone writes rather than only the ones this map names.
- **A criteria set whose hash no longer matches its source.** A record whose content no longer matches is treated as absent, which is the same rule everywhere in this bundle. Criteria that moved after ratification are not the criteria that were approved.

## Procedure

1. Read the spec record and confirm its hash matches. Follow `spec_source` to the unit's acceptance section.
2. Find what the requirements stage ratified from that section. If nothing, refuse per the first refusal above and stop.
3. Take the criterion ids from the ratified record. If the ratified record has no ids, mint them in this map, say in the header that the ids are the map's own, and raise it: an id scheme that lives only in the map cannot be cited by anything else.
4. List every criterion, must and must-not both, and the product invariants. Invariants are criteria: they are what the unit must not disturb, and they are the ones a reasonable implementation gets wrong.
5. For each criterion, decide whether it has observable behaviour. Where it does not, record the gap per the second refusal and move on.
6. Search the application repository for a test that already covers it. Record the path and the test name precisely enough to run, and the ref the search ran against, so the row can be re-checked later.
7. Where the search found nothing, record kind `none` and status `gap`. Where the search has not been run for that criterion yet, record status `not searched`, which is a different claim and reads as one. Do not write the test here; this skill maps, and the phase that owns the code writes.
8. Read the map the other way: every test in the paths this unit touches that cites no criterion. Record those too, because either the criteria are incomplete or the test protects something nobody ratified.
9. Write `acceptance-map.md` from `templates/acceptance-map.md`, beside the phase's other outputs, committed with the application the way every record in this bundle is.
10. Report the two gap counts in the phase's decisions file, so the gate sees them.

## What it writes

`acceptance-map.md`, one per unit, committed beside the phase outputs. The template is `templates/acceptance-map.md` in the bundle folder.

It writes nothing else. It does not modify tests, does not modify the criteria, and does not write a verdict.

## Worked example

Against the unit in the live example spec, salon opening hours. The spec's own acceptance list is the author's view, so a map built directly from it would be refused at step 2. What follows is a map against criteria a requirements stage ratified from that list. **The ids, the ratified status and the test paths below are invented for this example.** No requirements stage has run for this unit, and the map would say so in its header rather than implying otherwise.

    unit: GLAM-014
    phase: verify
    round: 1
    criteria_source: <the ratified criteria record>
    criteria_hash: <hash of exactly that content>
    written_by: hand
    date: <YYYY-MM-DD>

| Criterion | Statement | Test | Ref | Kind | Status | Provenance |
|---|---|---|---|---|---|---|
| `A1` | An owner sets hours per weekday, including more than one open period in a day, and including weekdays with none | `hours.spec::sets multiple periods` | `<application repository>@<ref>` | automated | covered | spec acceptance, must |
| `A2` | An owner changes hours already set, and sees the change on the schedule | `hours.spec::edit reflects on schedule` | `<application repository>@<ref>` | automated | covered | spec acceptance, must |
| `A3` | The schedule shows closed time as visibly closed, distinct from open time with nothing booked | none | `<application repository>@<ref>` | manual | gap | spec acceptance, must. Visual distinctness has no assertion yet; a person checks it |
| `A4` | Booking into closed time warns the owner, and proceeds if the owner confirms | `booking.spec::warns then proceeds` | `<application repository>@<ref>` | automated | covered | spec acceptance, must |
| `A5` | A booking in closed time is never refused without asking | `booking.spec::never silently refuses` | `<application repository>@<ref>` | automated | covered | spec acceptance, must not |
| `A6` | The schedule renders for a salon with no hours set | `schedule.spec::renders without hours` | `<application repository>@<ref>` | automated | covered | spec acceptance, must not |
| `A7` | Appointments already in the past are unchanged, whatever the new hours say | `hours.spec::past appointments untouched` | `<application repository>@<ref>` | automated | covered | product invariant |
| `A8` | Appointments already booked for a future date stay booked, including any the new hours put in closed time | `hours.spec::future bookings survive` | `<application repository>@<ref>` | automated | covered | product invariant |
| `A9` | A salon that has never set hours behaves exactly as it does today | none | `<application repository>@<ref>` | manual | gap | product invariant. Behaves exactly as today has no fixed reference to assert against; needs rewording or a captured baseline |

Two rows are gaps and both are honest ones. `A3` is observable but nothing asserts it yet. `A9` is the second refusal in practice: as written it names no behaviour a test could fail, so it goes back to the requirements stage rather than getting a test invented for it.

Reading the map the other way is part of the same pass. Any test in `hours.spec` or `booking.spec` citing no criterion goes in a second short list, because a test protecting something nobody ratified is worth a sentence either way.

## The open destination

Separate from everything above, which is what a person can follow now. None of this is built and none of it is assumed.

- **Behaviour verification driven from the criteria.** The team document's Stage 6 names Playwright run against acceptance criteria as the initial concept, with Gherkin-style criteria as the source. Whether it is configured for the application repository, and whether its output supports id-to-test mapping, is unverified.
- **A runner that reads the criteria and executes the matching tests.** The team document raises it; the definitions call it an open spike and say to try an existing adapter first. Not attempted.
- **The architecture-contract check.** The definitions describe a second conformance dimension: automated checks that package boundaries, dependency direction and other structural constraints the plan named still hold. Named there as unbuilt. Until it exists a reviewer reads for it by hand, and this skill neither builds nor invokes it.
- **The coverage check that fails the gate.** The definitions describe it failing on any missing id. The map this skill writes is what such a check would read, which is why the gaps are recorded as rows rather than omitted.

Operational verification, the monitoring and alerting half of Stage 6, is a different concern and is not carried here.

## Model

Which model runs this skill, and why. Recorded in the metrics row. Not decided.

## Stop conditions

- Any item in What it refuses.
- The spec record's hash does not match its source.
- The unit's criteria and the plan's decisions file disagree about what is in scope. That is a question for a person, not something this skill reconciles.

## Open

- **Where criteria get their ids**, which is a prerequisite this skill needs and does not supply. Step 3 works around it and says so.
- **Whether the map is a record or an artifact.** It is committed beside the phase outputs, and nothing says whether it is hash-bound the way an approval record is.
- **Who runs it, and when in a phase.** Named in the definitions as unsettled.
- **Whether a gap blocks the gate today.** Nothing enforces it, so today a gap is visible and not blocking, which is a weaker guarantee than the definitions describe.
