---
component: medical-legal-specialist
type: agent
status: deleted
source: recall
superseded_by: [mx2-security-auditor, per-domain context in CLAUDE.md]
---

# medical-legal-specialist

Early domain-specific agent. Existed during the harness's first months of use against a legal document processing codebase. The agent's prompt embedded the domain knowledge (HIPAA constraints, PII handling for medical records, audit trail requirements for legal documents) and was invoked any time the work touched medical or legal artifacts.

## What it did

The author recalls medical-legal-specialist as the agent invoked for any work touching:

- Document content (medical records, deposition transcripts, legal filings)
- PII fields (patient identifiers, attorney-client privileged content)
- Audit logging for compliance (HIPAA, SOC 2 reporting)
- Vendor handling for PHI-bearing data (BAA-covered LLM APIs, etc.)

## Why it was retired

The agent worked well for the cases it covered, but the boundary it drew between "medical-legal" concerns and "general security" concerns was wrong. Most of the agent's findings were generic security concerns (audit logging, PII masking, error message sanitization) that applied to any sensitive-data codebase, not just medical-legal. The domain-specific framing was making the agent's findings less reusable than they should have been.

The replacement pattern split the responsibilities:

- **Generic security concerns** → `mx2-security-auditor`: domain-agnostic agent for PII handling, audit trails, log discipline, vendor data flow. The agent embeds knowledge that medical-legal is one example domain among many; the principles (no log leakage, correct BAA coverage, error message sanitization) apply broadly.
- **Domain-specific context** → moved to CLAUDE.md and project rules. The codebase's specific domain (legal documents) and its specific compliance posture (BAA with vendors, SOC 2 reporting, HIPAA-adjacent rules) live in inline harness rules rather than in a single specialist agent. This means the context is loaded for ALL agents working in the codebase, not just one.

The split was correct because the domain-specific knowledge needed to be ambient (every agent benefits from knowing the codebase handles medical records) rather than gatekept to one specialist (the user has to remember to invoke the right agent to get the right care).

## Lessons captured

The retirement codified an early design principle: **specialist agents should embed reusable principles, not codebase-specific context**. Codebase-specific context belongs in the rules that every session loads, so it propagates to every agent's working knowledge.

The pattern shows up in the surviving agents: `mx2-security-auditor` is generic (its principles apply broadly), but the codebase-specific facts it draws on (which LLM vendors have BAAs, what the audit log format looks like, where PII fields live) come from rules and from context loaded at session start. The agent contributes the auditing discipline; the context contributes the project specifics.
