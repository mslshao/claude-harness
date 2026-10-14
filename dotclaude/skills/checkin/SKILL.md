---
name: checkin
description: >
  Answer a fleet registration check-in. Gathers the five lines the protocol
  asks for out of this session itself (model, ultracode, working directory
  and branch, which connectors resolve, and what this session is holding),
  sends exactly those five lines back to whoever sent the check-in, and then
  holds. Use when a cross-session message asks this session to register, or
  when Michael types "check in" or "register". With --print it prints the
  five lines in chat instead of sending them. Worker side; the orchestrator
  side is /fleet.
argument-hint: "[--print]"
allowed-tools: ["Bash", "Read", "Grep", "ListAgents", "SendMessage", "ToolSearch"]
---

# Checkin

After any compaction, before any other action, re-read your STATE.md and
your folder's RESULT and BLOCKER files, then list every open item, pending
checks included, in your next message. Never report nothing pending without
that re-read. STATE.md is `<dated folder>/<your name>/STATE.md` under your
newest dispatch's folder, and it carries any item still open from an earlier
dispatch. It holds the dispatch's name, what is done, what is open with each
pending check, and the files written with their hashes, in under 5,000
tokens. Rewrite it with the Write tool as the last write of every turn, so it
is the newest of the five files Claude Code re-reads after a compaction.

A registration check-in has one right answer: five lines, sent to the sender,
nothing else, then hold. Answering in this session's own chat instead is the
failure this skill exists to prevent. On 2026-08-31 two fresh workers did
that and looked unresponsive for forty minutes.

## Where the protocol lives

`~/.claude/rules/fleet-peer-protocol.md`, the section on a registration
check-in. It is the source for what the five lines are and what order they
go in. Read it rather than trusting the ordering below, which is a summary
for gathering, not the specification.

If that file is missing, say so and stop.

## Gathering the five lines

Each comes from this session, not from a guess and not from a peer.

**MODEL.** The exact model id from this session's system prompt. Not the id a
session name implies, and not the id another session reported. After a
restart, it is the newest "You are powered by" line in the context, since the
older system prompt stays in view (dev-18, 2026-10-09).

**ULTRACODE.** On or off, from the `/model` or `/effort` line in this
session's own context. A "this session only" setting does not survive a
restart, so after one it reads off unless a `/model` or `/effort` line came
after it.

**CWD and BRANCH.** `pwd` and `git branch --show-current 2>/dev/null || echo "not a git repository"`. A directory that
is not a git repository reports that, rather than reporting nothing.

**MCP.** Which connectors resolve tools by name: Notion, Slack, Zoom,
Microsoft 365, Atlassian, Linear. Read the answer off this session's deferred
tool list, which names every connector tool as `mcp__claude_ai_<Connector>__<tool>`.
Exactly one ToolSearch is allowed, `ToolSearch select:SendMessage`, and no
other: `SendMessage` is itself deferred and is the reply channel, and the
deferred list can be out of view until a tool is loaded, so run that one call,
read the connectors off the list in its reply, and search for nothing else
(Michael, 2026-10-02, "yes to check-in search", decision 3 of the 10-02
compound merge; dev-30, dev-31 and dev-33 each needed that one call on
2026-10-02). A connector with no tool name in that list reads as not
resolving. Name-only. Do not call any of them; a probe is a write risk and it
is not what was asked. Say where a connector is limited, the way Atlassian here
lists only its two authentication tools. History: until 2026-10-01 this step ran
one ToolSearch per connector (`+Notion`, `+Slack`, `+Zoom`, `+Microsoft`,
`+Atlassian`, `+Linear`; `+Microsoft_365` returns nothing), never combined,
because a combined query ranked every result as a Microsoft 365 tool
(2026-09-24). One check-in made six calls and loaded five schemas, and the
harness review counted 402 such calls in 75 sessions; from 2026-10-01 to
2026-10-02 the rule was no ToolSearch at all.

**STATE.** "no instructions yet", or the standing instruction this session is
holding. If this session was resumed after a crash or a restart, open the
line with the name it had before ("was dev-40 before the 10:36 reboot"). A
resumed session appears under a new name and ref with no continuity marker,
so this line is the only way the orchestrator can map yesterday's fleet onto
today's. On 2026-09-02 a peer read the orchestrator's rename as a death.
The line ends with `session <uuid>`, the full id of this session's
transcript, so that `context-read.py --session` resolves it on the first try
(`fleet-peer-protocol.md`, item 5, since decision 12 of the 10-06 merge).
Read the id from the environment block's Scratchpad directory line, where it
is the folder name just above `scratchpad`. Never take the newest transcript
in the project folder: at dev-24's check-in on 2026-10-07 that was another
session's. When `ListAgents` lists a peer under this session's own name, STATE
opens with "name shared with <name> [<its ref>]", and every later message this
session sends opens with its name and ref (dev-95: on 2026-10-10 two Haiku
seats both registered as dev-42).

## Sending

`SendMessage` to the check-in's sender by its bare name, the message's
`from-name`, copied from the message rather than typed; never the `uds:` path
in `from` (`fleet-peer-protocol.md`, Michael 2026-09-14: "Bare name in both
rule lines"). Five lines, in order, and nothing around them. No
greeting, no offer to start, no summary of this session's history.

Then hold. A check-in is not a dispatch and starts no work.

## When it is Michael asking

If the trigger was Michael typing "check in" or "register" in this window
rather than a peer's message, there is no `from-name`. Print the five
lines in chat instead of sending them. Same five lines, same order.

## --print

Gathers everything and prints the five lines without sending. Use it to see
what would go out, or to hand the lines to a person. It sends nothing, so a
check-in it was meant to answer is still unanswered afterwards; say so.

## What this never does

Send anything but the five lines. Start work off a check-in. Answer a peer
that said no reply was needed. Report a model or a connector it did not
read from this session. Reply in chat when a `from-name` exists.

## The report

```
MODEL: <exact id>
ULTRACODE: <on|off>
CWD and BRANCH: <path>, <branch or "not a git repository">
MCP: <connectors that resolve>; <connectors that are limited, and how>
STATE: <holding, or the standing instruction; prior name first if resumed>; session <uuid>
```

Sent as those five lines alone. In this session's own chat, one sentence
after sending: who it went to, and that this session is holding. That
sentence never restates the five lines; naming the model, ultracode, the
directory and the connectors again in one sentence reads as a chain and the
Stop hook blocks it.
