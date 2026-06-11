# 2026-06-04: A model-tier decision shipped as fact was a prediction; an eval converted it to evidence (own-loop)

**Source**: the author's own session, 2026-06-04. The work ran an empirical probe (bead docr-k0g4) against a model-tier decision that a prior 27-agent audit had recorded as settled. Scrubbed for public version.

**Context.** The harness assigns each of its specialist agents to a model tier (Haiku, Sonnet, or Opus) by a written gate:

- Haiku iff the agent does a bounded transform or extraction, its hard parts are pinned by deterministic contracts, blast radius is low, and there is no flag-vs-route or attribution judgment layer.
- Opus iff the agent does multi-source synthesis across conflicting inputs, or is a high-blast autonomous gate that ships or blocks unattended.
- Sonnet otherwise: bounded execution, or bounded single-domain review with calibrated severity and route judgment.

A corollary the gate states explicitly: a stronger model does not move an agent across tiers. Judgment-vs-mechanical and blast-radius are model-independent axes; a stronger model only makes the existing tier more reliable.

A 27-agent audit applied this gate and returned zero tier changes. For the two most mechanical-looking Sonnet agents (a provenance-classifier and a pydantic-settings reviewer), the audit kept them on Sonnet on the strength of a prediction: "Haiku would miscalibrate here." That prediction was never run. It was a confident-sounding line in an audit that otherwise read as settled.

**What AI did.** The discipline triggered on the gap between "shipped as a decision" and "rests on an untested prediction." Rather than leave the keep as an assertion, the session built a probe that could falsify it: run worry-case inputs (inputs designed to provoke the predicted failure) through Haiku-4.5 and Sonnet-4.6 side by side, then read where they diverge.

- *Provenance-classifier.* 6 worry-case inputs, 5/6 parity. The two models diverged on the safe-asymmetry default: an input with no source, no bot mention, and an empty verification field. Haiku returned the wrong class and was overconfident about it; Sonnet was contract-correct. The wrong class is not a cosmetic miss: it renders the finding in the author's own voice. Mislabeling provenance in that direction is exactly the trust-protection failure the agent exists to prevent, so Haiku's miss landed squarely in the agent's reason-to-exist.

- *Pydantic-settings reviewer.* 5 worry-case inputs, 4/5 parity. The divergence was on a real shipped diff: a required table-name settings field with no default. That is correct per the architecture rule "required fields have no default" (the field should fail fast at startup if missing). Haiku flagged it anyway, a false positive driven by a "bare-str-type" over-reach. Sonnet correctly left it alone.

**Baseline.** The human-only alternative here is not a different engineer; it is the same author leaving the audit's prediction unexamined. The audit had already shipped the decision. Absent the probe, the keep would have stood as fact ("Haiku would miscalibrate"), indistinguishable in the record from a tested conclusion. The alternative failure mode is subtler than getting the tier wrong: it is carrying a guess in the audit log dressed as evidence, where a later reader cannot tell prediction from measurement.

**Verifiability.** The probe is reproducible in shape: worry-case inputs, two named models, a contract to score against. The divergence on each agent is a concrete input-output pair (the no-source provenance default; the required-field-no-default diff), not a summary impression. The architecture rule the pydantic case turns on is written down ("required fields have no default"), so the false positive is checkable against a fixed standard rather than against taste.

**Honest read.**

1. *What this entry supports.* The verdict (keep both agents on Sonnet) is no longer speculation. A re-tier to Haiku was on the table and would have been cheaper; the probe could have ratified that downgrade. The evidence said no, and on the exact axis each agent exists to protect: provenance attribution and false-positive discipline. The narrow claim the evidence justifies is that on these selected worry-cases, Haiku diverged from the contract in the predicted direction and Sonnet did not. The harness discipline that mattered was converting an untested prediction into an eval that could falsify it, and keeping the tier only because the evidence agreed, not because the prior audit had asserted it.

2. *What this entry does NOT support.* The N is small (6 inputs and 5 inputs). The inputs were selected as worry-cases, deliberately built to probe the predicted failure, so the probe evidences the specific divergence, not Haiku's general quality; on broad inputs the two models hit parity most of the time, which the probe also showed. This says nothing about whether Haiku is "worse"; it says these two agents have a judgment edge that Haiku missed and Sonnet held. The corollary the gate leans on (a stronger model does not move tiers) is a design assumption the probe did not test: the probe compared two fixed tiers on fixed agents, it did not vary model strength within a tier to check the corollary's claim.

## Caveats specific to this entry

- *Selection bias.* This session is written up because the probe produced a clean divergence. A probe that returned 6/6 parity (ratifying the cheaper downgrade) would have been a different and arguably more interesting entry; the one that "saved" a tier is the one that gets remembered. The honest version is that the probe was worth running either way: parity would have justified a downgrade with evidence, divergence justified the keep with evidence. The value was the measurement, not the direction it happened to point.
- *Tooling-generation.* The baseline here is not a slower human with worse tools; it is the same author with the same tools choosing not to run the probe. The compression is not time, it is the conversion of a prediction into a falsifiable test. A reader should not infer any wall-clock or attempt-count savings from this entry; there are none to claim.
- *Sample-size.* N=1 at the session level, and small-N (6 and 5) at the input level. This is one decision, two agents, two models, a handful of hand-picked inputs. It supports "this one tier-keep was converted from guess to evidence," nothing broader about the gate's accuracy across the other 25 agents the audit also kept unchanged.

## The core pattern: a decision is only as settled as its weakest untested premise

An audit can return "zero changes" and read as fully settled while resting on a premise nobody ran. The provenance and pydantic keeps were correct, but until the probe they were correct by prediction, and a prediction in an audit log is indistinguishable from a measurement to the next reader. The discipline is to find the load-bearing untested premise and build the smallest eval that could falsify it. The keep survives only if the evidence agrees.

## Why this entry matters for the repo

Most of `evidence/` is shaped around AI doing a thing faster. This entry is a different shape, and a quieter one: the outcome did not change. Both agents stayed on Sonnet, exactly where the audit had put them. What changed is the epistemic status of that placement, from "we predict Haiku would miscalibrate" to "we ran it and Haiku miscalibrated on the axis that matters." The harness value is not a better answer; it is the refusal to let a prediction masquerade as a conclusion, even when the prediction turns out right.
