#!/usr/bin/env python3
"""Filter Checkov findings to those whose file_line_range overlaps with +hunks in a diff.

Used by /pr-intel checkov.md spec to suppress pre-existing-tech-debt false positives.

Usage:
    python3 checkov-filter.py \\
        --checkov-json <path-to-checkov-json> \\
        --diff <path-to-git-diff> \\
        --file <tf-path-relative-to-repo>

Outputs filtered failed_checks as JSON list to stdout. Exit 0 always.
"""

import argparse
import json
import re
import sys
from pathlib import Path


HUNK_HEADER = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def parse_plus_ranges(diff_text: str) -> list[tuple[int, int]]:
    """Extract post-image line ranges from `@@ -A,B +C,D @@` hunk headers.

    Returns inclusive [start, end] pairs. Length 0 hunks (pure deletions in this
    region) produce no range entry.
    """
    ranges = []
    for line in diff_text.splitlines():
        m = HUNK_HEADER.match(line)
        if not m:
            continue
        start = int(m.group(1))
        length = int(m.group(2)) if m.group(2) else 1
        if length > 0:
            ranges.append((start, start + length - 1))
    return ranges


def overlaps(finding_range, plus_ranges: list[tuple[int, int]]) -> bool:
    """Return True if Checkov's file_line_range overlaps any +hunk range."""
    if not finding_range or len(finding_range) < 2:
        return False
    f_start, f_end = finding_range[0], finding_range[1]
    return any(f_start <= r_end and r_start <= f_end for r_start, r_end in plus_ranges)


def extract_file_diff(full_diff: str, target_path: str) -> str:
    """Pull out the section of `full_diff` for `target_path` only.

    A unified diff is a sequence of `diff --git a/X b/Y` blocks. We want only
    the block whose b-side matches `target_path` so hunks from other files
    don't leak into our +range computation.
    """
    out_lines = []
    in_target = False
    for line in full_diff.splitlines():
        if line.startswith("diff --git "):
            in_target = f" b/{target_path}" in line or line.endswith(f"b/{target_path}")
        if in_target:
            out_lines.append(line)
    return "\n".join(out_lines)


def filter_findings(checkov_data, diff_text: str, target_path: str) -> list[dict]:
    """Return failed_checks for `target_path` whose ranges overlap +diff hunks."""
    items = checkov_data if isinstance(checkov_data, list) else [checkov_data]
    tf = next((d for d in items if d.get("check_type") == "terraform"), None)
    if not tf:
        return []
    all_failed = tf.get("results", {}).get("failed_checks", [])
    file_diff = extract_file_diff(diff_text, target_path)
    plus_ranges = parse_plus_ranges(file_diff)
    if not plus_ranges:
        return []
    survivors = []
    for c in all_failed:
        rng = c.get("file_line_range")
        if overlaps(rng, plus_ranges):
            survivors.append(c)
    return survivors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--checkov-json", required=True, type=Path,
                    help="Path to Checkov --output json file")
    ap.add_argument("--diff", required=True, type=Path,
                    help="Path to git diff output covering the PR")
    ap.add_argument("--file", required=True,
                    help="Repo-relative path to the .tf file being scanned")
    args = ap.parse_args()

    checkov_data = json.loads(args.checkov_json.read_text())
    diff_text = args.diff.read_text()
    survivors = filter_findings(checkov_data, diff_text, args.file)
    print(json.dumps(survivors, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
