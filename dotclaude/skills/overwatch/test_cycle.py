#!/usr/bin/env python3
"""Fixture tier for cycle.py's pure state-machine functions.

Covers the reviewed-critical branches (interval calibration, per-source baseline
seeding, diff+known-update, compose) with canned inputs, no live tools. Run on any
change to cycle.py:  python3 ~/.claude/skills/overwatch/test_cycle.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone

import cycle

NOW = datetime(2026, 7, 13, 12, 0, 0, tzinfo=timezone.utc)
FAILURES: list[str] = []


def check(name: str, cond: bool, detail: object = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + ("" if cond else f": {detail}"))
    if not cond:
        FAILURES.append(name)


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
        "jira": {"status": "ok", "items": [{"key": "MX2-NNNNN"}]},
    }
    base = cycle.seed_baseline(sources, NOW, age_days=7)
    check("baseline.beads_full", set(base["beads_ready"]["known_items"]) == {"docr-a", "docr-b"})
    check("baseline.in_progress_aged_only", base["in_progress"]["known_items"] == ["docr-old"])
    check("baseline.pr_key", base["prs_authored"]["known_items"] == ["o/r#5"])
    check("baseline.errored_skipped", "review_requests" not in base)
    check("baseline.jira_key", base["jira"]["known_items"] == ["MX2-NNNNN"])

    # diff: new membership item surfaces; known one does not; known := current
    prev = {
        "beads_ready": {"known_items": ["docr-a"]},
        "in_progress": {"known_items": ["docr-old"]},
        "prs_authored": {"known_items": ["o/r#5"]},
        "review_requests": {"known_items": ["o/r#9"]},
        "jira": {"known_items": ["MX2-NNNNN"]},
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
        "jira": {"status": "ok", "items": [{"key": "MX2-NNNNN"}, {"key": "MX2-NNNNN", "summary": "s"}]},
    }
    deltas, new_ps = cycle.diff_and_update(cur, prev, NOW, age_days=7)
    check("diff.beads_new_only", [r["id"] for r in deltas["beads_ready"]] == ["docr-new"])
    check("diff.beads_known_replaced", set(new_ps["beads_ready"]["known_items"]) == {"docr-a", "docr-new"})
    check("diff.in_progress_newly_aged", [r["id"] for r in deltas["in_progress"]] == ["docr-newaged"])
    check("diff.in_progress_pruned",
          set(new_ps["in_progress"]["known_items"]) == {"docr-old", "docr-newaged"})
    check("diff.review_gone_no_alert", deltas["review_requests"] == [])
    check("diff.review_known_emptied", new_ps["review_requests"]["known_items"] == [])
    check("diff.jira_new", [r["key"] for r in deltas["jira"]] == ["MX2-NNNNN"])

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
    check("diff.rebaseline_known_set", set(ps3["jira"]["known_items"]) == {"MX2-NNNNN", "MX2-NNNNN"})

    # compose: quiet -> None; deltas -> lines; error -> warn line; catch-up prefix
    check("compose.quiet_none", cycle.compose({}, {"beads_ready": {"status": "ok"}}, 7, False) is None)
    out = cycle.compose(deltas, cur, 7, catch_up=True)
    check("compose.catchup_prefix", out.startswith("[overwatch catch-up"))
    check("compose.has_unblocked", "🔓 newly unblocked: docr-new" in out)
    check("compose.has_review_none", "👀" not in out)  # review delta empty this case
    errout = cycle.compose({}, {"review_requests": {"status": "error", "error_detail": "x"}}, 7, False)
    check("compose.source_failure_line", errout is not None and "⚠️ source review_requests failed" in errout)

    # watermark source (prs_reviewing): baseline stores per-key updatedAt marks
    t1 = "2026-07-10T00:00:00Z"
    t2 = "2026-07-12T00:00:00Z"
    rv_base = cycle.seed_baseline(
        {"prs_reviewing": {"status": "ok", "items": [
            {"repository": "o/r", "number": 7, "title": "R7", "url": "u7", "updated_at": t1}]}},
        NOW, age_days=7)
    check("watermark.baseline_marks", rv_base["prs_reviewing"]["known_items"] == {"o/r#7": t1})

    # advance alerts + updates mark; first appearance baselines silently;
    # departed key (closed/merged) is pruned from the marks
    rv_prev = {"prs_reviewing": {"known_items": {"o/r#7": t1, "o/r#8": t1}}}
    rv_cur = {"prs_reviewing": {"status": "ok", "items": [
        {"repository": "o/r", "number": 7, "title": "R7", "url": "u7", "updated_at": t2},
        {"repository": "o/r", "number": 9, "title": "R9", "url": "u9", "updated_at": t2}]}}
    rvd, rvps = cycle.diff_and_update(rv_cur, rv_prev, NOW, age_days=7)
    check("watermark.advance_alerts_only", [cycle._pr_key(r) for r in rvd["prs_reviewing"]] == ["o/r#7"])
    check("watermark.marks_updated_new_silent_departed_pruned",
          rvps["prs_reviewing"]["known_items"] == {"o/r#7": t2, "o/r#9": t2})

    # unchanged watermark: quiet
    rvd2, _ = cycle.diff_and_update(
        {"prs_reviewing": {"status": "ok", "items": [
            {"repository": "o/r", "number": 7, "updated_at": t1}]}},
        {"prs_reviewing": {"known_items": {"o/r#7": t1}}}, NOW, age_days=7)
    check("watermark.unchanged_quiet", rvd2["prs_reviewing"] == [])

    # errored source: no delta, marks carried forward unchanged
    rvd3, rvps3 = cycle.diff_and_update(
        {"prs_reviewing": {"status": "error", "error_detail": "gh 500"}},
        rv_prev, NOW, age_days=7)
    check("watermark.error_no_delta", "prs_reviewing" not in rvd3)
    check("watermark.error_carries_marks",
          rvps3["prs_reviewing"]["known_items"] == {"o/r#7": t1, "o/r#8": t1})
    check("watermark.error_marked", rvps3["prs_reviewing"]["status"] == "error")

    # never-succeeded source re-baselines silently with full marks
    rvd4, rvps4 = cycle.diff_and_update(rv_cur, {}, NOW, age_days=7)
    check("watermark.rebaseline_silent", rvd4["prs_reviewing"] == [])
    check("watermark.rebaseline_marks",
          rvps4["prs_reviewing"]["known_items"] == {"o/r#7": t2, "o/r#9": t2})

    # compose renders the named reviewed-PR activity line, not the digest
    rvout = cycle.compose(rvd, rv_cur, 7, catch_up=False)
    check("compose.reviewed_pr_line",
          rvout is not None and "🔁 activity on reviewed PR: o/r#7 R7 u7" in rvout)
    check("compose.reviewed_pr_not_other", rvout is not None and "other:" not in rvout)

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
