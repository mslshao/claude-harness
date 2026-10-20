---
component: compound skill, "The merge's failure ledger" bullet
type: skill paragraph
status: deleted
source: snapshot
superseded_by: [one line in briefs/compound-merge.md, Mode 1]
---

# compound-failure-ledger-bullet

## What it was

Line 37 of `skills/compound/SKILL.md` (hash 3f9dfedc), quoted in full:

> - **The merge's failure ledger:** the merging session runs `python3 (local scratch file) import-board (local scratch file)<date>.md > <merge dir>/ledger-candidates.tsv`, then `failure-ledger.py import-hooks <date> >> <merge dir>/ledger-candidates.tsv`. It fills each `?`, deletes each row that is not a failure, runs `failure-ledger.py add --from <merge dir>/ledger-candidates.tsv`, and names the appended ids in MERGE.md under "Failure ledger". Neither import appends; only that `add` writes (C27, `c27-failure-log/DESIGN-v2.md`). Since 2026-10-16 `import-board` also reads the ticks `fleet-log.py` renders; before that it printed 0 candidates from the board of 2026-10-15.

The same duty sat in `briefs/compound-merge.md`, Mode 1: "Run the failure ledger as `skills/compound/SKILL.md` describes, and name the appended ids in MERGE.md."

## Why it went

Dev-88 found no reader of the ledger other than `failure-ledger.py report` and no file showing a report run. Each merge paid two imports, a hand-filled TSV and an append. the user approved item 3 C8 at about 16:29Z on 2026-10-20.

## What supersedes it

`briefs/compound-merge.md`, Mode 1: "The failure ledger runs when the user asks for a failure report, not on every merge." The commands remain in `scratch/scripts/failure-ledger.py`.

**Source: snapshot** `(local snapshot) skills/compound/SKILL.md.txt`
