#!/usr/bin/env python3
"""
capture_neo4j_ranking.py
=========================
Mirror of capture_baseline_ranking.py for Neo4j hybrid retrieval.

For each of 15 factual queries, prints top-10 retrieved sections with
composite scores and prompts for the rank where the correct answer appears.

Key difference: scores shown are composite (vector × 0.6 + graph signals × 0.4)
not raw cosine similarities. Sections are full text, not 900-char chunks.

Baseline for comparison: evals/results/baseline_ranking.json
  top1_precision: 46.7%   top3_precision: 80.0%   MRR: 0.621

Output: evals/results/neo4j_ranking.json

Usage (from project root):
    python evals/capture_neo4j_ranking.py
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from neo4j_utils import query_neo4j_rag  # noqa: E402

RESULTS_DIR = _HERE / "results"
OUTPUT_FILE = RESULTS_DIR / "neo4j_ranking.json"

# Identical query set to baseline_ranking.json for direct comparison.
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

N_RESULTS = 10  # Match baseline for valid rank comparison


def get_rank(n_results: int) -> int:
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
    print("Neo4j Ranking Eval")
    print("Baseline (ChromaDB): top1=46.7%  top3=80.0%  MRR=0.621")
    print("─" * 60)
    print(
        "\nFor each query, review the top sections and enter the rank where "
        "the correct answer first appears (0 = not in top results).\n"
        "Scores shown are composite (vector + graph signals), not raw cosine.\n"
    )

    results = []

    for i, test in enumerate(RANKING_QUERIES, 1):
        query = test["query"]
        hint = test["answer_hint"]

        print(f"\n{'='*60}")
        print(f"Query {i}/{len(RANKING_QUERIES)}: {query}")
        print(f"Answer hint: {hint}")
        print("─" * 60)

        rag = query_neo4j_rag(query, visitor_tier="public", k=N_RESULTS)

        for j, (src, score, related) in enumerate(
            zip(rag["sources"], rag["scores"], rag["related_projects"]), 1
        ):
            related_str = f"  → Describes: {', '.join(related)}" if related else ""
            print(f"\n  [Rank {j:2d}] score={score:.3f}  {src}{related_str}")

        # Show top section text preview to help with ranking
        ctx_lines = rag["context"].split("\n")
        preview_lines = []
        in_text = False
        for line in ctx_lines:
            if line.startswith("[") and line.endswith("]"):
                in_text = True
                continue
            if line == "---":
                break
            if in_text and not line.startswith("(Describes:"):
                preview_lines.append(line)
        preview = "\n".join(preview_lines)[:400]
        if preview:
            print(f"\n  Top section preview:\n  {preview}{'...' if len(preview) == 400 else ''}")

        rank = get_rank(len(rag["sources"]))
        results.append({
            "query": query,
            "answer_hint": hint,
            "answer_rank": rank,
            "sources": rag["sources"],
            "scores": [round(s, 3) for s in rag["scores"]],
        })

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
    print(f"Neo4j    — top1: {top1:.1f}%  top3: {top3:.1f}%  MRR: {mrr:.3f}")
    print(f"Baseline — top1: 46.7%       top3: 80.0%       MRR: 0.621")
    print(f"Results written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
