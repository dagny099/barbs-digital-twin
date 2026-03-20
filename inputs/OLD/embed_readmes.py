"""
embed_readmes.py
─────────────────────────────────────────────────────────────────
ONE-TIME script to chunk, embed, and persist all README files
into the existing ChromaDB collection used by app.py.

USAGE:
    1. Place this file in the same directory as app.py
    2. Make sure your READMEs/ folder is also there (or update PATH below)
    3. Run:  python embed_readmes.py
    4. Check the summary — then launch app.py as normal

FOLDER STRUCTURE EXPECTED:
    your-project/
    ├── app.py
    ├── embed_readmes.py          ← this file
    ├── .chroma_db_DT/            ← shared ChromaDB (created by app.py)
    └── READMEs/
        ├── concept-cartographer_README.md
        ├── beehive-monitor_README.md
        └── ...
"""

import os
import glob
import uuid
from openai import OpenAI
import chromadb
from pprint import pprint
from utils import chunk_prose, parse_paragraphs

# ── CONFIG ──────────────────────────────────────────────────────
README_FOLDER = "READMEs"          # folder containing your .md files
CHROMA_PATH   = ".chroma_db_DT"   # must match app.py
COLLECTION    = "barb-twin"        # must match app.py
CHUNK_SIZE    = 500                # must match app.py
OVERLAP       = 50                 # must match app.py
MIN_CHARS     = 100                # skip READMEs shorter than this (stubs)
# ────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("❌ OPENAI_API_KEY not set — check your environment variables")

client       = OpenAI(api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection   = chroma_client.get_or_create_collection(name=COLLECTION)


# ── CHUNKING ────────────────────────────────────────────────────
# NOTE: chunk_prose() and parse_paragraphs() are now imported from utils.py
#       to eliminate code duplication across ingestion scripts
# ────────────────────────────────────────────────────────────────


def load_readmes(folder: str) -> list[dict]:
    """Load all .md files from the READMEs folder."""
    pattern = os.path.join(folder, "*.md")
    files   = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"❌ No .md files found in '{folder}/' — check your path")

    docs, skipped = [], []
    for filepath in sorted(files):
        text = open(filepath, encoding="utf-8", errors="ignore").read().strip()
        repo_name = os.path.basename(filepath).replace("_README.md", "").replace(".md", "")

        if len(text) < MIN_CHARS:
            skipped.append(repo_name)
            continue

        docs.append({"source": f"github-readme:{repo_name}", "text": text})

    print(f"\n📁 Found {len(files)} files  →  {len(docs)} usable  |  {len(skipped)} skipped (too short)")
    if skipped:
        print(f"   Skipped: {skipped}")
    return docs


def already_embedded(source: str) -> bool:
    """Check if this source is already in the collection (safe to re-run)."""
    results = collection.get(where={"source": source})
    return len(results["ids"]) > 0


def embed_documents(docs: list[dict]):
    """Chunk → embed → store all docs. Skips already-embedded sources."""
    all_chunks, all_ids, all_metadatas = [], [], []
    skipped_sources = []

    for doc in docs:
        source = doc["source"]

        if already_embedded(source):
            skipped_sources.append(source)
            continue

        results  = chunk_prose(doc["text"], chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        chunks_  = [r["text"] for r in results]
        ids_     = [str(uuid.uuid4()) for _ in chunks_]
        # TODO: Future enhancement - parse README sections by numbered headers (# 1., # 2., etc.)
        # and populate section field. For now, omit section field for README chunks.
        metas_   = [{"source": source, "chunk_index": i} for i in range(len(chunks_))]

        all_chunks.extend(chunks_)
        all_ids.extend(ids_)
        all_metadatas.extend(metas_)
        print(f"   ✅ {source}  →  {len(chunks_)} chunks")

    if skipped_sources:
        print(f"\n⏭️  Already embedded ({len(skipped_sources)} sources) — skipping:")
        for s in skipped_sources:
            print(f"   • {s}")

    if not all_chunks:
        print("\n✨ Nothing new to embed — collection is already up to date!")
        return 0

    print(f"\n🔢 Embedding {len(all_chunks)} total chunks via OpenAI (batched)...")

    # Batch embedding to avoid API limits (same pattern as embed_mkdocs.py)
    BATCH_SIZE = 500  # well under the 2048 limit, safe for large chunks too
    embeddings = []
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        response = client.embeddings.create(model="text-embedding-3-small", input=batch)
        embeddings.extend([item.embedding for item in response.data])
        batch_num = i // BATCH_SIZE + 1
        total_batches = -(-len(all_chunks) // BATCH_SIZE)  # ceiling division
        print(f"      Batch {batch_num}/{total_batches} done ✅")

    collection.add(ids=all_ids, embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas)
    return len(all_chunks)


def print_summary():
    """Show what's now in the collection."""
    total = collection.count()
    print(f"\n{'─'*50}")
    print(f"📊 COLLECTION SUMMARY  →  '{COLLECTION}'")
    print(f"   Total chunks in DB : {total}")

    # Show sources breakdown
    all_metas = collection.get(include=["metadatas"])["metadatas"]
    source_counts = {}
    for m in all_metas:
        src = m.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    print(f"   Sources ({len(source_counts)}):")
    for src, count in sorted(source_counts.items()):
        print(f"   • {src:55s} {count:3d} chunks")
    print(f"{'─'*50}\n")


# ── MAIN ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  embed_readmes.py — README Ingestion Pipeline")
    print("=" * 50)

    print(f"\n📂 Loading READMEs from: {README_FOLDER}/")
    docs = load_readmes(README_FOLDER)

    print(f"\n⚙️  Processing {len(docs)} documents...")
    n_embedded = embed_documents(docs)

    if n_embedded > 0:
        print(f"\n💾 Saved {n_embedded} new chunks to ChromaDB at '{CHROMA_PATH}/'")

    print_summary()
    print("🎉 Done! You can now launch app.py — READMEs are in the knowledge base.\n")
