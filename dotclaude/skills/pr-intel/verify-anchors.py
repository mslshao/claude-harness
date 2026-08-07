#!/usr/bin/env python3
"""Verify drafted /pr-intel inline anchors sit inside the PR's net 3-dot diff hunks.

GitHub's review API 422s ("Line could not be resolved") on any anchor outside a
post-image hunk range, so an out-of-hunk anchor is unpostable. /post-review Step 2
catches it, but only after the briefing is rendered and previewed. Run this at
synthesis time instead.

Usage:
    python3 verify-anchors.py --base main --head <sha> audit_scan.py:172 models.py:95

Prints one line per anchor: OK (with the anchored line's content), OK-WEAK when that
content is blank or punctuation-only (postable, but a closing paren is the wrong
anchor), or NOT_IN_HUNK with the valid ranges and the nearest postable line.
Exit 1 if any anchor fails, 0 otherwise.
"""

import argparse
import re
import subprocess
import sys

HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def plus_ranges(base: str, head: str, path: str) -> list[tuple[int, int]]:
    """Post-image [start, end] ranges from the three-dot diff for one file."""
    diff = subprocess.run(
        ["git", "diff", f"origin/{base}...{head}", "--", path],
        capture_output=True, text=True, check=False,
    ).stdout
    ranges = []
    for line in diff.splitlines():
        match = HUNK_HEADER.match(line)
        if not match:
            continue
        start = int(match.group(1))
        length = int(match.group(2)) if match.group(2) else 1
        if length > 0:
            ranges.append((start, start + length - 1))
    return ranges


STRUCTURAL_ONLY = re.compile(r"^[\s()\[\]{},:;]*$")


def line_content(head: str, path: str, line: int) -> str:
    """The file's line at the PR head, trimmed; empty when unreadable."""
    blob = subprocess.run(
        ["git", "show", f"{head}:{path}"],
        capture_output=True, text=True, check=False,
    )
    if blob.returncode != 0:
        return ""
    lines = blob.stdout.splitlines()
    return lines[line - 1].strip()[:80] if 0 < line <= len(lines) else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="PR baseRefName, not a hardcoded main")
    parser.add_argument("--head", required=True, help="headRefOid")
    parser.add_argument("anchors", nargs="+", help="path:line pairs")
    args = parser.parse_args()

    failed = False
    for anchor in args.anchors:
        path, _, raw_line = anchor.rpartition(":")
        line = int(raw_line)
        ranges = plus_ranges(args.base, args.head, path)
        if any(lo <= line <= hi for lo, hi in ranges):
            content = line_content(args.head, path, line)
            weak = not content or STRUCTURAL_ONLY.match(content)
            label = "OK-WEAK    " if weak else "OK         "
            print(f"{label} {path}:{line} | {content or '<blank>'}")
            continue
        failed = True
        candidates = [n for lo, hi in ranges for n in (lo, hi)]
        nearest = min(candidates, key=lambda n: abs(n - line)) if candidates else None
        pretty = ", ".join(f"[{lo}-{hi}]" for lo, hi in ranges) or "none"
        print(f"NOT_IN_HUNK {path}:{line} | valid: {pretty} | nearest: {nearest}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
