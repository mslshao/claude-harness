---
name: codility-review
description: Evaluate a Codility Legal Document Management API submission using the two-pass rubric (authorship authenticity gate + level calibration). Use when the user pastes a Codility submission, mentions reviewing a candidate with timeline + Cody transcript + code, or invokes /codility-review. Produces a per-row scored Pass 1 read, a level recommendation if Pass 1 cleared, and an optional draft recruiter reply.
---

# Codility Submission Review

Two-pass evaluator rubric for the Legal Document Management API assessment.

- Source rubric: https://<company>.atlassian.net/wiki/spaces/PPET/pages/5920882702
- Beads memory: `assessment-calibration`

## Inputs to gather

If the user did not paste these already, ask in one batched message before scoring:

1. **Target level**: L3, L4, L5, or "open / depends on outcome"
2. **Claimed skills**: Python / FastAPI / Pydantic ratings, or resume excerpt
3. **Codility timeline**: verify events with timestamps and result types (RUNTIME ERROR / WRONG ANSWER / OK)
4. **Cody chat transcript**: full chat log from the assessment
5. **Submitted code**: at minimum `solution.py`, `document_service.py`, `storage.py`

Run with whatever subset is provided; explicitly mark "n/a" for rows that cannot be evaluated and note the confidence cost.

## Pass 1: Authorship authenticity (gate)

Cite specific evidence per row: `file:line` for code signals, exact transcript quotes for Cody signals, resume excerpts for cross-references. Do not score a row without evidence.

### Code shape

| # | Signal | Weight |
|---|---|---|
| 1 | Defensive guards against impossible conditions (e.g., `result if result is not None else []` against typed `List[X]` return) | High |
| 2 | Helper extraction for trivial expressions (e.g., `_ckey(id)` returning `f"document:{id}"` used a few times) | High |
| 3 | Mapping/dict-of-sets where if-ladder fits the spec literally (most common in `_is_valid_status_transition`-shape functions) | High |
| 4 | Idiomatic library usage contradicting claimed skill level (`model_dump(exclude_unset=True)`, FastAPI `Query` validation, async correctly first try) | High |
| 5 | Polished idioms sitting alongside dead `# TODO` comments and deprecated APIs (`datetime.utcnow()`) | Medium |

### Cody transcript

| # | Signal | Weight |
|---|---|---|
| 6 | "Is X in my code?" / "Did I implement Y?" (one-shot tell, no innocent reading) | High |
| 7 | Repeated spec-summarization questions ("what is the problem about", "how many tasks", "is X mentioned") | Medium |
| 8 | No library API questions for libraries the candidate uses (FastAPI / Pydantic / async) | High |
| 9 | No pushback or verification of Cody answers anywhere in the transcript | Low |

### Resume cross-reference

| # | Signal | Weight |
|---|---|---|
| 10 | Libraries used in solution that are not claimed on resume AND not asked about in Cody | High |
| 11 | Skill self-rating mismatched against idiom density (e.g., "basic Python" + correct `model_dump(exclude_unset=True)`) | High |

### Timeline

| # | Signal | Weight |
|---|---|---|
| 12 | More than 2 RUNTIME ERROR verifies before first WRONG ANSWER or OK | Medium |
| 13 | More than 3 verifies needed to clear Milestone 1 | Medium |

### Pass 1 decision

Tally high-weight reds and medium-weight reds.

| High reds | Medium reds | Decision |
|---|---|---|
| 0 | any | Authentic. Proceed to Pass 2. |
| 1 | 0-1 | Authentic. Proceed to Pass 2. |
| 1 | 2+ | Inconclusive. Recommend second-engineer review. |
| 2 | any | Inconclusive. Recommend second-engineer review. |
| 3+ | any | Pass on candidate. Do not advance. |

(Rows are disjoint and exhaustive; exactly one row matches any tally.)

If Pass 1 fails or is inconclusive, draft the recruiter reply without naming the AI-paste theory directly. Frame as "the code shape and Cody transcript don't match the seniority signal we'd expect at this level" and recommend either passing or pulling in a second engineer for review.

## Pass 2: Level calibration

Run only if Pass 1 cleared. Each row votes L3 / L4 / L5. Median across rows is the recommended level.

| Signal | L3 | L4 | L5 |
|---|---|---|---|
| Dead `# TODO` comments and deprecated APIs in submitted code | Many | Some | None |
| Verifies to clear M1 | 4+ | 2-3 | 1 |
| Cody spec-comprehension questions | Many | Some | None |
| Cody questions about trade-offs vs definitions | None | Few | Most |
| Defensive coding density (against possible-but-unlikely conditions) | Present | Some | Minimal |
| Separation of concerns (storage dumb, service owns business logic, endpoints handle HTTP) | Mixed | Mostly correct | Clean |
| Typed exception hierarchy (custom exceptions like `InvalidStatusTransition` mapped at the endpoint) | Generic exceptions | Mixed | Custom hierarchy present |

Calibration:

- Median below target level: recommend pass or downlevel offer.
- Median matches or exceeds target: recommend advance.
- Two or more rows vote two levels above the median: mark as inconclusive, ask for second-engineer review.
- Separation of concerns at L5 is non-negotiable; verify count at L5 is a soft signal.

## Output structure

1. Pass 1 score table with cited evidence per row + tally
2. Pass 1 decision
3. Pass 2 score table (only if Pass 1 cleared) with cited evidence per row
4. Pass 2 level recommendation
5. Final recommendation against target level (screening signal ONLY: informs the go/no-go to interview; it must NOT anchor an actual leveling or debrief decision, which requires behavioral + live code-review + judgment evidence per `bd memories correction:workflow:codility-not-primary-signal`)
6. Optional: draft Slack reply for recruiter (plain text, no markdown bullets per Slack convention, 1-3 sentences, name-first or they-first if referring to the candidate)

## Calibration anchor: Noyal Binu (Apr 2026)

Reference benchmark for Pass 1 fail. The submission scored eight high-weight reds:

1. Row 1: `result if result is not None else []` defensive guard against typed `List[Document]` return
2. Row 2: `_ckey(doc_id)` helper extracting `f"document:{doc_id}"`, used 4 times
3. Row 3: Dict-of-sets in `_is_valid_status_transition` for a 3-bullet spec (when an if-ladder matches the docstring literally)
4. Row 4: `model_dump(exclude_unset=True)` first-try usage with no Pydantic claim and no Cody Pydantic questions
5. Row 6: "In my answer is filter present?" Cody question
6. Row 8: No library API questions for Pydantic, FastAPI, or async, all of which are used in the solution
7. Row 10: Pydantic used correctly but not claimed on resume AND not asked about in Cody
8. Row 11: Claimed "very limited Python" mismatched against idiom density (model_dump, dict-of-sets, async endpoints)

The four library-skill-mismatch rows (4, 8, 10, 11) are designed to fire together when a candidate uses a library at a level inconsistent with their claimed skill. This is intentional amplification: a single library mismatch examined from four angles produces stronger joint-distribution evidence than any single row alone. The marginal review pattern (each row explained away in isolation) is what the original Noyal review fell into; the rubric prevents that by counting each angle.

If a new submission scores 2-5 high reds, compare row-by-row against this list before deciding inconclusive vs reject. If the pattern matches Noyal's shape (defensive impossible-condition guards + LLM-style helper extraction + multiple library-skill mismatch rows on the same library), lean toward reject.

## Non-goals

- Not a substitute for the live interview, which still measures problem decomposition, communication, coachability, and system design
- Does not catch manually-edited LLM output that has had author tells removed (rewrite dict-of-sets to if-ladder, inline helpers, sprinkle small mistakes); future assessment design changes raise the cost of that strategy
- Specific to the Legal Document Management API task; other Codility tasks need their own anchor cases
