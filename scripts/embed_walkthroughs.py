"""
embed_walkthroughs.py — Ingest project walkthrough contexts into ChromaDB
═════════════════════════════════════════════════════════════════════════════

Reads the walkthrough_context (and design_insight, summary, tags) from
each FEATURED_PROJECT and embeds it as a single chunk in the same
ChromaDB collection used by app.py.

WHY:
  Previously, walkthrough content only existed in featured_projects.py
  and was only accessible via the walkthrough classification path.
  By embedding it in ChromaDB, normal RAG retrieval can also surface
  this content — so questions like "how does Resume Explorer normalize
  entities?" can pull from the walkthrough even without triggering the
  walkthrough flow. Including the design_insight means "why" questions
  ("why did you use SKOS?", "what's distinctive about that project?")
  also match against the embedded content.

DESIGN DECISIONS:
  - No chunking: each combined doc_text is ~1400-2300 chars (well within
    text-embedding-3-small's 8192-token limit). Splitting would break
    narrative coherence.
  - Doc structure: title + summary + design_insight + walkthrough_context
    + tags. This ordering puts "what" and "why" before "how", which
    gives the embedding a strong conceptual signal alongside the
    technical details.
  - Source naming: "project-walkthrough:{title-slug}" for easy
    identification in retrieval logs and Collection Browser.
  - Idempotent: checks if source already exists before embedding.
  - Metadata includes project_name and section="walkthrough" so the
    retrieval inspector shows useful provenance.

USAGE:
    python embed_walkthroughs.py
    python embed_walkthroughs.py --force-reembed
    python embed_walkthroughs.py --dry-run
"""

import os
import re
import uuid
import argparse
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from featured_projects import FEATURED_PROJECTS
from utils import delete_chunks_by_source

load_dotenv(override=True)

# ── CONFIG (must match app.py) ────────────────────────────────────────────
CHROMA_PATH   = ".chroma_db_DT"
COLLECTION    = "barb-twin"
SOURCE_PREFIX = "project-walkthrough:"
# ─────────────────────────────────────────────────────────────────────────

def _slugify(title: str) -> str:
    """Convert project title to a URL-safe slug for source naming."""
    return re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')


def _existing_sources(collection) -> set:
    """Return the set of source values already in the collection."""
    all_meta = collection.get(include=["metadatas"])["metadatas"]
    return {m.get("source", "") for m in all_meta}


def embed_walkthroughs(client, collection, force: bool = False, dry_run: bool = False) -> int:
    """
    Embed walkthrough contexts into ChromaDB.

    Args:
        client:  OpenAI client for embeddings.
        collection: ChromaDB collection to store embeddings.
        force:   If True, delete existing walkthrough chunks first and re-embed all.
        dry_run: If True, print what would be embedded without calling OpenAI.

    Returns:
        Number of new chunks added (0 if all already present or dry run).
    """
    if force:
        print(f"  🗑  Force re-embed: deleting existing walkthrough chunks...")
        delete_chunks_by_source(collection, SOURCE_PREFIX)
        existing = set()
    else:
        existing = _existing_sources(collection)

    chunks    = []
    ids       = []
    metadatas = []

    for project in FEATURED_PROJECTS:
        title   = project.get("title", "unknown")
        context = project.get("walkthrough_context", "").strip()
        slug    = _slugify(title)
        source  = f"{SOURCE_PREFIX}{slug}"

        if not context:
            print(f"  ⏭  {title} — no walkthrough_context, skipping")
            continue

        if source in existing:
            print(f"  ✓  {title} — already embedded, skipping")
            continue

        # Build a retrieval-friendly document:
        # Prepend the project title + summary + design_insight so the
        # embedding captures "what project is this about" and "why it's
        # distinctive" alongside the technical details.
        summary = project.get("summary", "")
        insight = project.get("design_insight", "")
        tags    = project.get("tags", [])

        # Structure: what → why → how → tags
        doc_parts = [f"{title}: {summary}"]
        if insight:
            doc_parts.append(f"What makes it distinctive: {insight}")
        doc_parts.append(context)
        doc_parts.append(f"Tags: {', '.join(tags)}")
        doc_text = "\n\n".join(doc_parts)

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

    if dry_run:
        print(f"\n  [DRY RUN] Would embed {len(chunks)} walkthrough chunk(s):")
        for meta in metadatas:
            print(f"    • {meta['source']}  ({meta['char_count']} chars)")
        return 0

    print(f"\n🔢 Embedding {len(chunks)} walkthrough chunks via OpenAI...")
    response   = client.embeddings.create(model="text-embedding-3-small", input=chunks)
    embeddings = [item.embedding for item in response.data]

    collection.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    print(f"✅ Added {len(chunks)} walkthrough chunks to collection")
    return len(chunks)


def print_summary(collection):
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


# ── MAIN ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Embed project walkthrough contexts into ChromaDB."
    )
    parser.add_argument("--force-reembed", action="store_true",
                        help="Delete existing walkthrough chunks and re-embed all")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be embedded without calling OpenAI")
    args = parser.parse_args()

    print("=" * 55)
    print("  embed_walkthroughs.py — Project Walkthrough Ingestion")
    print("=" * 55)
    print(f"\n📂 Loading {len(FEATURED_PROJECTS)} featured projects...\n")

    # Setup clients
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise Exception("❌ OPENAI_API_KEY not set")

    chroma_client = None
    if not args.dry_run:
        client = OpenAI(api_key=OPENAI_API_KEY)
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_or_create_collection(name=COLLECTION)
    else:
        client = None
        collection = None

    try:
        n = embed_walkthroughs(client, collection, force=args.force_reembed, dry_run=args.dry_run)

        if n > 0:
            print(f"\n💾 Saved {n} new walkthrough chunks to ChromaDB")

        if not args.dry_run:
            print_summary(collection)

        print("🎉 Done! Walkthrough content is now retrievable via normal RAG.\n")
    finally:
        # Explicitly close ChromaDB connection to release SQLite file locks
        if chroma_client is not None:
            del collection
            del chroma_client
            import gc
            gc.collect()
