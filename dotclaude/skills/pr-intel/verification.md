# Verification (size-gated)

After synthesis, before producing output, run a verification pass to catch false
positives. The depth scales with PR size:

| Size | Verification |
|------|-------------|
| XS, S | **None.** Return synthesis directly. |
| M | **Challenge only.** Extract assumptions from BLOCKING findings. Verify FRAGILE ones against code with Grep/Read. Correct or drop findings that fail verification. No specialist re-dispatch. |
| L | **Challenge + targeted consult.** Challenge all BLOCKING and DISCUSSION findings. For any FRAGILE assumption that survives challenge, dispatch 1-2 specialists (via Agent tool) to validate the specific claim. Correct findings, then re-synthesize. |
| XL+ | **Full loop.** Challenge all findings. Consult with all relevant specialists on corrected findings. Synthesize into final output. This is the same loop as manually invoking `/challenge` then `/consult` then `/synthesize`. |

## Verification Process

1. **Extract assumptions from each finding.** For each BLOCKING/DISCUSSION finding,
   identify the core factual claim (e.g., "exception X is not caught by handler Y").

2. **Verify against code.** Read the actual code in the PR worktree. Trace call
   chains, check exception hierarchies, verify that claimed behavior matches reality.
   Record what you searched and what you found.

   **Falsifiable library/framework claims.** When a specialist's finding rests on a
   claim about library or framework behavior that can be checked directly (e.g.,
   "mockito's `times(never)` is syntactically broken," "Pydantic v2 rejects field X,"
   "FastAPI swallows ValueError at the boundary"), run the verification: a one-line
   Python invocation in Bash, a Read of the library's installed source, or a doc
   check. Do NOT accept a confident specialist claim about library behavior as
   evidence; verify it. A specialist's reputation does not transfer to claims they
   could not actually test from their tool surface. This is the load-bearing case
   the falsifiable-claims rule in CLAUDE.md is written for.

   **Resolve inconclusive falsifiable claims locally; do not ship them as a confident
   verdict.** When the local check is inconclusive (behavior depends on framework version
   or wiring, the installed source is ambiguous, or the claim asserts repo-wide
   consistency such as "all callers migrated" or "field X is unused" that a worktree grep
   cannot fully settle), do NOT ship the claim in reviewer voice and do NOT silently drop
   it. For the cross-system column/field class, run the named Cross-System Investigation
   recipe (synthesis.md "Unverified-Assertion Containment + Cross-System Investigation"):
   resolve the expected mirror column via `simplify_sf_name` and grep a sibling query in
   an UNCHANGED file; the result drives the verdict. For the general class with no named
   recipe, surface an explicit UNVERIFIED-ASSERTION finding (honest uncertainty, verdict
   capped per mode) and attach the manual `@claude review once` (managed Code Review)
   escalation note. Canonical instance (2026-05-29, PR 9451): a confident specialist claim
   that "Starlette's default TestClient is a loopback client" drove a false "healthcheck
   any-client test gap"; the default host is the non-IP string "testclient". This is the
   general-class case (no named recipe), so it surfaces as an UNVERIFIED-ASSERTION rather
   than a confident gap. This verification pass is size-gated off for XS/S PRs; on those
   the same containment fires at synthesis time (synthesis.md rule 10 + the Cross-System
   Investigation trip-wire). 9451 was S-sized, so verification was skipped, which is
   exactly why the wrong claim would have shipped a confident verdict. The behavior is
   uniform across modes now (no bot-routing in any mode): surface the unverified claim as
   an UNVERIFIED-ASSERTION finding (or, in `--mine`, a pre-submission item to check).

3. **Adjudicate.** For each assumption:
   - **CONFIRMED**: Code evidence supports the claim. Keep the finding.
   - **INVALIDATED**: Code evidence contradicts the claim. Drop or correct the finding.
   - **PARTIALLY CORRECT**: Some aspects hold, others don't. Correct the finding to
     reflect only what's verified.

4. **Correct inline comments.** Update draft comment text to reflect verified claims
   only. Remove or rephrase any overclaims. A corrected finding is stronger than an
   overclaimed one.

5. **For L+ sizes: consult.** Dispatch specialists with the corrected findings and
   specific validation questions (e.g., "does any layer above this catch ValueError?").
   Specialists validate as parallel foreground calls (same rule as initial dispatch:
   no `run_in_background`). Incorporate their confirmations or corrections.

## Why This Matters

False positives on a PR review erode reviewer credibility. A BLOCKING comment that
the author can refute with "that's caught by line 125" damages trust in the review
process. The cost of one verification pass (30-90 seconds of tool calls) is far less
than the cost of a false positive on a security-critical PR.

The size gate exists because XS/S PRs have low surface area for false positives, while
L+ PRs have complex interactions where specialists are more likely to overclaim about
code they analyzed from diff hunks rather than full file context.
