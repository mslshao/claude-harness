# Design Doc Hydration & Spec Compliance Check

When the PR body links a Confluence design page, hydrate it and compare the
implementation against the spec. This is the class of issue that code-only
review (including all specialist agents) cannot detect. The SKILL.md Data
Gathering section points here; runs in default and `--mine` modes, skipped
for `--quick`.

## Design Doc Hydration

After metadata is loaded, scan the PR body for Confluence links matching the pattern
`<company>.atlassian.net/wiki/` (URLs or Confluence short links). If found, extract the
page ID and fetch the page content AND comments **in parallel** with Jira hydration:

```
mcp__atlassian__getConfluencePage
  cloudId: <atlassian-cloud-id>
  pageId: <extracted page ID>
  contentFormat: markdown

mcp__atlassian__getConfluencePageInlineComments
  cloudId: <atlassian-cloud-id>
  pageId: <extracted page ID>
  contentFormat: markdown

mcp__atlassian__getConfluencePageFooterComments
  cloudId: <atlassian-cloud-id>
  pageId: <extracted page ID>
  contentFormat: markdown
```

Extract and store:
- **Design spec**: the page body (parameters, logic steps, response shapes, limitations)
- **Inline comments**: each with author, resolution status, and the text they annotate
- **Footer comments**: each with author and body
- **Unresolved comment count**: total open inline + footer comments from non-author users

**Page ID extraction**: Confluence URLs contain the page ID as a numeric path segment
(e.g., `.../pages/5799772177/...`). Short links (`/wiki/x/<encoded>`) can be passed
directly as `pageId` to the MCP.

If no Confluence link is found in the PR body, skip silently. If the MCP call fails,
note the failure and continue without design doc context.

**Downstream effects:**
- **Spec Compliance Check**: runs after design doc is loaded (see below)
- **Open Threads**: unresolved design doc comments surface as open threads in the output,
  separate from PR inline comment threads
- **Specialist preamble**: append design spec context so specialists can flag deviations

## Spec Compliance Check (when design doc is available)

When a Confluence design page was successfully hydrated, compare the PR's
implementation against the design spec. This complements AC Compliance (Jira)
with a deeper comparison against the full design document.

For each behavioral specification in the design doc:
1. **Trace it in the diff.** Can you identify the code that implements this spec?
2. **Check for deviations.** Common divergences:
   - Response shapes differ (field names, values, status codes)
   - Parameters differ (naming, optionality, semantics)
   - Routing or branching logic differs from described flow
   - Edge cases described in the spec are not handled (or handled differently)
3. **Surface unresolved design comments.** If the design page has open comments
   from reviewers (especially tech leads), these represent design-level feedback
   that may not have been addressed in the implementation. Flag them as open
   threads regardless of whether they map to code findings.

Deviations are not automatically bugs. The spec may have been updated after the
code, or the author may have intentionally diverged. The goal is to surface the
gap so the reviewer can ask "was this intentional?" This is the class of issue
that code-only review (including all specialist agents) cannot detect.

This check produces a **Design Doc Compliance** section in the output (see
output-formats.md). It runs in default and --mine modes. Skip for --quick.
