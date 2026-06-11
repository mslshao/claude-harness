# Consult Report Format

## Report Template

```
## Consult: <brief description of what was analyzed>

### Summary
**Specialists consulted**: <list>
**Overall assessment**: <one sentence>

### Findings

| # | Finding | Severity | Sources | Status |
|---|---------|----------|---------|--------|
| 1 | [statement] | CRITICAL | [which specialists] | Confirmed / Contradicted / Gap |
| 2 | [statement] | WARNING | [which specialists] | Confirmed / Contradicted / Gap |

Detail on CRITICAL and WARNING findings (skip SUGGESTION unless asked):

🚨 CRITICAL: [Issue] (`file.py:line`)
[What's wrong, who flagged it, what to do]
Flagged by: mx2-security-auditor, mx2-code-reviewer

⚠️ WARNING: [Issue] (`file.py:line`)
[Description]
Flagged by: mx2-code-reviewer

💡 SUGGESTION: [Issue] (`file.py:line`)
[Description]

### Contradictions
[Where specialists disagreed. State both positions with attribution.
Use decision record format below for significant trade-offs.]

### Open Decisions
[Decisions surfaced but not resolved. State the decision needed and
what information would resolve it.]

### Deferred
[Issues triaged as low-priority, with reasoning]
```

## Decision Record Format

Use this when specialists disagree on a significant trade-off:

```
## Decision: [Title]
Context: [What prompted this]
Decision: [What and why]
Trade-offs: [What downsides were accepted]
Revisit when: [Conditions that invalidate this decision]
Sources: [Which specialists contributed to each section]
```
