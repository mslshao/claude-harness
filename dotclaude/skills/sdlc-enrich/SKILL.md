---
name: sdlc-enrich
description: The SDLC bundle's phase skill that gathers context a phase needs, filtered to the slice, without planning, ranking, judging or deciding.
---

# Skill: enrich

Gather the context a phase needs, filter it to the slice, and write what was found and what was not. It collects facts. It does not plan, rank, judge, or decide.

**Who runs it.** The worker session, at the start of a phase, before it does any of the phase's own work. The orchestrator does not run it. The handoff prompt tells the worker to run it and hands it the slice input; the worker uses that input as the intent-match against the record plane. Michael's direction of 2026-08-28, and the reason it is a skill in the bundle rather than a step in the controller: it is how a cold-start session knows where to begin.

Provenance: Michael's definition of 2026-08-28, and his rulings of 2026-09-01 on the source hierarchy and on what this harness may not reach. The record shapes it reads and writes are `rules/record-contract.md` and the bundle's `templates/`. Not ratified.

## Input

One slice input, in this order of preference:

- A unit id, which is the normal case, because the handoff prompt carries it.
- A path to a spec record, when the run has one.
- The spec itself, when the unit has no record yet, which is what the first phase of a new unit looks like.

With none of these, stop and say so rather than guessing. A brief built from a guessed unit is worse than no brief, because it reads as evidence.

## The source order, and why it is an order

Michael's ruling of 2026-09-01. Sources are not equal and the brief must say which one each item came from.

1. **The record plane in the application repository. This is the source of truth.** The decisions files, the approval records, the spec record, the ADRs in force by applies-to match, and the learnings stubs of earlier phases. A decision here is ratified or it is flagged as an assumption, and either way it is the thing later sources are read against.
2. **The bundle's own records.** `decisions/`, `CHANGELOG.md` and `adrs/`, which say how the harness itself was decided and what changed under the run's feet. Read at the version the run recorded.
3. **The team's pages under the team document.** The definitions, the design page, the build plan, the spec proposal. These carry intent that no repository file states.
4. **GitHub, read only, through `gh`.** Pull requests and issues touching the unit's paths. High signal about what is in flight and who is already changing the same files. It reads; it never comments, opens, or closes anything.
5. **The decision channel's threads for this unit**, where a connector exists. Discussion is context, not decision: `rules/record-contract.md` is explicit that a verdict in a chat message is not an approval, so a thread can explain a record and can never replace one.
6. **The codebase, as description of the present only.** Michael's ruling, 2026-09-01: the code may carry bad practices and out of date things, so no intent is read from it and nothing is anchored to it. Use it to answer what is true right now, never what was meant.

**What this harness does not reach, by intent.** Michael's meeting captures are deliberately out of scope and no rule here should be written as though they exist. This is also what `skills/phase-skill-template.md` already requires of every phase skill: bundle files and application repository files only, never a personal agent, rule, or anything in one person's home directory.

## The filter

Everything gathered is matched against the slice input and most of it is discarded. Keep an item when it does at least one of these:

- It binds the unit: a ratified decision, an ADR whose applies-to covers a path this unit touches, an approval record for a predecessor phase.
- It changes what this phase would otherwise do: a prior attempt at the same shape, a learnings entry from a phase that hit this, an open pull request on the same paths.
- It states a constraint the unit must hold: a product invariant, a domain guardrail for a domain this unit touches.

Discard the rest without listing it. A brief that keeps everything has not filtered, and the reader pays for that in the one place the design cannot afford it, which is the person's attention at the gate.

## Discovery, before anything is read

The worker does not know which surfaces its own session can reach, and it must not assume. Michael's ruling of 2026-09-01: it should not stop working if a surface does not exist, and part of the workflow is to discover what it has available and then use what it can.

So the first act is a probe, not a read. Each check is cheap and none of them fetches content:

- **The application repository and its record plane: always available.** The session was handed a slice and a working copy to run in, so this source is never probed and never absent. If it were, the phase itself could not run and that is a different failure.
- **The bundle's own records: always available.** They were installed with the harness.
- **The team's pages:** does a documented-search or page-fetch tool resolve by name in this session.
- **GitHub:** does `gh` exist on the path and report an authenticated status. Both, because an unauthenticated `gh` resolves and then fails on the first read.
- **The decision channel:** does a channel-read tool resolve by name in this session.

Then launch readers only for the surfaces that answered yes. A surface that answered no is not retried, not worked around, and never a reason to stop: the phase gets a smaller brief, and the brief says which surfaces it is smaller by.

Record the whole probe, not only the failures. Every surface in the order above appears in the brief's not-reached section as reached or absent, so a reader can tell a surface that had nothing to say from one that was never asked. Those two look identical in a brief that lists only what it found, and they mean opposite things.

## Fan out, one reader per source

Sub-agents are allowed here and are the point: the sources are independent once the slice input is known, and a session that reads them one after another spends the phase's wall clock before the phase starts. One reader per source, launched together, then one merge step.

Model tier per reader, so a fan out does not cost more than the phase it serves:

- **Record plane reader: the worker's own tier.** It is the source everything else is filtered against, and misreading a hash-bound record is the one error that propagates.
- **Team pages reader: a cheaper tier.** Extraction from documents whose structure is known.
- **GitHub reader: a cheaper tier.** Listing and filtering by path.
- **Channel reader: a cheaper tier.** Extraction from threads.
- **Codebase reader: the cheapest tier that can grep and read.** It answers what is present, which is a lookup.
- **Merge step: the worker's own tier**, because deciding what survives the filter is judgment and it is the only step that sees all sources at once.

Each reader returns what it found, what it looked for and did not find, and what it could not reach. The merge step keeps those three separate all the way into the brief.

## Before gathering: look for an earlier brief

Run `metrics/emit.sh start` here, before anything else, from the bundle folder rather than the installed harness, since the installer copies `harness/` only. Where the first pass of `rules/risk-intake-rubric.md` has been scored for this unit, that vector is part of the record plane this step reads: record it in the brief like any other item, with the actor and the model that produced it. Where the gate wrote none, record this phase's vector as unscored rather than scoring one. Scoring is the orchestrator's, in that rubric's own words, and this skill collects rather than decides. Enrich is the first thing a worker does, and that start marker is what makes the run's minutes derivable later.

Look for a brief that already exists for this unit, or for a unit adjacent to it. Adjacent means linked by the spec record's `depends-on`, or by a decisions file that brief cited. Reuse a brief when both of these hold: its unit is this unit or one adjacent to it, and every source it recorded reading is unchanged, meaning the record-plane hashes it recorded and the bundle `VERSION` it recorded both equal what you see now. A brief that passes both is used as it stands, rather than gathering again. A brief that fails either is not reused and is not overwritten: gather again and write a new brief. How long ago a brief was written is never a criterion, in either direction.

A brief carries a `related_briefs` field naming the briefs of its adjacent units, on the same definition of adjacent. Follow that field one hop, never transitively. Read a linked brief's what-binds-the-unit section only, and do not carry its description of the present into this phase's work: it described another unit at another moment, and nothing has kept it true since.

A brief whose recorded sources no longer match is not left lying. Refresh it or annotate it, and never overwrite it without provenance.

Refresh it by regathering for that unit and writing the result as a new revision beside the old one, naming the old one in the new brief's `supersedes` field. That field names the immediate predecessor only; walk it one hop at a time to reach the first. Do not edit the brief being superseded, and do not invent any other linkage for the chain. If `supersedes` names a brief you cannot find, stop at that hop, treat the brief as not reusable, and annotate it stale naming the path that is missing. Reconstruct nothing: a superseded brief is never deleted, so a missing hop is a defect in the record plane rather than something to repair here.

Where refreshing is outside this phase's slice, annotate the stale brief instead, naming the date and the sources that moved, so no later reader takes it as current. The point is that nothing misleading or out of date sits in the repository unmarked.

Decided by Michael, 2026-09-01; `decisions/0007-enrich.md` in the bundle folder.

## What it writes

One context brief per phase, in the shape of `templates/context-brief.md` in the bundle folder, written before the phase's own work begins.

It is not the context handoff file. That file is written at the end of a phase for the session that continues the work, and `templates/context-handoff.md` owns it. This one is written at the start of a phase for the session doing the work now. A phase that continues another session's work reads both: the handoff for narration, this brief for what the records say.

The brief is not a record in the sense the contract means. Nothing gates on it, it carries no hash, and it decides no transition. It is the phase's reading of the record plane, and where it disagrees with a record, the record is right.

## Rules

- **Every item carries its source and whether it was verified.** VERIFIED means a file was read or a command was run and its output seen. INFERRED means it was reasoned from something adjacent. An item that is neither does not go in the brief.
- **An absence claim names the source that would have said so.** "No ADR governs this path" is only worth writing when the ADR directory was read and matched by applies-to. "Nothing found" without a named source is not a finding, it is a shrug, and it reads to the next person as though the ground was covered.
- **Say what could not be reached.** A connector that is absent, a repository that could not be read, a page that returned nothing. A brief that is silent about its own gaps invites the reader to treat it as complete.
- **Never infer intent from code.** The codebase answers what is true now. If the brief wants to say why something is the way it is, the answer comes from a record, a page, or a thread, or the brief says that no source states it.
- **Do not pad.** A unit with three relevant items has a three item brief. Manufacturing items to fill a shape is the same failure as manufacturing questions to fill a batch, which `rules/decision-discipline.md` already names.
- **Collect, do not decide.** Anything the phase would have to rule on is a decisions file entry, not a brief item. The brief may note that a question is open; it may not answer it.

## Open

- **Whether the handoff prompt should carry the available set** rather than each worker probing for itself. Discovery above settles that a missing surface degrades the brief instead of stopping the phase, which was the open half that mattered. What is still open is whether the orchestrator already knows what a worker can reach and should say so, which would make the probe a confirmation rather than a discovery.
- **Where the brief is written.** Closed by Michael on 2026-09-01: it is committed beside the phase output, so it travels with the work rather than living in a session. It remains not a record: nothing gates on it and it carries no hash.
- **How ADRs are matched by applies-to** when the ADR directory is empty, which it is. Until one exists, that step of the record plane read returns an absence, and the brief should say so rather than omitting the source.
- **Whether the codebase reader is worth its tokens** on a phase that touches no code. The lean is that it is skipped rather than run and discarded, and no source rules on it.
