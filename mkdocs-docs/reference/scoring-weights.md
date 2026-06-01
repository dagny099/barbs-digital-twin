---
title: Scoring Weights
tags:
  - reference
  - scoring
  - neo4j
---

# Scoring Weights

The composite scoring weights are the most consequential tunable parameters in the system. They live as named constants in `neo4j_utils.py` and determine which sections the LLM sees — and therefore what answers are generated.

!!! danger "Read before touching"
    These weights were rebalanced after a critical hallucination caused by oversized graph bonuses. See [Entry 001](../lessons-learned/entry-001.md) before making any changes. The incident includes before/after score comparisons and the reasoning behind the current values.

---

## Current Values

```python
# neo4j_utils.py
Wt_SEMANTIC    = 0.85   # dominant signal — do not reduce below ~0.80
BONUS_PROJECT  = 0.08   # graph bonus: linked to a Project node
BONUS_ENTITY   = 0.05   # graph bonus: entity mentions (capped at 5)
BONUS_LENGTH   = 0.02   # graph bonus: section > 2000 chars
```

---

## The Formula

```
final_score = (vector_similarity × Wt_SEMANTIC)
            + BONUS_PROJECT   # 0 or BONUS_PROJECT
            + BONUS_ENTITY    # 0 to BONUS_ENTITY (per-entity, capped at 5)
            + BONUS_LENGTH    # 0 or BONUS_LENGTH
```

| | Minimum | Maximum |
|---|---|---|
| **Vector component** | 0.00 (no similarity) | 0.85 (perfect match) |
| **Project bonus** | 0.00 | +0.08 |
| **Entity bonus** | 0.00 | +0.05 |
| **Length bonus** | 0.00 | +0.02 |
| **Total graph bonus** | 0.00 | **+0.15** |
| **Maximum possible score** | — | **1.00** |

---

## Design Constraints

### Vector similarity must dominate

`Wt_SEMANTIC = 0.85` — the vector component accounts for 85% of the maximum possible score. This is intentional. Vector similarity is earned by the chunk's actual content; graph bonuses are structural annotations. The semantic match should always be the primary signal.

**Do not reduce `Wt_SEMANTIC` below ~0.80.** Below 0.80, graph bonuses can begin to override the semantic leader for moderately-similar chunks.

### Graph bonuses must not reverse rankings

The total graph bonus (max +0.15) is small enough that a chunk with high vector similarity will never be displaced by a chunk with low vector similarity plus all graph bonuses:

- High-sim chunk: `0.90 × 0.85 = 0.765`
- Low-sim chunk with all bonuses: `0.65 × 0.85 + 0.15 = 0.703`

The high-similarity chunk still wins. This is the correct behavior.

### The tiebreaker case (intended)

For chunks with similar vector similarity, graph bonuses correctly promote the more contextually relevant one:

- Project-linked chunk: `0.80 × 0.85 + 0.08 = 0.760`
- Unlinked chunk: `0.80 × 0.85 = 0.680`

This is what graph signals are for — tiebreaking among semantically-similar candidates.

---

## History

| Period | `Wt_SEMANTIC` | `BONUS_PROJECT` | `BONUS_ENTITY` | `BONUS_LENGTH` | Outcome |
|---|---|---|---|---|---|
| Before 2026-05-17 | 0.60 | 0.25 | 0.10 | 0.05 | Critical hallucination — graph overrode semantic leader |
| **Current (2026-05-17+)** | **0.85** | **0.08** | **0.05** | **0.02** | Correct; graph serves as tiebreaker only |

---

## Before Changing Weights

1. Read [Entry 001](../lessons-learned/entry-001.md) — understand what went wrong and why
2. Run `replay_retrieval.py --compare` on a set of representative queries to understand the current ranking behavior
3. Make a small change (±0.02) and re-run the comparison
4. Run `evals/run_evals.py` before and after — look for regression in relationship-style queries AND biographical Q&A queries
5. Document the change in [Lessons Learned](../lessons-learned/index.md) if you find anything non-obvious

!!! tip "The safest test"
    After any weight change, run: `python replay_retrieval.py --query "How did you get into beekeeping?" --compare`

    The beekeeping answer bank chunk should rank #1 in Neo4j. If it doesn't, the graph bonuses are too large again.
