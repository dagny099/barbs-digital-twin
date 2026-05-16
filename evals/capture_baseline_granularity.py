#!/usr/bin/env python3
"""
capture_baseline_granularity.py
=================================
Measure ChromaDB context coherence (granularity problem) interactively.

For each of 10 queries, prints the top-5 retrieved chunks, prompts for a
1-5 coherence score, and automatically checks must_contain keywords.

Output: evals/results/baseline_granularity.json

Usage:
    python evals/capture_baseline_granularity.py
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
OUTPUT_FILE = RESULTS_DIR / "baseline_granularity.json"

GRANULARITY_QUERIES = [
    {
        "query": "What is Barbara's educational background?",
        "expected_section": "Education",
        "must_contain": ["UT Austin", "MIT", "Electrical Engineering", "Biology"],
    },
    {
        "query": "Tell me about the Resume Graph Explorer project",
        "expected_section": "Resume Graph Explorer",
        "must_contain": ["SKOS", "ESCO", "knowledge graph"],
    },
    {
        "query": "Describe Barbara's dissertation research",
        "expected_section": "Dissertation",
        "must_contain": ["MIT", "visual attention", "eye"],
    },
    {
        "query": "What makes the Poolula Platform distinctive?",
        "expected_section": "Poolula",
        "must_contain": ["LLC", "evaluation"],
    },
    {
        "query": "Tell me about the Beehive Monitor project",
        "expected_section": "Beehive Monitor",
        "must_contain": ["beehive", "sensor", "computer vision"],
    },
    {
        "query": "Explain the Digital Twin architecture",
        "expected_section": "Digital Twin",
        "must_contain": ["RAG", "ChromaDB", "Gradio"],
    },
    {
        "query": "What is Barbara's approach to knowledge graphs?",
        "expected_section": "Knowledge Graphs",
        "must_contain": ["graph", "semantic", "relationship"],
    },
    {
        "query": "What skills does Barbara demonstrate in her projects?",
        "expected_section": "Skills",
        "must_contain": ["machine learning", "Python", "data"],
    },
    {
        "query": "Describe the ConvoScope project",
        "expected_section": "ConvoScope",
        "must_contain": ["conversation", "LLM", "analysis"],
    },
    {
        "query": "What certifications does Barbara have?",
        "expected_section": "Certifications",
        "must_contain": ["certificate", "course", "certification"],
    },
]

SCORE_RUBRIC = """
Coherence Score (1-5):
  5 = Complete section, full context — no fragmentation
  4 = Mostly complete, minor gaps
  3 = Multiple related chunks, requires mental stitching
  2 = Fragments from different sections mixed together
  1 = Incoherent or wrong content returned
"""


def get_score(query: str) -> int:
    while True:
        try:
            raw = input(f"  Score (1-5) for above chunks: ").strip()
            score = int(raw)
            if 1 <= score <= 5:
                return score
            print("  Please enter a number between 1 and 5.")
        except (ValueError, EOFError):
            print("  Invalid input, defaulting to 3.")
            return 3


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
    print(f"Collection: {collection.count()} chunks")
    print(SCORE_RUBRIC)

    results = []

    for i, test in enumerate(GRANULARITY_QUERIES, 1):
        query = test["query"]
        must_contain = test["must_contain"]

        print(f"\n{'='*60}")
        print(f"Query {i}/{len(GRANULARITY_QUERIES)}: {query}")
        print("─" * 60)

        embedding = client.embeddings.create(
            model=EMBED_MODEL, input=query
        ).data[0].embedding
        raw = collection.query(query_embeddings=[embedding], n_results=5)
        docs = raw.get("documents", [[]])[0] if raw.get("documents") else []
        metas = raw.get("metadatas", [[]])[0] if raw.get("metadatas") else []

        for j, (doc, meta) in enumerate(zip(docs, metas), 1):
            source = meta.get("source", "?")
            section = meta.get("section", "?")
            print(f"\n  [Chunk {j}] {source} — {section}")
            print(f"  {doc[:400]}{'...' if len(doc) > 400 else ''}")

        combined = " ".join(docs)
        kw_found = [kw for kw in must_contain if kw.lower() in combined.lower()]
        kw_coverage = len(kw_found) / len(must_contain) if must_contain else 1.0
        print(f"\n  Keywords found {len(kw_found)}/{len(must_contain)}: {kw_found}")

        score = get_score(query)
        results.append({
            "query": query,
            "expected_section": test["expected_section"],
            "coherence_score": score,
            "keyword_coverage": round(kw_coverage, 2),
            "keywords_found": kw_found,
            "keywords_expected": must_contain,
        })

    avg_coherence = sum(r["coherence_score"] for r in results) / len(results)
    avg_keyword_coverage = sum(r["keyword_coverage"] for r in results) / len(results)

    output = {
        "avg_coherence": round(avg_coherence, 2),
        "avg_keyword_coverage": round(avg_keyword_coverage, 2),
        "n_queries": len(results),
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*60}")
    print(f"Average coherence: {avg_coherence:.2f}/5.0")
    print(f"Average keyword coverage: {avg_keyword_coverage:.0%}")
    print(f"Results written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
