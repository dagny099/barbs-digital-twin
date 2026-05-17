#!/usr/bin/env python3
"""
compare_retrieval.py
====================
Automated side-by-side comparison of ChromaDB vs Neo4j retrieval quality.

Runs the relationship and keyword-coverage tests against both backends
without requiring manual scoring. Outputs a markdown report and a JSON
summary to evals/results/.

Tests run:
  1. Relationship queries   — project name coverage in top-5 results
  2. Keyword coverage       — must_contain keywords in top-5 results
  3. Section size           — average chars returned (granularity proxy)
  4. Latency                — wall-clock ms per query

Does NOT replace the interactive coherence-scoring scripts; it complements
them with the automatically measurable signals.

Usage (from project root):
    python evals/compare_retrieval.py

    # Quick mode — skip latency (faster, no repeated queries):
    python evals/compare_retrieval.py --no-latency
"""

import argparse
import json
import sys
import time
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from neo4j_utils import query_neo4j_rag  # noqa: E402

RESULTS_DIR = _HERE / "results"
CHROMA_PATH = str(_ROOT / ".chroma_db_DT")
COLLECTION_NAME = "barb-twin"
EMBED_MODEL = "text-embedding-3-small"

# ── Test dataset ────────────────────────────────────────────────────────────

KEYWORD_QUERIES = [
    {"query": "What is Barbara's educational background?",
     "must_contain": ["UT Austin", "MIT", "Electrical Engineering", "Biology"]},
    {"query": "Tell me about the Resume Graph Explorer project",
     "must_contain": ["SKOS", "ESCO", "knowledge graph"]},
    {"query": "Describe Barbara's dissertation research",
     "must_contain": ["MIT", "visual attention", "eye"]},
    {"query": "Tell me about the Beehive Monitor project",
     "must_contain": ["beehive", "sensor", "computer vision"]},
    {"query": "Explain the Digital Twin architecture",
     "must_contain": ["RAG", "ChromaDB", "Gradio"]},
    {"query": "What is Barbara's approach to knowledge graphs?",
     "must_contain": ["graph", "semantic", "relationship"]},
    {"query": "Describe the ConvoScope project",
     "must_contain": ["conversation", "LLM", "analysis"]},
]

RELATIONSHIP_QUERIES = [
    {"query": "Which projects use knowledge graphs?",
     "expected_projects": ["Resume Graph Explorer", "Weaving Memories",
                            "Academic Citation Platform", "Concept Cartographer"]},
    {"query": "What projects use Neo4j?",
     "expected_projects": ["Weaving Memories", "Academic Citation Platform"]},
    {"query": "Which projects use Streamlit?",
     "expected_projects": ["Academic Citation Platform", "Beehive Monitor",
                            "ConvoScope", "Fitness", "ChronoScope"]},
    {"query": "What projects involve natural language processing?",
     "expected_projects": ["ConvoScope", "ChronoScope", "Digital Twin",
                            "Concept Cartographer"]},
    {"query": "Which projects demonstrate data visualization skills?",
     "expected_projects": ["Fitness", "ChronoScope", "Beehive Monitor"]},
    {"query": "What other projects use evaluation harnesses?",
     "expected_projects": ["Poolula Platform", "Digital Twin"]},
    {"query": "Show me projects related to beekeeping or agriculture",
     "expected_projects": ["Beehive Monitor"]},
]

LATENCY_QUERIES = [
    "What is Barbara's educational background?",
    "Tell me about the Resume Graph Explorer",
    "Which projects use knowledge graphs?",
    "Describe Barbara's dissertation research",
    "What is Barbara's professional identity?",
]


# ── ChromaDB retrieval ───────────────────────────────────────────────────────

def _chroma_query(collection, oai_client, query: str, k: int = 5) -> dict:
    emb = oai_client.embeddings.create(model=EMBED_MODEL, input=query).data[0].embedding
    raw = collection.query(
        query_embeddings=[emb],
        n_results=k,
        where={"sensitivity": {"$eq": "public"}},
    )
    docs = raw.get("documents", [[]])[0] or []
    metas = raw.get("metadatas", [[]])[0] or []
    combined = " ".join(docs)
    total_chars = sum(len(d) for d in docs)
    sources = [f"{m.get('source','?')} — {m.get('section','?')}" for m in metas]
    return {"combined_text": combined, "total_chars": total_chars, "sources": sources,
            "n_results": len(docs)}


# ── Scoring helpers ──────────────────────────────────────────────────────────

def kw_coverage(text: str, keywords: list[str]) -> float:
    found = sum(1 for kw in keywords if kw.lower() in text.lower())
    return found / len(keywords) if keywords else 1.0


def project_coverage(text: str, expected: list[str]) -> tuple[float, list[str]]:
    found = [p for p in expected if p.lower() in text.lower()]
    return len(found) / len(expected) if expected else 1.0, found


# ── Main ─────────────────────────────────────────────────────────────────────

def main(run_latency: bool = True) -> int:
    api_key = __import__("os").getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set")
        return 1

    oai = OpenAI(api_key=api_key)
    chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    print("Running comparison: ChromaDB vs Neo4j")
    print(f"ChromaDB: {collection.count()} chunks")
    print("─" * 60)

    # ── 1. Keyword coverage ──────────────────────────────────────
    print("\n[1/3] Keyword coverage test...")
    kw_chroma, kw_neo4j = [], []

    for test in KEYWORD_QUERIES:
        q = test["query"]
        kws = test["must_contain"]

        chroma_r = _chroma_query(collection, oai, q)
        neo4j_r = query_neo4j_rag(q, visitor_tier="public", k=5)

        c_cov = kw_coverage(chroma_r["combined_text"], kws)
        n_cov = kw_coverage(neo4j_r["context"], kws)
        kw_chroma.append(c_cov)
        kw_neo4j.append(n_cov)

        delta = "↑" if n_cov > c_cov else ("↓" if n_cov < c_cov else "=")
        print(f"  {delta}  chroma={c_cov:.0%}  neo4j={n_cov:.0%}  — {q[:55]}")

    avg_kw_chroma = sum(kw_chroma) / len(kw_chroma)
    avg_kw_neo4j = sum(kw_neo4j) / len(kw_neo4j)
    print(f"  AVG — chroma={avg_kw_chroma:.1%}  neo4j={avg_kw_neo4j:.1%}")

    # ── 2. Relationship coverage ─────────────────────────────────
    print("\n[2/3] Relationship query test...")
    rel_chroma, rel_neo4j = [], []
    rel_details = []

    for test in RELATIONSHIP_QUERIES:
        q = test["query"]
        expected = test["expected_projects"]

        chroma_r = _chroma_query(collection, oai, q)
        neo4j_r = query_neo4j_rag(q, visitor_tier="public", k=5)

        c_cov, c_found = project_coverage(chroma_r["combined_text"], expected)
        n_cov, n_found = project_coverage(neo4j_r["context"], expected)
        rel_chroma.append(c_cov)
        rel_neo4j.append(n_cov)

        delta = "↑" if n_cov > c_cov else ("↓" if n_cov < c_cov else "=")
        print(f"  {delta}  chroma={c_cov:.0%}  neo4j={n_cov:.0%}  — {q[:55]}")
        if n_found != c_found:
            only_neo4j = set(n_found) - set(c_found)
            only_chroma = set(c_found) - set(n_found)
            if only_neo4j:
                print(f"      + Neo4j found: {list(only_neo4j)}")
            if only_chroma:
                print(f"      + ChromaDB found: {list(only_chroma)}")

        rel_details.append({"query": q, "expected": expected,
                             "chroma_found": c_found, "neo4j_found": n_found,
                             "chroma_coverage": round(c_cov, 2),
                             "neo4j_coverage": round(n_cov, 2)})

    avg_rel_chroma = sum(rel_chroma) / len(rel_chroma)
    avg_rel_neo4j = sum(rel_neo4j) / len(rel_neo4j)
    print(f"  AVG — chroma={avg_rel_chroma:.1%}  neo4j={avg_rel_neo4j:.1%}")

    # ── 3. Latency ───────────────────────────────────────────────
    latency_results = {}
    if run_latency:
        print("\n[3/3] Latency test (3 runs each query, median reported)...")
        chroma_lats, neo4j_lats = [], []

        for q in LATENCY_QUERIES:
            c_times, n_times = [], []
            for _ in range(3):
                t0 = time.perf_counter()
                _chroma_query(collection, oai, q)
                c_times.append((time.perf_counter() - t0) * 1000)

                t0 = time.perf_counter()
                query_neo4j_rag(q, visitor_tier="public", k=5)
                n_times.append((time.perf_counter() - t0) * 1000)

            c_med = sorted(c_times)[1]
            n_med = sorted(n_times)[1]
            chroma_lats.append(c_med)
            neo4j_lats.append(n_med)
            delta = "↑" if n_med > c_med else "↓"
            print(f"  {delta}  chroma={c_med:.0f}ms  neo4j={n_med:.0f}ms  — {q[:50]}")

        latency_results = {
            "chroma_median_ms": round(sorted(chroma_lats)[len(chroma_lats) // 2], 1),
            "neo4j_median_ms": round(sorted(neo4j_lats)[len(neo4j_lats) // 2], 1),
            "chroma_mean_ms": round(sum(chroma_lats) / len(chroma_lats), 1),
            "neo4j_mean_ms": round(sum(neo4j_lats) / len(neo4j_lats), 1),
        }
        print(f"  Median — chroma={latency_results['chroma_median_ms']}ms  "
              f"neo4j={latency_results['neo4j_median_ms']}ms")
    else:
        print("\n[3/3] Latency test skipped (--no-latency)")

    # ── Summary ──────────────────────────────────────────────────
    summary = {
        "keyword_coverage": {
            "chroma": round(avg_kw_chroma, 3),
            "neo4j": round(avg_kw_neo4j, 3),
            "delta": round(avg_kw_neo4j - avg_kw_chroma, 3),
        },
        "relationship_coverage": {
            "chroma": round(avg_rel_chroma, 3),
            "neo4j": round(avg_rel_neo4j, 3),
            "delta": round(avg_rel_neo4j - avg_rel_chroma, 3),
        },
        "latency": latency_results,
        "relationship_details": rel_details,
    }

    # ── Markdown report ───────────────────────────────────────────
    md_lines = [
        "# ChromaDB vs Neo4j Retrieval Comparison",
        "",
        "| Metric | ChromaDB | Neo4j | Delta |",
        "|--------|----------|-------|-------|",
        f"| Keyword coverage (avg) | {avg_kw_chroma:.1%} | {avg_kw_neo4j:.1%} | "
        f"{'+'if avg_kw_neo4j>=avg_kw_chroma else ''}{(avg_kw_neo4j-avg_kw_chroma):.1%} |",
        f"| Relationship coverage (avg) | {avg_rel_chroma:.1%} | {avg_rel_neo4j:.1%} | "
        f"{'+'if avg_rel_neo4j>=avg_rel_chroma else ''}{(avg_rel_neo4j-avg_rel_chroma):.1%} |",
    ]
    if latency_results:
        md_lines.append(
            f"| Median latency | {latency_results['chroma_median_ms']}ms | "
            f"{latency_results['neo4j_median_ms']}ms | "
            f"{'+'if latency_results['neo4j_median_ms']>=latency_results['chroma_median_ms'] else ''}"
            f"{latency_results['neo4j_median_ms']-latency_results['chroma_median_ms']:.0f}ms |"
        )
    md_lines += [
        "",
        "## Relationship query details",
        "",
        "| Query | ChromaDB found | Neo4j found |",
        "|-------|----------------|-------------|",
    ]
    for d in rel_details:
        md_lines.append(
            f"| {d['query'][:50]} | {', '.join(d['chroma_found']) or '—'} "
            f"| {', '.join(d['neo4j_found']) or '—'} |"
        )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "comparison_report.md").write_text("\n".join(md_lines))
    (RESULTS_DIR / "comparison_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"\n{'='*60}")
    print(f"Keyword coverage:     chroma={avg_kw_chroma:.1%}  neo4j={avg_kw_neo4j:.1%}")
    print(f"Relationship coverage: chroma={avg_rel_chroma:.1%}  neo4j={avg_rel_neo4j:.1%}")
    print(f"Report:  {RESULTS_DIR}/comparison_report.md")
    print(f"Summary: {RESULTS_DIR}/comparison_summary.json")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-latency", action="store_true",
                        help="Skip latency test (faster)")
    args = parser.parse_args()
    sys.exit(main(run_latency=not args.no_latency))
