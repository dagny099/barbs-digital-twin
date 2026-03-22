"""
embed_publications.py
───────────────────────────────────────────────────────────────
ONE-TIME script to parse, chunk, embed, and persist the publications
document with section-aware metadata into ChromaDB.

STRUCTURE:
    Parses markdown by ## H2 headers to extract sections:
        Overview          → research background + Google Scholar link
        Research Focus    → core research questions
        Published Papers  → full citations with PDF URLs
        Conference Posters → poster citations with PDF URLs where available

PRIORITY:
    Publications document is authoritative for Barbara's academic work,
    paper titles, venues, and PDF/URL links. Do not fabricate citations.

USAGE:
    python embed_publications.py

    Optional flags:
    --publications-file PATH  Path to publications MD file
    --force-reembed           Delete existing chunks and re-embed
    --dry-run                 Parse and print sections without embedding

EXAMPLES:
    python embed_publications.py --dry-run
    python embed_publications.py
    python embed_publications.py --force-reembed
"""

import os
import uuid
import argparse
from openai import OpenAI
import chromadb
from utils import (
    parse_markdown_sections,
    chunk_prose,
    build_metadata,
    delete_chunks_by_source,
    section_already_embedded,
)

# ── CONFIG ──────────────────────────────────────────────────────
DEFAULT_PUBLICATIONS = "inputs/barbara-publications.md"
CHROMA_PATH          = ".chroma_db_DT"
COLLECTION           = "barb-twin"
CHUNK_SIZE           = 500
OVERLAP              = 50
BATCH_SIZE           = 500
# ────────────────────────────────────────────────────────────────


def parse_args():
    parser = argparse.ArgumentParser(
        description="Embed publications document with section metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python embed_publications.py --dry-run         # Test parsing
  python embed_publications.py                   # Embed
  python embed_publications.py --force-reembed   # Re-embed after updates
        """
    )
    parser.add_argument('--publications-file', default=DEFAULT_PUBLICATIONS,
                        help='Path to publications MD file')
    parser.add_argument('--force-reembed', action='store_true',
                        help='Delete existing chunks and re-embed')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and print sections without embedding')
    return parser.parse_args()



def process_publications(filepath: str, collection, client: OpenAI,
                         force_reembed: bool = False, dry_run: bool = False):
    """Parse → section → chunk → embed → store."""

    filename = os.path.basename(filepath)
    source_type = "publication"
    full_source = f"{source_type}:{filename}"

    print(f"\n📄 Loading: {filepath}")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"❌ File not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    print(f"   ✅ Loaded {len(raw_text)} characters")

    # Parse into sections by ## headers
    print(f"\n🔍 Parsing sections by ## headers...")
    sections = parse_markdown_sections(raw_text, header_level=2, include_nested=True)
    print(f"   ✅ Found {len(sections)} sections")

    print(f"\n📋 Section Summary:")
    print(f"   {'Section Name':<40} {'Lines':<15} {'Chars'}")
    print(f"   {'-'*70}")
    for s in sections:
        line_range = f"{s['start_line']}-{s['end_line']}"
        print(f"   {s['section_name']:<40} {line_range:<15} {len(s['text']):>6}")

    if dry_run:
        print(f"\n🔍 DRY RUN — showing first 300 chars of each section:")
        for s in sections:
            print(f"\n{'='*70}")
            print(f"SECTION: {s['section_name']}")
            print(f"{'='*70}")
            preview = s['text'][:300] + "..." if len(s['text']) > 300 else s['text']
            print(preview)
        print(f"\n✅ Dry run complete — nothing embedded")
        return

    if force_reembed:
        delete_chunks_by_source(collection, full_source)

    all_chunks, all_ids, all_metadatas = [], [], []
    section_stats = []

    for section in sections:
        section_name = section['section_name']
        section_text = section['text']

        if not force_reembed and section_already_embedded(collection, full_source, section_name):
            print(f"   ⏭️  Skipping '{section_name}' (already embedded)")
            continue

        chunk_results = chunk_prose(section_text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        if not chunk_results:
            print(f"   ⚠️  '{section_name}' produced no chunks")
            continue

        for chunk_index, chunk_data in enumerate(chunk_results):
            metadata = build_metadata(
                source_type=source_type,
                identifier=filename,
                section_name=section_name,
                chunk_index=chunk_index
            )
            all_chunks.append(chunk_data["text"])
            all_ids.append(str(uuid.uuid4()))
            all_metadatas.append(metadata)

        section_stats.append({"section": section_name, "chunks": len(chunk_results)})
        print(f"   ✅ '{section_name}'  →  {len(chunk_results)} chunks")

    if not all_chunks:
        print(f"\n✨ Nothing new to embed — already up to date")
        return

    print(f"\n🔢 Embedding {len(all_chunks)} chunks via OpenAI...")
    embeddings = []
    total_batches = -(-len(all_chunks) // BATCH_SIZE)
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        try:
            response = client.embeddings.create(model="text-embedding-3-small", input=batch)
            embeddings.extend([item.embedding for item in response.data])
            print(f"   Batch {i // BATCH_SIZE + 1}/{total_batches} done ✅")
        except Exception as e:
            print(f"   ❌ Embedding error: {e}")
            raise

    try:
        collection.add(ids=all_ids, embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas)
        print(f"\n💾 Saved {len(all_chunks)} chunks to ChromaDB")
    except Exception as e:
        print(f"\n❌ Failed to store chunks: {e}")
        raise

    print(f"\n{'='*70}")
    print(f"📊 PUBLICATIONS EMBEDDING COMPLETE")
    print(f"{'='*70}")
    print(f"   Source: {full_source}")
    print(f"   Total sections: {len(section_stats)}")
    print(f"   Total chunks:   {len(all_chunks)}")
    for stat in section_stats:
        print(f"   • {stat['section']:<40} {stat['chunks']:>3} chunks")
    print(f"{'='*70}\n")


def main():
    args = parse_args()

    print("=" * 70)
    print("  embed_publications.py — Publications Ingestion")
    print("=" * 70)

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise Exception("❌ OPENAI_API_KEY not set — check your environment variables")

    if not args.dry_run:
        client        = OpenAI(api_key=OPENAI_API_KEY)
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection    = chroma_client.get_or_create_collection(name=COLLECTION)
    else:
        client     = None
        collection = None

    process_publications(
        filepath=args.publications_file,
        collection=collection,
        client=client,
        force_reembed=args.force_reembed,
        dry_run=args.dry_run,
    )

    print("🎉 Done!\n")


if __name__ == "__main__":
    main()
