#!/usr/bin/env python3
"""Fixture tier for overwatch gather (docr-wtice).

Fast, no network, no side effects: feeds canned (returncode, stdout, stderr)
triples to classify() and asserts the status contract, above all the
empty-vs-error distinction that keeps a failed source from being read as quiet.

Run on every change to gather.py:
    python3 ~/.claude/skills/overwatch/test_gather.py

Exits 0 only if every assertion holds; non-zero (with the failing case named)
otherwise, so it is a real gate rather than documentation.
"""

from __future__ import annotations

import sys

import gather

# The fixtures are the exact stream shapes verified against live tools on
# 2026-07-09: a normal `gh` success (0 / json / empty stderr), a legitimately
# empty result (0 / "[]" / empty stderr), and a 401 (non-zero / "[]" on stdout /
# error on stderr). The 401 case is the whole point: stdout is a well-formed
# empty array, so only the exit code distinguishes it from a quiet success.
GH_401_STDERR = (
    'non-200 OK status code: 401 Unauthorized body: '
    '"{\\r\\n  \\"message\\": \\"Bad credentials\\"\\r\\n}"'
)

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name}: {detail}")


def main() -> int:
    # ok with items
    r = gather.classify(
        0,
        '[{"id": "docr-a", "title": "A", "priority": 1}, {"id": "docr-b"}]',
        "",
        gather._bead_rows,
    )
    check("ok_with_items.status", r["status"] == "ok", r)
    check("ok_with_items.ids", [x["id"] for x in r["items"]] == ["docr-a", "docr-b"], r)
    check("ok_with_items.title_captured", r["items"][0]["title"] == "A", r)
    check("ok_with_items.priority_captured", r["items"][0]["priority"] == "1", r)

    # ok with a legitimately empty result: quiet, NOT an error
    r = gather.classify(0, "[]", "", gather._bead_rows)
    check("empty_is_ok.status", r["status"] == "ok", r)
    check("empty_is_ok.items_empty", r.get("items") == [], r)

    # THE decoy: exit 1 with an empty "[]" on stdout must be an error, never empty items
    r = gather.classify(1, "[]", GH_401_STDERR, gather._pr_rows)
    check("gh401_is_error.status", r["status"] == "error", r)
    check("gh401_is_error.no_items_key", "items" not in r, r)
    check("gh401_is_error.detail_has_401", "401" in r.get("error_detail", ""), r)

    # non-zero exit with empty streams still errors, with a synthesized detail
    r = gather.classify(2, "", "", gather._bead_rows)
    check("nonzero_empty.status", r["status"] == "error", r)
    check("nonzero_empty.no_items_key", "items" not in r, r)

    # exit 0 but stdout will not parse: an anomaly, an error, never a silent empty
    r = gather.classify(0, "not json at all", "", gather._bead_rows)
    check("malformed_zero_exit.status", r["status"] == "error", r)
    check("malformed_zero_exit.no_items_key", "items" not in r, r)

    # parse coverage: bd rows keep updated_at, the field aged-detection needs
    ip = gather._bead_rows(
        '[{"id": "docr-x", "title": "T", "priority": 2, "updated_at": "2026-06-01T00:00:00Z"}]'
    )
    check("bead_rows.updated_at", ip[0]["updated_at"] == "2026-06-01T00:00:00Z", ip)

    # memory-bead filter: [memory]-titled and memory-labelled rows are dropped,
    # matched by leading title tag OR the memory label; real work is kept
    mf = gather._bead_rows(
        '[{"id": "docr-work", "title": "Real work"},'
        ' {"id": "docr-mem1", "title": "[memory] Jesup standup 2026-07-13"},'
        ' {"id": "docr-mem2", "title": "checkpoint", "labels": ["memory"]}]'
    )
    check("memory_filter.keeps_only_work", [r["id"] for r in mf] == ["docr-work"], mf)

    # parse coverage: review-request rows flatten the repository object
    rr = gather._review_request_rows(
        '[{"number": 5, "title": "R", "url": "u", "repository": {"nameWithOwner": "o/r"}}]'
    )
    check("review_request_parse.repo", rr[0]["repository"] == "o/r", rr)

    # contract invariant across every record shape: ok XOR error, keys disjoint
    for label, rec in [
        ("ok", gather.classify(0, "[]", "", gather._bead_rows)),
        ("error", gather.classify(1, "[]", "boom", gather._bead_rows)),
    ]:
        has_items = "items" in rec
        has_detail = "error_detail" in rec
        check(f"contract_shape.{label}", has_items != has_detail, rec)

    print()
    if FAILURES:
        print(f"FIXTURE TIER FAILED: {len(FAILURES)} assertion(s)")
        return 1
    print("FIXTURE TIER PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
