"""
embed_sections.py
=================
Phase 2 Step 4: Generate and store embeddings for all Section nodes.

Uses OpenAI text-embedding-3-small (1536-dim) with MD5 hash-based disk cache
to avoid redundant API calls on re-runs.

Run after populate_neo4j_graph.py:
    python scripts/embed_sections.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from neo4j_utils import get_driver, close_driver

load_dotenv(override=True)

SCRIPTS_DIR  = Path(__file__).resolve().parent
CACHE_DIR    = SCRIPTS_DIR / ".embedding_cache"
EMBED_MODEL  = "text-embedding-3-small"
BATCH_SIZE   = 100  # Conservative; OpenAI allows up to 2048 inputs per call


def _cache_path(text: str) -> Path:
    key = hashlib.md5(text.encode()).hexdigest()
    return CACHE_DIR / f"{key}.json"


def _get_cached(text: str) -> list[float] | None:
    p = _cache_path(text)
    if p.exists():
        return json.loads(p.read_text())["embedding"]
    return None


def _save_cached(text: str, embedding: list[float]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(text).write_text(json.dumps({
        "text_preview": text[:120],
        "embedding": embedding,
    }))


def embed_batch(texts: list[str], client: OpenAI) -> tuple[list[list[float]], int, int]:
    """
    Embed texts using cache where possible.
    Returns (embeddings, cache_hits, api_calls).
    """
    results    = [None] * len(texts)
    to_embed   = []  # (index, text) not in cache
    cache_hits = 0

    for i, text in enumerate(texts):
        cached = _get_cached(text)
        if cached is not None:
            results[i] = cached
            cache_hits += 1
        else:
            to_embed.append((i, text))

    if to_embed:
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=[t for _, t in to_embed],
        )
        for (i, text), item in zip(to_embed, response.data):
            results[i] = item.embedding
            _save_cached(text, item.embedding)

    return results, cache_hits, len(to_embed)


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not set")
        sys.exit(1)

    driver = get_driver()
    client = OpenAI(api_key=api_key)

    with driver.session() as session:
        total   = session.run("MATCH (s:Section) RETURN count(s) AS cnt").single()["cnt"]
        missing = session.run(
            "MATCH (s:Section) WHERE s.embedding IS NULL RETURN count(s) AS cnt"
        ).single()["cnt"]

    print(f"\nSection nodes: {total} total, {missing} without embeddings")

    if missing == 0:
        print("✓ All sections already have embeddings — nothing to do")
        close_driver()
        return

    with driver.session() as session:
        records = session.run(
            "MATCH (s:Section) WHERE s.embedding IS NULL RETURN s.id AS id, s.full_text AS text"
        ).data()

    print(f"Generating embeddings for {len(records)} sections...")
    total_cached = 0
    total_api    = 0

    for batch_start in range(0, len(records), BATCH_SIZE):
        batch = records[batch_start : batch_start + BATCH_SIZE]
        texts = [r["text"] for r in batch]

        embeddings, cache_hits, api_calls = embed_batch(texts, client)
        total_cached += cache_hits
        total_api    += api_calls

        with driver.session() as session:
            for record, embedding in zip(batch, embeddings):
                session.run(
                    "MATCH (s:Section {id: $id}) SET s.embedding = $embedding",
                    {"id": record["id"], "embedding": embedding},
                )

        end_idx = min(batch_start + BATCH_SIZE, len(records))
        print(f"  Sections {batch_start + 1}–{end_idx}: "
              f"{cache_hits} cached, {api_calls} from API ✓")

    close_driver()
    print(f"\n✓ Embedding complete")
    print(f"  From cache : {total_cached}")
    print(f"  From API   : {total_api}")
    print(f"\nVector index is now populated. Run test_neo4j_connection.py to verify.")


if __name__ == "__main__":
    main()
