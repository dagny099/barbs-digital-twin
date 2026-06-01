---
title: "Entry 001 — Graph Signals & Hallucination"
tags:
  - lessons-learned
  - retrieval
  - scoring
  - hallucination
---

# Entry 001 — Graph-signal bonuses overrode vector similarity, causing hallucination

**Date:** 2026-05-17  
**Category:** Retrieval, LLM  
**Severity:** :octicons-alert-fill-24:{ .warning } **Critical** — factually wrong answer delivered to a live user

---

## What Happened

The Digital Twin was asked the curated example question: *"How did you get into beekeeping, and does it influence your work?"*

The response stated:

> "Beekeeping started as a curiosity-turned-hobby when I moved into a house with enough backyard space and a bit of a 'why not?' attitude."

**This is factually wrong.** There was no house move. A colony of bees moved into a bat box in the backyard of Barbara's *existing* home — an unexpected event that started the whole thing. The correct origin story was in the knowledge base.

---

## Root Cause

A two-layer failure:

### Layer 1 — Retrieval failure (the cause)

The Neo4j hybrid retrieval used this composite scoring formula at the time:

```python
# Before fix (graph signals too dominant):
final_score = vector_score × 0.60
            + 0.25  (if section linked to any Project node)
            + 0.10  (entity mention bonus, capped at 5 entities)
            + 0.05  (length bonus, > 2000 chars)
```

The graph-signal bonuses (max +0.40) were disproportionately large relative to the vector weight (0.60). The answer bank chunk containing the correct origin story had the **highest raw vector similarity of any public-tier chunk** (`vec=0.860`) — but zero project links and few entity mentions. Its composite score was only ~0.516.

Richly-connected long-form sections like the Career Narrative chapter (`vec=0.679`, all three graph bonuses = +0.40) scored 0.807 and landed in the top-5 instead. None of the top-5 retrieved chunks contained the beekeeping origin story.

The vector signal was effectively *overruled* by graph topology for a purely biographical question.

### Layer 2 — LLM confabulation (the amplifier)

With no factual context about how Barbara got into beekeeping, GPT-4.1 synthesized a plausible-sounding narrative ("moved into a house with backyard space") that matches common beekeeping origin stories but is not Barbara's story.

The system prompt's Section 8 factual accuracy instructions were not sufficient to prevent confabulation when the correct context was absent from retrieval.

!!! warning "What made this hard to catch"
    - The correct chunk **existed** and was correctly embedded (ChromaDB ranked it #1)
    - The retrieval *appeared* to be working (average similarity scores logged as `avg=0.784`)
    - The hallucinated answer sounded confident and plausible
    - Only comparing the response to the actual facts revealed the problem

---

## Fix Applied

**`neo4j_utils.py`** — rebalanced composite scoring weights:

```python
# After fix (vector similarity restored as primary signal):
Wt_SEMANTIC    = 0.85   # was 0.60
BONUS_PROJECT  = 0.08   # was 0.25
BONUS_ENTITY   = 0.05   # was 0.10
BONUS_LENGTH   = 0.02   # was 0.05
```

Graph signals still apply as tiebreakers (max +0.15) but can no longer override a clear vector similarity lead. With the new weights, the beekeeping answer bank chunk ranks #1 (final=0.781) rather than below 5th.

**`fetch_k`** was also increased from `k × 2` to `k × 4` as a secondary measure, giving the candidate pool more runway before reranking.

**`replay_retrieval.py`** (new tool) — built a debug script that replays any query against Neo4j, shows the exact context injected into the LLM, decomposes the composite score, and optionally compares Neo4j and ChromaDB rankings side-by-side:

```bash
python replay_retrieval.py --replay "beekeeping" --compare
python replay_retrieval.py --query "any question" --compare --full
```

---

## Lesson / Takeaway

!!! note "Graph-signal bonuses in GraphRAG are topology-dependent, not semantics-dependent."
    Sections that happen to be richly connected in the graph receive bonuses regardless of query relevance. For biographical or Q&A-style questions, this is actively harmful — those chunks are intentionally *not* project nodes, and their value is entirely in their semantic match, not their graph position.

**The design implication:** graph signals should serve as *tiebreakers*, not *determiners*. The vector similarity score is earned by a chunk's actual content. The graph signals are structural annotations. They should modulate a semantically-ranked list, not reverse it.

**A useful heuristic:** if any bonus can turn a lower-similarity result into the top result, the bonus is probably too large.

---

## Blog Post Angle

*"I built a knowledge graph to improve retrieval quality. Then the graph made retrieval worse."*

The irony is deep: the whole point of migrating to Neo4j was to add graph signals that would promote contextually relevant chunks. Instead, the graph topology *demoted* the most relevant chunk (the one explicitly written to answer the exact question) because it wasn't connected to a Project node.

This is a great example of how RAG evaluation needs to test specific factual claims, not just "does the response sound good?" The hallucinated answer was fluent and topically appropriate — it would have passed a vibe-check evaluation. Only comparing it to the actual facts revealed the problem.

The debugging workflow is also worth writing about: `replay_retrieval.py` makes the invisible visible. Before building it, a hallucination meant guessing what went wrong. After, it's a 30-second diagnosis.

---

## Supporting Data

| | Before fix | After fix |
|---|---|---|
| Beekeeping chunk rank (Neo4j) | Not in top-5 | **#1** (final=0.781) |
| Beekeeping chunk raw vector score | 0.860 (highest!) | 0.860 |
| Career Narrative composite score | 0.807 (was #1) | 0.727 (now #3) |
| Maximum graph bonus | +0.40 | +0.15 |
| Vector weight | 0.60 | **0.85** |

**Query log entry:** `ts: 2026-05-17T20:08:39.104424+00:00`  
Model: `openai/gpt-4.1` | Tier: public | k=5
