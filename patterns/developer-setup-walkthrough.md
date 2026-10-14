# The developer-setup walkthrough

A template for the one document a new engineer actually reads: how to get a workstation from nothing to a verified, working session against the team's infrastructure. The shape below is lifted from an internal platform team's "Developer Setup" page that the harness's author called, on 2026-09-04, "infinitely more valuable than anything we've produced so far". That page is the bar for every reader-facing document this harness writes, and the reasons it works are listed before the template so the template is not copied without them.

## Why it works

- **One sentence of purpose, then the work.** The page opens with what you will have at the end ("set up your workstation to authenticate to AWS and EKS") and nothing about why the platform exists, who decided what, or what is provisional.
- **Every section ends in a verify command.** Install, then `aws eks list-clusters`. Authenticate, then `kubectl get ns`. Deploy, then open the Swagger page. The reader never has to wonder whether a step took; the next command tells them.
- **Per-OS blocks, side by side, copy-paste ready.** Bash and PowerShell each get their own fenced block for the same step, with the package manager named and the "you already installed this another way" case handled in one line.
- **Exact strings.** Tool versions ("must be at least version 2"), environment variable names in code font, the exact error text a failing step prints, the exact command that fixes it. A reader greps for the error they see and lands on the answer.
- **The skip link.** A reader who has done part of it before is told where to jump ("If you already have a My Apps tile... skip down to").
- **Troubleshooting is organised by the tool that failed, keyed on the message it printed.** Not by symptom category, not by concept. Each entry is: the error, in code font; the cause, in one sentence; the fix, as a command.
- **Workarounds carry their reason.** "The previous command was X. However, that kept being blocked by the endpoint agent. The above steps should get around that issue." The reader learns why the odd step exists and can recognise the next occurrence.
- **Links go to the authority, not to a summary of it.** The vendor's install page, the internal access-request form, the wiki page that owns the account list. The walkthrough does not restate what those pages say.
- **Optional is labelled optional.** The end-to-end app deploy is a section a reader can stop before, and it says so in its heading.
- **No status, no provenance, no hedging.** Nothing on the page says who wrote it, what is ratified, or what might change. The page describes the system as it works. Where the author is unsure, the page still gives an instruction and a fallback, never a discussion.

What it does not do is also the point: it does not explain the architecture, argue for the choices, or list open questions. Those belong on other pages, linked once.

## The template

Replace every `<placeholder>`. Keep the section order; a reader who has used one walkthrough in this shape can use the next one without re-learning it. Delete a section only when there is nothing to put in it, and say so in one line rather than leaving a heading over nothing.

```markdown
The purpose of this guide is to set up your workstation to <the one outcome: authenticate to X and run Y>.

## Software installation

Skip down to the quick install for <OS A> or <OS B>.

At the end of this section the following tools are installed:

- <Tool> (<vendor install page>): <one-line purpose>. **Must be at least version <N>.**
- <Tool> (<link>): <purpose>.

*Note: <the one trap in installing these, if there is one>.*

### <OS A> (<shell>)

You need <package manager> (<link>) before running these.

1. Run:

```<shell>
# Install <tool list>
<package manager> install <tool>
<package manager> install <tool>
```

   Already installed some of these another way? <what to do about it, one line>.

### <OS B> (<shell>)

You need <package manager> (<link>) before running these.

1. <Any manual download step, with the link and where it goes on PATH.>
2. Run:

```<shell>
<package manager> install <tool>
```

3. <Any step that has to be done by hand, and why the obvious command does not work here.>

### <Security or compliance prerequisite, if production access needs one>

You must have <agent or client> installed to reach <environment>. Get it from <link>. <Who configures it> can be reached in <channel>. Questions about access policy go to <channel>.

## <Grant yourself the roles or permissions the environments need>

1. <Where to click, in the tool's own words.>
2. <Next click.>
3. <What you see now, so you know you are in the right place.>
4. Enter <the exact value> for <environment>. Repeat for <the other environments>, with the values:
   - <Environment>: `<value>`
   - <Environment>: `<value>`
5. <What confirms it worked: what the screen shows afterwards.>

Note: <the optional tool that makes this easier, with the link that shows its configuration>.

## Obtain credentials

If you already have <the tile or the token> and can sign in, skip to <the next section>.

1. Request <credentials or group membership> via <the form>, at <link>.
2. Sign in at <portal>. (<The one thing that trips people here, in parentheses.>)
3. Register <the second factor> at <link>.
4. Open <the tile or app>.

## Command-line authentication

1. Install <the auth tool> following <link>.
2. Generate the configuration files following <link>.
3. <Any helper that keeps you signed in, with the config block to paste and where it goes.>

```<format>
<the exact block>
```

4. Tokens last <N hours>, so sign in with:

```<shell>
<the exact login command>
```

   *Note: <the flag or setting that has to be unset for the login to work, and why>.*

5. Verify: list <a resource you can only see when authenticated>.

```<shell>
<the exact command> --profile=<profile>
```

6. Connect to <the cluster or environment>, replacing `<placeholder>` with the value from step 5.

```<shell>
<the exact command>
```

7. Verify: <the command whose output proves you are in>. You must be on <the network or VPN> for this to work.

```<shell>
<the exact command>
```

   If <the expected thing> is missing, <the exact remedy, with the link>.

You are set up against <the development environment>. <The next environments> are on <link>.

## Run <a sample app> in <the development environment> (optional)

1. Clone <the sample repository>. (<How to get the credential the clone needs, if any.>)
2. Set <the environment variable that selects the environment>.
3. <Any token the build needs and where to generate it.>
4. Build and deploy:

```<shell>
cd <dir>
<the run command>
```

5. Open <the URL or the UI path> and confirm <what you should see>. If it errors, see Troubleshooting below.

## Troubleshooting

### <Tool that fails>

- `<the exact error text>`: <the cause in one sentence>. Fix:

```<shell>
<the exact fix>
```

- `<the next exact error text>`: <cause>. Fix: <command or click path>.

### <Next tool>

- `<error>`: <cause>. Fix: <fix>.
```

## Writing notes

- Test the page by doing it: a fresh machine, or a colleague who has never done it, following only the page. Every place they stop is a defect in the page, not in the colleague.
- Keep the values that differ per environment in one list, once, and refer to it. The source page listed its account identifiers in two places and they disagreed on one of them, which is the failure this note exists to prevent.
- When a step has a workaround, keep the original command visible with the reason it was replaced, so the next person can tell whether the workaround still applies.
- A troubleshooting entry is only worth adding if it carries the exact error text. "If it fails, check your config" is not an entry.
- Nothing about the project's status, decisions, or open questions goes on this page. Link the page that carries them once, at the top or the foot, and stop.
