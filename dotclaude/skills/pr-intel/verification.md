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
