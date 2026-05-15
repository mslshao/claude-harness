---
component: .claude/rules/best-practices.md (project tier)
type: rule
status: deleted
source: git log (PR #8170, <jira-ticket>)
superseded_by: separate scoped rules (tenets.md, code-style.md, debugging.md, verification.md)
---

# best-practices.md (project tier)

A single project-tier rule file that captured general best-practice guidance for the codebase. Removed when the rules directory was restructured into scoped rule files.

## What it did

Single file at `.claude/rules/best-practices.md` that bundled multiple concerns: code style, testing conventions, verification discipline, debugging approach, security considerations. The file grew to several hundred lines as new principles were added.

## Why it was retired

The single-file approach failed for two reasons:

1. **No scoping.** A "best practices" file contains all principles; the model loads all of them for every task, even when most are irrelevant. A debugging task gets style guidance loaded. A style review gets debugging principles loaded. The signal-to-noise dropped as the file grew.

2. **No specialization.** A monolithic best-practices file cannot be path-scoped (Python rules vs TypeScript rules vs legacy paths). The restructure introduced path scoping: certain rules load only for `src/python/**`, others only for `src/typescript/**`, others only for `app/**` and `libs/**` (legacy paths). The path-scoped loading is what makes the rules useful at scale.

## Replacement structure

The single file was split into scoped rules:

- `tenets.md`: the highest-level meta-rules (best practice over precedent, review in isolation, verify before asserting)
- `code-style.md`: Python style enforcement (path-scoped to `src/python/**`)
- `python-testing.md`: testing conventions for Python (same path scope)
- `debugging.md`: debugging discipline (global)
- `verification.md`: verification gate before claiming work complete (global)
- `architecture.md`: SOLID, data store selection, error handling (global)
- `security.md`: PII handling, audit logging (global)
- `code-review.md`: code review process (path-scoped to Python)
- `typescript-exploration.md`: TypeScript guidance (path-scoped to TS)
- `legacy-paths.md`: rules for `/app` and `/libs` legacy directories (path-scoped)
- `build-commands.md`: lint, test, build invocations (global)

## Lessons captured

The split codified a project-tier rule design principle: **scoping by path or domain produces better-targeted rule loading than a single bundled file**. The model loads only what is relevant; signal stays high; new rules can be added to existing files without bloating the whole rule set.

The retirement is a project-tier example of the Keymaker principle. The single file had served its purpose (capturing the initial rule set during early codebase scaffolding) and was superseded by a more specific structure; deletion was the correct move once the replacement was in place.
