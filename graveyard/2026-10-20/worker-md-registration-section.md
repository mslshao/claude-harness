# worker.md, "On a registration check-in" (lines 64 to 93)

## What it was

The section as it stood on 2026-10-20, lines 64 to 93 of `fleet/worker.md`:

> ## On a registration check-in
>
> Record the five facts below as this session's own board entry with one command, and send no message
> (approved by the user, 2026-10-15; until then the reply was these five lines by SendMessage to the
> check-in's sender by its bare name, the user, 2026-09-14 10:09 PDT). Then stop (retest on the next
> model: Registration message without the rule: does the model add prose or send a message):
>
> ```
> fleet-log.py me idle --role worker --model <MODEL> --mode <on|off> --session <full uuid> --note "<CWD and BRANCH>; MCP <names>; STATE <state>"
> ```
>
> The note is at most 300 characters; the script refuses a longer one. Each fact goes in its field:
>
> 1. MODEL (`--model`): the exact model id from your system prompt.
> 2. ULTRACODE (`--mode`): on or off, from the `/model` line; a line that names ultracode in any
> wording (an effort level, a mode, a toggle) reads as on.
> 3. CWD and BRANCH (first in the note): `pwd` and `git branch --show-current`; a directory that is not
> a git repository reports that, not nothing.
> 4. MCP (second in the note): which of Notion, Slack, Zoom, Microsoft 365, Atlassian, Linear resolve
> tools by name (Atlassian here is authenticate-only). Name-only; no probes. Read the names off this
> session's deferred tool list. Exactly one ToolSearch is allowed, `ToolSearch select:SendMessage`,
> because the deferred list can be out of view until a tool is loaded; search for nothing else
> (the user, 2026-10-02, approved the one check-in search, decision 3 of the 10-02 compound merge).
> 5. STATE (last in the note): "no instructions yet", or the standing instruction you hold. If this
> session was resumed after a reboot or restart, open STATE with the name you had before, since
> `ListAgents` shows a resumed session under a new name and ref with no continuity marker. `--session`
> is the full id of this session's transcript, so `context-read.py --session` resolves it on the
> first try.
>
> Do not start work on a check-in.

## Why it went

the user approved the trim on 2026-10-20 (harness trim, item 7, W3). The same facts, the one ToolSearch and the same command are in the checkin skill, so every launched seat was loading them twice.

## Superseded by

`~/.claude/skills/checkin/SKILL.md` (its line 107 holds the command), reached by the core's "run `/checkin`" line. The retest mark moved to `fleet/worker-detail.md`.

**Source: snapshot** `(local snapshot) fleet/worker.md.txt`
