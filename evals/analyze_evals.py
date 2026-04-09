#!/usr/bin/env python3
"""
Evaluation Results Analyzer (Richer Schema Edition)

Understands both:
- legacy list-based result files
- richer payloads with run_metadata + results

Adds:
- schema-aware export for manual review
- richer stats on question types and issue patterns
- project-overuse and follow-up diagnostics
"""

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

RESULTS_DIR = str(Path(__file__).resolve().parent / "eval_results")


def get_latest_results_file(results_dir: str = RESULTS_DIR) -> str:
    results_files = list(Path(results_dir).glob("eval_results_*.json"))
    if not results_files:
        print(f"ERROR: No results files found in {results_dir}")
        print("Run 'python run_evals_rich.py' first to generate results.")
        sys.exit(1)
    latest = max(results_files, key=lambda p: p.stat().st_mtime)
    return str(latest)


def load_results(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return {}, payload
    if isinstance(payload, dict):
        return payload.get("run_metadata", {}), payload.get("results", [])
    raise ValueError("Unsupported results file format")


def analyze_results(results):
    stats = {
        "total_questions": len(results),
        "successful": 0,
        "errors": 0,
        "by_category": defaultdict(lambda: {"total": 0, "successful": 0, "errors": 0}),
        "by_question_type": defaultdict(lambda: {"total": 0, "successful": 0, "errors": 0}),
        "retrieval_stats": {"no_context": 0, "one_chunk": 0, "two_chunks": 0, "three_or_more_chunks": 0},
        "feature_stats": {"with_followup": 0, "with_links": 0, "markdown_none": 0, "markdown_light": 0, "markdown_strong": 0},
        "avg_response_words": None,
        "avg_similarity": None,
        "flagged_for_review": [],
        "project_mentions": Counter(),
        "common_issue_sources": Counter(),
    }

    response_lengths = []
    similarities = []

    for result in results:
        category = result.get("legacy_category") or result.get("category") or "unknown"
        question_type = result.get("question_type") or "unknown"
        stats["by_category"][category]["total"] += 1
        stats["by_question_type"][question_type]["total"] += 1

        if "error" in result:
            stats["errors"] += 1
            stats["by_category"][category]["errors"] += 1
            stats["by_question_type"][question_type]["errors"] += 1
            stats["flagged_for_review"].append(
                {"question": result.get("question", ""), "category": category, "reason": f"Error: {result['error']}", "response": ""}
            )
            continue

        stats["successful"] += 1
        stats["by_category"][category]["successful"] += 1
        stats["by_question_type"][question_type]["successful"] += 1

        num_chunks = len(result.get("retrieved_chunks", []))
        if num_chunks == 0:
            stats["retrieval_stats"]["no_context"] += 1
            stats["flagged_for_review"].append(
                {
                    "question": result.get("question", ""),
                    "category": category,
                    "reason": "No context retrieved",
                    "response": (result.get("response") or "")[:120],
                }
            )
        elif num_chunks == 1:
            stats["retrieval_stats"]["one_chunk"] += 1
        elif num_chunks == 2:
            stats["retrieval_stats"]["two_chunks"] += 1
        else:
            stats["retrieval_stats"]["three_or_more_chunks"] += 1

        response_text = result.get("response", "")
        response_len = result.get("response_length_words")
        if response_len is None:
            response_len = len((response_text or "").split())
        response_lengths.append(response_len)

        sim = result.get("chunk_similarity_avg")
        if sim is not None:
            similarities.append(sim)

        if response_len < 30:
            stats["flagged_for_review"].append(
                {
                    "question": result.get("question", ""),
                    "category": category,
                    "reason": f"Very short response ({response_len} words)",
                    "response": response_text[:120],
                }
            )

        if result.get("followup_present"):
            stats["feature_stats"]["with_followup"] += 1
        if result.get("links_used"):
            stats["feature_stats"]["with_links"] += 1

        md = result.get("markdown_used", "none")
        if md == "strong":
            stats["feature_stats"]["markdown_strong"] += 1
        elif md == "light":
            stats["feature_stats"]["markdown_light"] += 1
        else:
            stats["feature_stats"]["markdown_none"] += 1

        for project in result.get("specific_projects_mentioned", []) or []:
            stats["project_mentions"][project] += 1

        if result.get("issue_source"):
            stats["common_issue_sources"][result["issue_source"]] += 1

    stats["avg_response_words"] = round(mean(response_lengths), 1) if response_lengths else None
    stats["avg_similarity"] = round(mean(similarities), 3) if similarities else None
    return stats


def _rate(successful: int, total: int) -> float:
    return (successful / total * 100.0) if total else 0.0


def print_report(stats, results_file, run_metadata):
    print(f"\n{'='*78}")
    print("EVALUATION RESULTS ANALYSIS")
    print(f"{'='*78}")
    print(f"Results file: {results_file}")
    if run_metadata:
        print(
            f"Run metadata: model={run_metadata.get('model', '')} | provider={run_metadata.get('provider', '')} | temperature={run_metadata.get('temperature', '')} | top_k={run_metadata.get('top_k', '')}"
        )
    print()

    print("OVERALL STATISTICS")
    print("-" * 78)
    print(f"  Total questions:     {stats['total_questions']}")
    print(f"  Successful:          {stats['successful']} ({_rate(stats['successful'], stats['total_questions']):.1f}%)")
    print(f"  Errors:              {stats['errors']}")
    print(f"  Avg response words:  {stats['avg_response_words']}")
    print(f"  Avg similarity:      {stats['avg_similarity']}")
    print()

    print("BY CATEGORY")
    print("-" * 78)
    for category, cat_stats in sorted(stats["by_category"].items()):
        print(
            f"  {category:18s} Total: {cat_stats['total']:2d}  |  Success: {cat_stats['successful']:2d}  |  Errors: {cat_stats['errors']:2d}  |  Rate: {_rate(cat_stats['successful'], cat_stats['total']):5.1f}%"
        )
    print()

    print("BY QUESTION TYPE")
    print("-" * 78)
    for qtype, q_stats in sorted(stats["by_question_type"].items()):
        print(
            f"  {qtype:18s} Total: {q_stats['total']:2d}  |  Success: {q_stats['successful']:2d}  |  Errors: {q_stats['errors']:2d}  |  Rate: {_rate(q_stats['successful'], q_stats['total']):5.1f}%"
        )
    print()

    print("RETRIEVAL STATISTICS")
    print("-" * 78)
    total_with_results = stats["successful"] or 1
    print(f"  No context:             {stats['retrieval_stats']['no_context']:2d} ({stats['retrieval_stats']['no_context']/total_with_results*100:5.1f}%)")
    print(f"  1 chunk retrieved:      {stats['retrieval_stats']['one_chunk']:2d} ({stats['retrieval_stats']['one_chunk']/total_with_results*100:5.1f}%)")
    print(f"  2 chunks retrieved:     {stats['retrieval_stats']['two_chunks']:2d} ({stats['retrieval_stats']['two_chunks']/total_with_results*100:5.1f}%)")
    print(f"  3+ chunks retrieved:    {stats['retrieval_stats']['three_or_more_chunks']:2d} ({stats['retrieval_stats']['three_or_more_chunks']/total_with_results*100:5.1f}%)")
    print()

    print("RESPONSE FEATURES")
    print("-" * 78)
    print(f"  With follow-up:         {stats['feature_stats']['with_followup']:2d}")
    print(f"  With links:             {stats['feature_stats']['with_links']:2d}")
    print(
        f"  Markdown none/light/strong: {stats['feature_stats']['markdown_none']}/{stats['feature_stats']['markdown_light']}/{stats['feature_stats']['markdown_strong']}"
    )
    print()

    if stats["project_mentions"]:
        print("MOST COMMON PROJECTS MENTIONED")
        print("-" * 78)
        for project, count in stats["project_mentions"].most_common(8):
            print(f"  {project:35s} {count}")
        print()

    if stats["flagged_for_review"]:
        print(f"FLAGGED FOR MANUAL REVIEW ({len(stats['flagged_for_review'])} items)")
        print("-" * 78)
        for i, item in enumerate(stats["flagged_for_review"][:12], 1):
            print(f"\n  {i}. [{item['category']}] {item['question']}")
            print(f"     Reason: {item['reason']}")
            if item.get("response"):
                print(f"     Response: {item['response'][:90]}...")
        if len(stats["flagged_for_review"]) > 12:
            print(f"\n  ... and {len(stats['flagged_for_review']) - 12} more")
    else:
        print("FLAGGED FOR MANUAL REVIEW")
        print("-" * 78)
        print("  No items flagged!")

    print(f"\n{'='*78}\n")


def export_for_review(results, output_file="eval_review.csv"):
    columns = [
        "run_id",
        "question_id",
        "legacy_category",
        "question_type",
        "intent",
        "audience_mode",
        "difficulty",
        "priority",
        "question",
        "must_cover",
        "nice_to_have",
        "should_not_do",
        "preferred_structure",
        "preferred_followup_behavior",
        "acceptable_projects_or_examples",
        "grounding_expectation",
        "response",
        "response_length_words",
        "markdown_used",
        "links_used",
        "followup_present",
        "specific_projects_mentioned",
        "chunk_similarity_avg",
        "chunk_similarity_max",
        "accuracy_score",
        "specificity_score",
        "voice_fidelity_score",
        "narrative_arc_score",
        "followup_magnetism_score",
        "presentation_scanability_score",
        "relevance_score",
        "retrieval_alignment_score",
        "overall_score",
        "strengths_tags",
        "weakness_tags",
        "failure_mode_tags",
        "issue_source",
        "suggested_fix",
        "fix_priority",
        "retest_needed",
        "evaluator_notes",
    ]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        exported = 0
        for result in results:
            if "error" in result:
                continue
            row = {c: "" for c in columns}
            row.update(
                {
                    "run_id": result.get("run_id", ""),
                    "question_id": result.get("question_id", ""),
                    "legacy_category": result.get("legacy_category", result.get("category", "")),
                    "question_type": result.get("question_type", ""),
                    "intent": result.get("intent", ""),
                    "audience_mode": result.get("audience_mode", ""),
                    "difficulty": result.get("difficulty", ""),
                    "priority": result.get("priority", ""),
                    "question": result.get("question", ""),
                    "must_cover": result.get("must_cover", result.get("expected_info", "")),
                    "nice_to_have": result.get("nice_to_have", result.get("notes", "")),
                    "should_not_do": result.get("should_not_do", ""),
                    "preferred_structure": result.get("preferred_structure", ""),
                    "preferred_followup_behavior": result.get("preferred_followup_behavior", ""),
                    "acceptable_projects_or_examples": result.get("acceptable_projects_or_examples", ""),
                    "grounding_expectation": result.get("grounding_expectation", ""),
                    "response": result.get("response", ""),
                    "response_length_words": result.get("response_length_words", ""),
                    "markdown_used": result.get("markdown_used", ""),
                    "links_used": result.get("links_used", ""),
                    "followup_present": result.get("followup_present", ""),
                    "specific_projects_mentioned": " | ".join(result.get("specific_projects_mentioned", []) or []),
                    "chunk_similarity_avg": result.get("chunk_similarity_avg", ""),
                    "chunk_similarity_max": result.get("chunk_similarity_max", ""),
                }
            )
            writer.writerow(row)
            exported += 1
    print(f"Exported {exported} results to {output_file}")
    print("Open in Excel/Google Sheets and add manual scores, tags, and diagnosis.\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze evaluation results (richer schema aware)")
    parser.add_argument("--file", type=str, help="Specific results file to analyze")
    parser.add_argument("--export", action="store_true", help="Export richer CSV for manual review")
    parser.add_argument("--output", type=str, default="eval_review.csv", help="Output CSV path for --export")
    args = parser.parse_args()

    results_file = args.file or get_latest_results_file()
    print(f"Loading results from: {results_file}")
    run_metadata, results = load_results(results_file)
    stats = analyze_results(results)
    print_report(stats, results_file, run_metadata)
    if args.export:
        export_for_review(results, output_file=args.output)
    print("NEXT STEPS:")
    print("  1. Review flagged items above")
    print("  2. Use --export to create the richer manual-review sheet")
    print("  3. Tag weaknesses and assign issue_source diagnosis")
    print("  4. Compare model runs by category, question type, and repeated project mentions")
    print()


if __name__ == "__main__":
    main()
