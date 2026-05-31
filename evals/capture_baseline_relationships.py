#!/usr/bin/env python3
"""
capture_baseline_relationships.py
==================================
Test ChromaDB's ability to answer relationship traversal queries.

For each query, retrieves top-5 chunks and automatically scores whether
expected project names appear in the returned text.

Scores: ✅ (>=2 expected found), ⚠️ (1 found), ❌ (0 found)

Output: evals/results/baseline_relationships.json

Usage:
    python evals/capture_baseline_relationships.py
"""

import json
import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
CHROMA_PATH = str(_ROOT / ".chroma_db_DT")
COLLECTION_NAME = "barb-twin"
EMBED_MODEL = "text-embedding-3-small"
RESULTS_DIR = _HERE / "results"
OUTPUT_FILE = RESULTS_DIR / "baseline_relationships.json"

# Expected projects verified against featured_projects.py tags and walkthrough_context.
# Names must match how they appear in KB chunk text (substring match, case-insensitive).
# Note: the KB contains projects beyond featured_projects.py (e.g. "Local RAG Assistant",
# "Digital Memory Chest") — those aren't listed here, so ChromaDB returning them will
# appear as unexpected finds rather than scored hits. That's acceptable for a baseline.
RELATIONSHIP_QUERIES = [
    {
        "query": "Which projects use knowledge graphs?",
        # All four have "knowledge-graph" tag in featured_projects.py
        "expected_projects": [
            "Resume Graph Explorer",
            "Weaving Memories",
            "Academic Citation Platform",
            "Concept Cartographer",
        ],
    },
    {
        "query": "What projects use Neo4j?",
        # Both have "neo4j" tag; ChronoScope mentions it as optional/beta only
        "expected_projects": ["Weaving Memories", "Academic Citation Platform"],
    },
    {
        "query": "Which projects are similar to Resume Explorer?",
        # Subjective — shared domain (knowledge graphs, career data)
        "expected_projects": [
            "Concept Cartographer",
            "ChronoScope",
            "Weaving Memories",
        ],
    },
    {
        "query": "What other projects use evaluation harnesses?",
        # Poolula has an explicit eval harness; Digital Twin has evals/ suite
        "expected_projects": ["Poolula Platform", "Digital Twin"],
    },
    {
        "query": "Which projects use Streamlit?",
        # Verified from "streamlit" tag in featured_projects.py:
        #   Academic Citation Platform ✓, Beehive Monitor ✓, ConvoScope ✓,
        #   Fitness Tracker ✓ (also called "Fitness Dashboard" in KB),
        #   ChronoScope ✓
        # Resume Graph Explorer uses Flask + React — NOT Streamlit (was wrong before)
        "expected_projects": [
            "Academic Citation Platform",
            "Beehive Monitor",
            "ConvoScope",
            "Fitness",     # matches both "Fitness Tracker" and "Fitness Dashboard"
            "ChronoScope",
        ],
    },
    {
        "query": "What projects involve natural language processing?",
        # All have "nlp" tag: Resume Graph Explorer, Digital Twin, ConvoScope,
        # Concept Cartographer, ChronoScope. Listing the clearest ones.
        "expected_projects": [
            "ConvoScope",
            "ChronoScope",
            "Digital Twin",
            "Concept Cartographer",
        ],
    },
    {
        "query": "Which projects demonstrate data visualization skills?",
        # Strongest visualization projects (Plotly/Streamlit dashboards)
        "expected_projects": ["Fitness", "ChronoScope", "Beehive Monitor"],
    },
    {
        "query": "Show me projects related to beekeeping or agriculture",
        "expected_projects": ["Beehive Monitor"],
    },
]


def score_result(found_text: str, expected_projects: list[str]) -> tuple[str, list[str]]:
    found = [p for p in expected_projects if p.lower() in found_text.lower()]
    if len(found) >= 2 or (len(expected_projects) == 1 and found):
        return "✅ Success", found
    elif len(found) == 1:
        return "⚠️ Partial", found
    else:
        return "❌ Failure", found


def main() -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return 1

    client = OpenAI(api_key=api_key)
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )
    print(f"Collection: {collection.count()} chunks\n")

    results = []
    success_count = 0

    for test in RELATIONSHIP_QUERIES:
        query = test["query"]
        expected = test["expected_projects"]

        embedding = client.embeddings.create(
            model=EMBED_MODEL, input=query
        ).data[0].embedding
        raw = collection.query(query_embeddings=[embedding], n_results=5)
        docs = raw.get("documents", [[]])[0] if raw.get("documents") else []
        combined_text = " ".join(docs)

        status, found = score_result(combined_text, expected)
        if status.startswith("✅"):
            success_count += 1

        print(f"  {status}  {query}")
        print(f"           expected={expected}")
        print(f"           found={found}\n")

        results.append({
            "query": query,
            "expected_projects": expected,
            "found_projects": found,
            "status": status,
        })

    success_rate = success_count / len(RELATIONSHIP_QUERIES) * 100
    output = {
        "success_rate": round(success_rate, 1),
        "n_queries": len(RELATIONSHIP_QUERIES),
        "n_success": success_count,
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))

    print(f"Success rate: {success_rate:.1f}%  ({success_count}/{len(RELATIONSHIP_QUERIES)})")
    print(f"Results written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
