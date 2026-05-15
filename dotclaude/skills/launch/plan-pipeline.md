# Plan Pipeline Protocol

Phases 2-3 of `/launch`. Takes the implementation brief from Phase 1 and produces
a converged, stress-tested plan with a parallelization strategy.

## Phase 2: Initial Plan (Internal)

Feed the implementation brief into the converge pipeline as internal processing.
This mirrors `/converge` phases 1-4 but uses the enriched brief (not a rough idea)
as the seed.

### 2.1: Refine

Expand the brief with:
- Current git state (`git status`, `git log --oneline -5`)
- Active beads (`bd list --status=in_progress`)
- Codebase patterns (grep for similar implementations in `src/python/mx2/`)

### 2.2: Decompose

Identify natural seams in the work:
- **By layer**: infra (HCL/Terraform), scaffolding (BUILD files, __init__.py),
  implementation (models, services, handlers), tests
- **By domain**: if the ticket spans services, each service boundary is a seam
- **By dependency**: work that must happen before other work starts

For each seam, draft a work item with:
- Title (imperative, scoped)
- Description (what and why)
- Acceptance criteria (observable, verifiable outcomes)
- Design notes (patterns to follow, codebase references)
- Agent assignment (implementer, tester, or flex-{role})
- Phase assignment (A, B, C based on dependencies)

### 2.3: Pipeline Reuse Gate

**Before designing any new code path**, check:
1. Does the existing pipeline already handle this? Search for similar handlers,
   processors, or services in `src/python/mx2/`.
2. What happens if we send one message through the normal path?
3. Would a small modification to an existing path be cheaper than a new one?

New paths mean new bugs and new contracts. The existing path is tested. If reuse
works, the plan should leverage it.

### 2.4: Preliminary Agent Roster

Based on the decomposition, draft the agent roster:

| Agent | Role | Phase | Input |
|-------|------|-------|-------|
| implementer | Core implementation | B | Work items for src/python/mx2/ |
| tester | Tests | C | Work items for tests/, implementer output |
| flex-infra | Infrastructure | A | Work items for infra/, app/ |

The roster is preliminary - Phase 3 may modify it.

## Phase 3: Stress Test (Parallel)

Launch challenge and consult as parallel subagents via the Agent tool.

**CRITICAL: Single message, both agents. Do not serialize.**

### 3a: Challenge

Subagent prompt:
```
Apply the challenge embed protocol to this implementation plan.
Target 3-7 assumptions. Focus on:

1. "Does the approach account for existing patterns in the codebase?"
   Verify by reading the target modules.
2. "Are the acceptance criteria verifiable without running CI?"
   Each criterion should be checkable with a specific command or file read.
3. "Does the agent team structure match the ticket scope?"
   Over-staffing wastes context. Under-staffing creates phase bottlenecks.
4. "Are the phase gates specific enough for programmatic verification?"
   A gate like "implementation complete" is too vague. "All public functions
   in document_processor.py have implementations (no pass/NotImplementedError)"
   is verifiable.

Search bd memories for domain-specific gotchas relevant to this plan.
Read source files to verify codebase assumptions.

[Full draft plan here]
```

### 3b: Consult

Subagent prompt:
```
Act as tech lead coordinator. Review this implementation plan and dispatch
relevant specialists:

- If the plan touches error handling: mx2-silent-failure-hunter
- If the plan touches config/settings: mx2-pydantic-reviewer
- If the plan touches PII/auth/documents: mx2-security-auditor
- If the plan involves infrastructure: mx2-devops-build-deploy
- For structural review of the decomposition: mx2-code-reviewer

Focus on design-level concerns, not implementation details. The plan hasn't
been built yet. Key question for every specialist: "Does the existing pipeline
already provide this behavior?"

Synthesize findings into: Fix now / Fix next / Defer / Won't fix.

[Full draft plan here]
```

### 3c: Synthesize

When both subagents return:

1. **Merge findings**: deduplicate, connect themes, resolve contradictions
2. **Apply to plan**: revise work items based on findings
   - INVALIDATED assumptions: remove or revise affected items
   - "Fix now" concerns: incorporate into work items or acceptance criteria
   - Gaps: add items or criteria
3. **Finalize parallelization strategy**: the stress test may have changed
   dependencies, added work items, or shifted agent assignments

## Parallelization Strategy Output

The Phase 3 output MUST include this structure (passed to Phase 4 for the
approval artifact):

```yaml
agents:
  - name: implementer
    template: launch-implementer
    phase: B
    input: [work item IDs]
    specialists: [mx2-code-reviewer, mx2-silent-failure-hunter]
  - name: tester
    template: launch-tester
    phase: C
    input: [work item IDs, depends on implementer output]
    specialists: [test-quality-reviewer]
  - name: flex-infra
    template: launch-flex
    role: "Infrastructure Engineer"
    phase: A
    input: [work item IDs]
    specialists: [mx2-devops-build-deploy]

phases:
  A:
    agents: [flex-infra]
    gate:
      criteria:
        - "All .hcl files in infra/<service>/ parse without error"
        - "Module paths referenced in terragrunt.hcl exist"
      verification: "Run: terragrunt hcl-validate in worktree"
  B:
    agents: [implementer]
    depends_on: A
    gate:
      criteria:
        - "All public functions have implementations (no pass/NotImplementedError)"
        - "pants check src/python/mx2/<module> passes"
      verification: "Run: pants check <targets> in worktree"
  C:
    agents: [tester]
    depends_on: B
    gate:
      criteria:
        - "All test files import and reference the target module"
        - "pants test <test-targets> passes"
      verification: "Run: pants test <targets> in worktree"

commits:
  strategy: "single | behavior-gated"
  gates: ["description of each commit boundary, if behavior-gated"]
```

This structure is used by the orchestrator in Phase 5 to spawn agents, verify
gates, and manage phasing. Vague criteria ("tests are written") are rejected
during challenge (3a) - every gate must be programmatically verifiable.
