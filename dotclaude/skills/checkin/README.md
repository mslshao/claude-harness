# checkin

The worker's answer to a fleet registration check-in.

## The one command

```
/checkin
```

Add `--print` to see the five lines without sending them.

## What it does

Gathers five lines out of this session: the exact model id, whether ultracode
is on, the working directory and branch, which connectors resolve tools by
name, and what this session is holding. Sends exactly those five lines to
whoever sent the check-in. Then holds.

If Michael typed "check in" here rather than a peer sending one, there is no
address to reply to, so the five lines print in chat instead.

## Why it exists

A check-in answered in the session's own chat reaches nobody. Two fresh
workers did that on 2026-08-31 and looked unresponsive for forty minutes.
The reply has to be a message to the sender, and this makes that the default
rather than the thing to remember.

## What it never does

Send anything beyond the five lines. Start work; a check-in is not a
dispatch. Call a connector to test it, when the question was only whether its
tools resolve by name. Report a model this session did not read from its own
system prompt.

## The orchestrator side

The session sending the check-ins runs `/fleet up`, not this.
