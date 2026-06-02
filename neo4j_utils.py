"""
neo4j_utils.py
==============
Neo4j driver factory and connection helpers for the Digital Twin graph.

Provides a module-level singleton driver so all scripts share one connection pool.
LLM configuration stays in utils.py / litellm — not duplicated here.

Usage:
    from neo4j_utils import get_driver, close_driver, query_neo4j_rag

    driver = get_driver()
    with driver.session() as session:
        session.run("RETURN 1")
    close_driver()
"""

import os
from pathlib import Path
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

_driver: Driver | None = None
_openai_client: OpenAI | None = None

# Composite scoring weights — must sum to ≤ 1.0 with all bonuses at max.
# Import these in replay_retrieval.py so the debug script stays in sync.
Wt_SEMANTIC    = 0.85   # pure semantic relevance — dominant signal
BONUS_PROJECT  = 0.08   # graph bonus: section linked to a Project node
BONUS_ENTITY   = 0.05   # graph bonus: entity mentions (capped at 5)
BONUS_LENGTH   = 0.02   # graph bonus: section > 2000 chars

# Cypher: vector similarity + graph-signal composite ranking + neighbor context expansion.
# Weights defined above — edit there, not here.
# Relationship direction: Project -[:DESCRIBED_IN]-> Section.
# Neighbor expansion: each top-k section fetches its NEXT_SECTION (if any) so the
# LLM receives the continuation of narrative sections rather than an isolated fragment.
# Neighbor sensitivity is filtered to the same allowed_tiers as the anchor.
_HYBRID_CYPHER = f"""
CALL db.index.vector.queryNodes('section_embeddings', $fetch_k, $query_embedding)
YIELD node AS section, score AS vector_score

WHERE section.sensitivity IN $allowed_tiers

OPTIONAL MATCH (section)<-[:DESCRIBED_IN]-(p:Project)
OPTIONAL MATCH (section)-[:MENTIONS]->(entity)

WITH section, vector_score,
     count(DISTINCT p) AS projects_described,
     count(DISTINCT entity) AS entities_mentioned

WITH section,
     (vector_score * {Wt_SEMANTIC} +
      CASE WHEN projects_described > 0 THEN {BONUS_PROJECT} ELSE 0 END +
      toFloat(CASE WHEN entities_mentioned > 5 THEN 5 ELSE entities_mentioned END) / 5 * {BONUS_ENTITY} +
      (CASE WHEN section.char_count > 2000 THEN {BONUS_LENGTH} ELSE 0 END)) AS final_score,
     vector_score,
     projects_described

ORDER BY final_score DESC
LIMIT $k

MATCH (doc:Document)-[:HAS_SECTION]->(section)
OPTIONAL MATCH (section)<-[:DESCRIBED_IN]-(project:Project)
OPTIONAL MATCH (section)-[:NEXT_SECTION]->(neighbor:Section)
WHERE neighbor.sensitivity IN $allowed_tiers

RETURN section.full_text AS text,
       section.name AS section_name,
       doc.title AS source,
       final_score,
       vector_score,
       collect(DISTINCT project.title) AS related_projects,
       neighbor.full_text AS neighbor_text,
       neighbor.name AS neighbor_section_name
"""

_TIER_HIERARCHY = {
    "public": ["public"],
    "personal": ["public", "personal"],
    "inner_circle": ["public", "personal", "inner_circle"],
}


def get_driver() -> Driver:
    """Return the module-level Neo4j driver, creating it on first call."""
    global _driver
    if _driver is None:
        uri = os.environ["NEO4J_URI"]
        user = os.environ["NEO4J_USER"]
        password = os.environ["NEO4J_PASSWORD"]
        _driver = GraphDatabase.driver(uri, auth=(user, password))
    return _driver


def close_driver() -> None:
    """Close the driver and release all connections."""
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def _get_openai() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai_client


def query_neo4j_rag(user_query: str, visitor_tier: str = "public", k: int = 5) -> dict:
    """Hybrid vector + graph retrieval from Neo4j.

    Returns:
        {
            "context":          formatted string ready for system prompt injection,
            "sources":          ["Title — Section name", ...],
            "scores":           [0.89, 0.76, ...],   # final composite scores
            "related_projects": [["Resume Graph Explorer"], ...],
        }

    The context format per result block:
        [source — section_name]
        <full section text>
        (Describes: Project A, Project B)   ← only when projects linked
        [continued: source — neighbor_name] ← only when NEXT_SECTION exists and not in top-k
        <neighbor full text>
        ---
    sources/scores/chunks reflect the k anchor sections only; neighbor text is
    injected inline into the context string but not counted separately.
    """
    allowed_tiers = _TIER_HIERARCHY.get(visitor_tier, ["public"])

    query_embedding = (
        _get_openai()
        .embeddings.create(model="text-embedding-3-small", input=user_query)
        .data[0]
        .embedding
    )

    driver = get_driver()
    with driver.session() as session:
        records = session.run(
            _HYBRID_CYPHER,
            {
                "query_embedding": query_embedding,
                "k": k,
                "fetch_k": k * 4,   # wider candidate pool reduces graph-reranking displacement
                "allowed_tiers": allowed_tiers,
            },
        ).data()

    context_parts = []
    sources = []
    scores = []
    related_projects_list = []
    chunks = []
    neighbors = []  # parallel to chunks; None when anchor has no eligible neighbor

    # Collect (source, section_name) pairs upfront so we can skip neighbors that
    # are already in the top-k result set. Using the compound key prevents false
    # dedup when two different documents contain sections with the same name.
    # NEXT_SECTION only links sections within the same document, so the neighbor's
    # source is always rec["source"] — used as the lookup key below.
    anchor_keys = {(rec["source"], rec["section_name"]) for rec in records}

    for rec in records:
        source_label = f"{rec['source']} — {rec['section_name']}"
        sources.append(source_label)
        scores.append(rec["final_score"])
        related_projects_list.append(rec["related_projects"])
        chunks.append({
            "text":    rec["text"] or "",
            "source":  rec["source"] or "",
            "section": rec["section_name"] or "",
            "score":   rec["final_score"],
        })

        context_parts.append(f"[{source_label}]")
        context_parts.append(rec["text"] or "")

        if rec["related_projects"]:
            projects = ", ".join(rec["related_projects"])
            context_parts.append(f"(Describes: {projects})")

        neighbor_text = rec.get("neighbor_text")
        neighbor_name = rec.get("neighbor_section_name")
        if neighbor_text and neighbor_name and (rec["source"], neighbor_name) not in anchor_keys:
            context_parts.append(f"[continued: {rec['source']} — {neighbor_name}]")
            context_parts.append(neighbor_text)
            neighbors.append({"text": neighbor_text, "section": neighbor_name})
        else:
            neighbors.append(None)

        context_parts.append("---")

    return {
        "context": "\n".join(context_parts),
        "sources": sources,
        "scores": scores,
        "related_projects": related_projects_list,
        "chunks": chunks,   # raw records for admin panel / debug tools
        "neighbors": neighbors,  # parallel to chunks; None entries have no neighbor
    }
