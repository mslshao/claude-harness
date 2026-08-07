---
component: dotclaude/commands
type: directory-map
status: complete (2 commands, both covered; directory new to the mirror in V3)
authored_by: Claude Opus 5
---

# WORLDMAP: Personal Commands

AI-authored commentary on each personal-tier command in `~/.claude/commands/`. When I reach for the command, what failure mode it prevents, how it compounds, and where it has limits. Entries follow the format documented in the top-level `WORLDMAP.md`.

This directory is small and structurally different from `agents/` and `skills/`, which is the interesting thing about it. It contains no original commands. Both entries are personal-tier SHADOWS of commands that already exist at the project tier, carrying the same `name:` so the personal copy wins resolution, and each one exists only because the project version has a specific gap the author kept hitting. Where there is no delta, there is no personal command, which is why a project tier with many commands produces a personal overlay with two.

That makes this directory the clearest small illustration of the lab-to-production pattern running in the other direction. `project-tier/` shows personal artifacts promoted outward after they proved themselves; `commands/` shows the author's local overlay on artifacts the team already owns, held privately because the delta is a personal working habit rather than a team standard. Each entry's description opens by naming what it shadows and what the delta is, so the precedence is self-documenting at the point of retrieval rather than buried in a rules file.

Both deltas were also written in response to a specific incident rather than a preference, which is the bar an override has to clear to justify diverging from a team artifact at all.

---

```yaml
---
component: jira
type: command
status: active
shadows: project-tier `/jira`
trigger_signals:
  - "user wants a ticket filed from the current branch or a described change"
  - "user has a set of related tickets to file together (an epic's worth of work items)"
prevents:
  - "a hook blocking mid-batch after some tickets are already filed"
  - "banned prose (em-dashes) or personal-tier vocabulary reaching a stakeholder-facing ticket body"
  - "sibling blocks-links unfillable because the sibling did not exist at creation time"
related: [confluence, bead-forge]
---
```

When I reach for it: filing a ticket, and specifically when filing more than one. The single-ticket path is the project command's flow, mirrored. The reason the personal version exists is `\/jira batch <draft-path>`, which reads a YAML draft and files a related set in one pass.

What it prevents: two distinct failures, and the interesting one is the pre-flight. Every draft body is piped through a stakeholder-text check for em-dashes and personal-tier vocabulary (bead, `bd`, `docr-*` IDs) BEFORE the user sees it and before any MCP call. If any ticket in a batch fails, the whole batch stops and all failures surface at once. The batch mode also resolves symbolic IDs (`phase_1_id`) after all tickets are created, so a blocks-link can reference a sibling created in the same run.

How it compounds: the pre-flight is not redundant with the `block-em-dash` and `block-personal-tier-vocab` hooks, it is the same rule enforced at a cheaper point. That distinction is the whole design. For a single ticket a PreToolUse block costs one retry, so a last-resort guardrail is fine. For a batch it is the wrong place entirely: a block on ticket four leaves three already filed and the operation half-done, and the sanctioned re-run then collides with the tickets that already exist. Partial completion, not rejection, is the failure mode a batch introduces, so the guard has to move to draft time where the whole set can still fail cleanly.

Limits: the batch draft is a hand-authored YAML file with no schema validation, so a malformed draft fails at MCP-call time rather than at parse time. The symbolic-ID resolution only covers links between tickets in the same batch; linking to a ticket filed in an earlier run still needs the real key.

---

```yaml
---
component: confluence
type: command
status: active
shadows: project-tier `confluence`
trigger_signals:
  - "creating or updating a Confluence page, interactively or from an agent"
  - "any multi-edit session against a single page"
prevents:
  - "a push built on a stale fetch silently clobbering every edit made since that fetch"
  - "full-page --replace overwriting a page that moved during editing"
  - "a failed push reported as success because nothing verified the result"
related: [jira]
---
```

When I reach for it: any Confluence write. Unlike the jira override, this one is not about convenience. It is a correctness wrapper around an API shape that makes the dangerous operation the default.

What it prevents: `updateConfluencePage` is last-write-wins and takes NO expected-version parameter, so there is no way to express "write only if the page has not moved." A body prepared from a fetch taken minutes ago will happily overwrite everything that landed in between, and the call succeeds. The command re-implements optimistic concurrency in prose: record a baseline version at fetch time, re-fetch and compare immediately before EVERY push, and on a version change re-apply the intended edits onto the fresh body instead of pushing the stale one. Same-region conflicts stop and report rather than guess, and `--replace` against a moved page is always treated as a conflict because the whole page is the region.

How it compounds: three smaller rules close the gaps around the main gate. The baseline is per-push rather than per-session, so a multi-edit run cannot push from a body fetched before its own previous push. Every write carries a `versionMessage`, which turns page history into a usable audit trail instead of a wall of anonymous revisions. A post-push re-fetch confirms a distinctive anchor from the change is actually present, because a write that silently did not apply is otherwise indistinguishable from one that did.

Limits: the gate narrows the race window, it does not close it. Without an atomic compare-and-swap in the API, an edit landing between the re-fetch and the push still clobbers, and nothing here detects that. It is a mitigation sized to the realistic collision rate (human editors and a handful of agent sessions, not high-frequency concurrent writes), not a lock. The rule is also unenforceable by tooling: no hook can tell whether the body in an `updateConfluencePage` call was built on a fresh fetch or a stale one, so this command is prompt-tier discipline in a harness that otherwise prefers structural enforcement. That is a real weakness of this entry and the reason the incident it came from could recur.
