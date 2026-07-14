# Roster Differentiation

This section documents which agents are personal-only vs project-shared, to
inform future promotion decisions (see CLAUDE.md "Lab-to-production for
personal/project artifact pairs").

| Agent | Personal | Project | Notes |
|-------|----------|---------|-------|
| `mx2-code-reviewer` | yes | (project has `code-reviewer`) | Personal variant has skill-catalog awareness and write-capable tools per CLAUDE.md "lab-to-production" intentional divergence. |
| `test-quality-reviewer` | yes | yes (name-overlap) | Personal takes precedence via name-overlap convention. |
| `observability-reviewer` | yes | yes (name-overlap) | Personal takes precedence. Both promoted via PR #8970. |
| `mx2-silent-failure-hunter` | yes | (project has `silent-failure-hunter`) | Personal variant exists at `mx2-silent-failure-hunter`; project version landed via PR #8971 as `silent-failure-hunter` (unprefixed). |
| `mx2-security-auditor` | yes | yes (name-overlap) | Personal takes precedence via name-overlap convention. Project /review dispatches `mx2-security-auditor`; PII/PHI exposure focus on legal-domain. |
| `mx2-devops-build-deploy` | yes | no | Personal-only. Terraform/HCL specialist. Promotion candidate. |
| `mx2-typescript-reviewer` | yes | no | Personal-only. TS app specialist. Promotion candidate. |
| `mx2-git-historian` | yes | no | Personal-only. Regression-of-recent-fix detector. Higher promotion bar (false-positive sensitivity). |
| `bot-review` | yes | no | Personal-only. Cross-file blast-radius. Advisory severity contract. Promotion candidate, but advisory model needs project-tier consensus first. |
| `mx2-skeptic` | yes | yes (name-overlap; promoted via PR #9322, 2026-05-23) | Personal takes precedence via name-overlap. Adversarial dissent (QUESTION severity only). Designed as safety net for multi-window fragmented attention. |
| `module-cohesion-reviewer` | yes | yes (name-overlap; project version from MX2-NNNNN) | Personal takes precedence via name-overlap. Cross-file cohesion and coupling lens; advisory (author-facing questions, QUESTION/SUGGESTION/COMMENT). Reverse of the usual promotion direction: born project-tier, personal shadow added so its seam can defer to the personal roster by name; the project version merged 2026-07-01. |
| `mx2-pydantic-reviewer` | yes | no | Personal-only. Pydantic Settings + configuration patterns specialist. Codebase-general; promotion candidate after soak. |
| `mx2-python-style` | yes | no | Personal-only. Style enforcement (Google Python + MX2 overrides). Promotion bar is HIGH: most findings duplicate CI signal (pylint, yapf, isort, autoflake). Worth keeping at personal tier for pre-CI catch but promoting risks redundant noise. |
| `mx2-pr-precedent` | yes | no | NOT in /review (queries `gh` API, violates local-only). Used only in /pr-intel. |

Promotion criteria (informal): an agent is a candidate when (a) it has run
without false-positive churn for 30+ days at personal tier, (b) its scope is
codebase-general not michael-specific, and (c) its severity contract is clear
enough that a less-tuned operator can act on findings without context. Track
candidates via beads `docr-*` series.
