#!/usr/bin/env python3
"""One-call cycle planner for the overwatch loop.

Collapses the per-cycle boilerplate (load state, gather, diff, compose, build the
next blob, decide arming) into a single invocation so the agent's wakeup handler is
just: gather Jira via MCP -> run this -> act on the returned plan. It ports the
SKILL.md state machine verbatim; SKILL.md remains the spec and the manual fallback.

    python3 cycle.py <tracking-bead-id> --jira-file <path> [--now <iso>]
                     [--resume] [--stop] [--interval N] [--age-days N]

`--jira-file` holds the agent's classified Jira record as JSON, one of:
    {"status": "ok", "items": [{"key": "MX2-NNNNN"}, ...]}
    {"status": "error", "error_detail": "..."}
(Jira is MCP-only, so the agent gathers it and passes it in; everything else here.)

Output (stdout, JSON) is a PLAN the agent executes; this script performs NO writes
and never arms a wakeup (ScheduleWakeup is agent-only). The agent, in order:
  1. if plan.chat: print it to chat AND `bd comment <id> "<chat>"`
  2. if plan.persist: `bd update <id> --notes '<plan.blob JSON>'`
  3. if plan.arming_due: ScheduleWakeup(delaySeconds=plan.interval, prompt="/overwatch")
Persisting AFTER chat preserves the duplicate-over-drop ordering from SKILL.md.

plan.action is one of:
  "skip"     double-fire guard tripped; do nothing, do not persist, do not arm.
  "terminal" loop is stopped (active:false) and this was not --resume; do nothing.
  "run"      a normal/baseline/catch-up cycle; act on chat/persist/arming_due.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

sys.path.insert(0, "/home/vscode/.claude/skills/overwatch")
import gather  # noqa: E402

DOUBLE_FIRE_WINDOW_S = 60
CATCHUP_GRACE_S = 1800
COLD_START_JIRA_LOOKBACK_DAYS = 14


def _now(args: argparse.Namespace) -> datetime:
    if args.now:
        return datetime.fromisoformat(args.now.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_state(bead_id: str) -> dict[str, Any] | None | str:
    """Return the parsed state dict, None (empty/first-cycle), or "corrupt"."""
    proc = subprocess.run(
        ["bd", "show", bead_id, "--json"], capture_output=True, text=True, timeout=60, check=False
    )
    if proc.returncode != 0:
        return None
    data = json.loads(proc.stdout)
    row = data[0] if isinstance(data, list) else data
    notes = (row.get("notes") or "").strip()
    if not notes:
        return None
    try:
        return json.loads(notes)
    except (json.JSONDecodeError, ValueError):
        return "corrupt"


def interval_for(cqsc: int, override: int | None) -> int:
    """Calibration table; a --interval override replaces the 900s floor."""
    floor = override if override else 900
    if cqsc < 3:
        return floor
    if cqsc <= 5:
        return max(floor, 1800)
    return max(floor, 3600)


def _pr_key(item: dict[str, Any]) -> str:
    return f"{item.get('repository', '')}#{item['number']}"


def _aged_ids(rows: list[dict[str, Any]], now: datetime, age_days: int) -> list[str]:
    cutoff = now - timedelta(days=age_days)
    out = []
    for r in rows:
        ts = r.get("updated_at")
        if ts and _parse_iso(ts) < cutoff:
            out.append(r["id"])
    return out


def seed_baseline(sources: dict[str, Any], now: datetime, age_days: int) -> dict[str, Any]:
    """Preflight baseline: membership sources seed full; in_progress seeds aged-only;
    errored sources are left unset so they re-baseline on first success."""
    per_source: dict[str, Any] = {}
    iso = now.isoformat()
    for name, rec in sources.items():
        if rec.get("status") != "ok":
            continue
        if name == "in_progress":
            known = _aged_ids(rec["items"], now, age_days)
        elif name in ("prs_authored", "review_requests"):
            known = [_pr_key(i) for i in rec["items"]]
        elif name == "jira":
            known = [i["key"] for i in rec["items"]]
        else:  # beads_ready
            known = [i["id"] for i in rec["items"]]
        per_source[name] = {"status": "ok", "known_items": known,
                            "last_success_at": iso, "error_detail": None}
    return per_source


def diff_and_update(
    sources: dict[str, Any], prev_per_source: dict[str, Any], now: datetime, age_days: int
) -> tuple[dict[str, list], dict[str, Any]]:
    """Return (deltas_by_source, new_per_source). Ports SKILL.md Step 3 exactly."""
    deltas: dict[str, list] = {}
    new_ps: dict[str, Any] = {}
    iso = now.isoformat()
    for name, rec in sources.items():
        prev = prev_per_source.get(name, {})
        prev_known = set(prev.get("known_items", []))
        never_succeeded = "known_items" not in prev
        if rec.get("status") != "ok":
            # carry forward unchanged, mark error, no delta
            new_ps[name] = {
                "status": "error",
                "known_items": prev.get("known_items", []),
                "last_success_at": prev.get("last_success_at"),
                "error_detail": rec.get("error_detail", "unknown"),
            }
            continue
        if name == "in_progress":
            aged = _aged_ids(rec["items"], now, age_days)
            current_ids = [r["id"] for r in rec["items"]]
            if never_succeeded:
                new_known = list(aged)
                delta = []  # re-baseline silently
            else:
                newly_aged = [i for i in aged if i not in prev_known]
                new_known = [i for i in (prev_known | set(aged)) if i in current_ids]
                delta = newly_aged
            rows_by_id = {r["id"]: r for r in rec["items"]}
            deltas[name] = [rows_by_id[i] for i in delta if i in rows_by_id]
        else:
            if name in ("prs_authored", "review_requests"):
                keys = [_pr_key(i) for i in rec["items"]]
            elif name == "jira":
                keys = [i["key"] for i in rec["items"]]
            else:  # beads_ready
                keys = [i["id"] for i in rec["items"]]
            key_to_item = dict(zip(keys, rec["items"]))
            if never_succeeded:
                new_known = list(keys)
                delta = []  # re-baseline silently
            else:
                delta = [k for k in keys if k not in prev_known]
                new_known = list(keys)
            deltas[name] = [key_to_item[k] for k in delta]
        new_ps[name] = {"status": "ok", "known_items": new_known,
                        "last_success_at": iso, "error_detail": None}
    return deltas, new_ps


def compose(deltas: dict[str, list], sources: dict[str, Any], age_days: int, catch_up: bool) -> str | None:
    """SKILL.md Step 4 output. None if fully quiet AND all sources ok."""
    lines: list[str] = []
    for r in deltas.get("beads_ready", []):
        lines.append(f"🔓 newly unblocked: {r['id']} [P{r.get('priority', '')}] {r.get('title', '')}")
    for r in deltas.get("review_requests", []):
        lines.append(f"👀 review requested: {_pr_key(r)} {r.get('title', '')} {r.get('url', '')}")
    for r in deltas.get("in_progress", []):
        lines.append(f"⏳ stalling (in_progress, no update in >{age_days}d): {r['id']} {r.get('title', '')}")
    for r in deltas.get("prs_authored", []):
        lines.append(f"other: opened PR {_pr_key(r)} {r.get('title', '')}")
    for r in deltas.get("jira", []):
        lines.append(f"other: jira {r['key']} {r.get('summary', '')}".rstrip())
    for name, rec in sources.items():
        if rec.get("status") == "error":
            lines.append(f"⚠️ source {name} failed: {rec.get('error_detail', '')}")
    if not lines:
        return None
    prefix = "[overwatch catch-up, spans a gap]\n" if catch_up else ""
    return prefix + "\n".join(lines)


def plan_cycle(args: argparse.Namespace) -> dict[str, Any]:
    now = _now(args)
    iso = now.isoformat()
    state = load_state(args.bead_id)

    # Termination gate (SKILL.md preflight step 3)
    if isinstance(state, dict) and state.get("active") is False and not args.resume:
        return {"action": "terminal", "note": "loop stopped; bare invocation is a no-op",
                "chat": None, "blob": None, "persist": False, "arming_due": False, "interval": 0}

    if args.stop:
        blob = state if isinstance(state, dict) else {}
        blob = dict(blob)
        blob["active"] = False
        blob["terminal_reason"] = "operator-stopped"
        blob["last_cycle_at"] = blob.get("last_cycle_at", iso)
        return {"action": "stop", "note": "operator stop",
                "chat": None,
                "event_comment": f"[OVERWATCH_TERMINATED] ts={iso} terminal_reason=operator-stopped",
                "blob": blob, "persist": True, "arming_due": False, "interval": 0}

    age_days = args.age_days or (state.get("age_days") if isinstance(state, dict) else None) or 7
    override = args.interval or (state.get("interval_seconds") if isinstance(state, dict) else None)

    # Gather bash-pollable sources, then merge the agent-supplied Jira record.
    sources = gather.gather()
    jira_record = json.load(open(args.jira_file)) if args.jira_file else {"status": "ok", "items": []}
    sources["jira"] = jira_record

    fresh = state is None or state == "corrupt"

    if fresh:
        # Baseline: seed known, surface nothing, arm.
        per_source = seed_baseline(sources, now, age_days)
        interval = interval_for(0, args.interval)
        blob = {
            "schema_version": 1, "active": True, "terminal_reason": None,
            "last_cycle_at": iso, "next_wakeup_at": (now + timedelta(seconds=interval)).isoformat(),
            "consecutive_quiet_successful_cycles": 0, "interval_seconds": args.interval or 900,
            "age_days": age_days, "per_source": per_source,
        }
        return {"action": "run", "note": "baseline (silent)", "chat": None, "blob": blob,
                "persist": True, "arming_due": True, "interval": interval}

    # Well-formed state. Double-fire guard (only when NOT resuming).
    loaded_nwa = _parse_iso(state["next_wakeup_at"]) if state.get("next_wakeup_at") else None
    last_cycle = _parse_iso(state["last_cycle_at"])
    gap = (now - last_cycle).total_seconds()
    if not args.resume and gap < DOUBLE_FIRE_WINDOW_S and loaded_nwa and loaded_nwa > now:
        return {"action": "skip", "note": f"double-fire guard (gap {int(gap)}s, wakeup still armed)",
                "chat": None, "blob": None, "persist": False, "arming_due": False, "interval": 0}

    prev_interval = state.get("interval_seconds", 900)
    catch_up = (not fresh) and gap > prev_interval + CATCHUP_GRACE_S

    deltas, new_ps = diff_and_update(sources, state["per_source"], now, age_days)
    chat = compose(deltas, sources, age_days, catch_up)

    all_ok = all(r.get("status") == "ok" for r in sources.values())
    quiet = chat is None and all_ok
    cqsc = state.get("consecutive_quiet_successful_cycles", 0)
    cqsc = cqsc + 1 if quiet else 0
    interval = interval_for(cqsc, args.interval)

    arming_due = (loaded_nwa is None) or (now >= loaded_nwa)
    next_wakeup = (now + timedelta(seconds=interval)).isoformat() if arming_due else state.get("next_wakeup_at")

    blob = {
        "schema_version": 1, "active": True, "terminal_reason": None,
        "last_cycle_at": iso, "next_wakeup_at": next_wakeup,
        "consecutive_quiet_successful_cycles": cqsc,
        "interval_seconds": interval if arming_due else prev_interval,
        "age_days": age_days, "per_source": new_ps,
    }
    return {"action": "run", "note": ("catch-up" if catch_up else "normal") + (" quiet" if quiet else " delta"),
            "chat": chat, "event_comment": chat, "blob": blob,
            "persist": True, "arming_due": arming_due, "interval": interval}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bead_id")
    ap.add_argument("--jira-file")
    ap.add_argument("--now")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--interval", type=int)
    ap.add_argument("--age-days", type=int)
    args = ap.parse_args(argv)
    print(json.dumps(plan_cycle(args), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
