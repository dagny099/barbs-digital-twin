"""
embed_walkthroughs.py — Ingest project walkthrough contexts into ChromaDB
═════════════════════════════════════════════════════════════════════════════

Reads the walkthrough_context from each FEATURED_PROJECT and embeds it
as a single chunk in the same ChromaDB collection used by app.py.

WHY:
  Previously, walkthrough content only existed in featured_projects.py
  and was only accessible via the walkthrough classification path.
  By embedding it in ChromaDB, normal RAG retrieval can also surface
  this content — so questions like "how does Resume Explorer normalize
  entities?" can pull from the walkthrough even without triggering the
  walkthrough flow.

DESIGN DECISIONS:
  - No chunking: each walkthrough_context is ~500-800 chars, already
    within chunk_size. Splitting would break narrative coherence.
  - Source naming: "project-walkthrough:{title-slug}" for easy
    identification in retrieval logs and Collection Browser.
  - Idempotent: checks if source already exists before embedding.
  - Metadata includes project_name and section="walkthrough" so the
    retrieval inspector shows useful provenance.

USAGE:
    python embed_walkthroughs.py

    Or integrate into ingest.py --all by calling embed_walkthroughs()
    from that script.
"""

import os
import re
import uuid
import chromadb
from openai import OpenAI
from featured_projects import FEATURED_PROJECTS


# ── CONFIG (must match app.py) ───────────────────────────────────
CHROMA_PATH  = ".chroma_db_DT"
COLLECTION   = "barb-twin"
# ─────────────────────────────────────────────────────────────────

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--force-reembed", action="store_true",
                    help="Delete existing walkthrough chunks and re-embed all")
parser.add_argument("--dry-run", action="store_true",
                    help="Show what would be embedded without calling OpenAI")
args = parser.parse_args()


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("❌ OPENAI_API_KEY not set")

client        = OpenAI(api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection    = chroma_client.get_or_create_collection(name=COLLECTION)


def _slugify(title: str) -> str:
    """Convert project title to a URL-safe slug for source naming."""
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')


def _existing_sources() -> set[str]:
    """Return the set of source values already in the collection."""
    all_meta = collection.get(include=["metadatas"])["metadatas"]
    return {m.get("source", "") for m in all_meta}


def embed_walkthroughs() -> int:
    """
    Embed walkthrough contexts into ChromaDB.

    Returns the number of new chunks added (0 if all already present).
    """
    existing = _existing_sources()

    chunks    = []
    ids       = []
    metadatas = []

    for project in FEATURED_PROJECTS:
        title   = project.get("title", "unknown")
        context = project.get("walkthrough_context", "").strip()
        slug    = _slugify(title)
        source  = f"project-walkthrough:{slug}"

        if not context:
            print(f"  ⏭  {title} — no walkthrough_context, skipping")
            continue

        if source in existing:
            print(f"  ✓  {title} — already embedded, skipping")
            continue

        # Build a retrieval-friendly document:
        # Prepend the project title + summary so the embedding captures
        # "what project is this about" alongside the technical details.
        summary = project.get("summary", "")
        tags    = project.get("tags", [])

        doc_text = (
            f"{title}: {summary}\n\n"
            f"{context}\n\n"
            f"Tags: {', '.join(tags)}"
        )

        chunks.append(doc_text)
        ids.append(str(uuid.uuid4()))
        metadatas.append({
            "source":       source,
            "project_name": title,
            "section":      "walkthrough",
            "chunk_index":  0,
            "char_count":   len(doc_text),
        })
        print(f"  +  {title} — {len(doc_text)} chars")

    if not chunks:
        print("\n  Nothing new to embed.")
        return 0

    print(f"\n🔢 Embedding {len(chunks)} walkthrough chunks via OpenAI...")
    response   = client.embeddings.create(model="text-embedding-3-small", input=chunks)
    embeddings = [item.embedding for item in response.data]

    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    print(f"✅ Added {len(chunks)} walkthrough chunks to collection")
    return len(chunks)


def print_summary():
    """Show collection state after ingestion."""
    total = collection.count()
    print(f"\n{'─'*55}")
    print(f"📊 COLLECTION SUMMARY  →  '{COLLECTION}'")
    print(f"   Total chunks in DB : {total}")

    all_metas = collection.get(include=["metadatas"])["metadatas"]
    source_counts = {}
    for m in all_metas:
        src = m.get("source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    print(f"   Sources ({len(source_counts)}):")
    for src, count in sorted(source_counts.items()):
        marker = "  ★" if "walkthrough" in src else ""
        print(f"   • {src:50s} {count:3d} chunks{marker}")
    print(f"{'─'*55}\n")


# ── MAIN ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  embed_walkthroughs.py — Project Walkthrough Ingestion")
    print("=" * 55)

    print(f"\n📂 Loading {len(FEATURED_PROJECTS)} featured projects...\n")
    n = embed_walkthroughs()

    if n > 0:
        print(f"\n💾 Saved {n} new walkthrough chunks to ChromaDB")

    print_summary()
    print("🎉 Done! Walkthrough content is now retrievable via normal RAG.\n")
