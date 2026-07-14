#!/usr/bin/env python3
"""Append a chronological log entry for a bead to memory/log.md.

Called from /bead-forge Phase 5 after bd create + bd label add for any bead
with a memory, decision, discovery, or review category label. Best-effort:
exits 0 even on failure so bead creation is never blocked by log issues.

Entry format (one line per bead):

    ## [YYYY-MM-DD] <category> | <domain-csv> | bead <id> | <title>

  - Date: bead's created_at (YYYY-MM-DD).
  - Category: matching category label (memory/decision/discovery/review).
  - Domain CSV: comma-joined labels minus the five category labels; falls
    back to 'uncategorized' if no domain labels remain.

Usage:
  python3 ~/.claude/skills/bead-forge/log-append.py <bead-id>

The log file lives at:
  ~/.claude/projects/-workspaces-main/memory/log.md

This is the temporal index over memory; topic files (Phase 2b) are the
per-domain index. Both write paths fire on the same trigger
(memory/decision/discovery label) but produce different views.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

LOG_FILE = (
  Path.home()
  / ".claude"
  / "projects"
  / "-workspaces-main"
  / "memory"
  / "log.md"
)

CATEGORY_LABELS = {"memory", "decision", "discovery", "review", "task"}
LOGGED_CATEGORIES = {"memory", "decision", "discovery", "review"}


def fetch_bead(bead_id: str) -> dict | None:
  try:
    result = subprocess.run(
      ["bd", "show", bead_id, "--json"],
      capture_output=True, text=True, timeout=10, check=False,
    )
  except (subprocess.TimeoutExpired, FileNotFoundError):
    return None
  if result.returncode != 0:
    return None
  try:
    payload = json.loads(result.stdout)
  except json.JSONDecodeError:
    return None
  if isinstance(payload, list):
    return payload[0] if payload else None
  return payload


def category_for(labels: list[str]) -> str | None:
  for cat in ("memory", "decision", "discovery", "review"):
    if cat in labels:
      return cat
  return None


def domain_csv(labels: list[str]) -> str:
  domain = [l for l in labels if l not in CATEGORY_LABELS]
  return ",".join(sorted(domain)) if domain else "uncategorized"


def format_entry(bead: dict) -> str | None:
  labels = bead.get("labels") or []
  category = category_for(labels)
  if category is None:
    print(
      f"log-append: bead {bead.get('id', '?')} has no category label "
      f"(memory/decision/discovery/review); skipping log.md append. "
      f"Add one first, e.g.: bd label add {bead.get('id', '<id>')} memory",
      file=sys.stderr,
    )
    return None
  date = (bead.get("created_at") or "")[:10]
  if not date:
    print(
      f"log-append: bead {bead.get('id', '?')} has no created_at date; "
      f"skipping log.md append.",
      file=sys.stderr,
    )
    return None
  return (
    f"## [{date}] {category} | {domain_csv(labels)} "
    f"| bead {bead['id']} | {bead['title']}\n"
  )


def append_entry(entry: str) -> bool:
  try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as fh:
      fh.write(entry)
    return True
  except OSError:
    return False


def main() -> int:
  if len(sys.argv) != 2:
    print("usage: log-append.py <bead-id>", file=sys.stderr)
    return 0
  bead = fetch_bead(sys.argv[1])
  if bead is None:
    print(
      f"log-append: could not fetch bead {sys.argv[1]} "
      f"(not found or bd error); skipping log.md append.",
      file=sys.stderr,
    )
    return 0
  entry = format_entry(bead)
  if entry is None:
    return 0
  append_entry(entry)
  return 0


if __name__ == "__main__":
  sys.exit(main())
