# 2026-04-30: Salesforce insurance-company dedup algorithm

**Source**: ad-hoc chat with a teammate, 2026-04-30. Original retelling preserved in personal memory; scrubbed for public version.

**Context.** Users manually create Salesforce accounts and roles with no validation, producing duplicates (a common insurance company created multiple times, addresses as subsidiaries, etc.). A team was building a deduping middleware to fuzzy-match incoming records against the existing universe. Prior approach: a teammate plus PM had assembled curated lists of common insurance names and agencies; the resulting Levenshtein + token-matching code produced OK results with lots of one-off failures.

**What AI did.** The teammate pointed Claude at the existing DynamoDB table containing every insurance company the firm had ever worked with. Claude iterated over the dataset, dynamically tested different matching algorithms, identified failure modes for each, produced an algorithm that covered the existing data, and generated tests demonstrating the failure modes the prior approach missed. Reported wall-clock time: 10 to 15 minutes.

**Baseline.** A different teammate spent days to weeks on the same problem roughly a year prior, working from PM-curated lists rather than the full dataset.

**Verifiability.** The output is testable against the live DDB (50k+ entries). The remaining failure mode is an insurance company strikingly similar to existing entries but absent from the database; per the teammate, this is rare since the firm operates in every state.

**Honest read.** Supports "task-specific AI use given the full dataset can dramatically compress engineering time on pattern-matching problems." Does NOT support any claim about persona design, agent design, or the specific Claude workflow being optimal. The prior-baseline comparison is partly unfair counterfactual: a year ago, dumping 50k rows into a long-context model was not a workflow option; the comparison is partly tooling generation, not human vs AI.

## The core pattern: real data over descriptions

"Doesn't work as well with just a small info like what the PMs did. Took the whole database."

When Claude has access to the actual dataset (DDB table of insurance company names), it iterates exhaustively against real cases. When given only descriptions from PMs about what the data looks like, output is generic and miss-prone. The data IS the spec.

The decision rule that follows: identify the source of truth and give Claude direct access. Human descriptions are fallbacks, not primary inputs.

## Generalizable lesson

The next dedup problem on the same team's roadmap is medical facilities. Apply the same pattern: do not start from a curated list, get the full dataset. The pattern transfers to any deduplication / similarity / classification problem where ground truth data already exists.

## Sharper distillation: source-of-truth over curation

The PM's list isn't wrong; it's single-threaded. One human's curated mental model is necessarily a subset of the underlying data. Authoritative data stores (DDB tables, schemas, code, indexes) give Claude parallel coverage of every case, which is exactly what Claude is good at and humans are bad at.

## Caveat for citing this entry

Frame as "tools have improved" rather than "the original engineer was slow." The comparison is real but the original work was harder because the tools did not exist. Lead with the pattern; mention the time delta as evidence, not as judgment.
