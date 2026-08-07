# GitHub Review API Reference

Empirically verified 2026-04-03. See `memory/github-api.md` for full context.

## Posting a Review with Inline Comments

Write the payload to a file with the Write tool, then pass it with `--input <file>`. Do NOT use a stdin heredoc: heredocs are fragile with special characters in comment bodies and trip the em-dash Bash hook.

Payload shape (write this to e.g. `/tmp/pr-review-<number>.json`):

```json
{
  "body": "review summary",
  "event": "COMMENT",
  "comments": [
    {
      "path": "src/python/mx2/service/file.py",
      "line": 42,
      "body": "comment text"
    }
  ]
}
```

Then post it:

```bash
gh api -X POST /repos/<company>/docr/pulls/{pull_number}/reviews --input /tmp/pr-review-<number>.json
```

Returns: `{"id": <review_id>, "html_url": "...#pullrequestreview-<id>", "state": "COMMENTED"}`

## Parameters

| Field | Required | Notes |
|-------|----------|-------|
| `body` | Yes | Top-level review summary |
| `event` | Yes | `COMMENT`, `APPROVE`, or `REQUEST_CHANGES` |
| `comments` | No | Array of inline comment objects. Omit for summary-only. |
| `comments[].path` | Yes | Relative file path (e.g. `src/python/mx2/foo/bar.py`) |
| `comments[].line` | Yes | **File-relative** line number. Must be in the diff. |
| `comments[].body` | Yes | Comment text |
| `comments[].side` | No | `RIGHT` (additions/context) or `LEFT` (deletions). Defaults to RIGHT. |

## Line Number Semantics

`line` is **file-relative** - the same line number you see in the file and in the GitHub diff's line gutter. Line 64 in the file = `line: 64` in the API call.

pr-intel reports lines using **Line N** markers that reference file-relative line numbers.
These can be used directly with no translation.

**Constraint**: The line must be visible in the diff (added, deleted, or context lines within
a hunk). Lines outside diff hunks return: `422 Unprocessable Entity: "Line could not be resolved"`

## Event Type Mapping

| pr-intel Action | GitHub event |
|----------------|--------------|
| Request Changes | `REQUEST_CHANGES` |
| Comment | `COMMENT` |
| Approve | `APPROVE` |
| Approve with Comments | `APPROVE` |

## Review Lifecycle

- Submitted reviews are **permanent** - no delete, no dismiss for COMMENT reviews
- Only PENDING reviews (created without `event`) can be deleted
- This is why preview + confirm before posting is non-negotiable

## Error Codes

| Code | Message | Cause |
|------|---------|-------|
| 422 | "Line could not be resolved" | Line not in diff, or wrong side |
| 422 | "Validation Failed" | Missing required field or invalid event |
| 403 | Forbidden | Not a member or insufficient permissions |
