#!/usr/bin/env python3
"""
Evaluation Results Analyzer

Analyzes the results from run_evals.py and produces a summary report.

Usage:
    python analyze_evals.py                           # Analyze latest results
    python analyze_evals.py --file eval_results/...   # Analyze specific file
    python analyze_evals.py --export                  # Export to CSV for manual review
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


RESULTS_DIR = str(Path(__file__).parent / "eval_results")


#------ LOAD RESULTS ------
def get_latest_results_file(results_dir: str = RESULTS_DIR) -> str:
    """Get the most recent results file"""
    results_files = list(Path(results_dir).glob("eval_results_*.json"))

    if not results_files:
        print(f"ERROR: No results files found in {results_dir}")
        print("Run 'python run_evals.py' first to generate results.")
        sys.exit(1)

    # Sort by modification time, newest first
    latest = max(results_files, key=lambda p: p.stat().st_mtime)
    return str(latest)


def load_results(filepath: str) -> List[Dict]:
    """Load results from JSON file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


#------ ANALYSIS ------
def analyze_results(results: List[Dict]) -> Dict:
    """Analyze results and produce summary statistics"""

    stats = {
        'total_questions': len(results),
        'successful': 0,
        'errors': 0,
        'by_category': defaultdict(lambda: {'total': 0, 'successful': 0, 'errors': 0}),
        'retrieval_stats': {
            'no_context': 0,
            'one_chunk': 0,
            'two_chunks': 0,
            'three_chunks': 0
        },
        'flagged_for_review': []
    }

    for result in results:
        category = result.get('category', 'unknown')
        stats['by_category'][category]['total'] += 1

        # Success vs error
        if 'error' in result:
            stats['errors'] += 1
            stats['by_category'][category]['errors'] += 1
        else:
            stats['successful'] += 1
            stats['by_category'][category]['successful'] += 1

            # Retrieval stats
            num_chunks = len(result.get('retrieved_chunks', []))
            if num_chunks == 0:
                stats['retrieval_stats']['no_context'] += 1
                # Flag questions with no retrieved context
                stats['flagged_for_review'].append({
                    'question': result['question'],
                    'category': category,
                    'reason': 'No context retrieved',
                    'response': result.get('response', '')[:100]
                })
            elif num_chunks == 1:
                stats['retrieval_stats']['one_chunk'] += 1
            elif num_chunks == 2:
                stats['retrieval_stats']['two_chunks'] += 1
            elif num_chunks == 3:
                stats['retrieval_stats']['three_chunks'] += 1

            # Flag very short responses (possible failures)
            response_length = len(result.get('response', ''))
            if response_length < 50:
                stats['flagged_for_review'].append({
                    'question': result['question'],
                    'category': category,
                    'reason': f'Very short response ({response_length} chars)',
                    'response': result.get('response', '')
                })

    return stats


#------ REPORTING ------
def print_report(stats: Dict, results_file: str):
    """Print a formatted analysis report"""

    print(f"\n{'='*70}")
    print(f"EVALUATION RESULTS ANALYSIS")
    print(f"{'='*70}")
    print(f"Results file: {results_file}\n")

    # Overall stats
    print(f"OVERALL STATISTICS")
    print(f"{'-'*70}")
    print(f"  Total questions:     {stats['total_questions']}")
    print(f"  Successful:          {stats['successful']} ({stats['successful']/stats['total_questions']*100:.1f}%)")
    print(f"  Errors:              {stats['errors']}")
    print()

    # By category
    print(f"BY CATEGORY")
    print(f"{'-'*70}")
    for category, cat_stats in sorted(stats['by_category'].items()):
        success_rate = (cat_stats['successful'] / cat_stats['total'] * 100) if cat_stats['total'] > 0 else 0
        print(f"  {category:15s}  Total: {cat_stats['total']:2d}  |  Success: {cat_stats['successful']:2d}  |  Errors: {cat_stats['errors']:2d}  |  Rate: {success_rate:5.1f}%")
    print()

    # Retrieval stats
    print(f"RETRIEVAL STATISTICS")
    print(f"{'-'*70}")
    total_with_results = stats['successful']
    if total_with_results > 0:
        print(f"  No context:          {stats['retrieval_stats']['no_context']:2d} ({stats['retrieval_stats']['no_context']/total_with_results*100:5.1f}%)")
        print(f"  1 chunk retrieved:   {stats['retrieval_stats']['one_chunk']:2d} ({stats['retrieval_stats']['one_chunk']/total_with_results*100:5.1f}%)")
        print(f"  2 chunks retrieved:  {stats['retrieval_stats']['two_chunks']:2d} ({stats['retrieval_stats']['two_chunks']/total_with_results*100:5.1f}%)")
        print(f"  3 chunks retrieved:  {stats['retrieval_stats']['three_chunks']:2d} ({stats['retrieval_stats']['three_chunks']/total_with_results*100:5.1f}%)")
    print()

    # Flagged items
    if stats['flagged_for_review']:
        print(f"FLAGGED FOR MANUAL REVIEW ({len(stats['flagged_for_review'])} items)")
        print(f"{'-'*70}")
        for i, item in enumerate(stats['flagged_for_review'][:10], 1):  # Show first 10
            print(f"\n  {i}. [{item['category']}] {item['question']}")
            print(f"     Reason: {item['reason']}")
            print(f"     Response: {item['response'][:80]}...")

        if len(stats['flagged_for_review']) > 10:
            print(f"\n  ... and {len(stats['flagged_for_review']) - 10} more")
    else:
        print(f"FLAGGED FOR MANUAL REVIEW")
        print(f"{'-'*70}")
        print(f"  No items flagged! All responses had adequate context and length.")

    print(f"\n{'='*70}\n")


#------ EXPORT FOR MANUAL REVIEW ------
def export_for_review(results: List[Dict], output_file: str = "eval_review.csv"):
    """Export results to CSV for manual grading"""
    import csv

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'category',
            'question',
            'response',
            'expected_info',
            'accuracy_1_5',
            'personality_1_5',
            'retrieval_quality_1_5',
            'notes'
        ])

        for result in results:
            if 'error' not in result:
                writer.writerow([
                    result.get('category', ''),
                    result.get('question', ''),
                    result.get('response', ''),
                    result.get('expected_info', ''),
                    '',  # accuracy - to be filled manually
                    '',  # personality - to be filled manually
                    '',  # retrieval_quality - to be filled manually
                    ''   # notes - to be filled manually
                ])

    print(f"Exported {len([r for r in results if 'error' not in r])} results to {output_file}")
    print(f"Open in Excel/Google Sheets and add ratings (1-5) for manual review.\n")


#------ MAIN ------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Analyze evaluation results")
    parser.add_argument('--file', type=str, help='Specific results file to analyze')
    parser.add_argument('--export', action='store_true', help='Export to CSV for manual review')

    args = parser.parse_args()

    # Load results
    if args.file:
        results_file = args.file
    else:
        results_file = get_latest_results_file()

    print(f"Loading results from: {results_file}")
    results = load_results(results_file)

    # Analyze
    stats = analyze_results(results)

    # Print report
    print_report(stats, results_file)

    # Export if requested
    if args.export:
        export_for_review(results)

    # Next steps
    print("NEXT STEPS:")
    print("  1. Review flagged items above")
    print("  2. Run with --export to create manual review sheet")
    print("  3. Import eval_review.csv to Google Sheets for collaborative grading")
    print("  4. Look for patterns in failed retrievals")
    print()


if __name__ == "__main__":
    main()
