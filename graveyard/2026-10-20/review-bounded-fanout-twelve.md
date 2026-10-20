# review-bounded-fanout-twelve

**What it was.** The "Bounded fan-out" bullet in `~/.claude/skills/review/SKILL.md` (Bounds section, lines 704 to 719 at hash 595190c7), in full:

```
- **Bounded fan-out.** Up to twelve review agents with conditional dispatch;
  the tenth is the advisory `records-reviewer`, which fires only on a
  the app diff that the records matcher ties to at least one active record and
  in which at least one changed path is not a Markdown file under `docs/`.
  The eleventh is the advisory `race-reviewer`, which fires on
  `has_write_path` or `has_payments_signal`. The twelfth is the advisory
  `payments-auditor`, which fires on `has_payments_signal`.
  Maximum six verdict-emitting specialists fire on a single diff (four of the
  five always-or-conditional agents from project /review, security-review
  included and the advisory module-cohesion-reviewer excluded,
  plus two personal-only conditional agents: typescript and git-historian).
  Three advisory-only agents fire conditionally and produce
  non-verdict output: `blast-radius-reviewer` (cross-file invariant questions, fires on
  public-surface changes), `skeptic` (adversarial questions, fires
  on M+ diffs), and `module-cohesion-reviewer` (cross-file cohesion and coupling
  questions, fires on Python-module changes).
```

**Why it went.** the user approved capping the fan-out on 2026-10-20 (audit item 2, line R8): a review agent costs 74,738 to 193,753 notification tokens whatever the diff size, and the old default ran every agent whose signal was true (11 on a PR).

**Superseded by.** Step 4a "Cap the set" in the same skill, and the shorter Bounds bullet: three agents by default, four on a payments diff, five over 200 lines or 5 files, all true-signal agents with `--full`. The per-agent trigger conditions survive in the step 4 table and `dispatch-rules.md`.

**Source: snapshot** `(local snapshot) skills/review/SKILL.md.txt`
