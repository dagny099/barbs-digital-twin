---
title: "Entry 003 — NEXT_SECTION Neighbor Expansion"
tags:
  - lessons-learned
  - retrieval
  - neo4j
  - graphrag
---

# Entry 003 — Latent graph value: NEXT_SECTION was there all along

**Date:** 2026-06-02  
**Category:** Retrieval  
**Severity:** :octicons-info-16: **Enhancement** — no failure; addresses structural gap in context coherence

---

## What Happened

Timeline-sensitive queries — *"What was your role at UT Austin after MIT?"*, *"What research did you do at MIT after your PhD?"* — returned weaker answers than expected from the Neo4j backend. The correct sections were being retrieved (scoring was working), but the LLM lacked the continuation text needed to answer sequential or temporal questions coherently.

---

## Root Cause

Section boundaries often split a narrative mid-story. The top-k retrieval returned isolated anchors without their continuations. The LLM was being asked to reconstruct a timeline from fragments, with no visibility into what came next in the document structure.

The graph already contained `NEXT_SECTION` relationships (built by `populate_neo4j_graph.py` on every ingestion run), but `_HYBRID_CYPHER` in `neo4j_utils.py` never used them. The infrastructure was there; the query just didn't ask for it.

---

## Fix Applied

Added `OPTIONAL MATCH (section)-[:NEXT_SECTION]->(neighbor:Section)` after the `LIMIT $k` clause in `_HYBRID_CYPHER`, with `WHERE neighbor.sensitivity IN $allowed_tiers` for tier filtering. In `query_neo4j_rag()`, neighbor text is appended inline after the anchor under a `[continued: source — section_name]` label. Neighbors already present in the top-k set are deduplicated by section name.

`replay_retrieval.py` was updated to mirror the same Cypher change and displays neighbors with a `↓ continued:` label.

---

## Lesson / Takeaway

!!! tip "Retrieve enough context that the answer doesn't require inference"
    Section-level chunking helps. Neighbor expansion helps further. For a portfolio chatbot where narrative coherence matters — career timelines, project stories, research arcs — the continuation of a section is often as important as the section itself.

    **The broader principle**: before tuning scoring weights, check whether the right content is even *reachable* by the retrieval query. The `NEXT_SECTION` relationship existed silently for weeks. Adding it to the query was a one-clause change with zero risk.

---

## Blog Post Angle

*"The graph had the answer the whole time — we just weren't asking for it."*

`NEXT_SECTION` relationships were built into the graph from day one, on every ingestion run. The scoring formula, the candidate pool size, the entity extraction — all of these were carefully designed. But the most basic graph traversal (follow the next section) was never wired up.

This is a clean example of latent graph value: the structure is there, the query doesn't exploit it. For RAG systems, it's worth auditing which relationships exist in the graph but never appear in the retrieval Cypher.

---

## Supporting Data

Use `replay_retrieval.py` to verify:

```bash
python replay_retrieval.py --query "What was your role at UT Austin after MIT?"
```

The `↓ continued:` block in the output shows the neighbor text the LLM now receives. Compare with ChromaDB (`--compare`) to see that ChromaDB has no equivalent — this is a Neo4j-only capability.
