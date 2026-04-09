#!/usr/bin/env python3
"""
Offline Evaluation Runner for Digital Twin (Richer Schema Edition)

Backwards-compatible with the legacy CSV shape:
    category,question,expected_info,notes

Also supports richer question-bank columns such as:
    question_id,source_of_question,legacy_category,question_type,intent,audience_mode,
    difficulty,priority,must_cover,nice_to_have,should_not_do,preferred_structure,
    preferred_followup_behavior,acceptable_projects_or_examples,grounding_expectation

Key upgrades:
- Preserves legacy workflow while carrying richer metadata into results
- Supports multi-provider completion models via LiteLLM
- Adds run-level metadata
- Derives lightweight response features for better review exports
- Stores retrieval similarity signals per chunk when available
"""

import csv
import json
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional

import chromadb
import litellm
from openai import OpenAI

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent

QUESTIONS_FILE = str(_HERE / "eval_questions.csv")
RESULTS_DIR = str(_HERE / "eval_results")
CHROMA_PATH = str(_ROOT / ".chroma_db_DT")
SYSTEM_PROMPT_FILE = str(_ROOT / "SYSTEM_PROMPT.md")
COLLECTION_NAME = "barb-twin"

DEFAULT_MODEL = os.getenv("LLM_MODEL", "openai/gpt-4.1-mini")
DEFAULT_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
DEFAULT_TOP_K = int(os.getenv("N_CHUNKS_RETRIEVE", "10"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

PROJECT_PATTERNS = [
    "Digital Twin",
    "Resume Explorer",
    "Resume Graph Explorer",
    "Concept Cartographer",
    "ChronoScope",
    "ConvoScope",
    "Poolula Platform",
    "Beehive Photo Metadata Tracker",
    "Beehive Tracker",
    "Fitness Dashboard",
    "Weaving Memories Into Graphs",
]

FOLLOWUP_PATTERNS = [
    r"\blet me know\b",
    r"\bif you want\b",
    r"\bif you['’]re curious\b",
    r"\bwant me to\b",
    r"\bhappy to\b",
    r"\bI can walk through\b",
    r"\bI can talk more\b",
    r"\bI can share more\b",
]

LINK_PATTERN = re.compile(r"\[[^\]]+\]\([^)]+\)|https?://\S+", re.I)
BULLET_PATTERN = re.compile(r"^\s*(?:[-*]|\d+\.)\s+", re.M)

Path(RESULTS_DIR).mkdir(exist_ok=True)


def normalize_model_name(model_name: str) -> str:
    return model_name if "/" in model_name else f"openai/{model_name}"


def provider_from_model(model_name: str) -> str:
    return normalize_model_name(model_name).split("/", 1)[0]


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def compute_similarity_from_distance(distance):
    if distance is None:
        return None
    try:
        sim = 1.0 - float(distance)
        return max(0.0, min(1.0, sim))
    except Exception:
        return None


def build_run_id() -> str:
    return f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def markdown_usage(text: str) -> str:
    if not text:
        return "none"
    score = 0
    if BULLET_PATTERN.search(text):
        score += 1
    if "**" in text or "__" in text:
        score += 1
    if "#" in text:
        score += 1
    if LINK_PATTERN.search(text):
        score += 1
    if score == 0:
        return "none"
    if score == 1:
        return "light"
    return "strong"


def links_used(text: str) -> bool:
    return bool(LINK_PATTERN.search(text or ""))


def followup_present(text: str) -> bool:
    text = text or ""
    return any(re.search(p, text, re.I) for p in FOLLOWUP_PATTERNS)


def specific_projects_mentioned(text: str):
    text = text or ""
    found = []
    for project in PROJECT_PATTERNS:
        if re.search(re.escape(project), text, re.I):
            found.append(project)
    return found


def load_system_prompt() -> str:
    with open(SYSTEM_PROMPT_FILE, "r", encoding="utf-8") as f:
        return f.read()


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    return OpenAI(api_key=api_key)


def load_questions(filepath: str, category_filter: Optional[str] = None, limit: Optional[int] = None):
    if not os.path.exists(filepath):
        print(f"ERROR: Questions file not found: {filepath}")
        sys.exit(1)
    questions = []
    with open(filepath, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip(): (v if v is not None else "") for k, v in row.items()}
            category_value = row.get("legacy_category") or row.get("category") or ""
            if category_filter and category_value != category_filter:
                continue
            row["question"] = (row.get("question") or "").strip()
            row["legacy_category"] = category_value
            row["question_id"] = row.get("question_id") or ""
            row["question_type"] = row.get("question_type") or ""
            row["intent"] = row.get("intent") or ""
            row["audience_mode"] = row.get("audience_mode") or ""
            row["difficulty"] = row.get("difficulty") or ""
            row["priority"] = row.get("priority") or ""
            row["must_cover"] = row.get("must_cover") or row.get("expected_info") or ""
            row["nice_to_have"] = row.get("nice_to_have") or row.get("notes") or ""
            row["should_not_do"] = row.get("should_not_do") or ""
            row["preferred_structure"] = row.get("preferred_structure") or ""
            row["preferred_followup_behavior"] = row.get("preferred_followup_behavior") or ""
            row["acceptable_projects_or_examples"] = row.get("acceptable_projects_or_examples") or ""
            row["grounding_expectation"] = row.get("grounding_expectation") or ""
            row["source_of_question"] = row.get("source_of_question") or ""
            row["notes"] = row.get("notes") or ""
            if not row["question"]:
                continue
            questions.append(row)
            if limit and len(questions) >= limit:
                break
    return questions


def query_digital_twin(question: str, embed_client: OpenAI, collection, model_name: str, temperature: float, top_k: int, system_prompt_base: str):
    embed_response = embed_client.embeddings.create(input=question, model=EMBED_MODEL)
    query_embedding = embed_response.data[0].embedding
    raw_results = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    retrieved_chunks = []
    docs = raw_results.get("documents", [[]])[0] if raw_results.get("documents") else []
    metas = raw_results.get("metadatas", [[]])[0] if raw_results.get("metadatas") else []
    distances = raw_results.get("distances", [[]])[0] if raw_results.get("distances") else []

    for i, doc in enumerate(docs):
        meta = metas[i] if i < len(metas) else {}
        distance = distances[i] if i < len(distances) else None
        similarity = compute_similarity_from_distance(distance)
        retrieved_chunks.append(
            {
                "text": doc,
                "source": meta.get("source", "unknown"),
                "section": meta.get("section"),
                "chunk_index": meta.get("chunk_index"),
                "distance": distance,
                "similarity": similarity,
            }
        )

    if retrieved_chunks:
        context_text = "\n\n---\n\n".join(
            [
                f"Source: {c['source']}" + (f" | Section: {c['section']}" if c.get("section") else "") + "\n" + c["text"]
                for c in retrieved_chunks
            ]
        )
    else:
        context_text = "(No relevant context found)"

    system_prompt = system_prompt_base + f"\n\nContext:\n{context_text}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    completion = litellm.completion(model=normalize_model_name(model_name), messages=messages, temperature=temperature)
    response_text = completion.choices[0].message.content or ""

    similarities = [c["similarity"] for c in retrieved_chunks if c.get("similarity") is not None]
    avg_similarity = round(mean(similarities), 3) if similarities else None
    max_similarity = round(max(similarities), 3) if similarities else None

    usage = getattr(completion, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    completion_tokens = getattr(usage, "completion_tokens", None) if usage else None
    total_tokens = getattr(usage, "total_tokens", None) if usage else None
    try:
        cost_usd = litellm.completion_cost(completion_response=completion)
    except Exception:
        cost_usd = None

    return {
        "response": response_text,
        "retrieved_chunks": retrieved_chunks,
        "model_used": normalize_model_name(model_name),
        "provider": provider_from_model(model_name),
        "context_found": len(retrieved_chunks) > 0,
        "chunk_similarity_avg": avg_similarity,
        "chunk_similarity_max": max_similarity,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "response_length_words": word_count(response_text),
        "markdown_used": markdown_usage(response_text),
        "links_used": links_used(response_text),
        "followup_present": followup_present(response_text),
        "specific_projects_mentioned": specific_projects_mentioned(response_text),
    }


def run_evaluation(questions, embed_client, collection, model_name, temperature, top_k, run_id):
    results = []
    total = len(questions)
    system_prompt_base = load_system_prompt()
    print(f"\n{'='*70}")
    print(f"Running evaluation on {total} questions")
    print(f"Model: {normalize_model_name(model_name)} | Temperature: {temperature} | Top-K: {top_k}")
    print(f"{'='*70}\n")
    for i, q in enumerate(questions, 1):
        question_text = q["question"]
        category = q.get("legacy_category", "")
        print(f"[{i}/{total}] {category or 'uncategorized'}: {question_text[:80]}...")
        try:
            result = query_digital_twin(question_text, embed_client, collection, model_name, temperature, top_k, system_prompt_base)
            result.update(
                {
                    "run_id": run_id,
                    "timestamp": datetime.now().isoformat(),
                    "question": question_text,
                    "question_id": q.get("question_id", ""),
                    "source_of_question": q.get("source_of_question", ""),
                    "legacy_category": category,
                    "question_type": q.get("question_type", ""),
                    "intent": q.get("intent", ""),
                    "audience_mode": q.get("audience_mode", ""),
                    "difficulty": q.get("difficulty", ""),
                    "priority": q.get("priority", ""),
                    "must_cover": q.get("must_cover", ""),
                    "nice_to_have": q.get("nice_to_have", ""),
                    "should_not_do": q.get("should_not_do", ""),
                    "preferred_structure": q.get("preferred_structure", ""),
                    "preferred_followup_behavior": q.get("preferred_followup_behavior", ""),
                    "acceptable_projects_or_examples": q.get("acceptable_projects_or_examples", ""),
                    "grounding_expectation": q.get("grounding_expectation", ""),
                    "notes": q.get("notes", ""),
                    "expected_info": q.get("expected_info", ""),
                }
            )
            print(
                f"   ✓ {result['response_length_words']} words | {len(result['retrieved_chunks'])} chunks | sim(avg/max)={result['chunk_similarity_avg']}/{result['chunk_similarity_max']}"
            )
            print(f"   ✓ Response preview: {result['response'][:90].replace(chr(10), ' ')}...\n")
            results.append(result)
        except Exception as e:
            print(f"   ✗ ERROR: {str(e)}\n")
            results.append(
                {
                    "run_id": run_id,
                    "timestamp": datetime.now().isoformat(),
                    "question": question_text,
                    "question_id": q.get("question_id", ""),
                    "legacy_category": category,
                    "question_type": q.get("question_type", ""),
                    "intent": q.get("intent", ""),
                    "audience_mode": q.get("audience_mode", ""),
                    "must_cover": q.get("must_cover", ""),
                    "nice_to_have": q.get("nice_to_have", ""),
                    "notes": q.get("notes", ""),
                    "error": str(e),
                }
            )
    return results


def save_results(results, run_metadata, output_dir=RESULTS_DIR):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = os.path.join(output_dir, f"eval_results_{timestamp}.json")
    payload = {"schema_version": "2.0", "run_metadata": run_metadata, "results": results}
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n{'='*70}")
    print(f"Results saved to: {output_file}")
    print(f"{'='*70}\n")
    return output_file


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run offline evaluations (richer schema aware)")
    parser.add_argument("--category", type=str, help="Filter by legacy category")
    parser.add_argument("--limit", type=int, help="Limit number of questions")
    parser.add_argument("--questions", type=str, default=QUESTIONS_FILE, help="Path to questions CSV")
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL, help="LLM model for completion (supports LiteLLM provider prefixes)")
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help="Temperature for completion")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help="Number of chunks to retrieve")
    parser.add_argument("--label", type=str, default="", help="Optional run label")
    args = parser.parse_args()

    model_name = normalize_model_name(args.model)
    top_k = safe_int(args.top_k, DEFAULT_TOP_K)
    temperature = safe_float(args.temperature, DEFAULT_TEMPERATURE)

    embed_client = get_openai_client()
    print("Loading ChromaDB collection...")
    collection = get_collection()
    print(f"Collection loaded: {collection.count()} chunks\n")

    questions = load_questions(args.questions, category_filter=args.category, limit=args.limit)
    if not questions:
        print("No questions found matching your criteria.")
        sys.exit(0)

    run_id = build_run_id()
    run_metadata = {
        "run_id": run_id,
        "run_timestamp": datetime.now().isoformat(),
        "model": model_name,
        "provider": provider_from_model(model_name),
        "temperature": temperature,
        "top_k": top_k,
        "questions_file": os.path.abspath(args.questions),
        "question_count": len(questions),
        "label": args.label,
        "system_prompt_file": os.path.abspath(SYSTEM_PROMPT_FILE),
        "chroma_path": os.path.abspath(CHROMA_PATH),
    }

    results = run_evaluation(questions, embed_client, collection, model_name, temperature, top_k, run_id)
    output_file = save_results(results, run_metadata)

    print("\nSummary:")
    print(f"  Total questions: {len(results)}")
    print(f"  Successful: {sum(1 for r in results if 'response' in r and 'error' not in r)}")
    print(f"  Errors: {sum(1 for r in results if 'error' in r)}")
    print("\nNext steps:")
    print(f"  1. Review results in: {output_file}")
    print("  2. Run analysis: python analyze_evals_rich.py")
    print("  3. Export richer review sheet: python analyze_evals_rich.py --export\n")


if __name__ == "__main__":
    main()
