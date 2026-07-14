# Provenance Classification

Top-level pr-intel phase. Dispatches the `provenance-classifier` agent to
classify each finding as `speed-amplified` (reviewer would have caught from
careful single-file diff reading) or `bot-surfaced` (verification path
required live-state checks, multi-page document synthesis, or cross-file
blast-radius analysis). Runs AFTER Synthesis, BEFORE Verification.

This phase exists because earlier attempts to embed the classifier dispatch
as a sub-step of synthesis.md were systematically skipped by the orchestrator
(confirmed via transcript inspection on 2026-05-21: zero Agent dispatches on
PR #9276 and #9146 R3 sessions despite synthesis.md step 5d instructing
otherwise). The attention-floor failure mode is fixed by promoting the
dispatch to a top-level SKILL.md phase with its own dedicated file.

## When This Phase Runs

- **default mode**: always, after Synthesis produces the finalized findings list
- **`--mine` mode**: always; classification still informs the briefing-context
  audit even when no comments will be posted
- **`--quick` mode**: skip entirely (the quick template has no Provenance line
  and no inline comments to classify)

**Zero-findings short-circuit.** When synthesis produced zero Draft Inline
Comments AND zero substantive Draft Review Summary findings (a clean Approve),
skip the agent dispatch and populate the header line directly as
`Speed-amplified: 0 | Bot-surfaced: 0`. The classifier on an empty list is a
guaranteed no-op, so the dispatch is pure overhead. This is the ONLY case the
dispatch may be skipped: any non-empty findings list still dispatches, regardless
of size or specialist outcome.

## Inputs

The agent receives a JSON array. One entry per surviving Draft Inline Comment
PLUS any substantive Draft Review Summary bullet that warrants tracking
(BLOCKING / DISCUSSION / MINOR severity items; skip pure-acknowledgment lines).
Each entry has:

- `finding_id`: stable identifier. Construct as `<specialist_source>:<file>:<line>`
  when no explicit ID exists. Must be unique within the array.
- `source`: specialist source if known. Valid values (canonical list):
  - `mx2-code-reviewer`, `mx2-security-auditor`, `test-quality-reviewer`,
    `mx2-devops-build-deploy`, `mx2-typescript-reviewer`, `mx2-silent-failure-hunter`,
    `observability-reviewer`, `mx2-pr-precedent`, `mx2-git-historian`, `bot-review`,
    `mx2-pydantic-reviewer`, `mx2-skeptic`, `module-cohesion-reviewer`
  - `AC Compliance Check`, `Spec Compliance Check`, `Design Doc Compliance`
  - `sonarcloud-pre-check`, `checkov`
  - `pre-synthesis-analysis-patterns`
  - `null` when the finding came from an inline pipeline step without a
    specialist dispatch and no source tag was set upstream
- `evidence`: VERIFIED / DIFF-VISIBLE / QUESTION (per grounding.md)
- `severity`: BLOCKING / DISCUSSION / MINOR
- `verification`: the verification path text the specialist produced
  (e.g., "Grep'd worktree for caller; read function at file:line").
  This is the canonical signal for classification when source is null.
- `draft_comment_text`: the rendered comment text (post-synthesis Step 5b
  compression and Step 5c hunk-edge pre-check) that will be posted

## Dispatch

Use a SINGLE Agent tool call with the full findings list as a JSON-encoded
input. Foreground dispatch (NOT `run_in_background: true`). The agent name
is `provenance-classifier`.

Example dispatch shape:

```
Agent(
  subagent_type="provenance-classifier",
  description="Classify pr-intel findings",
  prompt="Classify the following findings per your decision flow. Return a
  JSON array of classifications in the same order as the input.

  Findings:
  <JSON-encoded array as described above>"
)
```

The agent owns its classifier table (see `~/.claude/agents/provenance-classifier.md`).
Do NOT re-implement the table here; the agent is the canonical reference.

## Applying Classifications

The agent returns a JSON array of classification entries, one per input finding,
in the same order. Each entry has:

```
{
  finding_id: "<matches input>",
  classification: "speed-amplified" | "bot-surfaced",
  rationale: "<one sentence>",
  confidence: "high" | "low"
}
```

For each returned classification, apply to the corresponding finding's
metadata BEFORE rendering output:

1. **Briefing-context line**: set the `Classification:` token in each finding's
   `**Briefing context**` block per the output-formats.md template. If
   confidence is `low`, append `(low confidence)`.

2. **Review Recommendation header**: count `speed-amplified` and `bot-surfaced`
   entries across all classifications. Emit:

   ```
   **Provenance**: Speed-amplified: N (would have caught from diff reading) | Bot-surfaced: M (required live-state, multi-page docs, or cross-file analysis)
   ```

3. **Decision count line**: count cognitive decisions (inline comments + AC
   deviations + design surfaces + verifiability "Assumed" items). Emit:

   ```
   **Decision count**: N (ceiling: 5 per reviewer-discipline.md T6; if > 5, compression gate fires per synthesis.md step 11)
   ```

4. **Audit fields** (consumed by /post-review's bd memory write): record
   `bot_surfaced_count`, `speed_amplified_count`. The `bot_endorsement_count`
   field is populated by the Bot Reactions phase, not this one.

## Low-Confidence Handling

When the agent returns `confidence: low` on a classification, surface it in
the briefing-context line as `Classification: <value> (low confidence)`.
Michael's editing pass can manually flip these before /post-review consumes
the output.

Low confidence three or more times in a single run is a signal that the
upstream source-tagging is leaking findings without source fields. Record via:

```
bd remember --key="calibration:provenance-classifier:<topic>" "<one-line drift note>"
```

The right fix is upstream (set source explicitly when constructing the finding),
not in this agent's defaults.

## Source-Tagging Discipline Upstream

Inline pipeline steps that produce findings without a specialist dispatch
MUST set the finding's `source` field explicitly so the agent doesn't fall
back to text-heuristic alone. The canonical sources to set:

- SonarCloud Pre-Check findings (from `mcp__sonarqube__*`) → `source: sonarcloud-pre-check`
- Datadog Code Analysis Pre-Check findings (from `mcp__datadog__search_pr_insights`) → `source: datadog-code-analysis`
- Checkov findings → `source: checkov`
- AC Compliance Check deviations → `source: AC Compliance Check`
- Spec Compliance / Design Doc Compliance deviations → `source: Spec Compliance Check`
- Pre-Synthesis Analysis Patterns (Pydantic frozen, pre-existing pattern,
  error path reachability, opaque constants) → `source: pre-synthesis-analysis-patterns`

When the orchestrator constructs the findings list for this phase, set the
source field at construction time. Don't rely on the agent's text-heuristic
fallback (it works but is brittle on borderline phrasings).

## Recurrence Context

- `bd memories agent:provenance-classifier-2026-05-21`: agent's design rationale
- `bd memories calibration:pr-intel-provenance-rule-2026-05-21`: the original
  classifier work that landed (then was bypassed when buried in synthesis.md)
- `bd memories calibration:mx2-decision-maker:ideation:pr-intel-cross-cutting`:
  the /ideate gate that ESCALATE-ROUTE'd to instrumentation-first, leading to
  the transcript inspection that confirmed attention-layer skip
