---
title: Neo4j vs ChromaDB
tags:
  - architecture
  - neo4j
  - chromadb
---

# Neo4j vs ChromaDB

Both databases are active. They store the same chunks. They serve different purposes. This page explains the architecture, the tradeoffs, and why neither has been removed.

---

## The Short Version

| | Neo4j | ChromaDB |
|---|---|---|
| **Role** | Production retrieval | Fallback + A/B comparison baseline |
| **Retrieval** | Hybrid: vector + graph signals | Pure vector only |
| **Scoring** | Composite formula with bonuses | Cosine similarity only |
| **Tier gating** | `WHERE s.sensitivity_tier IN $allowed_tiers` | Post-filter on metadata |
| **Entity links** | Yes — 167 canonical entity nodes via `MENTIONS` | No |
| **Project links** | Yes — `Project -[:DESCRIBED_IN]-> Section` | No |
| **Fallback if unavailable** | ChromaDB takes over automatically | — |
| **Debugging** | `replay_retrieval.py --compare` shows ranking drift | `chunk_inspector.py` |

---

## Why Neo4j Is Production

Pure vector similarity is a strong baseline, but it has one structural blind spot: it ranks chunks by how well they *sound like* the query, not by how *factually connected* they are to the topics the query raises.

For project-specific questions ("What projects use Neo4j?"), this is a real problem — a generic career overview chunk can outscore a specific project description if it uses more matching vocabulary.

Neo4j's hybrid retrieval closes this gap:

- **Graph-aware tiebreaking**: Sections linked to a Project node (+0.08) or mentioning relevant entities (+0.05, capped at 5) rank slightly higher among otherwise-equal candidates
- **Sensitivity tier gating**: The `allowed_tiers` filter in Cypher is cleaner than ChromaDB's post-filter metadata matching
- **Relationship coverage**: +34.3% vs ChromaDB baseline on relationship-style queries (from `evals/results/`)

!!! note "Graph signals as tiebreakers, not determiners"
    Graph bonuses are capped at +0.15 total. The vector similarity weight (0.85) is dominant by design. Graph signals modulate a semantically-ranked list — they don't reverse it. This constraint was established after a hallucination caused by oversized bonuses. See [Entry 001](../lessons-learned/entry-001.md).

---

## Why ChromaDB Stays

**Three reasons ChromaDB has not been removed:**

1. **A/B comparison baseline** — The same chunks stored in both systems means `replay_retrieval.py --compare` can produce a ranking-drift table for any query. This is the fastest diagnostic for determining whether a graph signal is helping or hurting. Without ChromaDB, this comparison is impossible.

2. **Fallback** — If Neo4j is unavailable (network issue, credentials problem, cold start), `app.py` falls back to ChromaDB automatically. No code changes needed; the app degrades gracefully.

3. **Data integrity** — Both stores are kept in sync during ingestion. If you need to audit Neo4j content, ChromaDB provides an independent reference.

!!! warning "Do not remove ChromaDB until..."
    ChromaDB should not be removed until Neo4j has run in production for at least 72 hours without incident AND `evals/run_evals.py` passes at 90%+. As of the initial Neo4j migration, the comparison baseline is still actively used for debugging.

---

## When Rankings Diverge

Running `replay_retrieval.py --compare` on a query produces output like:

```
Neo4j Rank | ChromaDB Rank | Δ | Section Name        | Neo4j Score | Vec Score
-----------+---------------+---+---------------------+-------------+----------
    1      |      3        | ↑ | Project: Beekeeping |    0.781    |  0.860
    2      |      1        | ↓ | Career Narrative Ch3 |   0.727    |  0.855
    3      |      4        | ↑ | Resume Explorer KB  |    0.701    |  0.743
```

Sections moving up (↑) in Neo4j vs ChromaDB ranking earned graph bonuses — project links, entity mentions, or length. Sections moving down (↓) had strong vector similarity but fewer graph connections.

If you see a high-confidence chunk (strong vector score) being demoted, check its graph connectivity. If the demotion is causing wrong answers, the bonuses may need rebalancing.

---

## Ingestion: Both Stores Updated Together

The ingestion pipeline writes to both databases:

```
embed_sections.py (Neo4j) ←— text-embedding-3-small ——→ embed_kb_doc.py (ChromaDB)
```

Both stores receive the same chunks with the same embeddings. The metadata schema is slightly different (Neo4j uses node properties; ChromaDB uses a metadata dict), but `source`, `section`, and `sensitivity_tier` are present in both.

See [KB Ingestion](../developer-docs/kb-ingestion.md) for the full ingestion command reference.
