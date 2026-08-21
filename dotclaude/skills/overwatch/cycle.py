#!/usr/bin/env python3
"""One-call cycle planner for the overwatch loop.

Collapses the per-cycle boilerplate (load state, gather, diff, compose, build the
next blob, decide arming) into a single invocation so the agent's wakeup handler is
just: gather Jira via MCP -> run this -> act on the returned plan. It ports the
SKILL.md state machine verbatim; SKILL.md remains the spec and the manual fallback.

    python3 cycle.py <tracking-bead-id> --jira-file <path> [--now <iso>]
                     [--resume] [--stop] [--interval N] [--age-days N]
                     [--quiet-period N]

`--jira-file` holds the agent's classified Jira record as JSON, one of:
    {"status": "ok", "items": [{"key": "MX2-NNNNN"}, ...]}
    {"status": "error", "error_detail": "..."}
(Jira is MCP-only, so the agent gathers it and passes it in; everything else here.)

TWO-PHASE prs_reviewing cycle. The fire policy for PRs the user already reviewed
needs per-PR event classification (bot-vs-self-vs-author, explicit signals), which
is a per-PR `gh` read and therefore agent-side by design. So when a watermark
advances, phase 1 returns `action: "classify"` with the candidate list; the agent
classifies and calls phase 2:

    # phase 1 (also the ONLY call on a cycle with no candidates)
    python3 cycle.py <bead> --jira-file J --gather-out G --candidates-out C
    # phase 2, after classifying C into R
    python3 cycle.py <bead> --gather-in G --reviewing-file R

Those two flags are required TOGETHER (either alone exits 2). Phase 1 arms the next
wakeup before classifying (a dead classification round trip must not kill the loop),
and the gather file is where phase 1 records that arm so phase 2 does not arm a
second chain; phase 2 reuses phase 1's frozen sources, so no candidate can appear
between the phases. `--reviewing-file` holds an OBJECT keyed by PR key
(`repo#number`), one record per candidate, NOT the list `--candidates-out` writes:

    {"<company>/docr#11539": {"status": "ok",
      "observed_updated_at": "...", "last_author_activity_at": "..." | null,
      "explicit": bool, "explicit_kinds": [...], "noted_kinds": [...],
      "author_event_count": int}}
    {"<key>": {"status": "error", "error_detail": "..."}}   # per-key, one PR only

Output (stdout, JSON) is a PLAN the agent executes; this script performs NO writes
and never arms a wakeup (ScheduleWakeup is agent-only). The agent, in order:
  1. if plan.chat: print it to chat AND `bd comment <id> "<chat>"`
  2. if plan.persist: `bd update <id> --notes '<plan.blob JSON>'`
  3. if plan.arming_due: ScheduleWakeup(delaySeconds=plan.interval, prompt="/overwatch")
Persisting AFTER chat preserves the duplicate-over-drop ordering from SKILL.md.

plan.action is one of:
  "skip"     double-fire guard tripped; do nothing, do not persist, do not arm.
  "terminal" loop is stopped (active:false) and this was not --resume; do nothing.
  "stop"     --stop was passed; persist the terminal blob and do not arm.
  "error"    usage error (the two-phase flags unpaired, or a --reviewing-file that is
             not an object keyed by PR key). Exit code 2; nothing to print, persist or
             arm. Fix the call and re-run; state has not moved.
  "run"      a normal/baseline/catch-up cycle; act on chat/persist/arming_due.
  "classify" a prs_reviewing watermark advanced; the three steps above still apply
             verbatim (its `chat` carries the OTHER sources' deltas and its
             `arming_due` mirrors `arm.due`), then classify `candidates` and call
             phase 2. Because that ordering holds, an agent that only knows the
             generic contract still arms the next wakeup and still surfaces
             everything except the reviewed-PR line.
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

# prs_reviewing fire policy (see plan_reviewing).
QUIET_PERIOD_DEFAULT_S = 7200
QUIET_PERIOD_MIN_S = 300
QUIET_PERIOD_MAX_S = 86400
# Ceiling on the poll interval while any hold is open. A pending hold is not an
# alert, so consecutive_quiet_successful_cycles keeps growing and the calibration
# table would stretch to 3600s, detecting the settle up to an hour late.
HOLD_MAX_INTERVAL_S = 1800
# Agent-supplied timestamps are boundary input: anything past this much ahead of
# `now` is clock skew (GitHub vs local, or a client-dated commit) and is clamped,
# because a future anchor makes `now - anchor` negative and the hold never settles.
SKEW_TOLERANCE_S = 300
# `gh search prs` is eventually consistent: a lagging index drops a still-open PR
# from the result with exit 0. Pruning an UNFIRED hold on that would destroy a
# pending alert, so an unfired hold survives this many consecutive absences.
HOLD_ABSENT_GRACE_CYCLES = 3

EXPLICIT_PHRASES = {
    "mention": "you were mentioned",
    "thread_reply": "reply on your thread",
    "review_requested": "re-review requested",
}


def _now(args: argparse.Namespace) -> datetime:
    if args.now:
        return datetime.fromisoformat(args.now.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _safe_parse(value: str | None) -> datetime | None:
    """Parse a PERSISTED or agent-supplied timestamp, or None if it is unusable.

    Never raises and never returns a tz-naive datetime. A naive or unparseable
    value reaching a comparison raises inside `reviewing_candidates`, i.e. BEFORE
    plan_cycle returns a plan and before the agent arms anything, so the loop
    would die with no wakeup queued and re-die on every `/overwatch` from the same
    persisted blob. Every read of a watermark or a hold anchor goes through here.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


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


def load_classified(path: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse the phase-2 payload, or return the reason it is unusable.

    The contract shape is an OBJECT keyed by PR key (`repo#number`) whose values are
    the per-key records. A LIST is the plausible mistake, because that is what
    `--candidates-out` emits, and a non-record value is the other one; both used to
    reach `.get(...)` inside plan_reviewing as an unhandled AttributeError. Rejecting
    them here rather than crashing matters because a phase-2 CRASH equals skipping
    phase 2, which SKILL.md names the one genuinely lossy option: nothing persists, no
    reviewed-PR line renders, and the same failure repeats every cycle from the same
    candidate. An error plan instead holds the watermark and says why.
    """
    try:
        payload = json.load(open(path))
    except (OSError, ValueError) as exc:
        return None, f"--reviewing-file is not readable JSON: {exc}"
    if not isinstance(payload, dict):
        return None, (f"--reviewing-file must be an OBJECT keyed by PR key, got "
                      f"{type(payload).__name__} (the --candidates-out list is a "
                      "different shape; see SKILL.md Step 3)")
    bad = sorted(k for k, v in payload.items() if not isinstance(v, dict))
    if bad:
        return None, (f"--reviewing-file values must be per-key record objects; "
                      f"not one for {bad}")
    return payload, None


def _error_plan(note: str) -> dict[str, Any]:
    """An inert plan: nothing to print, nothing to persist, nothing to arm."""
    return {"action": "error", "note": note, "chat": None, "blob": None,
            "persist": False, "arming_due": False, "interval": 0}


def interval_for(
    cqsc: int,
    override: int | None,
    holds_open: bool = False,
    hold_max: int = HOLD_MAX_INTERVAL_S,
) -> int:
    """Calibration table; a --interval override replaces the 900s floor.

    `holds_open` caps the backoff at `hold_max` so a pending quiet-period hold is
    still polled often enough to detect its settle. An EXPLICIT user override still
    wins (`max(floor, ...)`): someone who asks for hourly gets hourly.
    """
    floor = override if override else 900
    if cqsc < 3:
        base = floor
    elif cqsc <= 5:
        base = max(floor, 1800)
    else:
        base = max(floor, 3600)
    if holds_open:
        return max(floor, min(base, hold_max))
    return base


def _clamp_ts(value: str | None, now: datetime, floor: datetime | None = None) -> datetime | None:
    """Parse an agent-supplied timestamp defensively (boundary validation).

    A tz-naive value is read as UTC: comparing one against a tz-aware `now` raises,
    which would kill the WHOLE cycle rather than one key. A value past
    `now + SKEW_TOLERANCE_S` is clock skew and clamps to `now`. A value at or below
    `floor` (the previous watermark) is outside this cycle's window and is dropped.
    """
    dt = _safe_parse(value)
    if dt is None:
        return None
    if dt > now + timedelta(seconds=SKEW_TOLERANCE_S):
        dt = now
    if floor is not None and dt <= floor:
        return None
    return dt


def _iso_z(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _dur(seconds: int) -> str:
    hours, minutes = divmod(int(seconds or 0) // 60, 60)
    if hours and minutes:
        return f"{hours}h{minutes:02d}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def resolve_quiet_period(flag: int | None, persisted: int | None) -> int:
    """Quiet period in seconds: this run's flag, else the persisted value, else the
    default, clamped. Persisted like age_days so a bare wakeup keeps the override."""
    raw = flag or persisted or QUIET_PERIOD_DEFAULT_S
    return max(QUIET_PERIOD_MIN_S, min(QUIET_PERIOD_MAX_S, int(raw)))


def carry_auto_review(state: dict[str, Any] | None, blob: dict[str, Any]) -> None:
    """Carry the ``auto_review`` config forward, verbatim and uninterpreted.

    Every blob in this module is rebuilt from a fixed schema rather than mutated, so any
    key this function does not copy is DROPPED on the next cycle. auto-review config and
    its append-only posted/held ledger live in the state blob (see auto-review.md), so
    without this carry-forward an auto-review loop would silently forget its own scope,
    its caps, and what it had already done, one cycle after being configured.

    Deliberately opaque: cycle.py performs no writes and takes no auto-review action, so
    it has no reason to read inside this key. Keeping it uninterpreted is what preserves
    the separation between detection (here) and action (agent-side).

    Called on the steady-state path ONLY. The baseline path is unreachable for it by
    construction (`fresh = state is None or state == "corrupt"`, so `state` is never a
    dict there), and a corrupt blob SHOULD lose the config rather than carry it: this key
    authorizes unattended posting, so an unparseable state must fail closed and force
    reconfiguration.
    """
    if isinstance(state, dict) and isinstance(state.get("auto_review"), dict):
        blob["auto_review"] = state["auto_review"]


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
    prs_reviewing seeds each key's updatedAt watermark; errored sources are left
    unset so they re-baseline on first success."""
    per_source: dict[str, Any] = {}
    iso = now.isoformat()
    for name, rec in sources.items():
        if rec.get("status") != "ok":
            continue
        if name == "in_progress":
            known = _aged_ids(rec["items"], now, age_days)
        elif name == "prs_reviewing":
            known = {_pr_key(i): i.get("updated_at", "") for i in rec["items"]}
        elif name in ("prs_authored", "review_requests"):
            known = [_pr_key(i) for i in rec["items"]]
        elif name == "jira":
            known = [i["key"] for i in rec["items"]]
        else:  # beads_ready
            known = [i["id"] for i in rec["items"]]
        out: dict[str, Any] = {"status": "ok", "known_items": known}
        if name == "prs_reviewing":
            out["holds"] = {}
        out["last_success_at"] = iso
        out["error_detail"] = None
        per_source[name] = out
    return per_source


def diff_and_update(
    sources: dict[str, Any], prev_per_source: dict[str, Any], now: datetime, age_days: int
) -> tuple[dict[str, list], dict[str, Any]]:
    """Return (deltas_by_source, new_per_source). Ports SKILL.md Step 3 exactly.

    `prs_reviewing` is NOT handled here: its fire policy needs agent-classified
    per-PR events, which this pure fold over gather records has no access to, so
    plan_reviewing owns that source end to end (marks, holds, fires, pruning).
    """
    deltas: dict[str, list] = {}
    new_ps: dict[str, Any] = {}
    iso = now.isoformat()
    for name, rec in sources.items():
        if name == "prs_reviewing":
            continue
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


def _advanced(mark: str, current: str | None) -> bool:
    """Did the PR's updatedAt move past the persisted watermark?

    Both sides go through `_safe_parse`: an unusable persisted mark reads as "no
    advance" for this cycle and is rewritten from the current row (see
    `_resolve_mark`), which self-heals a legacy or hand-edited blob instead of
    raising here, where the raise would kill the cycle before it returns a plan.
    """
    lo, hi = _safe_parse(mark), _safe_parse(current)
    return lo is not None and hi is not None and hi > lo


def _resolve_mark(observed: str | None, row_ts: str | None, prev: str, now: datetime) -> str:
    """The watermark to PERSIST for a classified key, canonicalized.

    `observed_updated_at` is echoed back by the agent, so it is boundary input: a
    tz-naive or unparseable echo written straight into the blob poisons state, and
    every later cycle then raises while diffing it, before a plan exists and before
    anything is armed (the loop dies and stays dead across restarts).

    The mark never advances past the end of the window that was actually classified
    (events after it were never examined), never regresses below the previous mark
    (that would re-candidate the same window forever), and never lands in the future,
    which would freeze the key: nothing would ever advance past it again.
    """
    prev_dt = _safe_parse(prev)
    ceiling = now + timedelta(seconds=SKEW_TOLERANCE_S)
    usable = [d for d in (_safe_parse(row_ts), _safe_parse(observed))
              if d is not None and d <= ceiling]
    if not usable:
        return _iso_z(prev_dt) if prev_dt else ""
    chosen = min(usable)
    if prev_dt and chosen < prev_dt:
        chosen = prev_dt
    return _iso_z(chosen)


def reviewing_candidates(
    record: dict[str, Any], prev: dict[str, Any], skip_keys: set[str]
) -> list[dict[str, Any]]:
    """Keys whose updated_at advanced past the known watermark, as classify requests.

    Empty when the source errored or never succeeded (nothing to diff), for a key
    on its first appearance (baselined silently: the usual first appearance is the
    self-echo of the user's own just-posted review), and for the user's own PRs.
    """
    if record.get("status") != "ok" or "known_items" not in prev:
        return []
    prev_marks = prev.get("known_items") or {}
    out = []
    for row in record["items"]:
        key = _pr_key(row)
        if key in skip_keys or key not in prev_marks:
            continue
        if not _advanced(prev_marks[key], row.get("updated_at")):
            continue
        out.append({
            "key": key,
            "repository": row.get("repository", ""),
            "number": row.get("number"),
            "title": row.get("title", ""),
            "url": row.get("url", ""),
            "prev_watermark": prev_marks[key],
            "observed_updated_at": row.get("updated_at", ""),
        })
    return out


def _fold_author_activity(
    hold: dict[str, Any], anchor: datetime, events: int, quiet_s: int, absorb: bool
) -> dict[str, Any]:
    """Fold one cycle's author activity into the burst record.

    A NEW burst starts when the activity is at least a full quiet period after the
    burst's last author activity; that single rule is what makes one real burst one
    alert (#11539: 18 author events, max intra-burst gap 43m34s, 13:05:01Z to
    13:48:35Z, comfortably inside the 2h period) while post-settle activity always
    opens a fresh burst. `absorb` forces same-burst folding for a
    hold that already settled THIS cycle, so a catch-up cycle emits one settled
    alert instead of alerting now and again a quiet period later.
    """
    prev_anchor = _clamp_ts(hold.get("last_author_activity_at"), anchor + timedelta(days=3650))
    if prev_anchor is None or (not absorb and (anchor - prev_anchor).total_seconds() >= quiet_s):
        return {
            "last_author_activity_at": _iso_z(anchor),
            "opened_at": _iso_z(anchor),
            "author_events": events,
            "fired": False,
            "fired_at": None,
            "fired_via": None,
        }
    out = dict(hold)
    out["last_author_activity_at"] = _iso_z(max(prev_anchor, anchor))
    out["author_events"] = int(out.get("author_events", 0)) + events
    out.setdefault("opened_at", _iso_z(prev_anchor))
    return out


def _fire(
    hold: dict[str, Any],
    row: dict[str, Any],
    reason: str,
    kinds: list[str],
    anchor: datetime,
    quiet_s: int,
    now: datetime,
) -> dict[str, Any]:
    """Mark the burst fired and build its alert row. One fire per burst."""
    hold["fired"] = True
    hold["fired_at"] = _iso_z(now)
    via = ("explicit:" + ",".join(kinds)) if reason == "explicit" and kinds else reason
    hold["fired_via"] = via
    opened = _clamp_ts(hold.get("opened_at"), now)
    burst = int((anchor - opened).total_seconds()) if opened else 0
    return {
        **row,
        "fire_reason": reason,
        "explicit_kinds": list(kinds),
        # Signals seen in the burst that did NOT qualify as explicit (a re-review
        # request within 300s of a push). The `👀 review requested` line is
        # suppressed while this policy owns the key, so naming them here is the
        # only place the user learns a re-review was asked for.
        "noted_kinds": list(hold.get("noted_kinds") or []),
        "author_events": int(hold.get("author_events", 0)),
        "burst_seconds": max(0, burst),
        "quiet_period_seconds": quiet_s,
    }


def plan_reviewing(
    record: dict[str, Any],
    prev: dict[str, Any],
    classified: dict[str, dict[str, Any]],
    now: datetime,
    quiet_period_s: int,
    skip_keys: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Own the prs_reviewing source: return (fires, new_source_record).

    Fire policy, per key, at most one fire per cycle:

    PATH A (explicit, immediate): the classified window carries a signal aimed at
    the user (an @mention, a reply in a thread the user started, a deliberate
    re-review request). Fires now and closes the burst.

    PATH B (hold, then fire once settled): author activity with no explicit signal
    does not fire. It anchors a timer at the last author activity; the alert fires
    once `now - last_author_activity_at >= quiet_period_s`. Further author activity
    refreshes the anchor instead of firing.

    BOT AND SELF ACTIVITY NEVER ANCHOR THE TIMER. The agent reports
    `last_author_activity_at: null` when every post-watermark event was a bot's or
    the user's own; that advances the watermark only. Counting a bot comment as
    author activity would let a per-push CI bot hold a burst open forever and the
    alert would never fire, which is the opposite of the noise this policy removes.
    """
    prev_marks = dict(prev.get("known_items") or {})
    prev_holds = dict(prev.get("holds") or {})
    iso = now.isoformat()

    if record.get("status") != "ok":
        # Not diffed, and no hold is evaluated: firing needs the current row's
        # title/url. The settle test stays true across the outage, so the hold
        # fires on the first successful cycle.
        return [], {
            "status": "error",
            "known_items": prev.get("known_items", {}),
            "holds": prev_holds,
            "last_success_at": prev.get("last_success_at"),
            "error_detail": record.get("error_detail", "unknown"),
        }

    current = {_pr_key(row): row for row in record["items"]}

    def ok_record(marks: dict[str, str], holds: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "known_items": marks, "holds": holds,
                "last_success_at": iso, "error_detail": None}

    if "known_items" not in prev:  # never succeeded: re-baseline silently
        return [], ok_record({k: r.get("updated_at", "") for k, r in current.items()}, {})

    fires: list[dict[str, Any]] = []
    marks: dict[str, str] = {}
    holds: dict[str, Any] = {}

    for key, row in current.items():
        mark = prev_marks.get(key, "")
        hold = dict(prev_holds.get(key) or {})
        hold.pop("absent_cycles", None)

        # Own PRs (covered by prs_authored) and first appearances record the
        # watermark and never hold.
        if key in skip_keys or key not in prev_marks:
            marks[key] = row.get("updated_at", "")
            continue

        advanced = _advanced(mark, row.get("updated_at"))
        cls = classified.get(key) if advanced else None

        if advanced and (cls is None or cls.get("status", "ok") != "ok"):
            # Unclassified advance: hold the watermark so the next cycle
            # re-candidates and re-classifies, and never anchor the timer on
            # updatedAt (bots bump it, so anchoring there would re-anchor on bot
            # activity every cycle and the hold would never settle).
            marks[key] = mark
            if hold:
                if not hold.get("fired"):
                    hold["unclassified"] = True
                holds[key] = hold
            continue

        anchor_in: datetime | None = None
        explicit = False
        kinds: list[str] = []
        noted: list[str] = []
        if cls is not None:
            marks[key] = _resolve_mark(cls.get("observed_updated_at"),
                                       row.get("updated_at"), mark, now)
            floor = _safe_parse(mark)
            anchor_in = _clamp_ts(cls.get("last_author_activity_at"), now, floor=floor)
            explicit = bool(cls.get("explicit"))
            kinds = [str(k) for k in (cls.get("explicit_kinds") or [])]
            noted = [str(k) for k in (cls.get("noted_kinds") or [])]
            if explicit and anchor_in is None:
                # Contract invariant: an explicit event IS author activity. This is
                # also what lets a `review_requested` whose ACTOR is a bot fire Path
                # A: the requesting event is dropped from the author survivors, so
                # the anchor comes back null while `explicit` is true.
                anchor_in = _clamp_ts(marks[key], now) or now
        else:
            marks[key] = row.get("updated_at", "") or mark

        pre_anchor = _clamp_ts(hold.get("last_author_activity_at"), now) if hold else None
        pre_settled = (
            pre_anchor is not None
            and not hold.get("fired")
            and (now - pre_anchor).total_seconds() >= quiet_period_s
        )
        if anchor_in is not None:
            hold = _fold_author_activity(hold, anchor_in, int(cls.get("author_event_count") or 1),
                                         quiet_period_s, absorb=pre_settled)
            hold.pop("unclassified", None)
        if not hold:
            continue
        if noted:
            hold["noted_kinds"] = sorted(set(hold.get("noted_kinds") or []) | set(noted))
        # Identity for the alert line, so a hold can still be reported when the key
        # has fallen out of the search result (see the absence branch below).
        hold["pr"] = {"repository": row.get("repository", ""), "number": row.get("number"),
                      "title": row.get("title", ""), "url": row.get("url", "")}

        anchor = _clamp_ts(hold.get("last_author_activity_at"), now)
        if anchor is not None and not hold.get("fired"):
            settle_due = pre_settled or (now - anchor).total_seconds() >= quiet_period_s
            # Explicit wins the reason when both apply this cycle: a settled-labelled
            # alert would never tell the user they were named, and the burst then
            # suppresses the mention for another quiet period.
            if explicit:
                fires.append(_fire(hold, row, "explicit", kinds, anchor, quiet_period_s, now))
            elif settle_due:
                fires.append(_fire(hold, row, "settled", [], anchor, quiet_period_s, now))
        elif explicit and kinds and hold.get("fired"):
            # One fire per burst is the ratified rule (Fixture 1 fires once for a
            # timeline holding two explicit signals), so this mention is NOT
            # re-alerted. Record it: the drop then shows in state instead of being
            # invisible, and the burst boundary still lets a later burst fire.
            hold["suppressed_explicit_kinds"] = sorted(
                set(hold.get("suppressed_explicit_kinds") or []) | set(kinds))
        holds[key] = hold

    # A key absent from the current result is usually closed or merged, and a
    # merged PR needs no re-review ping, so its hold prunes with its watermark.
    # `gh search prs` is eventually consistent though, so an UNFIRED hold (a
    # pending alert) survives a bounded number of absences rather than being
    # dropped: it cannot fire while absent anyway (the alert renders the row).
    for key, stale in prev_holds.items():
        if key in holds or key in current or stale.get("fired"):
            continue
        absent = int(stale.get("absent_cycles", 0)) + 1
        if absent <= HOLD_ABSENT_GRACE_CYCLES:
            kept = dict(stale)
            kept["absent_cycles"] = absent
            holds[key] = kept
            marks.setdefault(key, prev_marks.get(key, ""))
            continue
        # Grace exhausted with the alert still PENDING. Dropping the hold and its
        # watermark together (what this branch used to do) loses the burst outright:
        # the key returns as a first appearance and is baselined silently, so every
        # author event from the absent window goes unreported. Fire it on the way
        # out instead, which is the duplicate-over-drop direction.
        anchor = _clamp_ts(stale.get("last_author_activity_at"), now)
        if anchor is None:
            continue
        pr = dict(stale.get("pr") or {})
        repo, _, number = key.rpartition("#")
        absent_row = {"repository": pr.get("repository") or repo,
                      "number": pr.get("number") if pr.get("number") is not None else number,
                      "title": pr.get("title", ""), "url": pr.get("url", "")}
        fired_row = _fire(dict(stale), absent_row, "settled", [], anchor, quiet_period_s, now)
        fires.append({**fired_row, "absent_from_search": True})

    return fires, ok_record(marks, holds)


def has_open_hold(record: dict[str, Any]) -> bool:
    """Any unfired hold. Ignores fired holds: counting those would pin the poll
    interval at the hold ceiling forever after one PR ever fired."""
    return any(not h.get("fired") for h in (record.get("holds") or {}).values())


def reviewing_owned_keys(
    record: dict[str, Any], fires: list[dict[str, Any]], now: datetime, quiet_s: int
) -> set[str]:
    """Keys whose notification the prs_reviewing fire policy is currently carrying.

    The `👀 review requested` membership line is suppressed for these and ONLY
    these. Suppressing it for every key in the reviewing result was too wide: a
    re-review request that produces no fire and no hold (a bot-actor request the
    reduction could not attribute, or a request on a PR whose burst already
    settled) then produced NO line at all, and the key is consumed into
    `review_requests.known_items`, so it never re-deltas and the ask is lost.

    Owned means: fired this cycle, OR an unfired hold (an alert is coming), OR a
    fired hold whose burst is still live (`now - last_author_activity_at` inside
    one quiet period), which is the per-restack re-request noise this suppression
    was built for. A settled, quiet PR owns nothing.
    """
    owned = {_pr_key(f) for f in fires}
    for key, hold in (record.get("holds") or {}).items():
        if not hold.get("fired"):
            owned.add(key)
            continue
        anchor = _clamp_ts(hold.get("last_author_activity_at"), now)
        if anchor is not None and (now - anchor).total_seconds() < quiet_s:
            owned.add(key)
    return owned


def compose(deltas: dict[str, list], sources: dict[str, Any], age_days: int, catch_up: bool,
            owned_keys: set[str] | frozenset[str] = frozenset(),
            degraded: list[tuple[str, str]] | None = None) -> str | None:
    """SKILL.md Step 4 output. None if fully quiet AND all sources ok.

    `owned_keys` are the PRs whose notification the prs_reviewing fire policy is
    currently carrying (see `reviewing_owned_keys`). A re-review request on one of
    those re-adds the key to the review_requests membership source (GitHub drops the
    user from requested reviewers when they submit a review, and tooling re-adds them
    on every restack), so its 👀 line would bypass the quiet period entirely and
    re-alert per push; for those keys the richer prs_reviewing line is the alert.

    `degraded` is `(key, detail)` per prs_reviewing candidate the agent could not
    classify. It MUST render: the watermark is held and the key re-candidates
    forever, so without a line the cycle looks healthy-quiet while activity on a
    reviewed PR sits unread indefinitely. An errored SOURCE already gets a line;
    this is the same guarantee at per-key granularity.
    """
    lines: list[str] = []
    for r in deltas.get("beads_ready", []):
        lines.append(f"🔓 newly unblocked: {r['id']} [P{r.get('priority', '')}] {r.get('title', '')}")
    for r in deltas.get("review_requests", []):
        if _pr_key(r) in owned_keys:
            continue
        lines.append(f"👀 review requested: {_pr_key(r)} {r.get('title', '')} {r.get('url', '')}")
    for r in deltas.get("in_progress", []):
        lines.append(f"⏳ stalling (in_progress, no update in >{age_days}d): {r['id']} {r.get('title', '')}")
    for r in deltas.get("prs_reviewing", []):
        head = f"{_pr_key(r)} {r.get('title', '')} {r.get('url', '')}".rstrip()
        noted = ", ".join(EXPLICIT_PHRASES.get(k, k) for k in (r.get("noted_kinds") or []))
        if r.get("fire_reason") == "settled":
            events = int(r.get("author_events", 0))
            span = f" over {_dur(r.get('burst_seconds', 0))}" if r.get("burst_seconds") else ""
            quiet = _dur(r.get("quiet_period_seconds", QUIET_PERIOD_DEFAULT_S))
            plural = "" if events == 1 else "s"
            tail = f"; {noted}" if noted else ""
            gone = "; PR left the search result" if r.get("absent_from_search") else ""
            lines.append(f"🔁 settled after author activity: {head} "
                         f"({events} author event{plural}{span}, quiet {quiet}{tail}{gone})")
        else:
            why = ", ".join(EXPLICIT_PHRASES.get(k, k) for k in (r.get("explicit_kinds") or []))
            if noted:
                why = f"{why}; {noted}" if why else noted
            suffix = f" ({why})" if why else ""
            lines.append(f"🔁 activity on reviewed PR: {head}{suffix}")
    for r in deltas.get("prs_authored", []):
        lines.append(f"other: opened PR {_pr_key(r)} {r.get('title', '')}")
    for r in deltas.get("jira", []):
        lines.append(f"other: jira {r['key']} {r.get('summary', '')}".rstrip())
    for name, rec in sources.items():
        if rec.get("status") == "error":
            lines.append(f"⚠️ source {name} failed: {rec.get('error_detail', '')}")
    for key, detail in (degraded or []):
        lines.append(f"⚠️ could not read activity on reviewed PR {key}: {detail} "
                     "(watermark held, retrying next cycle)")
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
    persisted_quiet = state.get("quiet_period_seconds") if isinstance(state, dict) else None
    quiet_s = resolve_quiet_period(args.quiet_period, persisted_quiet)

    # Phase 2 replays phase 1's frozen sources (and its arm decision); otherwise
    # gather the bash-pollable sources and merge the agent-supplied Jira record.
    carried_arm: dict[str, Any] | None = None
    chat_emitted = False
    if args.gather_in:
        payload = json.load(open(args.gather_in))
        sources = payload["sources"]
        carried_arm = payload.get("arm")
        chat_emitted = bool(payload.get("chat_emitted"))
    else:
        sources = gather.gather()
        jira_record = json.load(open(args.jira_file)) if args.jira_file else {"status": "ok", "items": []}
        sources["jira"] = jira_record

    fresh = state is None or state == "corrupt"

    if fresh:
        # Baseline: seed known, surface nothing, arm. Every prs_reviewing key is a
        # first appearance here, so a baseline cycle never has a classify candidate.
        per_source = seed_baseline(sources, now, age_days)
        interval = interval_for(0, args.interval)
        blob = {
            "schema_version": 2, "active": True, "terminal_reason": None,
            "last_cycle_at": iso, "next_wakeup_at": (now + timedelta(seconds=interval)).isoformat(),
            "consecutive_quiet_successful_cycles": 0, "interval_seconds": args.interval or 900,
            "age_days": age_days, "quiet_period_seconds": quiet_s, "per_source": per_source,
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

    # prs_reviewing: own PRs are covered by prs_authored, and its carried-forward
    # known_items is the right skip set even when that source is failing (an empty
    # one would leak own-PR noise on exactly the cycles gh is down).
    skip_keys = set(new_ps.get("prs_authored", {}).get("known_items") or [])
    rev_source = sources.get("prs_reviewing", {})
    rev_prev = state["per_source"].get("prs_reviewing", {})

    candidates = reviewing_candidates(rev_source, rev_prev, skip_keys)
    classified: dict[str, Any] | None = None
    if args.reviewing_file:
        classified, why = load_classified(args.reviewing_file)
        if why:
            return _error_plan(why)
    if classified is None:
        if candidates:
            # Phase 1: arm BEFORE handing off, so a classification round trip that
            # dies (turn limit on a chatty PR) cannot kill the loop, then record the
            # arm in the gather file so phase 2 does not arm a second chain.
            interval = interval_for(0, args.interval)
            arming_due = (loaded_nwa is None) or (now >= loaded_nwa)
            arm = {
                "due": arming_due,
                "interval": interval,
                "next_wakeup_at": ((now + timedelta(seconds=interval)).isoformat()
                                   if arming_due else state.get("next_wakeup_at")),
            }
            # Emit every OTHER source's delta here rather than after classification.
            # Phase 2's round trip has a real failure mode (a turn limit on a chatty
            # PR, a per-PR 403), and it is deterministic for the same PR, so holding
            # a P1 unblocked bead or a fresh review request behind it would suppress
            # them on every cycle for as long as that one PR stays unreadable.
            # Nothing is persisted yet, so a phase 2 that never runs re-derives and
            # re-prints these next cycle: duplicate over drop.
            chat = compose(deltas, sources, age_days, catch_up)
            if args.gather_out:
                with open(args.gather_out, "w") as fh:
                    json.dump({"gathered_at": iso, "sources": sources, "arm": arm,
                               "chat_emitted": chat is not None}, fh)
            if args.candidates_out:
                with open(args.candidates_out, "w") as fh:
                    json.dump(candidates, fh)
            return {"action": "classify", "candidates": candidates,
                    "candidates_file": args.candidates_out, "gather_file": args.gather_out,
                    "arm": arm, "chat": chat, "event_comment": chat, "blob": None,
                    "persist": False,
                    # Mirrors arm.due so the GENERIC plan contract ("if arming_due,
                    # ScheduleWakeup(interval)") arms the same chain the classify
                    # branch describes. Returning false here while arm.due was true
                    # meant an agent following only the generic ordering armed
                    # nothing, and a phase 2 that then died ended the loop silently.
                    "arming_due": arming_due, "interval": interval,
                    "note": f"{len(candidates)} prs_reviewing candidate(s) need classification"}
        classified = {}

    fires, rev_record = plan_reviewing(rev_source, rev_prev, classified, now, quiet_s, skip_keys)
    deltas["prs_reviewing"] = fires
    new_ps["prs_reviewing"] = rev_record
    owned_keys = reviewing_owned_keys(rev_record, fires, now, quiet_s)
    degraded: list[tuple[str, str]] = []
    for c in candidates:
        rec = classified.get(c["key"])
        if rec is None:
            degraded.append((c["key"], "no classification returned"))
        elif rec.get("status", "ok") != "ok":
            degraded.append((c["key"], str(rec.get("error_detail") or "classification failed")))

    if chat_emitted:
        # Phase 1 already printed the other sources' lines; re-composing them here
        # would double them in one cycle.
        chat = compose({"prs_reviewing": fires}, {}, age_days, False, owned_keys, degraded)
    else:
        chat = compose(deltas, sources, age_days, catch_up, owned_keys, degraded)

    all_ok = all(r.get("status") == "ok" for r in sources.values())
    quiet = chat is None and all_ok and not chat_emitted
    cqsc = state.get("consecutive_quiet_successful_cycles", 0)
    cqsc = cqsc + 1 if quiet else 0
    # A hold-only cycle is genuinely quiet (nothing was surfaced), so the counter
    # keeps climbing; the clamp is what stops the cadence from stretching past the
    # point where the settle would be detected on time.
    interval = interval_for(cqsc, args.interval, holds_open=has_open_hold(rev_record),
                            hold_max=min(HOLD_MAX_INTERVAL_S, quiet_s))

    if carried_arm:
        arming_due = False  # phase 1 already armed (or deliberately deferred)
        interval = carried_arm["interval"]
        next_wakeup = carried_arm["next_wakeup_at"]
        persisted_interval = interval if carried_arm.get("due") else prev_interval
    else:
        arming_due = (loaded_nwa is None) or (now >= loaded_nwa)
        next_wakeup = ((now + timedelta(seconds=interval)).isoformat() if arming_due
                       else state.get("next_wakeup_at"))
        persisted_interval = interval if arming_due else prev_interval

    blob = {
        "schema_version": 2, "active": True, "terminal_reason": None,
        "last_cycle_at": iso, "next_wakeup_at": next_wakeup,
        "consecutive_quiet_successful_cycles": cqsc,
        "interval_seconds": persisted_interval,
        "age_days": age_days, "quiet_period_seconds": quiet_s, "per_source": new_ps,
    }
    carry_auto_review(state, blob)
    note = ("catch-up" if catch_up else "normal") + (" quiet" if quiet else " delta")
    if degraded:
        note += (f"; DEGRADED: unclassified prs_reviewing {','.join(k for k, _ in degraded)}"
                 " (held, not dropped, reported in chat)")
    return {"action": "run", "note": note,
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
    ap.add_argument("--quiet-period", type=int)
    ap.add_argument("--candidates-out", help="phase 1: write the classify requests here")
    ap.add_argument("--gather-out", help="phase 1: freeze sources + the arm decision here")
    ap.add_argument("--gather-in", help="phase 2: replay phase 1's frozen sources")
    ap.add_argument("--reviewing-file",
                    help="phase 2: the agent's classified prs_reviewing records, as an "
                         "object keyed by repo#number (NOT the --candidates-out list)")
    args = ap.parse_args(argv)
    # The two phase-2 flags are required TOGETHER, in both directions.
    if args.reviewing_file and not args.gather_in:
        # Without the frozen gather, phase 2 re-derives arming from a still-past
        # next_wakeup_at and arms a SECOND chain on top of phase 1's arm.
        print(json.dumps(_error_plan("--reviewing-file requires --gather-in "
                                     "(it carries phase 1's arm decision)"), indent=2))
        return 2
    if args.gather_in and not args.reviewing_file:
        # The mirror. Without the classified records there is nothing for phase 2 to
        # do, and a cycle with candidates falls into phase 1's branch instead: the
        # frozen `arm` is ignored (a second chain is armed on top of phase 1's) and
        # every other source's delta is composed and printed a second time.
        print(json.dumps(_error_plan("--gather-in requires --reviewing-file "
                                     "(phase 2 has nothing to classify without it)"),
                         indent=2))
        return 2
    plan = plan_cycle(args)
    print(json.dumps(plan, indent=2))
    return 2 if plan.get("action") == "error" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
