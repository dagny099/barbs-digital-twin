#!/usr/bin/env python3
"""
capture_neo4j_relationships.py
================================
Mirror of capture_baseline_relationships.py for Neo4j, with graph traversal.

For each relationship query, runs TWO retrieval paths and compares them:

  1. Vector path  — query_neo4j_rag() (same hybrid search as the chatbot uses)
  2. Graph path   — direct Cypher traversal (the Neo4j advantage over ChromaDB)

The graph path is the key differentiator: ChromaDB can only infer relationships
from text co-occurrence; Neo4j can traverse explicit Project→Skill/Technology edges.

Scoring is automatic: ✅ if ≥2 expected projects found, ⚠️ if 1, ❌ if 0.
Each path is scored independently so you can see where graph traversal wins.

Baseline for comparison: evals/results/baseline_relationships.json
  success_rate: 37.5%  (3/8 queries)

Output: evals/results/neo4j_relationships.json

Usage (from project root):
    python evals/capture_neo4j_relationships.py
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from neo4j_utils import get_driver, query_neo4j_rag  # noqa: E402

RESULTS_DIR = _HERE / "results"
OUTPUT_FILE = RESULTS_DIR / "neo4j_relationships.json"

# Same query set as baseline_relationships.json.
# graph_cypher: direct traversal query for this relationship type.
# None means no direct traversal applies — fall back to vector only.
RELATIONSHIP_QUERIES = [
    {
        "query": "Which projects use knowledge graphs?",
        "expected_projects": [
            "Resume Graph Explorer",
            "Weaving Memories",
            "Academic Citation Platform",
            "Concept Cartographer",
        ],
        "graph_cypher": """
            MATCH (s:Skill)<-[:DEMONSTRATES]-(p:Project)
            WHERE toLower(s.name) CONTAINS 'knowledge graph'
               OR toLower(s.name) CONTAINS 'graph'
               OR toLower(s.name) CONTAINS 'ontolog'
            RETURN DISTINCT p.title AS title
        """,
    },
    {
        "query": "What projects use Neo4j?",
        "expected_projects": ["Weaving Memories", "Academic Citation Platform"],
        "graph_cypher": """
            MATCH (t:Technology)<-[:USES_TECHNOLOGY]-(p:Project)
            WHERE toLower(t.name) CONTAINS 'neo4j'
            RETURN DISTINCT p.title AS title
        """,
    },
    {
        "query": "Which projects are similar to Resume Explorer?",
        "expected_projects": [
            "Concept Cartographer",
            "ChronoScope",
            "Weaving Memories",
        ],
        # Find projects sharing skills or methods with Resume Graph Explorer
        "graph_cypher": """
            MATCH (p1:Project {id: "resume-graph-explorer"})
                  -[:DEMONSTRATES|USES_METHOD]->(shared)
                  <-[:DEMONSTRATES|USES_METHOD]-(p2:Project)
            WHERE p1 <> p2
            RETURN DISTINCT p2.title AS title, count(shared) AS shared_count
            ORDER BY shared_count DESC
        """,
    },
    {
        "query": "What other projects use evaluation harnesses?",
        "expected_projects": ["Poolula Platform", "Digital Twin"],
        "graph_cypher": """
            MATCH (s)<-[:DEMONSTRATES|USES_METHOD]-(p:Project)
            WHERE toLower(s.name) CONTAINS 'eval'
               OR toLower(s.name) CONTAINS 'harness'
               OR toLower(s.name) CONTAINS 'metric'
            RETURN DISTINCT p.title AS title
        """,
    },
    {
        "query": "Which projects use Streamlit?",
        "expected_projects": [
            "Academic Citation Platform",
            "Beehive Monitor",
            "ConvoScope",
            "Fitness",
            "ChronoScope",
        ],
        "graph_cypher": """
            MATCH (t:Technology)<-[:USES_TECHNOLOGY]-(p:Project)
            WHERE toLower(t.name) CONTAINS 'streamlit'
            RETURN DISTINCT p.title AS title
        """,
    },
    {
        "query": "What projects involve natural language processing?",
        "expected_projects": [
            "ConvoScope",
            "ChronoScope",
            "Digital Twin",
            "Concept Cartographer",
        ],
        "graph_cypher": """
            MATCH (s)<-[:DEMONSTRATES|USES_METHOD]-(p:Project)
            WHERE toLower(s.name) CONTAINS 'nlp'
               OR toLower(s.name) CONTAINS 'natural language'
               OR toLower(s.name) CONTAINS 'text'
               OR toLower(s.name) CONTAINS 'language model'
            RETURN DISTINCT p.title AS title
        """,
    },
    {
        "query": "Which projects demonstrate data visualization skills?",
        "expected_projects": ["Fitness", "ChronoScope", "Beehive Monitor"],
        "graph_cypher": """
            MATCH (s:Skill)<-[:DEMONSTRATES]-(p:Project)
            WHERE toLower(s.name) CONTAINS 'visuali'
               OR toLower(s.name) CONTAINS 'dashboard'
               OR toLower(s.name) CONTAINS 'plotly'
            RETURN DISTINCT p.title AS title
        """,
    },
    {
        "query": "Show me projects related to beekeeping or agriculture",
        "expected_projects": ["Beehive Monitor"],
        # No structured entity for beekeeping — vector search is the only path
        "graph_cypher": None,
    },
]


def score_result(found_text: str, expected_projects: list[str]) -> tuple[str, list[str]]:
    found = [p for p in expected_projects if p.lower() in found_text.lower()]
    if len(found) >= 2 or (len(expected_projects) == 1 and found):
        return "✅ Success", found
    elif len(found) == 1:
        return "⚠️  Partial", found
    else:
        return "❌ Failure", found


def run_graph_traversal(cypher: str) -> list[str]:
    """Execute a direct Cypher traversal and return project titles found."""
    driver = get_driver()
    with driver.session() as session:
        records = session.run(cypher).data()
    return [r["title"] for r in records if r.get("title")]


def main() -> int:
    print("Neo4j Relationship Eval")
    print("Baseline (ChromaDB): success_rate=37.5%  (3/8 queries)")
    print("─" * 60)
    print(
        "\nEach query runs TWO paths:\n"
        "  Vector path — hybrid retrieval (what the chatbot sends to the LLM)\n"
        "  Graph path  — direct Cypher traversal (Neo4j structural advantage)\n"
    )

    results = []
    vector_successes = 0
    graph_successes = 0

    for test in RELATIONSHIP_QUERIES:
        query = test["query"]
        expected = test["expected_projects"]
        cypher = test.get("graph_cypher")

        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"Expected: {expected}")
        print("─" * 60)

        # ── Vector path ──────────────────────────────────────────
        rag = query_neo4j_rag(query, visitor_tier="public", k=5)
        vector_text = rag["context"]
        vector_status, vector_found = score_result(vector_text, expected)

        print(f"\n  Vector path: {vector_status}")
        print(f"    Found: {vector_found}")
        print(f"    Sources: {rag['sources']}")
        if rag["related_projects"]:
            linked = [p for sublist in rag["related_projects"] for p in sublist if p]
            if linked:
                print(f"    Graph-linked projects in context: {linked}")

        # ── Graph traversal path ──────────────────────────────────
        if cypher:
            graph_titles = run_graph_traversal(cypher)
            graph_text = " ".join(graph_titles)
            graph_status, graph_found = score_result(graph_text, expected)

            print(f"\n  Graph path:  {graph_status}")
            print(f"    Traversal returned: {graph_titles}")
            print(f"    Matched expected:   {graph_found}")

            if vector_status.startswith("✅"):
                vector_successes += 1
            if graph_status.startswith("✅"):
                graph_successes += 1
        else:
            graph_status = "N/A (no direct traversal for this query)"
            graph_titles = []
            graph_found = []
            print(f"\n  Graph path:  {graph_status}")
            if vector_status.startswith("✅"):
                vector_successes += 1

        results.append({
            "query": query,
            "expected_projects": expected,
            "vector_status": vector_status,
            "vector_found": vector_found,
            "vector_sources": rag["sources"],
            "graph_status": graph_status,
            "graph_found": graph_found,
            "graph_titles": graph_titles if cypher else None,
        })

    n_with_cypher = sum(1 for t in RELATIONSHIP_QUERIES if t.get("graph_cypher"))
    vector_rate = vector_successes / len(RELATIONSHIP_QUERIES) * 100
    graph_rate = graph_successes / n_with_cypher * 100 if n_with_cypher else 0

    output = {
        "vector_success_rate": round(vector_rate, 1),
        "graph_success_rate": round(graph_rate, 1),
        "n_queries": len(RELATIONSHIP_QUERIES),
        "n_vector_success": vector_successes,
        "n_graph_success": graph_successes,
        "n_with_graph_cypher": n_with_cypher,
        "chromadb_baseline_success_rate": 37.5,
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*60}")
    print(f"Neo4j vector path:  {vector_rate:.1f}%  ({vector_successes}/{len(RELATIONSHIP_QUERIES)})")
    print(f"Neo4j graph path:   {graph_rate:.1f}%  ({graph_successes}/{n_with_cypher} queries with Cypher)")
    print(f"ChromaDB baseline:  37.5%  (3/8)")
    print(f"Results written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
