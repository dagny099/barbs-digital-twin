#!/usr/bin/env python3
"""
Offline Evaluation Runner for Digital Twin

This script runs a set of evaluation questions through the Digital Twin
and saves the results for later analysis.

Usage:
    python run_evals.py                    # Run all questions
    python run_evals.py --category bio     # Run only biographical questions
    python run_evals.py --limit 10         # Run only first 10 questions
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Import from your existing app.py
# We'll query the RAG system directly
import chromadb
from openai import OpenAI


#------ CONFIGURATION ------
_HERE = Path(__file__).parent          # evals/
_ROOT = _HERE.parent                   # project root

QUESTIONS_FILE = str(_HERE / "eval_questions.csv")
RESULTS_DIR    = str(_HERE / "eval_results")
CHROMA_PATH    = str(_ROOT / ".chroma_db_DT")
SYSTEM_PROMPT_FILE = str(_ROOT / "SYSTEM_PROMPT.md")
COLLECTION_NAME = "barb-twin"
OPENAI_MODEL      = os.getenv("LLM_MODEL", "gpt-4.1-mini")
N_CHUNKS_RETRIEVE = int(os.getenv("N_CHUNKS_RETRIEVE", 10))  # Must match app.py
LLM_TEMPERATURE   = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Ensure results directory exists
Path(RESULTS_DIR).mkdir(exist_ok=True)


#------ LOAD CHROMADB CLIENT ------
def get_collection():
    """Get the ChromaDB collection (same as app.py)"""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )
    return collection


#------ QUERY THE RAG SYSTEM ------
def query_digital_twin(
    question: str,
    openai_client: OpenAI,
    collection
) -> Dict:
    """
    Query the Digital Twin RAG system and return detailed results.

    Returns:
        dict with keys: response, retrieved_chunks, model_used
    """

    # Step 1: Embed the question
    embed_response = openai_client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    query_embedding = embed_response.data[0].embedding

    # Step 2: Retrieve relevant chunks (matches N_CHUNKS_RETRIEVE in app.py)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=N_CHUNKS_RETRIEVE
    )

    # Extract retrieved chunks with metadata
    retrieved_chunks = []
    if results['documents'] and len(results['documents'][0]) > 0:
        for i, doc in enumerate(results['documents'][0]):
            chunk_info = {
                'text': doc,
                'source': results['metadatas'][0][i].get('source', 'unknown'),
                'section': results['metadatas'][0][i].get('section', None),
                'chunk_index': results['metadatas'][0][i].get('chunk_index', None)
            }
            retrieved_chunks.append(chunk_info)

    # Step 3: Build context
    if retrieved_chunks:
        context_text = "\n\n---\n\n".join([
            f"Source: {c['source']}\n{c['text']}"
            for c in retrieved_chunks
        ])
    else:
        context_text = "(No relevant context found)"

    # Step 4: Build system prompt — same base as app.py (reads SYSTEM_PROMPT.md)
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as _f:
        system_prompt_base = _f.read()
    system_prompt = system_prompt_base + f"\n\nContext:\n{context_text}"

    # Step 5: Call LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    completion = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=LLM_TEMPERATURE,
    )

    response_text = completion.choices[0].message.content

    return {
        'response': response_text,
        'retrieved_chunks': retrieved_chunks,
        'model_used': OPENAI_MODEL,
        'context_found': len(retrieved_chunks) > 0
    }


#------ LOAD QUESTIONS ------
def load_questions(
    filepath: str,
    category_filter: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict]:
    """Load questions from CSV file"""

    if not os.path.exists(filepath):
        print(f"ERROR: Questions file not found: {filepath}")
        print(f"Expected: {filepath}")
        sys.exit(1)

    questions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if category_filter and row['category'] != category_filter:
                continue
            questions.append(row)

            if limit and len(questions) >= limit:
                break

    return questions


#------ RUN EVALUATION ------
def run_evaluation(
    questions: List[Dict],
    openai_client: OpenAI,
    collection
) -> List[Dict]:
    """Run evaluation on a list of questions"""

    results = []
    total = len(questions)

    print(f"\n{'='*60}")
    print(f"Running evaluation on {total} questions")
    print(f"{'='*60}\n")

    for i, q in enumerate(questions, 1):
        question_text = q['question']
        category = q['category']

        print(f"[{i}/{total}] {category}: {question_text[:60]}...")

        try:
            result = query_digital_twin(question_text, openai_client, collection)

            # Add metadata
            result['question'] = question_text
            result['category'] = category
            result['expected_info'] = q.get('expected_info', '')
            result['notes'] = q.get('notes', '')
            result['timestamp'] = datetime.now().isoformat()

            # Print preview
            print(f"   ✓ Response preview: {result['response'][:80]}...")
            print(f"   ✓ Retrieved {len(result['retrieved_chunks'])} chunks\n")

            results.append(result)

        except Exception as e:
            print(f"   ✗ ERROR: {str(e)}\n")
            results.append({
                'question': question_text,
                'category': category,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })

    return results


#------ SAVE RESULTS ------
def save_results(results: List[Dict], output_dir: str = RESULTS_DIR):
    """Save results to JSON file with timestamp"""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(output_dir, f"eval_results_{timestamp}.json")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*60}\n")

    return output_file


#------ MAIN ------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run offline evaluations")
    parser.add_argument('--category', type=str, help='Filter by category (e.g., bio, projects)')
    parser.add_argument('--limit', type=int, help='Limit number of questions')
    parser.add_argument('--questions', type=str, default=QUESTIONS_FILE, help='Path to questions CSV')

    args = parser.parse_args()

    # Load OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)

    openai_client = OpenAI(api_key=api_key)

    # Load ChromaDB collection
    print("Loading ChromaDB collection...")
    collection = get_collection()
    print(f"Collection loaded: {collection.count()} chunks\n")

    # Load questions
    questions = load_questions(
        args.questions,
        category_filter=args.category,
        limit=args.limit
    )

    if not questions:
        print("No questions found matching your criteria.")
        sys.exit(0)

    # Run evaluation
    results = run_evaluation(questions, openai_client, collection)

    # Save results
    output_file = save_results(results)

    # Print summary
    print("\nSummary:")
    print(f"  Total questions: {len(results)}")
    print(f"  Successful: {sum(1 for r in results if 'response' in r and 'error' not in r)}")
    print(f"  Errors: {sum(1 for r in results if 'error' in r)}")

    print(f"\nNext steps:")
    print(f"  1. Review results in: {output_file}")
    print(f"  2. Run analysis: python analyze_evals.py")
    print(f"  3. Manual grading: Import to eval_review.csv for scoring\n")


if __name__ == "__main__":
    main()
