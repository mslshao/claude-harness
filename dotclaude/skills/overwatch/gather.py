#!/usr/bin/env python3
"""Cross-source gather for the overwatch skill.

Runs the bash-pollable work-queue sources (beads via `bd`, PRs via `gh`) and
emits one status-contract record per source to stdout as JSON:

    {"<source>": {"status": "ok", "items": [...]},
     "<source>": {"status": "error", "error_detail": "..."}, ...}

Jira is deliberately NOT gathered here: it is reachable only through the
Atlassian MCP tool, which a shell subprocess cannot call. The overwatch loop
(SKILL.md) gathers Jira agent-side and applies the SAME classify() contract to
that MCP result. Keeping the shell-pollable sources in one testable module is
what lets the fixture tier assert the contract without a live network.

The load-bearing invariant, verified against live `gh` on 2026-07-09:
a source's EXIT CODE is authoritative for ok-vs-error, never its stdout. `gh`
on a 401 writes an empty `[]` to stdout AND exits non-zero; a classifier that
keyed on stdout content would read that auth failure as "ok, quiet" and drop
it silently. So classify() reads status from the return code first and only
trusts stdout items when the command exited 0. An error record carries no
`items` key at all, so an errored source can never be mistaken for an empty one.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from typing import Any

# A high explicit cap: both `bd ready` and `bd list` default to a small row cap,
# but the newly-unblocked and aged diffs need the FULL set or an item outside the
# default window looks "new" the moment that window shifts.
BD_ROW_LIMIT = "2000"

ERROR_DETAIL_CAP = 500


def classify(
    returncode: int,
    stdout: str,
    stderr: str,
    parse: Callable[[str], list[Any]],
) -> dict[str, Any]:
    """Turn a finished subprocess into one status-contract record.

    Exit code is authoritative. A non-zero exit is an error even when stdout
    holds a well-formed empty `[]` (the gh-401 decoy). A zero exit whose stdout
    will not parse is also an error (truncated or malformed output), never a
    silent empty. Only a zero exit with parseable stdout yields items.
    """
    if returncode != 0:
        detail = stderr.strip() or stdout.strip() or f"exited {returncode} with no output"
        return {"status": "error", "error_detail": detail[:ERROR_DETAIL_CAP]}
    try:
        items = parse(stdout)
    except Exception as exc:  # noqa: BLE001 - any parse failure on a 0-exit is an error, not empty
        return {
            "status": "error",
            "error_detail": f"exit 0 but output did not parse: {exc}"[:ERROR_DETAIL_CAP],
        }
    return {"status": "ok", "items": items}


def run_source(argv: list[str], parse: Callable[[str], list[Any]]) -> dict[str, Any]:
    """Run one source command and classify it.

    Captures stdout and stderr as separate streams and reads the process's own
    return code. It never pipes the command into `head`/`jq`, because a pipe
    makes `$?` report the last pipeline stage and masks a source's real failure
    (observed while verifying this contract on 2026-07-09).
    """
    try:
        proc = subprocess.run(  # noqa: S603 - argv is a fixed literal per source, no shell
            argv,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,  # returncode is the status signal; raising would defeat classify()
        )
    except FileNotFoundError:
        return {"status": "error", "error_detail": f"command not found: {argv[0]}"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error_detail": f"timed out: {' '.join(argv)}"}
    return classify(proc.returncode, proc.stdout, proc.stderr, parse)


def _is_memory_bead(row: dict[str, Any]) -> bool:
    """A `[memory]` capture bead (standup/checkpoint/1:1 record), not real work.

    These were 25% of the ready pool (72/289, observed 2026-07-13) and are pure
    noise for a "what should I work on next" watcher, so both bd sources drop
    them. Matched by the leading title tag OR the `memory` label, since the two
    conventions do not always coincide.
    """
    title = (row.get("title") or "").lstrip().lower()
    labels = row.get("labels") or []
    return title.startswith("[memory]") or "memory" in labels


def _bead_rows(stdout: str) -> list[dict[str, str]]:
    """Rows for both bd sources: the id plus the fields the alerts render.

    beads_ready needs title and priority to render the newly-unblocked alert;
    in_progress needs updated_at for aged-detection ("aged" means an in-progress
    item gone untouched, the stall signal a work-next watcher cares about, which
    is why this reads updated_at rather than started_at). One parser serves both.
    `[memory]` capture beads are filtered out (see _is_memory_bead).
    """
    data = json.loads(stdout)
    rows = data if isinstance(data, list) else data.get("issues", data.get("data", []))
    return [
        {
            "id": row["id"],
            "title": row.get("title", ""),
            "priority": str(row.get("priority", "")),
            "updated_at": row.get("updated_at", ""),
        }
        for row in rows
        if not _is_memory_bead(row)
    ]


def _pr_rows(stdout: str) -> list[dict[str, Any]]:
    data = json.loads(stdout)
    return [
        {
            "number": row["number"],
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "state": row.get("state", ""),
            "isDraft": row.get("isDraft", False),
            "repository": (row.get("repository") or {}).get("nameWithOwner", ""),
        }
        for row in data
    ]


def _review_request_rows(stdout: str) -> list[dict[str, Any]]:
    data = json.loads(stdout)
    return [
        {
            "number": row["number"],
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "repository": (row.get("repository") or {}).get("nameWithOwner", ""),
        }
        for row in data
    ]


def _reviewing_rows(stdout: str) -> list[dict[str, Any]]:
    """Rows for prs_reviewing: identity fields plus updated_at (from gh's
    camelCase updatedAt), the watermark cycle.py diffs on to detect author
    activity (a new push, a reply) on a PR the user already reviewed."""
    data = json.loads(stdout)
    return [
        {
            "number": row["number"],
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "repository": (row.get("repository") or {}).get("nameWithOwner", ""),
            "updated_at": row.get("updatedAt", ""),
        }
        for row in data
    ]


# name -> (argv, parse). Bash-pollable sources only; Jira is handled agent-side.
SOURCES: dict[str, tuple[list[str], Callable[[str], list[Any]]]] = {
    "beads_ready": (
        ["bd", "ready", "-n", BD_ROW_LIMIT, "--json"],
        _bead_rows,
    ),
    # Explicit -n: `bd list` has its own default row cap; without this the aged
    # set silently truncates once in-progress work exceeds the default.
    "in_progress": (
        ["bd", "list", "--status=in_progress", "-n", BD_ROW_LIMIT, "--json"],
        _bead_rows,
    ),
    # `gh search prs` (cross-repo, no cwd git-repo dependency), NOT `gh pr list`
    # (which infers the repo from cwd and errors when the loop re-enters outside
    # a checkout, verified 2026-07-09). Open only: a merged PR is not work-to-do.
    "prs_authored": (
        [
            "gh", "search", "prs", "--author=@me", "--state=open",
            "--json", "number,title,url,state,isDraft,repository",
        ],
        _pr_rows,
    ),
    "review_requests": (
        [
            "gh", "search", "prs", "--review-requested=@me", "--state=open",
            "--json", "number,title,url,repository",
        ],
        _review_request_rows,
    ),
    # Same `gh search prs` shape as prs_authored (cross-repo, no cwd git-repo
    # dependency, so the loop can re-enter outside a checkout). Open only, and
    # approved-but-still-open PRs are deliberately INCLUDED: a push after the
    # user's approval is exactly the author activity worth surfacing. updatedAt
    # rides along as the watermark cycle.py diffs on; membership alone cannot
    # see new pushes or replies on an already-known PR.
    "prs_reviewing": (
        [
            "gh", "search", "prs", "--reviewed-by=@me", "--state=open",
            "--json", "number,title,url,repository,updatedAt",
        ],
        _reviewing_rows,
    ),
}


def gather() -> dict[str, dict[str, Any]]:
    return {name: run_source(argv, parse) for name, (argv, parse) in SOURCES.items()}


if __name__ == "__main__":
    print(json.dumps(gather(), indent=2))
