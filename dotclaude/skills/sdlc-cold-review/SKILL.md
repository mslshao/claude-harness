---
name: sdlc-cold-review
description: The SDLC bundle's phase skill for adversarial review from a separate session, reviewing an artifact by path against the plan, decisions, spec and guardrails.
---

# Skill: cold review, adversarial review from a separate session

## Status

**Runs today.** A session that did not write the work can be given the artifact by path, along with the approved plan, its decisions file, the spec record and the domain guardrails, and can return findings under the three lenses with their labels and a could-not-determine section. The handoff below is complete enough to follow today.

**Manual today.** Obtaining the separate session. Passing the paths to it. Carrying its findings back. Judging whether a finding interrupts a person.

**Not built.** A spawner that starts the reviewing session. An escalation surface. Any mechanism that requires a cold review before a gate rather than leaving it to whoever is running the work.

Every rule below names where it came from.

**The portability rule:** this skill references bundle files and application repository files only. Never a personal agent, a personal rule, or anything in one person's home directory.

## Name and purpose

`cold-review` produces a self-contained review request and hands it to a session that did not write the thing being reviewed. It is a local, adversarial version of a pull-request review, delegated to a separate fresh session. Decided by Michael, 2026-09-01; `decisions/0008-launch-and-cold-review.md` in the bundle folder.

It produces a prompt and receives findings. It does not perform the review.

What it is not responsible for: fixing anything, ruling on its own findings, or deciding whether the work ships. A reviewer that also decides is not a reviewer.

## Why a separate session

Because the author never reviews their own work. `CLAUDE.md` states the rule for phases: the agent that runs a phase never writes the verdict on it. This skill is that rule applied to review.

The failure it prevents is subtler than laziness. A review run inside the authoring session inherits the author's framing even when the reviewer has a clean context, because the authoring session chooses what to show and how to describe it. The errors then correlate with the author's blind spots, which is the one thing an independent review exists to break.

That is the bundle author's reasoning from experience, proposed rather than team decided. Nothing in the 2026-08-31 meeting or the 2026-08-28 record establishes it.

## When it runs

- Routine review of a completed phase's work, before its gate. The 2026-08-28 definitions keep review provisionally, with routine review running as an adversarial agent.
- Ahead of a separate pre-launch review for security-sensitive changes. The 2026-08-28 definitions treat that review as its own class rather than a lens inside the routine pass, so this skill detects the class and checks the routing without performing the review.

## Inputs

- The artifact under review, **by path, never by paste**. The reviewer opens it. A reviewer handed a description reviews the description, and it cannot run any check that needs the actual bytes.
- The approved plan and its decisions file, by path. This is what the work is judged against.
- The spec record for the unit, by path, so the reviewer can see what was ratified.
- The domain guardrails for the domains the work touches, `domains/<domain>/` in the bundle folder.

Deliberately not passed: the author's account of what it did, its rationale, its self-review, and what it believes it already verified. The omission is the point. The reviewer forms its own judgment from the artifact and the requirement.

## How a fresh session is obtained

A new operator session, started the way `controller/CONTRACT.md` describes any session being started: the controller assembles the application repository at the ref under review, a copy of this bundle with its `VERSION` recorded, and credentials from the environment.

**The mechanism is open.** Nothing defines whether the reviewing session is started by the controller as a phase, started by a person, or run outside the run entirely. What is settled is the property it must have, and it is stronger than not having written the artifact: the session took no part in the build or in the tests. A session that wrote the tests for work it did not build is not independent of it for this purpose. It also did not receive the author's framing.

## The review request

The block the skill emits. Placeholders in angle brackets.

    COLD REVIEW REQUEST. You did not write this work. Review it with fresh eyes.

    Unit: <unit id>. Phase: <phase name>, round <n>.
    Artifact: <paths>. Open and read them yourself.
    Approved plan and decisions: <paths>.
    Spec record: <path>.
    Domain guardrails in force: <paths>.

    Judge the work against the approved plan and its decisions file. That is the object of
    the review: not whether you would have planned it this way, but whether what was built
    is what was approved, and whether it is correct.

    Lenses, in order:
    1. Correctness against the approved plan and its decisions. Every decision entry that
       applies to these paths: was it built the way it was ratified. An entry built
       differently is a finding whatever its merits.
    2. Conformance to the record. The five outputs a session owes exist and are complete,
       the decisions file has every entry with its class and its assumption flag, and the
       state file transition matches what happened.
    3. Pre-launch class detection and routing. Decide whether the change falls into the
       pre-launch class, and whether it was routed to that separate review. Do not perform
       the security review here; this lens finds and routes, it does not rule.
       The five areas: authentication and authorization, personal data, payments,
       potential health data, and encryption in transit and at rest. All five are in the
       class, decided by Michael, 2026-09-01. The review itself is
       `agents/security-review.md`, which arrives with this round.
       For any area not on that list, the conservative default holds: where it is unclear
       whether a change falls into the class, route it and say the classification is
       uncertain rather than settling it here.

    Report every finding, ranked by severity, labelled BLOCKING, NONBLOCKING or
    OBSERVATION, each with the evidence a reader can check: a path, a line, a quoted
    fragment, or the command you ran.

    End with what you could not determine, and why. That section is never empty. A review
    that claims complete coverage has not looked at its own edges.

    Do not fix anything. Do not rule on your own findings.

## The verdict labels

- **BLOCKING.** The work does not match what was approved, or it is wrong in a way that reaches the application. Named for consequence, not for confidence.
- **NONBLOCKING.** A real defect that does not stop the crossing. It goes into the record so it is not rediscovered.
- **OBSERVATION.** Something a person should know that is not a defect. A drift, a smell, an inconsistency with a sibling path.

`CLAUDE.md` asks that words like critical and blocking be reserved for things whose consequences warrant them. These labels are that rule made structural.

## Escalation to a person

The reviewer's findings do not all reach a person. The 2026-08-28 definitions keep review provisionally with a person interrupted only for a critical finding, a material divergence from the plan, or a genuine A-versus-B call. Those three, and nothing else, are what surface.

A genuine A-versus-B call is one where the reviewer can state two defensible options and no ratified decision chooses between them. It is not a preference. Where the reviewer merely prefers one, it rules on its own finding and records it.

Two reviewers disagreeing on whether a finding is material is the same trigger rather than a fourth one. The disagreement is two defensible readings with nothing ratified between them, which is what an A-versus-B call is, so it surfaces as one and is named as one. The list stays closed at three.

## The hand-back

What returns to the author. It has to stand alone, because the author never saw the review.

    REVIEW RESULT: <unit id>, <phase> round <n>, reviewed at <content hash>

    <One line: the verdict, and on a later round what is now closed so the author does not
    reopen settled items.>

    BLOCKING
    <finding, evidence, and what would satisfy it>

    NONBLOCKING
    <finding, evidence>

    OBSERVATION
    <finding, evidence>

    ESCALATED TO A PERSON
    <the critical findings, plan divergences and A-versus-B calls, each with what the
    person is being asked to decide>

    COULD NOT DETERMINE
    <never empty>

## Outputs

- The review request, emitted for a separate session to run.
- The hand-back, once findings return.
- A decisions file entry for anything the review settled, and for any A-versus-B call a person ruled on, with provenance recorded as ratified by a person.
- The metrics row field this feeds: any review finding that reached a person, with whether the outcome changed. Both halves. A finding that reached a person and changed nothing is the interesting case, and recording only the first half hides it. Pass both halves to `metrics/emit.sh gate`, in the bundle folder rather than the installed harness, through `--findings-to-person` and `--findings-changed-outcome`; this skill is the one that knows them.

## Model

Which model runs the reviewing session, and why. Recorded in the metrics row. Not decided, and worth deciding separately from the model that does the work, since the whole point is that the two are not the same reader.

## Stop conditions

- The artifact cannot be opened at the path given. Do not review a description of it.
- The approved plan or its decisions file is missing, or its hash no longer matches. There is nothing to judge the work against.
- The reviewing session turns out to be the authoring session.

## Open

- **How the reviewing session is started**, per the section above.
- **Whether the reviewer sees earlier rounds.** Showing them saves rediscovery and reintroduces framing. Not decided.
- **What happens when the author disagrees.** Nothing defines the path from a contested BLOCKING finding to a ruling, beyond the tie-break the decision channel already has.
- **Who owns the pre-launch review.** The class and the reviewing agent are settled; the owner is not (`domains/security/README.md`).
- **How often this runs.** Settled. Consequential work only, and for consequential work it is mandatory rather than discretionary. A unit is consequential when both conditions hold: its risk vector carries a score at or above a threshold, and its Integration scoring shows a boundary crossing that changes how the dependencies of other components operate. Both are read from `rules/risk-intake-rubric.md`, which is in this bundle, so the vector and the Integration anchors are looked up rather than handed over. Neither alone is enough. Decided by Michael, 2026-09-02; `decisions/0008-launch-and-cold-review.md` in the bundle folder.

  One thing is open and is not guessed here: the threshold's value. It sits under the assumption flag of the entry in `decisions/0008-launch-and-cold-review.md` in the bundle folder, with the lean recorded there. Until it is set, the threshold alone has to be handed to the session running this skill, and the person running the work decides where a unit carries no score at all.
