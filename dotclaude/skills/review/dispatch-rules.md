# Per-Agent Dispatch Rules

Full dispatch trigger, file-filter, skip-note, coordination, and advisory-contract
detail for each review agent. The SKILL.md step 4 keeps a compact dispatch table
and points here. Dispatch the triggered agents in a single parallel message.

- **`code-reviewer`** for structural design, naming, SOLID adherence,
  error handling strategy, code smells, project-rule compliance.
  **Always dispatch.** Filter: implementation files only (exclude tests,
  generated code, lockfiles).

- **`test-quality-reviewer`** for behavioral test coverage: the refactor
  test, mock saturation, no-assertion tests, name-vs-assertion drift,
  missing negative paths.
  Dispatch when `has_test_files`. Filter: test files + the source files
  they test (use Grep to map test_X.py to X.py).
  Skip note: "test-quality-reviewer: skipped (no test files in diff)".

- **`observability-reviewer`** for instrumentation gaps: exception class
  renames affecting Datadog Error Tracking monitor filters, error paths
  logged without paired metrics, ddtrace/OTel context propagation gaps
  across SNS/SQS/EventBridge boundaries, missing CloudWatch log retention,
  metric tag cardinality risks.
  Dispatch when `has_observability_signal`. Filter: files matching the
  observability sub-rules + sibling `*.tf` in the same service directory.
  Skip note: "observability-reviewer: skipped (no observability signals)".

- **`silent-failure-hunter`** for error propagation gaps: bare/broad
  excepts that swallow errors, log-and-continue where callers depend on
  success, fallback masking, boundary cases where Python errors become
  JSON responses TypeScript code silently drops.
  Dispatch when `has_error_handling_signal`. Filter: files containing
  try/except/raise patterns + frontend-backend boundary files.
  Skip note: "silent-failure-hunter: skipped (no error-handling signals)".

- **`security-review`** for PII/PHI exposure in logs and LLM data flows,
  audit trail field completeness on document operations, secret handling
  via SecretStr, error message sanitization.
  Dispatch when `has_security_signal`. Filter: auth/PII/audit/document
  files + any file touching `logger\.` or `SecretStr` patterns.
  Skip note: "security-review: skipped (no security-relevant signals)".

- **`typescript-reviewer`** for type safety in TS apps, React/Next.js
  patterns, frontend-specific concerns (a11y, performance, bundle size),
  TS-specific error handling.
  Dispatch when `has_typescript_files`. Filter: TS files only (do not send
  Python diff to this agent).
  Coordination: when both `code-reviewer` and `typescript-reviewer`
  would fire on the same diff, send each only its language-relevant files.
  Skip note: "typescript-reviewer: skipped (no TS files in diff)".

- **`git-historian`** for regression-of-recent-fix detection
  (modified lines authored within 90 days in commits referencing bug
  tickets) and flip-flop pattern detection (line ranges rewritten 3+ times
  in 60 days).
  Dispatch when `structural_risk_size` AND `has_file_history`. Filter:
  line ranges of changed files only (the agent runs `git log/blame/show`
  against the worktree itself).
  Skip note: "git-historian: skipped (PR small or no file history)".

- **`blast-radius-reviewer`** for cross-file consumer-invariant breakage. For each
  changed public symbol, identifies consumers via Grep and articulates the
  invariant each consumer assumes that the change weakens.
  Dispatch when `changes_public_surface`. Filter: changed public-symbol
  declarations only + full file path list (do not send full diff; the
  agent fetches consumers itself).
  Advisory-only: severity hard-capped at COMMENT/NOTE/SUGGESTION; never
  BLOCKING/CRITICAL. Findings appear in their own subsection of the
  output, not folded into the main severity buckets.
  Skip note: "blast-radius-reviewer: skipped (no public surface change)".

- **`skeptic`** for adversarial dissent: surfaces naive, dumb, or
  obvious-but-unasked questions about assumptions, scope, edge cases, and
  intent-vs-implementation drift. Designed as a safety net for fragmented
  attention; bigger diffs have more hiding spots.
  Dispatch when `structural_risk_size`. Filter: file path list + commit
  log + first 50 lines of each file's diff. The agent asks questions
  about intent; it does not need exhaustive code context.
  Advisory-only: severity vocabulary is QUESTION only; never emits
  verdicts. Findings appear in their own "Open questions" subsection of
  the output. Report every real question, ranked highest-blast-radius
  first (soft ceiling ~10); the synthesis pass filters, so a dropped
  question is lost rather than deferred.
  Skip note: "skeptic: skipped (XS/S diff)".

- **`module-cohesion-reviewer`** for cross-file cohesion and coupling: which
  concern owns a module, name-vs-contents drift, production vs test-only
  helper separation, a hand-rolled implementation duplicating a typed
  accessor a shared module already provides, cross-service reach-in past a
  published boundary, leaf-layer modules importing from a higher layer,
  behavior smuggled into a "pure move", and raw dicts where a typed model
  belongs.
  Dispatch when `has_python_module_change`. Filter: implementation `.py`
  files + the full changed-file list.
  **Reuse question (append to the prompt when `adds_capability` fires).**
  Pass the step-2a search results as evidence and ask the cross-service
  form of the question explicitly: "Does an existing endpoint, service, or
  shared-library symbol already own this capability? Answer with a
  `file:line` for the incumbent, or state that you searched and found
  none. Do NOT answer by proposing a cleaner local structure for the new
  code; extracting it into a tidier module is not an answer to whether it
  should exist." Without that last clause the agent reliably answers the
  module-local question instead (observed 2026-07-24, <service>
  `/metadata/refresh`).
  Advisory-only: severity capped at QUESTION/SUGGESTION/COMMENT, EXCEPT a
  finding naming an existing owner for a newly added capability, which
  promotes to Front Door (SKILL.md step 4 and step 6).
  Skip note: "module-cohesion-reviewer: skipped (no Python module changes)".
- **`race-reviewer`** for writes that land wrong when two actors interleave
  on one row, or when one actor retries: a missing basis, a condition
  narrower than the write, a retry that resends stale input or never stops.
  Dispatch when `has_write_path`. Filter: the range and the clone, and the
  spec's conflict lines for each aggregate the diff writes, quoted with
  their path and line. When no spec names a policy, say so in the prompt.
  Advisory-only: severity capped at QUESTION/SUGGESTION/COMMENT. Each
  finding gives its two-actor scenario and the smallest failing test.
  Skip note: "race-reviewer: skipped (no write path in the diff)".
