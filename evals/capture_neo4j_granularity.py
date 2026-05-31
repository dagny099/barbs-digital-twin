#!/usr/bin/env python3
"""
capture_neo4j_granularity.py
=============================
Mirror of capture_baseline_granularity.py for Neo4j hybrid retrieval.

For each of 10 queries, prints the top-5 retrieved sections from Neo4j and
prompts for a 1-5 coherence score. Keyword coverage is auto-computed.

Key difference from ChromaDB baseline: Neo4j returns full sections (2-3K chars)
rather than 900-char chunks, so fragmentation scores should improve.

Baseline for comparison: evals/results/baseline_granularity.json
  avg_coherence: 3.4/5   avg_keyword_coverage: 71%

Output: evals/results/neo4j_granularity.json

Usage (from project root):
    python evals/capture_neo4j_granularity.py
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
OUTPUT_FILE = RESULTS_DIR / "neo4j_granularity.json"

# Identical query set to baseline_granularity.json for direct comparison.
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

SCORE_RUBRIC_COMPACT = (
    "  Score the contents, not the order — "
    "5=complete+clean  4=mostly  3=workable  2=noisy/cut  1=unusable"
)


def get_score() -> int:
    print(SCORE_RUBRIC_COMPACT)
    while True:
        try:
            raw = input("  Score (1-5): ").strip()
            score = int(raw)
            if 1 <= score <= 5:
                return score
            print("  Please enter a number between 1 and 5.")
        except (ValueError, EOFError):
            print("  Invalid input, defaulting to 3.")
            return 3


def main() -> int:
    print("Neo4j Granularity Eval")
    print("Baseline (ChromaDB): avg_coherence=3.4/5  keyword_coverage=71%")
    print("─" * 60)
    print(
        "\nFor each query you will see the top-5 retrieved SECTIONS "
        "(full text, not chunks).\nScore coherence: is the returned context "
        "complete and free of fragmentation?\n"
    )

    results = []

    for i, test in enumerate(GRANULARITY_QUERIES, 1):
        query = test["query"]
        must_contain = test["must_contain"]

        print(f"\n{'='*60}")
        print(f"Query {i}/{len(GRANULARITY_QUERIES)}: {query}")
        print("─" * 60)

        rag = query_neo4j_rag(query, visitor_tier="public", k=5)

        combined_text = ""
        for j, (src, score, related) in enumerate(
            zip(rag["sources"], rag["scores"], rag["related_projects"]), 1
        ):
            # Extract section text from context block
            # Context format: "[source]\ntext\n(Describes: ...)\n---"
            # We display what we have from sources/scores; full text is in context
            print(f"\n  [Section {j}] score={score:.3f}  {src}")
            if related:
                print(f"  Describes: {', '.join(related)}")

        # Parse full_text from context for keyword checking
        # The context string has the actual section text
        combined_text = rag["context"]

        kw_found = [kw for kw in must_contain if kw.lower() in combined_text.lower()]
        kw_coverage = len(kw_found) / len(must_contain) if must_contain else 1.0

        # Print a preview of the top section's text
        # Grab the first text block from context (between "[label]" and "---")
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
        preview = "\n".join(preview_lines)[:500]
        if preview:
            print(f"\n  Top section preview:\n  {preview}{'...' if len(preview) == 500 else ''}")

        print(f"\n  Keywords found {len(kw_found)}/{len(must_contain)}: {kw_found}")

        score_val = get_score()
        results.append({
            "query": query,
            "expected_section": test["expected_section"],
            "coherence_score": score_val,
            "keyword_coverage": round(kw_coverage, 2),
            "keywords_found": kw_found,
            "keywords_expected": must_contain,
            "sources": rag["sources"],
            "scores": [round(s, 3) for s in rag["scores"]],
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
    print(f"Neo4j    — avg_coherence: {avg_coherence:.2f}/5.0  keyword_coverage: {avg_keyword_coverage:.0%}")
    print(f"Baseline — avg_coherence: 3.40/5.0  keyword_coverage: 71%")
    print(f"Results written to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
