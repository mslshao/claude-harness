#!/usr/bin/env python3
"""Checks for PR review comment posts (the engineering lead 2026-05-26 + Michael 2026-06-02).

Reads a `gh api` command string from stdin. If the command posts a PR review
(POST .../pulls/N/reviews) or creates/edits an inline review comment
(POST .../pulls/N/comments, PATCH .../pulls/comments/ID), it extracts the
payload and runs two checks:

1. @-mention guard: no posted body (summary OR inline comment) may @-tag a
   person; GitHub notifies every tagged handle. Only `@claude` (the pr-intel
   verify-loop bot trigger) is allowed. See
   correction:style:no-mentions-in-review-body.
2. Attribution lede: every INLINE comment body opens with an explicit tooling
   attribution prefix (the summary body is exempt: reviewer voice allowed).

Rationale: review-voice.md T5 / reviewer-discipline.md T5. Every finding
pr-intel emits passed through a specialist agent or an orchestrator pattern
check; none came from Michael's unaided reading, so each must be attributed as
the lede, not posted in his voice. The review summary (top-level `body` on the
reviews endpoint) is exempt: it is allowed to be in reviewer voice. Reactions
and replies endpoints are exempt (no authored finding to attribute).

Output contract: prints a human-readable block to stdout listing non-conforming
comments, or nothing when clean / not a checkable command. The wrapping bash
hook treats any stdout as a block (exit 2).
"""

import json
import os
import re
import sys

# Attribution must be the LEDE: the comment must OPEN with the source, not merely
# mention a tool somewhere in prose ("Your decline of Copilot's suggestion..." is
# Michael's voice, not an attribution). So the openers are anchored at the start
# of the body (after stripping leading markdown and an optional severity lead).
# Mirrors the accepted openers in review-voice.md T5.

# Leading markdown / whitespace to strip before anchoring (>, *, _, #, -, `).
_LEAD_STRIP = re.compile(r"^[\s>*_#`-]+")
# Optional leading severity/qualifier lead ("Minor, ", "Nit: ", "Note - ").
_SEV_STRIP = re.compile(r"^(minor|nit|note|small|optional|fyi)\b[\s,:.;-]+", re.IGNORECASE)

# Bot/static-analyzer names are only an attribution when used as the SUBJECT with
# an attribution verb nearby ("Copilot flagged ..."), never as a possessive object
# ("Copilot's suggestion ...").
_BOT = r"(sonar(cloud)?|datadog|copilot|sentry|checkov|pattern[\s-]check|static\s+analy\w*)"
_VERB = r"(flag|flagged|flags|report|reported|caught|noted|surfaced|found|raised|warns?|warned)"

OPENERS = [
    # "My automated <X> pass flagged ...", "My `mx2-...` specialist flagged ...",
    # "from my automated code-review and Pydantic-settings passes ..."
    r"(from\s+)?my\s+[\w/`'-]+(\s+[\w/`'&.-]+){0,7}?\s+"
    r"(specialist|pass|passes|review|reviews|analysis|audit|auditor|reviewer|hunter)\b",
    r"cross-file\b",
    r"cross-service\b",
    r"ac\s+item\b",
    r"acceptance\s+criteri",
    r"(per\s+)?the\s+design\s+doc\b",
    r"the\s+design\s+(spec|specifies)\b",
    r"the\s+spec\b",
    r"spec\s+(specifies|compliance)\b",
    _BOT + r"\b[\s\S]{0,40}?\b" + _VERB + r"\b",
    r"flagged\s+by\b",
    r"(an?\s+)?automated\s+[\w/-]+(\s+[\w/-]+){0,4}?\s+"
    r"(pass|passes|review|reviews|specialist|audit|analysis|check)\b",
    r"the\s+[\w/-]+\s+(specialist|pass|review|auditor|reviewer|hunter)\s+" + _VERB + r"\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in OPENERS]


def is_attributed(body: str) -> bool:
    s = _LEAD_STRIP.sub("", body)
    # Strip up to two leading severity qualifiers ("Minor, from my ..." -> "from my ...").
    for _ in range(2):
        stripped = _SEV_STRIP.sub("", s).lstrip()
        if stripped == s:
            break
        s = stripped
    return any(rx.match(s) for rx in _COMPILED)


# --- @-mention guard (Michael 2026-06-02, PR #9578) ---------------------------
# A posted review body or inline comment must not @-tag people: GitHub fires a
# notification to every tagged handle, turning a routine approval into noise for
# people who are not the review's audience. The ONLY allowed mention is the
# `@claude` verify-loop bot trigger (pr-intel default mode posts it deliberately
# in both the summary body and inline comments). Unlike attribution, this check
# covers the summary body too. See bd memories
# correction:style:no-mentions-in-review-body.
_MENTION_ALLOW = {"claude"}
# Mention = `@handle` (optionally `@org/team`). The negative lookbehind keeps
# email local parts (`user@example.com`) from matching; code identifiers
# (`@property`, `@injectable`) are excluded by stripping backticked spans first.
_MENTION = re.compile(
    r"(?<![A-Za-z0-9._%+/-])@([A-Za-z0-9][A-Za-z0-9-]{0,38}(?:/[A-Za-z0-9][A-Za-z0-9-]{0,38})?)")
_FENCED = re.compile(r"```.*?```", re.S)
_INLINE_CODE = re.compile(r"`[^`]*`")


def _strip_code(body: str) -> str:
    """Remove fenced blocks and inline-code spans so decorators like
    `@property` inside backticks are not mistaken for mentions."""
    return _INLINE_CODE.sub(" ", _FENCED.sub(" ", body))


def find_mentions(body: str) -> list[str]:
    """Return the disallowed @-mentions in a body (allowlist + code excluded)."""
    found: list[str] = []
    seen: set[str] = set()
    for m in _MENTION.finditer(_strip_code(body)):
        handle = m.group(1)
        if handle.split("/")[0].lower() in _MENTION_ALLOW:
            continue
        token = "@" + handle
        if token not in seen:
            seen.add(token)
            found.append(token)
    return found


def classify_endpoint(cmd: str) -> str | None:
    """Return 'review', 'comment', or None for not-checkable."""
    if not re.search(r"(?<![\"'`])gh\s+api\b", cmd):
        return None
    # Reactions and replies carry no authored finding to attribute.
    if re.search(r"/(reactions|replies)\b", cmd):
        return None
    if re.search(r"/pulls/\d+/reviews\b", cmd):
        return "review"
    # PATCH .../pulls/comments/ID  or  POST .../pulls/N/comments
    if re.search(r"/pulls/(comments/\d+|\d+/comments)\b", cmd):
        return "comment"
    return None


def extract_payload(cmd: str) -> str | None:
    # 1. --input <path> (the documented post-review mechanism)
    m = re.search(r"--input\s+(\S+)", cmd)
    if m:
        path = m.group(1).strip("'\"")
        if path != "-" and os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError:
                return None
    # 2. heredoc: <<TAG ... TAG  or  <<'TAG' ... TAG  or  <<-TAG
    m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?\r?\n(.*?)\r?\n\1\b", cmd, re.S)
    if m:
        return m.group(2)
    # 3. -f body=@file
    m = re.search(r"(?:-f|--field|-F|--raw-field)\s+body=@(\S+)", cmd)
    if m:
        path = m.group(1).strip("'\"")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.dumps({"body": f.read()})
            except OSError:
                return None
    return None


def evaluate(data: dict, kind: str) -> list[str]:
    """Run both checks on a parsed payload. Returns block-message lines
    (empty list = clean). Shared by command mode and file mode."""
    # Attribution applies to INLINE comments only (the summary is reviewer
    # voice). The @-mention guard applies to the summary body too.
    inline_bodies: list[tuple[str, str]] = []
    mention_bodies: list[tuple[str, str]] = []
    if kind == "review":
        if data.get("body"):
            mention_bodies.append(("review summary body", str(data["body"])))
        for i, c in enumerate(data.get("comments") or []):
            if isinstance(c, dict) and c.get("body"):
                label = "comment %d (%s:%s)" % (
                    i + 1, c.get("path", "?"), c.get("line", "?"))
                inline_bodies.append((label, str(c["body"])))
                mention_bodies.append((label, str(c["body"])))
    else:  # single inline comment create/edit
        if data.get("body"):
            inline_bodies.append(("inline comment", str(data["body"])))
            mention_bodies.append(("inline comment", str(data["body"])))

    out: list[str] = []

    # Check 1: @-mention of a person in any posted body (summary or inline).
    mention_hits = [
        (label, find_mentions(body)) for (label, body) in mention_bodies]
    mention_hits = [(label, ms) for (label, ms) in mention_hits if ms]
    if mention_hits:
        out.extend([
            "BLOCKED: @-mention of a person in a posted review body/comment "
            "(correction:style:no-mentions-in-review-body, Michael 2026-06-02).",
            "GitHub notifies every tagged handle; an approval must not ping "
            "people who are not its audience. Drop the @-tag (name the gate or "
            "person without the handle). Only `@claude` (the verify-loop "
            "trigger) is allowed.",
            "Offending mention(s):",
        ])
        out.extend("  - %s: %s" % (label, ", ".join(ms))
                   for (label, ms) in mention_hits)

    # Check 2: every inline comment opens with a tooling-attribution lede.
    bad = [label for (label, body) in inline_bodies if not is_attributed(body)]
    if bad:
        if out:
            out.append("")
        out.extend([
            "BLOCKED: unattributed PR review comment(s) (review-voice.md T5; "
            "the engineering lead 2026-05-26 uniform-attribution rule).",
            "Every INLINE comment must OPEN with explicit tooling attribution as "
            "the lede, not Michael's unaided voice. Accepted openers, e.g.:",
            "  'My automated <specialist> pass flagged ...'",
            "  'Cross-file analysis surfaced that ...'",
            "  'AC item N expects X, the diff implements Y'",
            "  'SonarCloud flagged python:S<code>: ...'  /  'Copilot flagged ...'",
            "Non-conforming comment(s):",
        ])
        out.extend("  - " + label for label in bad)
        out.append(
            "Rewrite the lede (attribution first), then re-post. If this is your "
            "own editing-pass comment, lead with the source anyway or post it "
            "outside this path.")

    return out


# --- file-mode endpoint inference (PostToolUse Write backup hook) -------------
# Review-event values that mark a JSON blob as a reviews-endpoint payload.
_REVIEW_EVENTS = {"APPROVE", "REQUEST_CHANGES", "COMMENT", "PENDING"}
# Keys a single-comment create/edit payload may carry. Used to gate file mode so
# the backup hook does NOT fire on unrelated {"body": ...} JSON.
_COMMENT_KEYS = {
    "body", "path", "line", "side", "start_line", "start_side",
    "in_reply_to", "commit_id", "subject_type"}
_REVIEW_NAME_HINT = re.compile(r"(review|comment|-edit-|-patch-|inline)", re.IGNORECASE)


def infer_kind_from_payload(data: object, filename: str = "") -> str | None:
    """Decide whether a written JSON looks like a review/comment payload, WITHOUT
    a gh command. Conservative, to avoid firing on unrelated JSON writes."""
    if not isinstance(data, dict):
        return None
    comments = data.get("comments")
    has_review_comments = isinstance(comments, list) and any(
        isinstance(c, dict) and "body" in c and ("path" in c or "line" in c)
        for c in comments)
    event = data.get("event")
    if has_review_comments or (
            isinstance(event, str) and event.upper() in _REVIEW_EVENTS):
        return "review"
    # Single-comment payload: only treat as a comment when the filename hints a
    # review payload, so an arbitrary {"body": ...} JSON write is not blocked.
    if "body" in data and set(data.keys()) <= _COMMENT_KEYS:
        if _REVIEW_NAME_HINT.search(os.path.basename(filename)):
            return "comment"
    return None


def _emit(out: list[str]) -> int:
    if not out:
        return 0
    sys.stdout.write("\n".join(out) + "\n")
    return 0


def _run_command_mode() -> int:
    cmd = sys.stdin.read()
    kind = classify_endpoint(cmd)
    if kind is None:
        return 0
    raw = extract_payload(cmd)
    if not raw:
        # Unparseable payload (inline heredoc edge cases, -f body=inline). Do not
        # block what cannot be parsed; the documented path uses --input <file>.
        return 0
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return 0
    if not isinstance(data, dict):
        return 0
    return _emit(evaluate(data, kind))


def _run_file_mode(path: str) -> int:
    if not path or not os.path.isfile(path):
        return 0
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return 0
    kind = infer_kind_from_payload(data, path)
    if kind is None:
        return 0
    return _emit(evaluate(data, kind))


def main() -> int:
    # File mode (PostToolUse Write backup hook): `--payload-file <path>` checks a
    # written JSON payload directly, catching review payloads created via the
    # Write tool that are then posted through a path the PreToolUse Bash hook
    # cannot see (e.g. a Python subprocess). Default (no args) is command mode:
    # reads a gh command from stdin (PreToolUse Bash hook).
    args = sys.argv[1:]
    if len(args) >= 2 and args[0] == "--payload-file":
        return _run_file_mode(args[1])
    return _run_command_mode()


if __name__ == "__main__":
    sys.exit(main())
