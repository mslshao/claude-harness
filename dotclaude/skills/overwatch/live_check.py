#!/usr/bin/env python3
"""Live integration tier for overwatch gather and the prs_reviewing fire policy.

Exercises the real tools end to end, the tier the fixtures cannot cover: that a
record this skill would surface actually round-trips through the live query, that a
real forced failure classifies as error rather than empty, and that the fire policy's
state survives a real `bd` write and a real CLI invocation (docr-wtice).

    python3 ~/.claude/skills/overwatch/live_check.py                    # safe, local only
    python3 ~/.claude/skills/overwatch/live_check.py --include-external # + real PR/Jira

Run before shipping or after touching gather.py or cycle.py. The default run mutates
only the local beads DB (create + delete a throwaway bead) and forces a gh auth
failure with a bogus token (no external state touched). Creating a real draft PR or
Jira ticket is outward-facing, so those live round-trips are gated behind
--include-external and are opt-in per run.

Why the fire policy needs a tier here at all: test_cycle.py stubs `load_state` and
drives `plan_cycle` in process, so nothing it does can catch the two failures that
live only at the boundary. First, the whole policy is keyed on `updated_at`, which
`gather._reviewing_rows` reads as `row.get("updatedAt", "")`; if the live `gh search`
projection ever stops returning that field every watermark silently becomes `""`,
`_advanced` reads every PR as unchanged, and the watcher goes quiet forever with
status `ok`. Second, the state blob now carries a nested `holds` map, and it is
round-tripped through `bd update --notes` and `bd show --json` between every cycle.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import cycle
import gather

# The #11539 ground truth (event set, watermark, and the executable form of the
# agent-side reduction) lives in the fixture tier. Import it rather than restating it:
# a second copy of those timestamps would drift from the fixtures silently.
import test_cycle as fixtures

FAILURES: list[str] = []
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))


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


def reviewing_watermark_is_usable() -> None:
    """The live `gh search prs` projection must still yield a diffable watermark.

    `_reviewing_rows` reads `row.get("updatedAt", "")`, so a dropped or renamed field
    degrades to an empty string per row instead of an error: `_advanced("", "")` is
    False for every PR, no candidate is ever raised, and the fire policy goes silent
    while the source still reports `ok`. Nothing in the fixture tier can see that,
    because the fixtures supply `updated_at` themselves.
    """
    rec = gather.run_source(*gather.SOURCES["prs_reviewing"])
    check("reviewing.live_query_ok", rec["status"] == "ok", rec.get("error_detail", rec))
    rows = rec.get("items") or []
    if not rows:
        # Legitimate (no open PRs the user has reviewed), but it makes the checks below
        # vacuous, so say so rather than banking a green.
        print("  ....  skipped: live prs_reviewing returned 0 rows, so the watermark")
        print("        and key checks below proved nothing this run")
        return
    unusable = [r for r in rows if cycle._safe_parse(r.get("updated_at")) is None]
    check("reviewing.every_live_row_has_a_parseable_updated_at", not unusable,
          [cycle._pr_key(r) for r in unusable[:5]])
    malformed = [r for r in rows if "/" not in cycle._pr_key(r).partition("#")[0]
                 or not cycle._pr_key(r).partition("#")[2]]
    check("reviewing.every_live_row_yields_a_repo_hash_number_key", not malformed,
          [r for r in malformed[:5]])
    print(f"  ....  {len(rows)} live reviewed PR(s) checked, newest "
          f"{max(r['updated_at'] for r in rows)}")


def _cli(bead_id: str, *argv: str) -> tuple[int, dict]:
    """Invoke the real cycle.py as a subprocess and parse its printed plan."""
    proc = _run([sys.executable, os.path.join(SKILL_DIR, "cycle.py"), bead_id, *argv])
    try:
        return proc.returncode, json.loads(proc.stdout)
    except ValueError:
        return proc.returncode, {"_stdout": proc.stdout[-400:], "_stderr": proc.stderr[-400:]}


def fire_policy_round_trip() -> None:
    """Drive one real Path A cycle through the real CLI against a real bead.

    Deterministic despite being live: phase 2 replays a frozen gather file, so no live
    PR state is consulted; `--now` pins the clock; and the classified record is derived
    by the fixture tier's own reduction over the verified #11539 event set. What is
    genuinely live is everything the fixture tier stubs: the process boundary (argparse,
    file reads, exit code), and `bd update --notes` / `bd show --json` carrying a state
    blob that now contains a NESTED holds map.
    """
    now = "2026-08-12T12:45:00Z"  # first cycle after the 12:38:17Z reply on the user's thread
    observed = fixtures.pr_updated_at(fixtures.F1_EVENTS, fixtures._p(now))
    classified = fixtures.classify_window(fixtures.F1_EVENTS, fixtures.BASELINE, observed)
    if not classified.get("explicit"):
        check("fire_policy.fixture_still_describes_an_explicit_signal", False, classified)
        return
    row = {"repository": fixtures.REPO, "number": fixtures.PR, "title": "live-check replay",
           "url": f"https://github.com/{fixtures.REPO}/pull/{fixtures.PR}",
           "updated_at": observed}
    blob = {
        "schema_version": 2, "active": True, "terminal_reason": None,
        "last_cycle_at": "2026-08-12T12:00:00Z", "next_wakeup_at": "2026-08-12T12:30:00Z",
        "consecutive_quiet_successful_cycles": 3, "interval_seconds": 900, "age_days": 7,
        "quiet_period_seconds": 7200,
        "per_source": {
            "prs_authored": {"status": "ok", "known_items": [], "error_detail": None},
            "review_requests": {"status": "ok", "known_items": [], "error_detail": None},
            "prs_reviewing": {"status": "ok", "known_items": {fixtures.KEY: fixtures.BASELINE},
                              "holds": {}, "error_detail": None},
        },
    }
    frozen = {"gathered_at": now, "chat_emitted": False,
              "sources": {"prs_authored": {"status": "ok", "items": []},
                          "review_requests": {"status": "ok", "items": []},
                          "prs_reviewing": {"status": "ok", "items": [row]}},
              "arm": {"due": True, "interval": 900,
                      "next_wakeup_at": "2026-08-12T13:00:00Z"}}

    create = _run([
        "bd", "create",
        "--title", "overwatch-live-check fire policy DELETE ME",
        "--description", "throwaway state bead for live_check.py; safe to delete",
        "--type", "task", "--priority", "4", "--json",
    ])
    if create.returncode != 0:
        check("fire_policy.bead_create", False, create.stderr.strip())
        return
    bead_id = json.loads(create.stdout)["id"]
    print(f"  ....  created throwaway state bead {bead_id}")
    gpath = os.path.join(SKILL_DIR, ".live_check_gather.json")
    rpath = os.path.join(SKILL_DIR, ".live_check_reviewing.json")
    try:
        with open(gpath, "w") as fh:
            json.dump(frozen, fh)
        with open(rpath, "w") as fh:
            json.dump({fixtures.KEY: classified}, fh)

        seeded = _run(["bd", "update", bead_id, "--notes", json.dumps(blob)])
        check("fire_policy.state_write", seeded.returncode == 0, seeded.stderr.strip())
        loaded = cycle.load_state(bead_id)
        check("fire_policy.nested_state_survives_a_real_bd_round_trip", loaded == blob,
              loaded if loaded != blob else "")

        code, plan = _cli(bead_id, "--gather-in", gpath, "--reviewing-file", rpath, "--now", now)
        check("fire_policy.phase2_exits_zero", code == 0 and plan.get("action") == "run",
              (code, plan.get("action"), plan.get("note")))
        chat = plan.get("chat") or ""
        check("fire_policy.path_a_fires_through_the_real_cli",
              "🔁 activity on reviewed PR" in chat and "reply on your thread" in chat, chat)
        # Phase 1 armed; a second arm here would stack two wakeup chains on one loop.
        check("fire_policy.phase2_does_not_arm_a_second_chain",
              plan.get("arming_due") is False, plan.get("arming_due"))
        hold = (((plan.get("blob") or {}).get("per_source", {})
                 .get("prs_reviewing", {}).get("holds") or {}).get(fixtures.KEY) or {})
        check("fire_policy.the_burst_is_recorded_as_fired",
              hold.get("fired") is True and hold.get("fired_via") == "explicit:thread_reply",
              hold)

        # Malformed-call checks run BEFORE the blob is persisted, and the order is
        # load-bearing: the payload-shape validation sits inside plan_cycle, downstream
        # of the double-fire guard, so re-invoking at the same `--now` after a write
        # returns `skip` and never reaches it. Production never hits that (phase 1
        # persists nothing, so at phase-2 time last_cycle_at is a full interval old).
        # Both two-phase flags are required together: either alone must exit 2 rather
        # than falling through to phase 1, which would re-arm and re-print the cycle.
        good = json.dumps({fixtures.KEY: classified})
        code, bad_plan = _cli(bead_id, "--gather-in", gpath, "--now", now)
        check("fire_policy.gather_in_alone_is_rejected_by_the_real_cli",
              code == 2 and bad_plan.get("action") == "error", (code, bad_plan))
        code, bad_plan = _cli(bead_id, "--reviewing-file", rpath, "--now", now)
        check("fire_policy.reviewing_file_alone_is_rejected_by_the_real_cli",
              code == 2 and bad_plan.get("action") == "error", (code, bad_plan))
        with open(rpath, "w") as fh:
            json.dump([{"key": fixtures.KEY}], fh)  # the --candidates-out shape
        code, bad_plan = _cli(bead_id, "--gather-in", gpath, "--reviewing-file", rpath,
                              "--now", now)
        check("fire_policy.a_list_shaped_payload_is_rejected_not_a_traceback",
              code == 2 and bad_plan.get("action") == "error", (code, bad_plan))
        with open(rpath, "w") as fh:
            fh.write(good)

        applied = _run(["bd", "update", bead_id, "--notes", json.dumps(plan["blob"])])
        check("fire_policy.plan_blob_write", applied.returncode == 0, applied.stderr.strip())
        reloaded = cycle.load_state(bead_id)
        check("fire_policy.the_hold_is_readable_on_the_next_cycle",
              reloaded == plan["blob"], reloaded if reloaded != plan["blob"] else "")
    finally:
        for path in (gpath, rpath):
            if os.path.exists(path):
                os.remove(path)
        deleted = _run(["bd", "delete", bead_id, "--force"])
        check("fire_policy.bead_delete", deleted.returncode == 0, deleted.stderr.strip())


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
    reviewing_watermark_is_usable()
    fire_policy_round_trip()
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
