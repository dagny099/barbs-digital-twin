#!/usr/bin/env python3
"""
capture_baseline_latency.py
============================
Measure ChromaDB retrieval latency before Neo4j migration.

Runs 20 representative queries, records end-to-end timing for each, and
outputs p50/p95/p99 statistics to evals/results/baseline_latency.json.

Usage:
    python evals/capture_baseline_latency.py
"""

import json
import os
import sys
import time
from pathlib import Path

import chromadb
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
CHROMA_PATH = str(_ROOT / ".chroma_db_DT")
COLLECTION_NAME = "barb-twin"
EMBED_MODEL = "text-embedding-3-small"
RESULTS_DIR = _HERE / "results"
OUTPUT_FILE = RESULTS_DIR / "baseline_latency.json"

QUERIES = [
    "What is Barbara's educational background?",
    "Tell me about the Resume Graph Explorer project",
    "What is Barbara's approach to knowledge graphs?",
    "Explain the Digital Twin architecture",
    "What skills does Barbara demonstrate in her projects?",
    "Describe Barbara's dissertation research",
    "What makes the Poolula Platform distinctive?",
    "How does Barbara approach problem-solving?",
    "What certifications does Barbara have?",
    "Tell me about the Beehive Monitor project",
    "Which projects use machine learning?",
    "What is Barbara's professional background?",
    "Tell me about the Weaving Memories project",
    "What evaluation methods does Barbara use?",
    "Describe the Concept Cartographer",
    "What experience does Barbara have with NLP?",
    "Tell me about the Academic Citation Platform",
    "What data engineering skills does Barbara have?",
    "Describe ChronoScope",
    "What is Barbara's philosophy on software development?",
]


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

    latencies_ms: list[float] = []
    results = []

    for i, query in enumerate(QUERIES, 1):
        t0 = time.perf_counter()
        embedding = client.embeddings.create(
            model=EMBED_MODEL, input=query
        ).data[0].embedding
        collection.query(query_embeddings=[embedding], n_results=10)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        latencies_ms.append(elapsed_ms)
        results.append({"query": query, "latency_ms": round(elapsed_ms, 1)})
        print(f"  [{i:2d}/20]  {elapsed_ms:6.1f} ms  {query[:60]}")

    arr = np.array(latencies_ms)
    stats = {
        "p50_ms": round(float(np.percentile(arr, 50)), 1),
        "p95_ms": round(float(np.percentile(arr, 95)), 1),
        "p99_ms": round(float(np.percentile(arr, 99)), 1),
        "mean_ms": round(float(arr.mean()), 1),
        "n": len(latencies_ms),
    }

    output = {"stats": stats, "queries": results}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(output, indent=2))

    print(f"\np50: {stats['p50_ms']} ms  p95: {stats['p95_ms']} ms  p99: {stats['p99_ms']} ms")
    print(f"Results written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
