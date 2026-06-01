---
title: Retrieval & Scoring
tags:
  - architecture
  - scoring
  - neo4j
  - graphrag
---

# Retrieval & Scoring

The composite scoring formula is the most consequential piece of the system. It determines what the LLM sees — and therefore what answer Barbara's twin gives. This page explains how it works, why the weights are set the way they are, and what can go wrong.

---

## The Composite Formula

```python
final_score = (vector_similarity × Wt_SEMANTIC)
            + BONUS_PROJECT   # if section linked to a Project node
            + BONUS_ENTITY    # per entity mention (capped at 5)
            + BONUS_LENGTH    # if section > 2000 chars
```

### Current Weight Values

These constants live in `neo4j_utils.py` and are imported by `replay_retrieval.py` so the debug tool and production code always stay in sync:

```python
Wt_SEMANTIC    = 0.85   # dominant signal — do not reduce below ~0.80
BONUS_PROJECT  = 0.08   # graph bonus: linked to a Project node
BONUS_ENTITY   = 0.05   # graph bonus: entity mentions (capped at 5)
BONUS_LENGTH   = 0.02   # graph bonus: section > 2000 chars
```

**Maximum possible score**: 1.00 (perfect vector match + all three graph bonuses)  
**Maximum graph bonus**: +0.15  
**Vector similarity range**: 0.0 – 1.0

!!! warning "Handle with care"
    These weights were rebalanced after a critical hallucination caused by graph bonuses overriding a higher-similarity chunk. See [Entry 001 — Graph Signals & Hallucination](../lessons-learned/entry-001.md) for the full incident. Before changing any weight, read that entry.

---

## Why This Formula?

### Pure vector similarity has a structural blind spot

Vector similarity ranks chunks by how well they *sound like* the query — not by how *factually connected* they are to the topics the query raises. For project- and entity-related questions, this means a generic career overview chunk can outscore a specific project description if it uses more matching vocabulary.

### Graph signals close the gap — carefully

Sections linked to a Project node or mentioning relevant entities carry structural evidence of relevance that isn't captured by semantics alone. The bonuses act as tiebreakers among otherwise-similar candidates.

### The constraint: graph signals must not override semantic leaders

The original design used much larger bonuses (`BONUS_PROJECT = 0.25`, `BONUS_ENTITY = 0.10`). A section with a lower vector score but richer graph connections could outscore a section with a higher vector score and no connections. This caused a hallucination — see [Entry 001](../lessons-learned/entry-001.md).

The design principle: **if any bonus can turn a lower-similarity result into the top result, the bonus is probably too large.**

---

## Candidate Pool: fetch_k

Before scoring, Neo4j retrieves `fetch_k = k × 4` candidates using pure vector similarity. Composite scoring then reranks this pool down to the final top-k.

The wider candidate pool was introduced as part of the Entry 001 fix — it gives graph-signal tiebreaking more runway without changing the final top-k size.

```python
fetch_k = N_CHUNKS_RETRIEVE * 4   # default N_CHUNKS_RETRIEVE = 10 → fetch_k = 40
```

---

## Sensitivity Tier Gating

Before any scoring happens, ineligible sections are excluded at the query level:

```cypher
WHERE s.sensitivity_tier IN $allowed_tiers
```

This means `inner_circle` sections never enter the scoring pool for a `public`-tier query — they're not scored and demoted, they're not retrieved at all.

---

## ChromaDB Comparison

ChromaDB stores the same chunks as Neo4j but uses pure vector similarity only — no graph bonuses. This makes it useful for:

1. **A/B evaluation**: `replay_retrieval.py --compare` shows ranking drift between Neo4j and ChromaDB for any query — the fastest way to diagnose whether a graph signal is helping or hurting
2. **Fallback**: If Neo4j is unavailable, ChromaDB provides pure-vector retrieval with no code changes to `app.py`

For relationship-style queries (*"What projects use Neo4j?"*), Neo4j scores +34.3% better than ChromaDB baseline (from `evals/results/`). For biographical Q&A queries with rich, curated answer chunks, the difference is smaller — and graph bonuses can sometimes hurt.

---

## Debugging Scores

The `replay_retrieval.py` tool shows the exact context the LLM would receive for any query, with each chunk's composite score decomposed:

```bash
# Run a query and see the scores
python replay_retrieval.py --query "How did you get into beekeeping?"

# Compare Neo4j vs ChromaDB rankings side-by-side
python replay_retrieval.py --query "How did you get into beekeeping?" --compare

# Find a past query in query_log.jsonl and replay it
python replay_retrieval.py --replay "beekeeping" --compare

# Unlock personal-tier chunks
python replay_retrieval.py --query "..." --tier personal

# Show full chunk text (not truncated)
python replay_retrieval.py --query "..." --full
```

The `--compare` flag produces a ranking-drift table that immediately reveals when graph signals are promoting or demoting chunks relative to pure vector similarity.

See [Debug Tools](../developer-docs/debug-tools.md) for the full reference.
