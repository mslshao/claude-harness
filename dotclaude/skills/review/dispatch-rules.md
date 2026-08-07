# Per-Agent Dispatch Rules

Full dispatch trigger, file-filter, skip-note, coordination, and advisory-contract
detail for each review agent. The SKILL.md step 4 keeps a compact dispatch table
and points here. Dispatch the triggered agents in a single parallel message.

- **`mx2-code-reviewer`** for structural design, naming, SOLID adherence,
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

- **`mx2-silent-failure-hunter`** for error propagation gaps: bare/broad
  excepts that swallow errors, log-and-continue where callers depend on
  success, fallback masking, boundary cases where Python errors become
  JSON responses TypeScript code silently drops.
  Dispatch when `has_error_handling_signal`. Filter: files containing
  try/except/raise patterns + frontend-backend boundary files.
  Skip note: "mx2-silent-failure-hunter: skipped (no error-handling signals)".

- **`mx2-security-auditor`** for PII/PHI exposure in logs and LLM data flows,
  audit trail field completeness on document operations, secret handling
  via SecretStr, error message sanitization.
  Dispatch when `has_security_signal`. Filter: auth/PII/audit/document
  files + any file touching `logger\.` or `SecretStr` patterns.
  Skip note: "mx2-security-auditor: skipped (no security-relevant signals)".

- **`mx2-devops-build-deploy`** for Terraform/HCL correctness: missing
  variable pass-through to child modules, duplicate HCL keys (silently
  keeps last value), missing environment configs, EventBridge subscription
  completeness, terragrunt dependency injection gaps.
  Dispatch when `has_terraform_files`. Filter: `*.tf`, `*.hcl`,
  `terragrunt.hcl` files + sibling environment directories.
  Skip note: "mx2-devops-build-deploy: skipped (no infra files in diff)".

- **`mx2-typescript-reviewer`** for type safety in TS apps, React/Next.js
  patterns, frontend-specific concerns (a11y, performance, bundle size),
  TS-specific error handling.
  Dispatch when `has_typescript_files`. Filter: TS files only (do not send
  Python diff to this agent).
  Coordination: when both `mx2-code-reviewer` and `mx2-typescript-reviewer`
  would fire on the same diff, send each only its language-relevant files.
  Skip note: "mx2-typescript-reviewer: skipped (no TS files in diff)".

- **`mx2-git-historian`** for regression-of-recent-fix detection
  (modified lines authored within 90 days in commits referencing Jira bug
  tickets) and flip-flop pattern detection (line ranges rewritten 3+ times
  in 60 days).
  Dispatch when `structural_risk_size` AND `has_file_history`. Filter:
  line ranges of changed files only (the agent runs `git log/blame/show`
  against the worktree itself).
  Skip note: "mx2-git-historian: skipped (PR small or no file history)".

- **`bot-review`** for cross-file consumer-invariant breakage. For each
  changed public symbol, identifies consumers via Grep and articulates the
  invariant each consumer assumes that the change weakens.
  Dispatch when `changes_public_surface`. Filter: changed public-symbol
  declarations only + full file path list (do not send full diff; the
  agent fetches consumers itself).
  Advisory-only: severity hard-capped at COMMENT/NOTE/SUGGESTION; never
  BLOCKING/CRITICAL. Findings appear in their own subsection of the
  output, not folded into the main severity buckets.
  Skip note: "bot-review: skipped (no public surface change)".

- **`mx2-skeptic`** for adversarial dissent: surfaces naive, dumb, or
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
  Skip note: "mx2-skeptic: skipped (XS/S diff)".

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

- **`mx2-pydantic-reviewer`** for configuration patterns: required fields
  with empty-string defaults (silent misbehavior), cross-service
  `AppSettings` imports (architecture violation), `os.environ` patterns
  that should be Settings fields, magic strings/numbers that belong in
  Settings, missing `default_factory` on dynamic values.
  Dispatch when `has_pydantic_settings_signal`. Filter: Settings/config
  files in the diff + sibling Settings files in the same service
  directory (to detect duplicate or conflicting field declarations).
  Skip note: "mx2-pydantic-reviewer: skipped (no Settings/config signals)".

- **`mx2-python-style`** for Google Python Style Guide + MX2 style
  overrides: 4-space indent, 108-char line length, modern type syntax
  (`X | None` not `Optional[X]`), logging conventions (percent-formatting,
  `extra` dict), import organization. Author Mode (pre-CI) only;
  duplicates CI signal otherwise.
  Dispatch when `has_python_files`. Filter: Python files only.
  Skip note: "mx2-python-style: skipped (no Python files in diff)".
  Note: this agent's findings overlap with what CI catches via pylint,
  yapf, isort, autoflake. The /review value is catching them BEFORE
  pushing to avoid the CI round-trip. If you are running /review
  post-CI for some reason, consider skipping this agent manually.
