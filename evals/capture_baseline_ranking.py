#!/usr/bin/env python3
"""
capture_baseline_ranking.py
============================
Measure ChromaDB ranking quality (Top-1, Top-3, MRR) before Neo4j migration.

For each of 15 factual queries, prints the top-10 retrieved chunks with rank
numbers and prompts for the rank where the correct answer first appears.
Enter 0 if the answer is not found in top-10.

Output: evals/results/baseline_ranking.json

Usage:
    python evals/capture_baseline_ranking.py
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
OUTPUT_FILE = RESULTS_DIR / "baseline_ranking.json"

# 15 factual queries covering bio and project categories
RANKING_QUERIES = [
    {"query": "What undergraduate degrees did Barbara earn?", "answer_hint": "UT Austin, Electrical Engineering, Biology"},
    {"query": "Where did Barbara do her PhD?", "answer_hint": "MIT"},
    {"query": "What was Barbara's dissertation about?", "answer_hint": "visual attention, eye movements"},
    {"query": "What certifications does Barbara have?", "answer_hint": "certificate, certification"},
    {"query": "Walk me through the Resume Graph Explorer", "answer_hint": "SKOS, ESCO, knowledge graph"},
    {"query": "How was the Digital Twin chatbot built?", "answer_hint": "ChromaDB, RAG, Gradio"},
    {"query": "What is the Weaving Memories project?", "answer_hint": "memorial, Neo4j, graph"},
    {"query": "Describe the Academic Citation Platform", "answer_hint": "TransE, embeddings, citations"},
    {"query": "What problems does Barbara solve professionally?", "answer_hint": "knowledge, data, AI"},
    {"query": "Tell me about Barbara's knowledge graph work", "answer_hint": "graph, SKOS, relationships"},
    {"query": "What is Barbara's experience with evaluation?", "answer_hint": "eval, harness, metrics"},
    {"query": "Describe the Fitness Tracker project", "answer_hint": "workout, fitness, data"},
    {"query": "What is ChronoScope?", "answer_hint": "timeline, temporal, extraction"},
    {"query": "Tell me about Concept Cartographer", "answer_hint": "real-time, knowledge graph, builder"},
    {"query": "What is Barbara's professional identity?", "answer_hint": "data scientist, engineer, AI"},
]


def get_rank(query: str, n_results: int) -> int:
    while True:
        try:
            raw = input(
                f"  Rank where answer appears (1-{n_results}, 0=not found): "
            ).strip()
            rank = int(raw)
            if 0 <= rank <= n_results:
                return rank
            print(f"  Please enter 0-{n_results}.")
        except (ValueError, EOFError):
            print("  Invalid input, defaulting to 0 (not found).")
            return 0


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
    print("For each query, review the top-10 chunks and enter the rank")
    print("where the correct answer first appears (0 = not in top 10).\n")

    results = []
    n_results = 10

    for i, test in enumerate(RANKING_QUERIES, 1):
        query = test["query"]
        hint = test["answer_hint"]

        print(f"\n{'='*60}")
        print(f"Query {i}/{len(RANKING_QUERIES)}: {query}")
        print(f"Answer hint: {hint}")
        print("─" * 60)

        embedding = client.embeddings.create(
            model=EMBED_MODEL, input=query
        ).data[0].embedding
        raw = collection.query(query_embeddings=[embedding], n_results=n_results)
        docs = raw.get("documents", [[]])[0] if raw.get("documents") else []
        metas = raw.get("metadatas", [[]])[0] if raw.get("metadatas") else []
        distances = raw.get("distances", [[]])[0] if raw.get("distances") else []

        for j, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
            source = meta.get("source", "?")
            section = meta.get("section", "?")
            sim = round(1 - (dist ** 2 / 2), 3) if dist else 0
            print(f"\n  [Rank {j:2d}] sim={sim:.3f}  {source} — {section}")
            print(f"  {doc[:300]}{'...' if len(doc) > 300 else ''}")

        rank = get_rank(query, n_results)
        results.append({
            "query": query,
            "answer_hint": hint,
            "answer_rank": rank,
        })

    # Calculate metrics
    ranks = [r["answer_rank"] for r in results]
    top1 = sum(1 for r in ranks if r == 1) / len(ranks) * 100
    top3 = sum(1 for r in ranks if 1 <= r <= 3) / len(ranks) * 100
    mrr = sum(1 / r for r in ranks if r > 0) / len(ranks)

    output = {
        "top1_precision": round(top1, 1),
        "top3_precision": round(top3, 1),
        "mrr": round(mrr, 3),
        "n_queries": len(results),
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))

    print(f"\n{'='*60}")
    print(f"Top-1: {top1:.1f}%  Top-3: {top3:.1f}%  MRR: {mrr:.3f}")
    print(f"Results written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
