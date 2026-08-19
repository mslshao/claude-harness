#!/usr/bin/env python3
"""Fixture tier for cycle.py's pure state-machine functions.

Covers the reviewed-critical branches (interval calibration, per-source baseline
seeding, diff+known-update, compose, and the prs_reviewing quiet-period fire policy)
with canned inputs, no live tools. Run on any change to cycle.py:

    python3 ~/.claude/skills/overwatch/test_cycle.py

The fire-policy checks are cycle-by-cycle replays of a real review round
(<company>/docr#11539, verified live 2026-08-12), not hand-written
classifications, and each of the three named failure modes has a check of its own.
Those checks passed on their first run because they were written alongside the
implementation, so they were separately shown to FAIL under a one-guard-at-a-time
revert: `bash ~/.claude/scratch/overwatch-mutation-check.sh`. Re-run that after any
change to the policy; a test that cannot fail is documentation, not verification.

Two later additions, and how each earned its red:
  - `boundary.*` and `fixture2.the_settled_fire_*` cover the mutation class the suite
    used to survive, since every pre-existing case crossed a threshold by hours and
    `burst_seconds` was only ever asserted on hand-built dicts: harness M21-M24 flip
    one comparison by a second, or zero one arithmetic result, and each fails exactly
    one of these and nothing else.
  - `cli.*` (main_guard_checks) was written test-first against the unguarded CLI, so
    its red is on record directly: `--gather-in` alone returned `action: classify` with
    `arming_due: true`, and a list- or scalar-valued payload raised AttributeError.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

import cycle
import gather

NOW = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond else f": {detail}"))
    if not cond:
        FAILURES.append(name)


def _p(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


# --- prs_reviewing helpers -----------------------------------------------------

QUIET = 7200


def rv_row(num: int, updated: str, repo: str = "o/r") -> dict:
    return {"repository": repo, "number": num, "title": f"R{num}", "url": f"u{num}",
            "updated_at": updated}


def cls_rec(observed: str, anchor: str | None = None, explicit: bool = False,
            kinds: tuple[str, ...] = (), events: int = 1, status: str = "ok",
            noted: tuple[str, ...] = ()) -> dict:
    """One classified record in the agent-side contract shape."""
    return {"status": status, "observed_updated_at": observed,
            "last_author_activity_at": anchor, "explicit": explicit,
            "explicit_kinds": list(kinds), "noted_kinds": list(noted),
            "author_event_count": events}


def one(prev_mark: str, updated: str, now: str, cls: dict | None = None,
        holds: dict | None = None, quiet: int = QUIET, skip: tuple[str, ...] = ()) -> tuple:
    """Drive plan_reviewing for a single PR (o/r#7) through one cycle."""
    prev = {"status": "ok", "known_items": {"o/r#7": prev_mark}, "holds": holds or {}}
    record = {"status": "ok", "items": [rv_row(7, updated)]}
    classified = {"o/r#7": cls} if cls else {}
    return cycle.plan_reviewing(record, prev, classified, _p(now), quiet, set(skip))


def held(rec: dict, key: str = "o/r#7") -> dict:
    """The hold for one key, or {}. Never raises: a policy regression that drops a
    hold must report as a FAILed check, not abort the rest of the suite."""
    return (rec.get("holds") or {}).get(key) or {}


def hold_of(anchor: str, fired: bool = False, events: int = 1, opened: str | None = None) -> dict:
    return {"o/r#7": {"last_author_activity_at": anchor, "opened_at": opened or anchor,
                      "author_events": events, "fired": fired,
                      "fired_at": None, "fired_via": None}}


# --- Ground truth: <company>/docr#11539 (verified live 2026-08-12) -----
#
# The PR this fire policy came from. Under the OLD policy (fire on any watermark
# advance that is not self and not bot-only) this timeline produced roughly one
# alert per cycle for two hours; the fixtures below assert it now produces exactly
# one, and that the CI bot's closing comment cannot move the quiet timer.

REPO = "<company>/docr"
PR = 11539
KEY = f"{REPO}#{PR}"
USER = "mslshao"
BASELINE = "2026-08-11T22:34:49Z"  # the user's round-2 review
PUSH_ADJACENCY_S = 300

# Events that count as author activity at all. Pushes are included (a new burst can
# start with a push, and the user's Path B covers "author activity"), which is why
# the committer-name bot check and the window filter below are load-bearing.
AUTHOR_KINDS = frozenset({"issue_comment", "review", "review_comment",
                          "review_requested", "committed", "head_ref_force_pushed"})


def ev(kind: str, t: str, who: str, bot: bool = False, **extra) -> dict:
    return {"kind": kind, "t": t, "who": who, "bot": bot, **extra}


# Fixture 1: the real timeline. Two explicit signals reach the user: the 12:38:17
# inline reply on a thread mslshao STARTED, and the 14:41:25 '@mslshao' mention.
F1_EVENTS = [
    # Pre-watermark review comments are kept deliberately: 3762222531 is the reply
    # parent, authored by mslshao 18s BEFORE the baseline watermark, so a window-
    # limited fetch would miss it and silently downgrade Path A to Path B.
    ev("review_comment", "2026-08-11T21:26:18Z", "mslshao", id=3761838445, parent=None),
    ev("review_comment", "2026-08-11T22:18:34Z", "jbyrne", id=3762124316, parent=3761838445),
    ev("review_comment", "2026-08-11T22:34:31Z", "mslshao", id=3762222531, parent=None),
    ev("review_comment", "2026-08-11T22:34:48Z", "mslshao", id=3762223805, parent=3761838445),
    ev("committed", "2026-08-12T12:37:53Z", "Jordan Byrne"),
    ev("review_comment", "2026-08-12T12:38:17Z", "jbyrne", id=3766451082, parent=3762222531),
    ev("review", "2026-08-12T12:38:18Z", "jbyrne", state="COMMENTED"),
    ev("issue_comment", "2026-08-12T12:39:34Z", "jbyrne"),
    ev("committed", "2026-08-12T12:54:13Z", "Jordan Byrne"),
    ev("issue_comment", "2026-08-12T12:56:17Z", "jbyrne"),
    ev("issue_comment", "2026-08-12T13:00:31Z", "jbyrne"),
    ev("committed", "2026-08-12T13:04:38Z", "Jordan Byrne"),
    ev("issue_comment", "2026-08-12T13:05:01Z", "jbyrne"),
    ev("issue_comment", "2026-08-12T13:48:35Z", "jbyrne"),
    ev("committed", "2026-08-12T14:20:32Z", "Jordan Byrne"),
    # Human actor, 2m39s after that push: `gt submit` re-requests reviewers under
    # the author's own token, so actor identity cannot tell a deliberate ask from
    # tooling. Push-adjacent re-requests are therefore NOT explicit.
    ev("review_requested", "2026-08-12T14:23:11Z", "jbyrne", requested="mslshao"),
    ev("issue_comment", "2026-08-12T14:24:20Z", "jbyrne"),
    ev("committed", "2026-08-12T14:36:24Z", "Jordan Byrne"),
    ev("issue_comment", "2026-08-12T14:36:46Z", "jbyrne"),
    ev("committed", "2026-08-12T14:38:12Z", "Jordan Byrne"),
    ev("issue_comment", "2026-08-12T14:40:00Z", "jbyrne"),
    ev("issue_comment", "2026-08-12T14:41:25Z", "jbyrne", mention=True),
    ev("issue_comment", "2026-08-12T14:43:11Z", "sonarqubecloud[bot]", bot=True),
]

# Fixture 2: the same timeline with both explicit signals removed. The 12:38:17
# inline is a NEW top-level thread by the author, and the 14:41:25 comment carries
# no mention. The 14:23:11 re-request stays (real data) and is non-explicit because
# it is push-adjacent.
F2_EVENTS = [
    dict(e, parent=None) if e.get("id") == 3766451082
    else {k: v for k, v in e.items() if k != "mention"} if e["t"] == "2026-08-12T14:41:25Z"
    else e
    for e in F1_EVENTS
]

BOT_LATE = ev("issue_comment", "2026-08-12T17:10:00Z", "sonarqubecloud[bot]", bot=True)
NEW_PUSH = ev("committed", "2026-08-12T18:00:00Z", "Jordan Byrne")


def classify_window(events: list[dict], since: str, upto: str, user: str = USER) -> dict:
    """Executable form of the SKILL.md agent-side reduction contract.

    In production this reduction is agent-side (it needs four paginated per-PR `gh`
    reads, which is why cycle.py is fed classified input rather than raw events).
    Encoding it here is what makes the fixtures end-to-end replays instead of
    hand-written classifications that could quietly agree with a buggy policy.
    """
    lo, hi = _p(since), _p(upto)
    roots = {e["id"]: e for e in events if e["kind"] == "review_comment"}
    pushes = [_p(e["t"]) for e in events
              if e["kind"] in ("committed", "head_ref_force_pushed")]

    def thread_root_author(comment: dict) -> str | None:
        cur = comment
        while cur.get("parent"):
            cur = roots.get(cur["parent"])
            if cur is None:
                return None  # parent deleted: Path A degrades to Path B
        return cur["who"]

    window = [e for e in events if lo < _p(e["t"]) <= hi and e["kind"] in AUTHOR_KINDS]
    # Bot and self events are dropped BEFORE the anchor is taken. This is the whole
    # mechanism behind failure mode 1.
    survivors = [e for e in window if not e["bot"] and e["who"] != user]
    kinds: set[str] = set()
    noted: set[str] = set()
    for e in survivors:
        if e.get("mention"):
            kinds.add("mention")
        if e["kind"] == "review_comment" and thread_root_author(e) == user:
            kinds.add("thread_reply")
    # A `review_requested` naming the user is judged over the FULL window, bot
    # actors INCLUDED. The bot drop exists to keep a CI bot from posing as the
    # author on the quiet timer; a request addressed to the user is aimed at the
    # user whoever's token sent it, and `graphite-app[bot]` is a routine actor on
    # stack re-requests. Dropping it first made this signal unreachable.
    for e in window:
        if e["kind"] != "review_requested" or e.get("requested") != user:
            continue
        if any(0 <= (_p(e["t"]) - p).total_seconds() <= PUSH_ADJACENCY_S for p in pushes):
            noted.add("review_requested")  # tooling re-request: held, but reported
        else:
            kinds.add("review_requested")
    anchor = max((_p(e["t"]) for e in survivors), default=None)
    return {"status": "ok", "observed_updated_at": upto,
            "last_author_activity_at": (anchor.isoformat().replace("+00:00", "Z")
                                        if anchor else None),
            "explicit": bool(kinds), "explicit_kinds": sorted(kinds),
            "noted_kinds": sorted(noted), "author_event_count": len(survivors)}


def pr_updated_at(events: list[dict], now: datetime, baseline: str = BASELINE) -> str:
    """The PR's updatedAt as gather.py would see it: bumped by ANY event, bots
    included (#11539's sonarqubecloud comment at 14:43:11Z moved it to 14:43:12Z)."""
    seen = [_p(e["t"]) for e in events if _p(e["t"]) <= now]
    if not seen:
        return baseline
    latest = max(seen) + timedelta(seconds=1)
    if latest <= _p(baseline):
        return baseline
    return latest.isoformat().replace("+00:00", "Z")


def ticks_every(start: str, end: str, step: int = 900) -> list[str]:
    out, cur = [], _p(start)
    while cur <= _p(end):
        out.append(cur.isoformat().replace("+00:00", "Z"))
        cur += timedelta(seconds=step)
    return out


def replay(events: list[dict], ticks: list[str], prev: dict | None = None,
           quiet: int = QUIET) -> tuple[list[tuple[str, dict]], dict]:
    """Drive the real cycle-by-cycle loop over a fixture timeline."""
    state = prev or {"status": "ok", "known_items": {KEY: BASELINE}, "holds": {}}
    fired: list[tuple[str, dict]] = []
    for tick in ticks:
        now = _p(tick)
        record = {"status": "ok", "items": [
            {"repository": REPO, "number": PR, "title": "R11539", "url": "u11539",
             "updated_at": pr_updated_at(events, now)}]}
        classified = {
            c["key"]: classify_window(events, c["prev_watermark"], c["observed_updated_at"])
            for c in cycle.reviewing_candidates(record, state, set())
        }
        fires, state = cycle.plan_reviewing(record, state, classified, now, quiet, set())
        fired.extend((tick, f) for f in fires)
    return fired, state


def plan_cycle_checks() -> None:
    """plan_cycle wiring, with `bd show` and the gather subprocesses stubbed.

    The pure-function checks above cannot reach the two branches that decide when the
    policy is even consulted: the phase-1 classify handoff, and the single-call cycle
    that detects a settle (no advance means no candidate, so no classification). The
    interval clamp only ever binds on that second one, which is why failure mode 2 is
    verified here and not only through interval_for.
    """
    import argparse

    real_load, real_gather = cycle.load_state, gather.gather
    watermark = "2026-08-12T14:43:12Z"
    anchor = "2026-08-12T14:41:25Z"
    state = {
        "schema_version": 1, "active": True, "terminal_reason": None,
        "last_cycle_at": "2026-08-12T14:00:00Z", "next_wakeup_at": "2026-08-12T14:30:00Z",
        "consecutive_quiet_successful_cycles": 8, "interval_seconds": 3600, "age_days": 7,
        "per_source": {
            "prs_authored": {"status": "ok", "known_items": [], "error_detail": None},
            "review_requests": {"status": "ok", "known_items": [], "error_detail": None},
            "prs_reviewing": {"status": "ok", "known_items": {KEY: BASELINE},
                              "error_detail": None},
            "jira": {"status": "ok", "known_items": [], "error_detail": None},
        },
    }
    row = {"repository": REPO, "number": PR, "title": "T", "url": "u",
           "updated_at": watermark}

    def stub_gather() -> dict:
        return {"prs_authored": {"status": "ok", "items": []},
                "review_requests": {"status": "ok", "items": [dict(row)]},
                "prs_reviewing": {"status": "ok", "items": [dict(row)]}}

    def argv(**kw) -> argparse.Namespace:
        base = dict(bead_id="stub", jira_file=None, now="2026-08-12T14:45:00Z", resume=False,
                    stop=False, interval=None, age_days=None, quiet_period=None,
                    candidates_out=None, gather_out=None, gather_in=None, reviewing_file=None)
        base.update(kw)
        return argparse.Namespace(**base)

    try:
        gather.gather = stub_gather
        cycle.load_state = lambda _b, s=state: json.loads(json.dumps(s))
        plan = cycle.plan_cycle(argv())
        check("plan_cycle.advance_asks_the_agent_to_classify",
              plan["action"] == "classify" and [c["key"] for c in plan["candidates"]] == [KEY],
              plan.get("action"))
        check("plan_cycle.classify_phase_persists_nothing",
              plan["persist"] is False and plan["blob"] is None)
        check("plan_cycle.classify_phase_arms_first_at_the_reset_floor",
              plan["arm"]["due"] is True and plan["arm"]["interval"] == 900, plan.get("arm"))
        # The generic plan contract is "if arming_due, ScheduleWakeup(interval)". A
        # classify plan that reported arming_due:false while arm.due was true meant
        # an agent following only that sentence armed nothing, and a phase 2 that
        # then died (turn limit on a chatty PR) ended the standing loop in silence.
        check("plan_cycle.classify_arming_due_matches_arm_due",
              plan["arming_due"] == plan["arm"]["due"]
              and plan["interval"] == plan["arm"]["interval"],
              (plan.get("arming_due"), plan.get("interval")))

        # A hold is open and nothing advanced: no candidate, single call, and the
        # calibration table alone (cqsc 8) would arm 3600s and find the settle late.
        settled = json.loads(json.dumps(state))
        settled["per_source"]["prs_reviewing"]["known_items"] = {KEY: watermark}
        settled["per_source"]["prs_reviewing"]["holds"] = {KEY: {
            "last_author_activity_at": anchor, "opened_at": "2026-08-12T12:39:34Z",
            "author_events": 18, "fired": False, "fired_at": None, "fired_via": None}}
        cycle.load_state = lambda _b, s=settled: json.loads(json.dumps(s))
        plan = cycle.plan_cycle(argv())
        check("failure_mode_2.open_hold_clamps_the_real_poll_interval",
              plan["action"] == "run" and plan["interval"] == 1800
              and plan["blob"]["interval_seconds"] == 1800, plan.get("interval"))
        check("failure_mode_2.hold_only_cycle_stays_silent_and_still_counts_quiet",
              plan["chat"] is None
              and plan["blob"]["consecutive_quiet_successful_cycles"] == 9)
        check("plan_cycle.upgrades_schema_and_persists_the_quiet_period",
              plan["blob"]["schema_version"] == 2
              and plan["blob"]["quiet_period_seconds"] == 7200)

        plan = cycle.plan_cycle(argv(now="2026-08-12T16:50:00Z"))
        check("plan_cycle.settle_fires_with_no_classification_round_trip",
              "🔁 settled after author activity" in (plan["chat"] or ""), plan.get("chat"))
        check("plan_cycle.settle_alert_describes_the_burst",
              "18 author events" in (plan["chat"] or ""), plan.get("chat"))
        # The re-review that re-added this key to review_requests must not also
        # render its own bare line: that path never sees the quiet period.
        check("plan_cycle.review_request_line_deduped_for_a_reviewed_pr",
              "👀" not in (plan["chat"] or ""), plan.get("chat"))

        # ...but once that burst has settled and been reported, the policy is no
        # longer speaking for the key, so a NEW request must reach the user. Nothing
        # advanced here (no candidate, no fire), and review_requests consumes the key
        # into known_items, so a suppressed line here is lost permanently.
        closed = json.loads(json.dumps(state))
        closed["per_source"]["prs_reviewing"]["known_items"] = {KEY: watermark}
        closed["per_source"]["prs_reviewing"]["holds"] = {KEY: {
            "last_author_activity_at": anchor, "opened_at": anchor, "author_events": 18,
            "fired": True, "fired_at": "2026-08-12T16:45:00Z", "fired_via": "settled"}}
        cycle.load_state = lambda _b, s=closed: json.loads(json.dumps(s))
        plan = cycle.plan_cycle(argv(now="2026-08-13T09:00:00Z"))
        check("plan_cycle.review_request_survives_once_the_burst_has_settled",
              "👀 review requested" in (plan["chat"] or ""), plan.get("chat"))
    finally:
        cycle.load_state, gather.gather = real_load, real_gather


def two_phase_checks() -> None:
    """The phase-1 -> phase-2 handoff, driven through real files.

    Two things only reachable here: that phase 1 surfaces the OTHER sources' deltas
    before the classification round trip (that trip's documented failure mode is a
    turn limit on a chatty PR, which is deterministic, so holding a P1 unblocked bead
    behind it suppressed the bead on every cycle for as long as the PR stayed
    unreadable), and that a classification which comes back errored is reported in
    chat instead of counted as a healthy quiet cycle.
    """
    import argparse
    import os
    import tempfile

    real_load, real_gather = cycle.load_state, gather.gather
    tmp = tempfile.mkdtemp(prefix="overwatch-twophase-")
    gpath = os.path.join(tmp, "gather.json")
    cpath = os.path.join(tmp, "candidates.json")
    rpath = os.path.join(tmp, "reviewing.json")
    watermark = "2026-08-12T14:43:12Z"
    row = {"repository": REPO, "number": PR, "title": "T", "url": "u", "updated_at": watermark}
    state = {
        "schema_version": 2, "active": True, "terminal_reason": None,
        "last_cycle_at": "2026-08-12T14:00:00Z", "next_wakeup_at": "2026-08-12T14:30:00Z",
        "consecutive_quiet_successful_cycles": 4, "interval_seconds": 1800, "age_days": 7,
        "quiet_period_seconds": 7200,
        "per_source": {
            "beads_ready": {"status": "ok", "known_items": [], "error_detail": None},
            "prs_authored": {"status": "ok", "known_items": [], "error_detail": None},
            "review_requests": {"status": "ok", "known_items": [], "error_detail": None},
            "prs_reviewing": {"status": "ok", "known_items": {KEY: BASELINE}, "holds": {},
                              "error_detail": None},
            "jira": {"status": "ok", "known_items": [], "error_detail": None},
        },
    }

    def stub_gather() -> dict:
        return {"beads_ready": {"status": "ok",
                                "items": [{"id": "docr-URGENT", "title": "Ship it",
                                           "priority": "1"}]},
                "prs_authored": {"status": "ok", "items": []},
                "review_requests": {"status": "ok", "items": []},
                "prs_reviewing": {"status": "ok", "items": [dict(row)]}}

    def argv(**kw) -> argparse.Namespace:
        base = dict(bead_id="stub", jira_file=None, now="2026-08-12T14:45:00Z", resume=False,
                    stop=False, interval=None, age_days=None, quiet_period=None,
                    candidates_out=None, gather_out=None, gather_in=None, reviewing_file=None)
        base.update(kw)
        return argparse.Namespace(**base)

    try:
        gather.gather = stub_gather
        cycle.load_state = lambda _b, s=state: json.loads(json.dumps(s))
        p1 = cycle.plan_cycle(argv(gather_out=gpath, candidates_out=cpath))
        check("two_phase.phase1_still_asks_for_classification", p1["action"] == "classify")
        check("two_phase.phase1_surfaces_the_other_sources_deltas",
              "🔓 newly unblocked: docr-URGENT" in (p1["chat"] or ""), p1.get("chat"))
        check("two_phase.phase1_records_that_it_emitted",
              json.load(open(gpath))["chat_emitted"] is True)

        with open(rpath, "w") as fh:
            json.dump({KEY: {"status": "error", "error_detail": "gh api: 403 rate limit"}}, fh)
        p2 = cycle.plan_cycle(argv(gather_in=gpath, reviewing_file=rpath))
        check("two_phase.a_failed_classification_is_reported_in_chat",
              "could not read activity on reviewed PR" in (p2["chat"] or ""), p2.get("chat"))
        check("two_phase.a_failed_classification_holds_the_watermark",
              p2["blob"]["per_source"]["prs_reviewing"]["known_items"] == {KEY: BASELINE},
              p2["blob"]["per_source"]["prs_reviewing"]["known_items"])
        check("two_phase.phase2_does_not_reprint_what_phase1_emitted",
              "🔓" not in (p2["chat"] or ""), p2.get("chat"))
        check("two_phase.phase2_persists_and_does_not_arm_a_second_chain",
              p2["persist"] is True and p2["arming_due"] is False)

        with open(rpath, "w") as fh:
            json.dump({KEY: {"status": "ok", "observed_updated_at": watermark,
                             "last_author_activity_at": "2026-08-12T14:41:25Z",
                             "explicit": True, "explicit_kinds": ["mention"],
                             "author_event_count": 18}}, fh)
        p2 = cycle.plan_cycle(argv(gather_in=gpath, reviewing_file=rpath))
        check("two_phase.a_good_classification_fires_path_a",
              "🔁 activity on reviewed PR" in (p2["chat"] or "")
              and "you were mentioned" in (p2["chat"] or ""), p2.get("chat"))
        check("two_phase.a_good_classification_advances_the_watermark",
              p2["blob"]["per_source"]["prs_reviewing"]["known_items"] == {KEY: watermark})

        # The same failed classification on a cycle where NOTHING else had a delta:
        # this is the state that used to be indistinguishable from healthy-quiet
        # (chat null, quiet counter still climbing, the only trace in plan.note,
        # which the agent contract never prints).
        def quiet_gather() -> dict:
            rec = stub_gather()
            rec["beads_ready"] = {"status": "ok", "items": []}
            return rec

        gather.gather = quiet_gather
        p1 = cycle.plan_cycle(argv(gather_out=gpath, candidates_out=cpath))
        check("two_phase.nothing_else_to_say_means_phase1_stays_silent",
              p1["action"] == "classify" and p1["chat"] is None
              and json.load(open(gpath))["chat_emitted"] is False, p1.get("chat"))
        with open(rpath, "w") as fh:
            json.dump({KEY: {"status": "error", "error_detail": "gh 404"}}, fh)
        p2 = cycle.plan_cycle(argv(gather_in=gpath, reviewing_file=rpath))
        check("two_phase.an_otherwise_quiet_failed_classification_still_speaks",
              "could not read activity on reviewed PR" in (p2["chat"] or ""), p2.get("chat"))
        check("two_phase.a_failed_classification_is_not_counted_as_quiet",
              p2["blob"]["consecutive_quiet_successful_cycles"] == 0
              and " quiet" not in p2["note"],
              (p2["note"], p2["blob"]["consecutive_quiet_successful_cycles"]))
    finally:
        cycle.load_state, gather.gather = real_load, real_gather


def auto_review_carry_checks() -> None:
    """`auto_review` must survive a cycle, because every blob is rebuilt from a fixed
    schema rather than mutated (cycle.py:908), so an uncopied key is DROPPED.

    Why this earns its place: the auto-review ledger (what was already posted, what was
    held, the caps) lives in that key per auto-review.md. Losing it one cycle after
    configuration would silently reset the caps, which is the failure that lets an
    unattended loop approve past its own bound. Shown to fail, not assumed: deleting the
    `carry_auto_review` call flips `survives_a_steady_state_cycle` to FAIL and leaves the
    other two PASSING, so the check is specific to the carry rather than blanket.

    Only the steady-state path is covered because only it is reachable: `fresh = state is
    None or state == "corrupt"` means the baseline path never holds a dict to carry, and a
    corrupt blob is meant to lose the config (it authorizes unattended posting, so it
    fails closed and forces reconfiguration).
    """
    import argparse

    real_load, real_gather = cycle.load_state, gather.gather
    cfg = {"scope": "src/python/mx2/ruleseng/**", "max": 3, "window_seconds": 28800,
           "started_at": "2026-08-17T18:00:00Z", "calibration": "critical only",
           "posted": [{"pr": 11386, "at": "2026-08-17T18:10:00Z", "review_url": "u"}],
           "held": []}

    def empty_gather() -> dict:
        return {"prs_authored": {"status": "ok", "items": []},
                "review_requests": {"status": "ok", "items": []},
                "prs_reviewing": {"status": "ok", "items": []}}

    def argv(**kw) -> argparse.Namespace:
        base = dict(bead_id="stub", jira_file=None, now="2026-08-17T19:00:00Z", resume=False,
                    stop=False, interval=None, age_days=None, quiet_period=None,
                    candidates_out=None, gather_out=None, gather_in=None, reviewing_file=None)
        base.update(kw)
        return argparse.Namespace(**base)

    steady = {
        "schema_version": 2, "active": True, "terminal_reason": None,
        "last_cycle_at": "2026-08-17T18:00:00Z", "next_wakeup_at": "2026-08-17T18:15:00Z",
        "consecutive_quiet_successful_cycles": 1, "interval_seconds": 900, "age_days": 7,
        "per_source": {
            "prs_authored": {"status": "ok", "known_items": [], "error_detail": None},
            "review_requests": {"status": "ok", "known_items": [], "error_detail": None},
            "prs_reviewing": {"status": "ok", "known_items": {}, "error_detail": None},
            "jira": {"status": "ok", "known_items": [], "error_detail": None},
        },
    }

    try:
        gather.gather = empty_gather

        # 1. Steady state: the ledger and caps survive, byte-identical.
        cycle.load_state = lambda _b: {**steady, "auto_review": cfg}
        plan = cycle.plan_cycle(argv())
        check("auto_review.survives_a_steady_state_cycle",
              (plan.get("blob") or {}).get("auto_review") == cfg, plan.get("note"))

        # 2. Baseline (no prior state): a loop configured on its very first cycle keeps it.
        cycle.load_state = lambda _b: None
        plan_fresh = cycle.plan_cycle(argv())
        check("auto_review.absent_when_never_configured",
              "auto_review" not in (plan_fresh.get("blob") or {}), plan_fresh.get("blob"))

        # 3. A non-dict value is not carried: garbage in state must not become config.
        cycle.load_state = lambda _b: {**steady, "auto_review": "ruleseng"}
        plan_bad = cycle.plan_cycle(argv())
        check("auto_review.non_dict_value_is_not_carried",
              "auto_review" not in (plan_bad.get("blob") or {}), plan_bad.get("blob"))
    finally:
        cycle.load_state, gather.gather = real_load, real_gather


def main_guard_checks() -> None:
    """The CLI boundary: the two-phase flags must be paired, and the phase-2 payload
    must be the object shape the contract names.

    Both are agent mistakes with the same consequence, which is why they are rejected
    rather than tolerated. An unpaired `--gather-in` fell through to phase 1's branch,
    which ignores the frozen `arm` and re-composes every other source: a second wakeup
    chain armed on top of phase 1's, and one cycle's deltas printed twice. A
    list-shaped payload (the shape `--candidates-out` emits, so the likely mistake)
    reached `classified.get(...)` as an unhandled AttributeError, and a phase-2 crash
    equals skipping phase 2: nothing persists, no reviewed-PR line renders, and the
    same crash repeats every cycle from the same candidate.
    """
    import contextlib
    import io
    import os
    import tempfile

    real_load, real_gather = cycle.load_state, gather.gather
    tmp = tempfile.mkdtemp(prefix="overwatch-guards-")
    gpath = os.path.join(tmp, "gather.json")
    rpath = os.path.join(tmp, "reviewing.json")
    watermark = "2026-08-12T14:43:12Z"
    row = {"repository": REPO, "number": PR, "title": "T", "url": "u", "updated_at": watermark}
    state = {
        "schema_version": 2, "active": True, "terminal_reason": None,
        "last_cycle_at": "2026-08-12T14:00:00Z", "next_wakeup_at": "2026-08-12T14:30:00Z",
        "consecutive_quiet_successful_cycles": 0, "interval_seconds": 900, "age_days": 7,
        "quiet_period_seconds": 7200,
        "per_source": {
            "prs_authored": {"status": "ok", "known_items": [], "error_detail": None},
            "review_requests": {"status": "ok", "known_items": [], "error_detail": None},
            "prs_reviewing": {"status": "ok", "known_items": {KEY: BASELINE}, "holds": {},
                              "error_detail": None},
        },
    }
    with open(gpath, "w") as fh:
        json.dump({"gathered_at": "2026-08-12T14:45:00Z",
                   "sources": {"prs_authored": {"status": "ok", "items": []},
                               "review_requests": {"status": "ok", "items": []},
                               "prs_reviewing": {"status": "ok", "items": [dict(row)]}},
                   "arm": {"due": True, "interval": 900,
                           "next_wakeup_at": "2026-08-12T15:00:00Z"},
                   "chat_emitted": False}, fh)

    def run_cli(*argv: str) -> tuple[int, dict]:
        """Drive the real main(): argparse, file reads, exit code and printed plan.

        Wrapped so a regression that RAISES reports as a FAILed check; the pure
        functions are driven in process elsewhere, but only main() decides exit codes.
        """
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                code = cycle.main(list(argv))
        except Exception as exc:  # noqa: BLE001 - a raise IS the regression
            return -1, {"_raised": repr(exc)}
        try:
            return code, json.loads(buf.getvalue())
        except ValueError:
            return code, {"_raw": buf.getvalue()}

    def is_usage_error(code: int, plan: dict) -> bool:
        return (code == 2 and plan.get("action") == "error"
                and "--reviewing-file" in (plan.get("note") or ""))

    try:
        gather.gather = lambda: {"prs_reviewing": {"status": "ok", "items": [dict(row)]}}
        cycle.load_state = lambda _b, s=state: json.loads(json.dumps(s))

        with open(rpath, "w") as fh:
            json.dump({KEY: {"status": "error", "error_detail": "x"}}, fh)
        code, plan = run_cli("stub", "--reviewing-file", rpath)
        check("cli.reviewing_file_without_gather_in_is_a_usage_error",
              is_usage_error(code, plan), (code, plan))

        # The mirror. Phase 2's other flag alone must not be read as phase 1: the
        # detail on a failure is `action: classify` + `arming_due: true`, the double-arm.
        code, plan = run_cli("stub", "--gather-in", gpath)
        check("cli.gather_in_without_reviewing_file_is_a_usage_error",
              is_usage_error(code, plan), (code, plan))

        with open(rpath, "w") as fh:
            json.dump([{"key": KEY, "prev_watermark": BASELINE}], fh)  # the candidates shape
        code, plan = run_cli("stub", "--gather-in", gpath, "--reviewing-file", rpath,
                             "--now", "2026-08-12T14:45:00Z")
        check("cli.a_list_shaped_payload_is_a_clean_error_not_a_crash",
              is_usage_error(code, plan), (code, plan))

        with open(rpath, "w") as fh:
            json.dump({KEY: "ok"}, fh)  # right container, wrong record type
        code, plan = run_cli("stub", "--gather-in", gpath, "--reviewing-file", rpath,
                             "--now", "2026-08-12T14:45:00Z")
        check("cli.a_non_record_value_is_a_clean_error_not_a_crash",
              is_usage_error(code, plan), (code, plan))

        # Positive control: the guards must not reject the documented shape.
        with open(rpath, "w") as fh:
            json.dump({KEY: {"status": "ok", "observed_updated_at": watermark,
                             "last_author_activity_at": "2026-08-12T14:41:25Z",
                             "explicit": True, "explicit_kinds": ["mention"],
                             "author_event_count": 18}}, fh)
        code, plan = run_cli("stub", "--gather-in", gpath, "--reviewing-file", rpath,
                             "--now", "2026-08-12T14:45:00Z")
        check("cli.a_well_formed_payload_runs_and_exits_zero",
              code == 0 and plan.get("action") == "run"
              and "🔁 activity on reviewed PR" in (plan.get("chat") or ""), (code, plan))
    finally:
        cycle.load_state, gather.gather = real_load, real_gather


def main() -> int:
    # interval calibration table + override floor
    check("interval.tier0", cycle.interval_for(0, None) == 900)
    check("interval.tier1_low", cycle.interval_for(3, None) == 1800)
    check("interval.tier1_high", cycle.interval_for(5, None) == 1800)
    check("interval.tier2", cycle.interval_for(6, None) == 3600)
    check("interval.override_floor", cycle.interval_for(0, 1200) == 1200)
    check("interval.override_below_backoff", cycle.interval_for(6, 1200) == 3600)

    # baseline seeding: membership full, in_progress aged-only, errored skipped
    old = "2026-06-01T00:00:00Z"  # ~6 weeks old -> aged at age_days=7
    sources = {
        "beads_ready": {"status": "ok", "items": [{"id": "docr-a"}, {"id": "docr-b"}]},
        "in_progress": {"status": "ok", "items": [
            {"id": "docr-old", "updated_at": old},
            {"id": "docr-fresh", "updated_at": "2026-07-13T11:00:00Z"}]},
        "prs_authored": {"status": "ok", "items": [{"repository": "o/r", "number": 5}]},
        "review_requests": {"status": "error", "error_detail": "boom"},
        "jira": {"status": "ok", "items": [{"key": "MX2-AAAAA"}]},
    }
    base = cycle.seed_baseline(sources, NOW, age_days=7)
    check("baseline.beads_full", set(base["beads_ready"]["known_items"]) == {"docr-a", "docr-b"})
    check("baseline.in_progress_aged_only", base["in_progress"]["known_items"] == ["docr-old"])
    check("baseline.pr_key", base["prs_authored"]["known_items"] == ["o/r#5"])
    check("baseline.errored_skipped", "review_requests" not in base)
    check("baseline.jira_key", base["jira"]["known_items"] == ["MX2-AAAAA"])

    # diff: new membership item surfaces; known one does not; known := current
    prev = {
        "beads_ready": {"known_items": ["docr-a"]},
        "in_progress": {"known_items": ["docr-old"]},
        "prs_authored": {"known_items": ["o/r#5"]},
        "review_requests": {"known_items": ["o/r#9"]},
        "jira": {"known_items": ["MX2-AAAAA"]},
    }
    cur = {
        "beads_ready": {"status": "ok", "items": [
            {"id": "docr-a", "title": "A", "priority": "2"},
            {"id": "docr-new", "title": "New", "priority": "1"}]},
        "in_progress": {"status": "ok", "items": [
            {"id": "docr-old", "updated_at": old},
            {"id": "docr-newaged", "title": "NA", "updated_at": old}]},
        "prs_authored": {"status": "ok", "items": [{"repository": "o/r", "number": 5}]},
        "review_requests": {"status": "ok", "items": []},
        "jira": {"status": "ok", "items": [{"key": "MX2-AAAAA"}, {"key": "MX2-BBBBB", "summary": "s"}]},
    }
    deltas, new_ps = cycle.diff_and_update(cur, prev, NOW, age_days=7)
    check("diff.beads_new_only", [r["id"] for r in deltas["beads_ready"]] == ["docr-new"])
    check("diff.beads_known_replaced", set(new_ps["beads_ready"]["known_items"]) == {"docr-a", "docr-new"})
    check("diff.in_progress_newly_aged", [r["id"] for r in deltas["in_progress"]] == ["docr-newaged"])
    check("diff.in_progress_pruned",
          set(new_ps["in_progress"]["known_items"]) == {"docr-old", "docr-newaged"})
    check("diff.review_gone_no_alert", deltas["review_requests"] == [])
    check("diff.review_known_emptied", new_ps["review_requests"]["known_items"] == [])
    check("diff.jira_new", [r["key"] for r in deltas["jira"]] == ["MX2-BBBBB"])

    # errored source: carried forward, no delta, marked error
    cur_err = dict(cur)
    cur_err["beads_ready"] = {"status": "error", "error_detail": "gh 401"}
    d2, ps2 = cycle.diff_and_update(cur_err, prev, NOW, age_days=7)
    check("diff.error_no_delta", "beads_ready" not in d2)
    check("diff.error_carries_known", ps2["beads_ready"]["known_items"] == ["docr-a"])
    check("diff.error_marked", ps2["beads_ready"]["status"] == "error")

    # never-succeeded source re-baselines silently (delta empty, known := current)
    prev_partial = {"beads_ready": {"known_items": ["docr-a"]}}  # others never succeeded
    d3, ps3 = cycle.diff_and_update(cur, prev_partial, NOW, age_days=7)
    check("diff.rebaseline_silent", d3.get("jira") == [])
    check("diff.rebaseline_known_set", set(ps3["jira"]["known_items"]) == {"MX2-AAAAA", "MX2-BBBBB"})

    # compose: quiet -> None; deltas -> lines; error -> warn line; catch-up prefix
    check("compose.quiet_none", cycle.compose({}, {"beads_ready": {"status": "ok"}}, 7, False) is None)
    out = cycle.compose(deltas, cur, 7, catch_up=True)
    check("compose.catchup_prefix", out.startswith("[overwatch catch-up"))
    check("compose.has_unblocked", "🔓 newly unblocked: docr-new" in out)
    check("compose.has_review_none", "👀" not in out)  # review delta empty this case
    errout = cycle.compose({}, {"review_requests": {"status": "error", "error_detail": "x"}}, 7, False)
    check("compose.source_failure_line", errout is not None and "⚠️ source review_requests failed" in errout)

    # ---- prs_reviewing: source ownership and watermark bookkeeping ------------
    t1 = "2026-07-10T00:00:00Z"
    t2 = "2026-07-12T00:00:00Z"
    rv_base = cycle.seed_baseline(
        {"prs_reviewing": {"status": "ok", "items": [rv_row(7, t1)]}}, NOW, age_days=7)
    check("watermark.baseline_marks", rv_base["prs_reviewing"]["known_items"] == {"o/r#7": t1})
    check("watermark.baseline_holds_empty", rv_base["prs_reviewing"]["holds"] == {})

    # diff_and_update no longer touches this source at all (plan_reviewing owns it).
    rv_cur = {"prs_reviewing": {"status": "ok", "items": [rv_row(7, t2), rv_row(9, t2)]}}
    rvd, rvps = cycle.diff_and_update(
        rv_cur, {"prs_reviewing": {"known_items": {"o/r#7": t1}}}, NOW, age_days=7)
    check("watermark.not_owned_by_diff_and_update",
          "prs_reviewing" not in rvd and "prs_reviewing" not in rvps)

    # A bare advance no longer alerts: without a classification it cannot be told
    # apart from a bot bump, so the watermark is HELD for the next cycle to retry.
    fires, rec = one(t1, t2, "2026-07-12T01:00:00Z")
    check("watermark.advance_alone_no_longer_alerts", fires == [])
    check("watermark.unclassified_holds_the_watermark", rec["known_items"] == {"o/r#7": t1})

    # first appearance silent, departed key pruned, own PR skipped, quiet unchanged
    _, rec = cycle.plan_reviewing(
        {"status": "ok", "items": [rv_row(7, t2), rv_row(9, t2)]},
        {"status": "ok", "known_items": {"o/r#7": t1, "o/r#8": t1}, "holds": {}},
        {"o/r#7": cls_rec(t2, anchor=t2)}, NOW + timedelta(days=1), QUIET, set())
    check("watermark.first_appearance_silent_and_departed_pruned",
          rec["known_items"] == {"o/r#7": t2, "o/r#9": t2})
    fires, rec = one(t1, t2, "2026-07-12T01:00:00Z", cls_rec(t2, anchor=t2), skip=("o/r#7",))
    check("watermark.own_pr_skipped", fires == [] and rec["holds"] == {})
    fires, rec = one(t1, t1, "2026-07-12T01:00:00Z")
    check("watermark.unchanged_quiet", fires == [] and rec["known_items"] == {"o/r#7": t1})

    # errored source: not diffed, marks AND holds carried forward, no hold evaluated
    fires, rec = cycle.plan_reviewing(
        {"status": "error", "error_detail": "gh 500"},
        {"status": "ok", "known_items": {"o/r#7": t1}, "holds": hold_of(t1),
         "last_success_at": t1},
        {}, NOW + timedelta(days=30), QUIET, set())
    check("watermark.error_no_fire", fires == [])
    check("watermark.error_carries_marks", rec["known_items"] == {"o/r#7": t1})
    check("watermark.error_carries_holds", rec["holds"] == hold_of(t1))
    check("watermark.error_marked", rec["status"] == "error")

    # never-succeeded source re-baselines silently with full marks and no holds
    fires, rec = cycle.plan_reviewing(
        {"status": "ok", "items": [rv_row(7, t2), rv_row(9, t2)]}, {}, {}, NOW, QUIET, set())
    check("watermark.rebaseline_silent", fires == [])
    check("watermark.rebaseline_marks", rec["known_items"] == {"o/r#7": t2, "o/r#9": t2})
    check("watermark.rebaseline_no_holds", rec["holds"] == {})

    # ---- Path A: an explicit signal fires immediately -------------------------
    a1 = "2026-07-12T00:30:00Z"
    fires, rec = one(t1, t2, "2026-07-12T00:35:00Z",
                     cls_rec(t2, anchor=a1, explicit=True, kinds=("mention",), events=3))
    check("pathA.explicit_fires_immediately",
          len(fires) == 1 and fires[0]["fire_reason"] == "explicit", fires)
    check("pathA.explicit_kinds_carried", fires and fires[0]["explicit_kinds"] == ["mention"])
    check("pathA.clears_the_hold", held(rec).get("fired") is True)
    check("pathA.records_which_path_fired",
          held(rec).get("fired_via") == "explicit:mention")
    fires, rec = one(t1, t2, "2026-07-12T00:35:00Z",
                     cls_rec(t2, anchor=a1, explicit=True, kinds=("mention",)),
                     holds=hold_of(a1, fired=True))
    check("pathA.suppressed_inside_an_already_fired_burst", fires == [])
    # One fire per burst is the ratified rule, so the mention is not re-alerted.
    # It must at least be VISIBLE in state: an invisible drop is how the suppression
    # stops being a documented tradeoff and becomes a silent bug.
    check("pathA.suppression_is_recorded_in_state",
          held(rec).get("suppressed_explicit_kinds") == ["mention"], held(rec))

    # A re-review request whose ACTOR is a bot (graphite's stack fan-out) is aimed
    # at the user all the same. The reduction judges it before the bot drop, so it
    # arrives with explicit=true and NO author anchor; the fire must still happen,
    # because the membership 👀 line is suppressed while this policy owns the key.
    bot_request = ev("review_requested", "2026-07-12T00:30:20Z", "graphite-app[bot]",
                     bot=True, requested=USER)
    req_seen = "2026-07-12T00:31:00Z"
    cw = classify_window([bot_request], t1, req_seen)
    check("pathA.a_bot_actor_review_request_is_explicit",
          cw["explicit"] and cw["explicit_kinds"] == ["review_requested"], cw)
    check("pathA.a_bot_actor_request_contributes_no_author_activity",
          cw["last_author_activity_at"] is None and cw["author_event_count"] == 0, cw)
    fires, rec = one(t1, t2, "2026-07-12T00:35:00Z",
                     cls_rec(t2, anchor=None, explicit=True,
                             kinds=("review_requested",), events=0))
    check("pathA.explicit_without_an_author_anchor_still_fires_now",
          len(fires) == 1 and fires[0]["fire_reason"] == "explicit", fires)
    check("pathA.explicit_without_an_author_anchor_closes_the_burst",
          held(rec).get("fired") is True and held(rec).get("fired_via")
          == "explicit:review_requested", held(rec))
    # Push-adjacent, i.e. `gt submit` re-requesting under the author's token: held
    # (Path B), but carried through so the settled line can name it.
    cw = classify_window([ev("committed", "2026-07-12T00:30:00Z", "Jordan Byrne"), bot_request],
                        t1, req_seen)
    check("pathB.a_push_adjacent_request_is_noted_not_explicit",
          cw["explicit"] is False and cw["noted_kinds"] == ["review_requested"], cw)
    fires, rec = one(t1, t2, "2026-07-12T00:35:00Z",
                     cls_rec(t2, anchor=a1, noted=("review_requested",)))
    check("pathB.a_noted_signal_rides_on_the_hold",
          fires == [] and held(rec).get("noted_kinds") == ["review_requested"], held(rec))

    # ---- Path B: hold, refresh, then fire once settled ------------------------
    fires, rec = one(t1, t2, "2026-07-12T00:35:00Z", cls_rec(t2, anchor=a1, events=4))
    check("pathB.author_activity_holds_instead_of_firing", fires == [])
    check("pathB.hold_anchors_on_last_author_activity",
          held(rec).get("last_author_activity_at") == a1)
    check("pathB.hold_counts_events", held(rec).get("author_events") == 4)

    t3 = "2026-07-12T01:00:00Z"
    fires, rec = one(t2, t3, "2026-07-12T01:05:00Z", cls_rec(t3, anchor=t3, events=2),
                     holds=hold_of(a1, events=4))
    check("pathB.new_activity_refreshes_the_timer", fires == [])
    check("pathB.refresh_moves_the_anchor",
          held(rec).get("last_author_activity_at") == t3
          and held(rec).get("author_events") == 6)

    fires, rec = one(t2, t2, "2026-07-12T02:29:59Z", holds=hold_of("2026-07-12T00:30:00Z"))
    check("pathB.does_not_fire_one_second_early", fires == [])
    fires, rec = one(t2, t2, "2026-07-12T02:30:00Z", holds=hold_of("2026-07-12T00:30:00Z"))
    check("pathB.fires_exactly_at_the_quiet_period", len(fires) == 1
          and fires[0]["fire_reason"] == "settled", fires)
    fires, _ = one(t2, t2, "2026-07-12T05:00:00Z", holds=rec["holds"])
    check("pathB.settled_fires_only_once", fires == [])

    # A burst that ended while nothing was polling (slept codespace) must fire on
    # the first cycle back, not one cycle later.
    fires, _ = one(t1, t2, "2026-07-12T09:00:00Z", cls_rec(t2, anchor=a1, events=9))
    check("pathB.settled_before_first_cycle_fires_immediately",
          len(fires) == 1 and fires[0]["fire_reason"] == "settled", fires)

    # A hold that settled AND saw new activity in the same cycle (a catch-up cycle
    # after a gap) fires ONCE and absorbs that activity into the burst it is
    # reporting. The activity is a full quiet period past the old anchor, so without
    # absorption it would open a fresh burst and the alert would describe only the
    # last event instead of the burst the user is being told about.
    t4 = "2026-07-12T03:00:00Z"
    fires, rec = one(t2, t4, "2026-07-12T03:05:00Z", cls_rec(t4, anchor=t4, events=2),
                     holds=hold_of("2026-07-12T00:30:00Z", events=5))
    check("pathB.settle_absorbs_same_cycle_activity",
          len(fires) == 1 and fires[0]["fire_reason"] == "settled", fires)
    check("pathB.absorbed_fire_describes_the_whole_burst",
          fires and fires[0]["author_events"] == 7
          and held(rec).get("opened_at") == "2026-07-12T00:30:00Z", fires)
    fires, _ = one(t4, t4, "2026-07-12T06:00:00Z", holds=rec["holds"])
    check("pathB.absorbed_activity_does_not_re_fire", fires == [])

    # Two `>=` comparisons decide the settle, and the checks above run through BOTH at
    # once (with no new activity the pre-anchor and the anchor are the same instant, so
    # either one alone still fires). Reverting either to `>` therefore left the suite
    # green. These two pin them independently: each isolates one comparison AT its
    # boundary while the other cannot mask it.
    b_now = "2026-07-12T04:00:00Z"          # exactly QUIET after 02:00:00Z
    b_anchor = "2026-07-12T02:00:00Z"
    # (a) settle_due's own `>=`: a FRESH hold, so pre_settled is False by construction.
    fires, _ = one(t2, b_now, b_now, cls_rec(b_now, anchor=b_anchor, events=3))
    check("boundary.a_fresh_hold_fires_exactly_at_the_quiet_period",
          len(fires) == 1 and fires[0]["fire_reason"] == "settled", fires)
    fires, _ = one(t2, b_now, "2026-07-12T03:59:59Z",
                   cls_rec(b_now, anchor=b_anchor, events=3))
    check("boundary.a_fresh_hold_does_not_fire_one_second_early", fires == [], fires)
    # (b) pre_settled's own `>=`: new author activity lands 60s before `now`, so the
    # anchor-side comparison is False and only pre_settled can fire this cycle. That
    # also proves the absorb path, which is gated on the same value.
    fires, rec = one(t2, b_now, b_now,
                     cls_rec(b_now, anchor="2026-07-12T03:59:00Z", events=2),
                     holds=hold_of(b_anchor, events=5))
    check("boundary.a_pre_settled_hold_fires_at_the_period_despite_newer_activity",
          len(fires) == 1 and fires[0]["fire_reason"] == "settled"
          and fires[0]["author_events"] == 7, fires)
    check("boundary.the_absorbed_burst_keeps_its_original_open",
          held(rec).get("opened_at") == b_anchor, held(rec))
    fires, _ = one(t2, b_now, "2026-07-12T03:59:59Z",
                   cls_rec(b_now, anchor="2026-07-12T03:59:00Z", events=2),
                   holds=hold_of(b_anchor, events=5))
    check("boundary.a_pre_settled_hold_does_not_fire_one_second_early", fires == [], fires)

    # The burst-start rule in _fold_author_activity is a third `>=` with no boundary
    # cover: reverting it to `>` left the whole suite green, because every case that
    # crosses it does so by hours. Exactly one quiet period must open a NEW burst.
    n_now = "2026-07-12T04:05:00Z"
    fires, rec = one(t2, n_now, n_now, cls_rec(n_now, anchor=b_now, events=2),
                     holds=hold_of(b_anchor, fired=True, events=5))
    check("boundary.activity_exactly_one_quiet_period_later_opens_a_new_burst",
          fires == [] and held(rec).get("opened_at") == b_now
          and held(rec).get("fired") is False
          and held(rec).get("author_events") == 2, held(rec))
    fires, rec = one(t2, n_now, n_now,
                     cls_rec(n_now, anchor="2026-07-12T03:59:59Z", events=2),
                     holds=hold_of(b_anchor, fired=True, events=5))
    check("boundary.activity_one_second_inside_the_period_stays_in_the_fired_burst",
          fires == [] and held(rec).get("opened_at") == b_anchor
          and held(rec).get("fired") is True
          and held(rec).get("author_events") == 7, held(rec))

    # Explicit beats settled on the reason: a settled-labelled alert would never
    # tell the user they were named, and the burst then suppresses the mention.
    fires, _ = one(t2, t3, "2026-07-12T02:35:00Z",
                   cls_rec(t3, anchor=t3, explicit=True, kinds=("thread_reply",)),
                   holds=hold_of("2026-07-12T00:30:00Z"))
    check("precedence.explicit_wins_over_settled",
          len(fires) == 1 and fires[0]["fire_reason"] == "explicit", fires)

    # ---- FAILURE MODE 1: bot activity must not refresh the quiet timer --------
    fires, rec = one(t2, t3, "2026-07-12T01:05:00Z", cls_rec(t3, anchor=None),
                     holds=hold_of(a1))
    check("failure_mode_1.bot_only_advance_does_not_refresh_the_timer",
          held(rec).get("last_author_activity_at") == a1 and fires == [])
    check("failure_mode_1.bot_only_advance_still_advances_the_watermark",
          rec["known_items"] == {"o/r#7": t3})
    fires, rec = one(t2, t3, "2026-07-12T01:05:00Z", cls_rec(t3, anchor=None))
    check("failure_mode_1.bot_only_advance_opens_no_hold", rec["holds"] == {} and fires == [])
    # The unclassified path is the other way a bot could reach the timer: it must
    # never anchor on updatedAt, which bots bump.
    fires, rec = one(t2, t3, "2026-07-12T01:05:00Z", holds=hold_of(a1))
    check("failure_mode_1.unclassified_never_anchors_on_updated_at",
          held(rec).get("last_author_activity_at") == a1
          and held(rec).get("unclassified") is True and fires == [])
    check("failure_mode_1.unclassified_does_not_advance_the_watermark",
          rec["known_items"] == {"o/r#7": t2})
    fires, rec = one(t2, t3, "2026-07-12T01:05:00Z", cls_rec(t3, status="error"))
    check("failure_mode_1.per_key_classification_error_opens_no_hold",
          rec["holds"] == {} and fires == [] and rec["known_items"] == {"o/r#7": t2})

    # ---- FAILURE MODE 2: interval clamp while a hold is open ------------------
    check("failure_mode_2.backoff_unclamped_without_holds", cycle.interval_for(6, None) == 3600)
    check("failure_mode_2.clamped_while_a_hold_is_open",
          cycle.interval_for(6, None, holds_open=True) == 1800)
    check("failure_mode_2.clamped_at_the_middle_tier_too",
          cycle.interval_for(4, None, holds_open=True) == 1800)
    check("failure_mode_2.explicit_override_still_wins",
          cycle.interval_for(6, 3600, holds_open=True) == 3600)
    check("failure_mode_2.clamp_respects_a_short_quiet_period",
          cycle.interval_for(6, None, holds_open=True, hold_max=600) == 900)
    check("failure_mode_2.has_open_hold_true_for_unfired",
          cycle.has_open_hold({"holds": hold_of(a1)}) is True)
    check("failure_mode_2.has_open_hold_ignores_fired",
          cycle.has_open_hold({"holds": hold_of(a1, fired=True)}) is False)
    check("failure_mode_2.has_open_hold_none", cycle.has_open_hold({}) is False)

    # ---- FAILURE MODE 3: one fire per burst ----------------------------------
    # (the fixture replays below are the load-bearing coverage; these pin the rule)
    fires, rec = one(t2, t3, "2026-07-12T01:05:00Z", cls_rec(t3, anchor=t3),
                     holds=hold_of(a1, fired=True))
    check("failure_mode_3.activity_inside_a_fired_burst_stays_silent",
          fires == [] and held(rec).get("fired") is True)
    far = "2026-07-12T06:00:00Z"
    fires, rec = one(t2, far, "2026-07-12T06:05:00Z", cls_rec(far, anchor=far),
                     holds=hold_of(a1, fired=True))
    check("failure_mode_3.activity_a_quiet_period_later_starts_a_new_burst",
          fires == [] and held(rec).get("fired") is False
          and held(rec).get("opened_at") == far)
    fires, _ = one(far, far, "2026-07-12T08:00:00Z", holds=rec["holds"])
    check("failure_mode_3.the_new_burst_fires_on_its_own_settle", len(fires) == 1, fires)

    # ---- hold lifecycle: eventual-consistency grace, skew, quiet-period clamp -
    absent = {"status": "ok", "items": []}
    prev_h = {"status": "ok", "known_items": {"o/r#7": t2}, "holds": hold_of(a1)}
    _, rec = cycle.plan_reviewing(absent, prev_h, {}, NOW, QUIET, set())
    check("hold.unfired_survives_a_lagging_search_index",
          held(rec).get("absent_cycles") == 1 and rec["known_items"] == {"o/r#7": t2})
    for _ in range(cycle.HOLD_ABSENT_GRACE_CYCLES):
        _, rec = cycle.plan_reviewing(absent, rec, {}, NOW, QUIET, set())
    check("hold.unfired_dropped_after_the_grace", rec["holds"] == {})
    _, rec = cycle.plan_reviewing(
        absent, {"status": "ok", "known_items": {"o/r#7": t2}, "holds": hold_of(a1, fired=True)},
        {}, NOW, QUIET, set())
    check("hold.fired_pruned_immediately_on_close", rec["holds"] == {})
    _, rec = cycle.plan_reviewing(
        {"status": "ok", "items": [rv_row(7, t2)]},
        {"status": "ok", "known_items": {"o/r#7": t2},
         "holds": {"o/r#7": dict(hold_of(a1)["o/r#7"], absent_cycles=2)}},
        {}, NOW, QUIET, set())
    check("hold.absence_counter_resets_when_the_pr_returns",
          "absent_cycles" not in held(rec))

    # Past the grace the hold used to be dropped WITH its watermark, so the key came
    # back as a first appearance and was baselined silently: the pending alert and
    # every author event in the absent window vanished. It now fires on the way out.
    with_id = {"o/r#7": dict(hold_of(a1)["o/r#7"],
                             pr={"repository": "o/r", "number": 7, "title": "R7", "url": "u7"})}
    rec = {"status": "ok", "known_items": {"o/r#7": t2}, "holds": with_id}
    grace_fires: list[dict] = []
    for _ in range(cycle.HOLD_ABSENT_GRACE_CYCLES + 1):
        f, rec = cycle.plan_reviewing(absent, rec, {}, NOW, QUIET, set())
        grace_fires.extend(f)
    check("hold.grace_expiry_fires_the_pending_alert_instead_of_dropping_it",
          len(grace_fires) == 1 and grace_fires[0]["fire_reason"] == "settled", grace_fires)
    check("hold.grace_expiry_alert_identifies_the_pr",
          grace_fires and cycle._pr_key(grace_fires[0]) == "o/r#7"
          and grace_fires[0].get("absent_from_search") is True, grace_fires)
    check("hold.grace_expiry_then_drops_the_hold", rec["holds"] == {} and rec["known_items"] == {})
    out = cycle.compose({"prs_reviewing": grace_fires}, {}, 7, False)
    check("compose.grace_expiry_line_says_the_pr_left_the_result",
          "PR left the search result" in (out or ""), out)
    # A hold with no anchor at all (nothing to report) still just prunes.
    _, rec = cycle.plan_reviewing(
        absent, {"status": "ok", "known_items": {"o/r#7": t2},
                 "holds": {"o/r#7": {"fired": False, "absent_cycles": 3}}},
        {}, NOW, QUIET, set())
    check("hold.anchorless_hold_prunes_without_a_phantom_alert", rec["holds"] == {})

    skew_now = "2026-07-12T01:00:00Z"
    _, rec = one(t2, t3, skew_now, cls_rec(t3, anchor="2026-07-12T09:00:00Z"))
    check("skew.future_anchor_clamped_to_now",
          held(rec).get("last_author_activity_at") == cycle._iso_z(_p(skew_now)))
    _, rec = one(t2, t3, skew_now, cls_rec(t3, anchor="2026-07-12T00:45:00"))
    check("skew.naive_anchor_read_as_utc_not_a_crash",
          held(rec).get("last_author_activity_at") == "2026-07-12T00:45:00Z")
    _, rec = one(t2, t3, skew_now, cls_rec(t3, anchor=t1))
    check("skew.anchor_below_the_watermark_is_dropped", rec["holds"] == {})

    # ---- Watermark validation: the agent's echo is boundary input --------------
    # A tz-naive or unparseable `observed_updated_at` written straight into the blob
    # poisoned state: every LATER cycle then raised while diffing it, inside
    # reviewing_candidates, before a plan existed and before anything was armed, so
    # the loop died and re-died from the persisted value on every /overwatch.
    _, rec = one(t1, t2, "2026-07-12T01:00:00Z", cls_rec("2026-07-12T00:00:00", anchor=None))
    check("watermark.naive_echo_is_canonicalized", rec["known_items"] == {"o/r#7": t2},
          rec["known_items"])
    _, rec = one(t1, t2, "2026-07-12T01:00:00Z", cls_rec("not a timestamp", anchor=None))
    check("watermark.unparseable_echo_falls_back_to_the_row",
          rec["known_items"] == {"o/r#7": t2}, rec["known_items"])
    cands = cycle.reviewing_candidates(
        {"status": "ok", "items": [rv_row(7, "2026-07-12T02:00:00Z")]}, rec, set())
    check("watermark.a_persisted_mark_stays_diffable_next_cycle",
          [c["key"] for c in cands] == ["o/r#7"], cands)
    _, rec = one(t2, "2026-07-12T03:00:00Z", "2026-07-12T04:00:00Z", cls_rec(t1, anchor=None))
    check("watermark.echo_below_the_previous_mark_does_not_regress",
          rec["known_items"] == {"o/r#7": t2}, rec["known_items"])
    _, rec = one(t2, "2026-07-12T03:00:00Z", "2026-07-12T04:00:00Z",
                 cls_rec("2026-07-12T02:00:00Z", anchor=None))
    check("watermark.mark_never_passes_the_end_of_the_classified_window",
          rec["known_items"] == {"o/r#7": "2026-07-12T02:00:00Z"}, rec["known_items"])
    # A future mark would freeze the key: nothing ever advances past it again.
    prev_f = {"status": "ok", "known_items": {"o/r#7": t2}, "holds": {}}
    _, rec = cycle.plan_reviewing(
        {"status": "ok", "items": [{"repository": "o/r", "number": 7, "title": "R7",
                                    "url": "u7", "updated_at": ""}]},
        prev_f, {"o/r#7": cls_rec("2027-01-01T00:00:00Z", anchor=None)},
        _p("2026-07-12T04:00:00Z"), QUIET, set())
    check("watermark.a_future_echo_cannot_freeze_the_key",
          rec["known_items"] == {"o/r#7": t2}, rec["known_items"])
    # A blob poisoned before this guard existed self-heals instead of raising. Both
    # calls are wrapped: the regression here is a raised TypeError that would abort
    # the whole suite, and a check that aborts reports nothing about the other checks.
    poisoned = {"status": "ok", "known_items": {"o/r#7": "2026-07-12T00:00:00"}, "holds": {}}
    try:
        cands = cycle.reviewing_candidates(
            {"status": "ok", "items": [rv_row(7, t3)]}, poisoned, set())
        ok, detail = [c["key"] for c in cands] == ["o/r#7"], cands
    except Exception as exc:  # noqa: BLE001 - a raise IS the regression
        ok, detail = False, f"raised {exc!r}"
    check("watermark.a_naive_persisted_mark_diffs_without_raising", ok, detail)
    try:
        fires, rec = cycle.plan_reviewing(
            {"status": "ok", "items": [rv_row(7, t2)]},
            {"status": "ok", "known_items": {"o/r#7": "garbage"}, "holds": {}},
            {}, NOW, QUIET, set())
        ok, detail = fires == [] and rec["known_items"] == {"o/r#7": t2}, rec["known_items"]
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"raised {exc!r}"
    check("watermark.an_unusable_persisted_mark_self_heals", ok, detail)

    # ---- Ownership of the notification for an already-reviewed PR --------------
    # The 👀 line is suppressed only for keys this policy is actually speaking for.
    # Suppressing it for every reviewed PR lost the ask entirely when the policy
    # produced neither a fire nor a hold (a request the reduction could not
    # attribute, or one on a PR whose burst had long settled).
    fresh_fire = {**rv_row(7, t2), "fire_reason": "explicit", "explicit_kinds": ["mention"]}
    check("owned.a_fire_this_cycle_owns_the_key",
          cycle.reviewing_owned_keys({"holds": {}}, [fresh_fire], NOW, QUIET) == {"o/r#7"})
    check("owned.an_unfired_hold_owns_the_key",
          cycle.reviewing_owned_keys({"holds": hold_of(cycle._iso_z(NOW))}, [], NOW, QUIET)
          == {"o/r#7"})
    live = cycle._iso_z(NOW - timedelta(seconds=QUIET - 60))
    check("owned.a_live_fired_burst_still_owns_the_key",
          cycle.reviewing_owned_keys({"holds": hold_of(live, fired=True)}, [], NOW, QUIET)
          == {"o/r#7"})
    old = cycle._iso_z(NOW - timedelta(seconds=QUIET + 60))
    check("owned.a_settled_burst_owns_nothing",
          cycle.reviewing_owned_keys({"holds": hold_of(old, fired=True)}, [], NOW, QUIET) == set())

    check("quiet_period.default", cycle.resolve_quiet_period(None, None) == 7200)
    check("quiet_period.flag_wins", cycle.resolve_quiet_period(3600, 7200) == 3600)
    check("quiet_period.persisted_used", cycle.resolve_quiet_period(None, 3600) == 3600)
    check("quiet_period.clamped_low", cycle.resolve_quiet_period(5, None) == 300)
    check("quiet_period.clamped_high", cycle.resolve_quiet_period(999999, None) == 86400)

    # ---- compose: fire lines and the review_requests dedup --------------------
    explicit_fire = {**rv_row(7, t2), "fire_reason": "explicit",
                     "explicit_kinds": ["mention"], "author_events": 3, "burst_seconds": 0,
                     "quiet_period_seconds": 7200}
    settled_fire = {**rv_row(7, t2), "fire_reason": "settled", "explicit_kinds": [],
                    "author_events": 11, "burst_seconds": 7511, "quiet_period_seconds": 7200}
    out = cycle.compose({"prs_reviewing": [explicit_fire]}, {}, 7, False)
    check("compose.explicit_line_names_the_signal",
          out == "🔁 activity on reviewed PR: o/r#7 R7 u7 (you were mentioned)", out)
    out = cycle.compose({"prs_reviewing": [settled_fire]}, {}, 7, False)
    check("compose.settled_line_carries_burst_context",
          out == "🔁 settled after author activity: o/r#7 R7 u7 "
                 "(11 author events over 2h05m, quiet 2h)", out)
    rr = {"review_requests": [rv_row(7, t2)], "prs_reviewing": [settled_fire]}
    out = cycle.compose(rr, {}, 7, False, owned_keys={"o/r#7"})
    check("compose.review_request_deduped_when_the_policy_owns_the_key",
          "👀" not in out and "🔁 settled" in out, out)
    out = cycle.compose(rr, {}, 7, False)
    check("compose.review_request_kept_when_the_policy_owns_nothing",
          "👀 review requested" in out)
    out = cycle.compose({"prs_reviewing": [{**settled_fire, "noted_kinds": ["review_requested"]}]},
                        {}, 7, False)
    check("compose.settled_line_names_a_held_re_review_request",
          "re-review requested" in (out or ""), out)

    # A candidate the agent could not classify MUST render. The watermark is held so
    # the key re-candidates forever; with no line the cycle looks healthy-quiet while
    # activity on a reviewed PR sits unread indefinitely.
    out = cycle.compose({}, {"prs_reviewing": {"status": "ok"}}, 7, False,
                        degraded=[("o/r#7", "gh api: 403 rate limit")])
    check("compose.an_unclassifiable_candidate_is_never_silent",
          out is not None and "could not read activity on reviewed PR o/r#7" in out
          and "403" in out, out)

    # ---- Ground-truth fixture replays (<company>/docr#11539) ----------
    day = ("2026-08-12T12:00:00Z", "2026-08-12T20:00:00Z")

    f1, f1_state = replay(F1_EVENTS, ticks_every(*day))
    check("fixture1.exactly_one_fire_for_the_whole_burst", len(f1) == 1,
          [(t, f["fire_reason"]) for t, f in f1])
    check("fixture1.fires_on_the_first_cycle_after_the_reply",
          f1 and f1[0][0] == "2026-08-12T12:45:00Z", f1 and f1[0][0])
    check("fixture1.fires_via_path_a_reply_on_the_users_thread",
          f1 and f1[0][1]["fire_reason"] == "explicit"
          and f1[0][1]["explicit_kinds"] == ["thread_reply"], f1 and f1[0][1])
    check("failure_mode_3.one_fire_per_burst_on_real_data",
          len(f1) == 1 and held(f1_state, KEY).get("fired") is True)
    check("failure_mode_3.late_mention_inside_the_burst_is_suppressed",
          held(f1_state, KEY).get("last_author_activity_at") == "2026-08-12T14:41:25Z"
          and len(f1) == 1)
    check("fixture1.the_suppressed_mention_is_at_least_visible_in_state",
          held(f1_state, KEY).get("suppressed_explicit_kinds") == ["mention"],
          held(f1_state, KEY))
    check("fixture1.the_push_adjacent_re_request_is_carried_as_a_noted_signal",
          held(f1_state, KEY).get("noted_kinds") == ["review_requested"],
          held(f1_state, KEY))

    # One extra tick at 14:42 so the author's last comment (14:41:25) and the CI
    # bot's (14:43:11) land in SEPARATE classification windows. On a bare 900s grid
    # they share the 14:45 window, the anchor is non-null either way, and the
    # fixture would pass whether or not bot activity can move the timer.
    f2_ticks = sorted(set(ticks_every(*day) + ["2026-08-12T14:42:00Z"]))
    f2, f2_state = replay(F2_EVENTS, f2_ticks)
    check("fixture2.exactly_one_fire", len(f2) == 1, [(t, f["fire_reason"]) for t, f in f2])
    check("fixture2.fires_via_path_b_settled", f2 and f2[0][1]["fire_reason"] == "settled")
    check("fixture2.silent_until_the_quiet_period_expires",
          f2 and f2[0][0] == "2026-08-12T16:45:00Z", f2 and f2[0][0])
    check("fixture2.folded_every_author_event_into_one_burst",
          f2 and f2[0][1]["author_events"] == 18, f2 and f2[0][1].get("author_events"))
    # `burst_seconds` is COMPUTED in _fire (last author activity minus opened_at) and
    # it renders to the user, but every other check on it hand-builds the fire dict and
    # calls compose() directly, so zeroing the computation kept the whole suite green.
    # Pin it off a real fire, from the fixture's own first and last author events.
    burst_span = int((_p("2026-08-12T14:41:25Z") - _p("2026-08-12T12:39:34Z")).total_seconds())
    check("fixture2.the_settled_fire_computes_the_burst_span",
          f2 and f2[0][1]["burst_seconds"] == burst_span
          and held(f2_state, KEY).get("opened_at") == "2026-08-12T12:39:34Z",
          (f2 and f2[0][1].get("burst_seconds"), burst_span, held(f2_state, KEY)))
    check("fixture2.the_computed_span_reaches_the_rendered_line",
          "18 author events over 2h01m"
          in (cycle.compose({"prs_reviewing": [f2[0][1]]}, {}, 7, False) or ""),
          f2 and cycle.compose({"prs_reviewing": [f2[0][1]]}, {}, 7, False))
    check("failure_mode_1.bot_comment_did_not_push_the_timer_to_1643",
          held(f2_state, KEY).get("last_author_activity_at") == "2026-08-12T14:41:25Z",
          held(f2_state, KEY))
    # Poll phase alone cannot distinguish the bug from the fix (both can land near
    # 16:43), so pin the boundary: 14:41:25 + 7200 exactly.
    pre_settle = sorted(set(ticks_every("2026-08-12T12:00:00Z", "2026-08-12T16:30:00Z")
                            + ["2026-08-12T14:42:00Z"]))
    early, _ = replay(F2_EVENTS, pre_settle + ["2026-08-12T16:41:24Z"])
    check("failure_mode_1.no_fire_one_second_before_the_authors_settle", early == [],
          [(t, f["fire_reason"]) for t, f in early])
    boundary, _ = replay(F2_EVENTS, pre_settle + ["2026-08-12T16:41:25Z"])
    check("failure_mode_1.fires_exactly_at_the_authors_settle_not_the_bots",
          len(boundary) == 1 and boundary[0][0] == "2026-08-12T16:41:25Z", boundary)

    _, f2_mid = replay(F2_EVENTS, ticks_every("2026-08-12T12:00:00Z", "2026-08-12T17:00:00Z"))
    f3, f3_state = replay(F2_EVENTS + [BOT_LATE],
                          ticks_every("2026-08-12T17:15:00Z", "2026-08-12T20:00:00Z"),
                          prev=f2_mid)
    check("fixture3.bot_only_activity_after_a_settled_fire_is_silent", f3 == [], f3)
    check("fixture3.bot_only_activity_cannot_resurrect_the_hold",
          held(f3_state, KEY).get("fired") is True
          and held(f3_state, KEY).get("last_author_activity_at") == "2026-08-12T14:41:25Z")

    plan_cycle_checks()
    two_phase_checks()
    auto_review_carry_checks()
    main_guard_checks()

    f4, f4_state = replay(F2_EVENTS + [NEW_PUSH],
                          ticks_every("2026-08-12T18:15:00Z", "2026-08-12T20:15:00Z"),
                          prev=f2_mid)
    check("fixture4.new_author_activity_after_a_fire_starts_a_new_burst",
          held(f4_state, KEY).get("opened_at") == "2026-08-12T18:00:00Z")
    check("fixture4.the_new_burst_fires_once_on_its_own_settle",
          len(f4) == 1 and f4[0][0] == "2026-08-12T20:00:00Z"
          and f4[0][1]["fire_reason"] == "settled", f4)

    print()
    if FAILURES:
        print(f"CYCLE TIER FAILED: {len(FAILURES)}: {FAILURES}")
        return 1
    print("CYCLE TIER PASSED")
    return 0


def test_cycle_tier() -> None:
    """Pytest bridge: main() is the suite; pytest collects nothing from the
    script-style check() calls on its own (no test_* functions), and a bare
    `pytest -q` on this file would exit 5 "no tests ran" while looking green."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
