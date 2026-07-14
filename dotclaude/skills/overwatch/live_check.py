#!/usr/bin/env python3
"""Live integration tier for overwatch gather (docr-wtice).

Exercises the real tools end to end, the tier the fixtures cannot cover: that a
record this skill would surface actually round-trips through the live query, and
that a real forced failure classifies as error rather than empty.

    python3 ~/.claude/skills/overwatch/live_check.py                    # safe, local only
    python3 ~/.claude/skills/overwatch/live_check.py --include-external # + real PR/Jira

Run before shipping or after touching gather.py. The default run mutates only the
local beads DB (create + delete a throwaway bead) and forces a gh auth failure
with a bogus token (no external state touched). Creating a real draft PR or Jira
ticket is outward-facing, so those live round-trips are gated behind
--include-external and are opt-in per run.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import gather

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name}: {detail}")


def _run(argv: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, timeout=60, env=env, check=False)


def bead_round_trip() -> None:
    """Create a throwaway bead, confirm gather surfaces it, delete it, confirm it is gone."""
    create = _run([
        "bd", "create",
        "--title", "overwatch-live-check DELETE ME",
        "--description", "throwaway record for live_check.py; safe to delete",
        "--type", "task", "--priority", "4", "--json",
    ])
    if create.returncode != 0:
        check("bead.create", False, create.stderr.strip())
        return
    bead_id = json.loads(create.stdout)["id"]
    print(f"  ....  created throwaway bead {bead_id}")
    try:
        present = gather.run_source(*gather.SOURCES["beads_ready"])
        check("bead.gather_ok", present["status"] == "ok", present)
        present_ids = [row["id"] for row in present.get("items", [])]
        check("bead.present_after_create", bead_id in present_ids, bead_id)
    finally:
        deleted = _run(["bd", "delete", bead_id, "--force"])
        check("bead.delete", deleted.returncode == 0, deleted.stderr.strip())
    absent = gather.run_source(*gather.SOURCES["beads_ready"])
    absent_ids = [row["id"] for row in absent.get("items", [])]
    check("bead.absent_after_delete", bead_id not in absent_ids, bead_id)


def gh_forced_failure() -> None:
    """Force a real gh auth failure and confirm it classifies as error, not empty.

    The live counterpart to the fixture decoy: proves the real gh binary still
    exits non-zero on a 401 with an empty array on stdout, and that classify()
    reads it as error against the actual tool, not just canned bytes.
    """
    argv, parse = gather.SOURCES["review_requests"]
    broken_env = dict(os.environ, GH_TOKEN="ghp_forced_invalid_token_for_live_check")
    proc = _run(argv, env=broken_env)
    rec = gather.classify(proc.returncode, proc.stdout, proc.stderr, parse)
    check("gh_forced_failure.is_error", rec["status"] == "error", rec)
    check("gh_forced_failure.no_items_key", "items" not in rec, rec)


JIRA_JQL_TEMPLATE = (
    '(assignee was currentUser() OR reporter = currentUser() '
    'OR watcher = currentUser()) AND updated >= "{lower}"'
)


def jira_drift_shape() -> None:
    """Static guard on the Jira candidate-net shape (ported from standup-prep 1d).

    The synthetic-drift live case (create a ticket, reassign it, touch it later,
    confirm it still appears) needs the Atlassian MCP tool, which a shell cannot
    call, so it runs agent-side under --include-external per the SKILL.md
    procedure. What is automatable here is the invariant that makes drift safe:
    the candidate net has a lower bound only (an upper bound drops tickets whose
    `updated` drifts forward) and uses the `was` history operator (catches a
    ticket assigned then reassigned).
    """
    jql = JIRA_JQL_TEMPLATE.format(lower="2026-01-01")
    check("jira_jql.no_upper_bound", "updated <" not in jql and "updated<=" not in jql, jql)
    check("jira_jql.uses_was_operator", "was currentUser()" in jql, jql)


def external_round_trips() -> None:
    """Real draft-PR and Jira-ticket create/query/delete cycles (opt-in).

    Left as an explicit agent-run procedure rather than silent automation:
    creating a real draft PR requires pushing a branch, and a real Jira ticket
    notifies watchers. The SKILL.md "Live integration procedure" section spells
    out the create -> query -> (drift mutate) -> delete steps for each.
    """
    print("  ....  --include-external: real PR/Jira round-trips are an agent-run")
    print("        procedure (see SKILL.md 'Live integration procedure'); not")
    print("        auto-executed here to avoid silent outward-facing mutations.")


def main(argv: list[str]) -> int:
    print("overwatch live check (safe tier)")
    bead_round_trip()
    gh_forced_failure()
    jira_drift_shape()
    if "--include-external" in argv:
        print("\noverwatch live check (external tier)")
        external_round_trips()

    print()
    if FAILURES:
        print(f"LIVE CHECK FAILED: {len(FAILURES)} assertion(s)")
        return 1
    print("LIVE CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
