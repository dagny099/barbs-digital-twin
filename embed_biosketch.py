"""
embed_biosketch.py
───────────────────────────────────────────────────────────────
ONE-TIME script to parse, chunk, embed, and persist biosketch with
section-aware metadata into ChromaDB.

STRUCTURE:
    Parses markdown by ## H2 headers to extract sections.
    Each section is chunked separately with metadata:
        {'source': 'biosketch:filename', 'section': 'Section Name', 'chunk_index': i}

PRIORITY:
    Biosketch is the authoritative source for Barbara's identity, background,
    and values. Maintains highest priority in RAG retrieval.

USAGE:
    python embed_biosketch.py

    Optional flags:
    --biosketch-file PATH  Path to biosketch MD file (default: barbara-hidalgo-sotelo-biosketch.md)
    --force-reembed        Delete existing biosketch chunks and re-embed
    --dry-run              Parse and print sections without embedding
    --header-level N       Header level to split on (default: 2 for ##)
    --include-nested       Include subsections in parent section (default: True)

EXAMPLES:
    # Test parsing without embedding
    python embed_biosketch.py --dry-run

    # Embed with default settings (## headers, include nested)
    python embed_biosketch.py

    # Re-embed after updates
    python embed_biosketch.py --force-reembed

    # Parse by ### headers instead
    python embed_biosketch.py --header-level 3 --dry-run
"""

import os
import uuid
import argparse
from openai import OpenAI
import chromadb
from utils import (
    parse_markdown_sections,
    chunk_prose,
    build_metadata
)

# ── CONFIG ──────────────────────────────────────────────────────
DEFAULT_BIOSKETCH = "barbara-hidalgo-sotelo-biosketch.md"
CHROMA_PATH       = ".chroma_db_DT"
COLLECTION        = "barb-twin"
CHUNK_SIZE        = 500
OVERLAP           = 50
BATCH_SIZE        = 500
# ────────────────────────────────────────────────────────────────


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Embed biosketch with section metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python embed_biosketch.py --dry-run              # Test parsing
  python embed_biosketch.py                        # Embed biosketch
  python embed_biosketch.py --force-reembed        # Re-embed existing
        """
    )
    parser.add_argument('--biosketch-file', default=DEFAULT_BIOSKETCH,
                        help='Path to biosketch MD file')
    parser.add_argument('--force-reembed', action='store_true',
                        help='Delete existing biosketch chunks and re-embed')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and print sections without embedding')
    parser.add_argument('--header-level', type=int, default=2,
                        help='Header level to split on (2 for ##, 3 for ###)')
    parser.add_argument('--include-nested', action='store_true', default=True,
                        help='Include subsections in parent section')
    return parser.parse_args()


def load_biosketch(filepath: str) -> str:
    """Load biosketch text from file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"❌ Biosketch file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def delete_existing_biosketch(collection, source_pattern: str):
    """Delete all chunks from biosketch source."""
    try:
        # Get all chunks matching source pattern
        all_data = collection.get(include=["metadatas"])
        matching_ids = [
            id for id, meta in zip(all_data["ids"], all_data["metadatas"])
            if meta.get("source", "").startswith(source_pattern)
        ]

        if matching_ids:
            print(f"   🗑️  Deleting {len(matching_ids)} existing chunks from {source_pattern}...")
            collection.delete(ids=matching_ids)
            print(f"   ✅ Deleted successfully")
        else:
            print(f"   ℹ️  No existing chunks found for {source_pattern}")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not delete existing chunks: {e}")


def section_already_embedded(collection, source: str, section: str) -> bool:
    """Check if a specific section from this source is already embedded."""
    try:
        results = collection.get(where={"$and": [{"source": source}, {"section": section}]})
        return len(results["ids"]) > 0
    except Exception:
        # If query fails (e.g., collection doesn't exist yet), assume not embedded
        return False


def process_biosketch(filepath: str, collection, client: OpenAI,
                      force_reembed: bool = False, dry_run: bool = False,
                      header_level: int = 2, include_nested: bool = True):
    """Main processing pipeline: parse → section → chunk → embed → store."""

    # Extract filename for metadata
    filename = os.path.basename(filepath)
    source_identifier = filename
    source_type = "biosketch"
    full_source = f"{source_type}:{source_identifier}"

    # Load biosketch
    print(f"\n📄 Loading biosketch: {filepath}")
    raw_text = load_biosketch(filepath)
    print(f"   ✅ Loaded {len(raw_text)} characters")

    # Parse into sections
    print(f"\n🔍 Parsing sections by markdown headers (level {header_level})...")
    sections = parse_markdown_sections(
        raw_text,
        header_level=header_level,
        include_nested=include_nested
    )
    print(f"   ✅ Found {len(sections)} sections")

    # Print section summary
    print(f"\n📋 Section Summary:")
    print(f"   {'Section Name':<50} {'Lines':<15} {'Chars'}")
    print(f"   {'-'*80}")
    for section in sections:
        line_range = f"{section['start_line']}-{section['end_line']}"
        char_count = len(section['text'])
        print(f"   {section['section_name']:<50} {line_range:<15} {char_count:>6}")

    if dry_run:
        print(f"\n🔍 DRY RUN MODE - Showing first 300 chars of each section:")
        for section in sections:
            print(f"\n{'='*80}")
            print(f"SECTION: {section['section_name']}")
            print(f"{'='*80}")
            preview = section['text'][:300] + "..." if len(section['text']) > 300 else section['text']
            print(preview)
        print(f"\n✅ Dry run complete - no data embedded")
        return

    # Handle force re-embed
    if force_reembed:
        delete_existing_biosketch(collection, full_source)

    # Process each section
    all_chunks = []
    all_ids = []
    all_metadatas = []
    section_stats = []

    for section in sections:
        section_name = section['section_name']
        section_text = section['text']

        # Check if already embedded
        if not force_reembed and section_already_embedded(collection, full_source, section_name):
            print(f"   ⏭️  Skipping '{section_name}' (already embedded)")
            continue

        # Chunk this section
        chunk_results = chunk_prose(section_text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)

        if not chunk_results:
            print(f"   ⚠️  '{section_name}' produced no chunks (empty section?)")
            continue

        # Build chunks, IDs, and metadata for this section
        for chunk_index, chunk_data in enumerate(chunk_results):
            chunk_text = chunk_data["text"]
            chunk_id = str(uuid.uuid4())
            metadata = build_metadata(
                source_type=source_type,
                identifier=source_identifier,
                section_name=section_name,
                chunk_index=chunk_index
            )

            all_chunks.append(chunk_text)
            all_ids.append(chunk_id)
            all_metadatas.append(metadata)

        section_stats.append({
            "section": section_name,
            "chunks": len(chunk_results)
        })
        print(f"   ✅ '{section_name}'  →  {len(chunk_results)} chunks")

    # Embed and store
    if not all_chunks:
        print(f"\n✨ Nothing new to embed - biosketch already processed")
        return

    print(f"\n🔢 Embedding {len(all_chunks)} total chunks via OpenAI (batched)...")
    embeddings = []
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        try:
            response = client.embeddings.create(model="text-embedding-3-small", input=batch)
            embeddings.extend([item.embedding for item in response.data])
            batch_num = i // BATCH_SIZE + 1
            total_batches = -(-len(all_chunks) // BATCH_SIZE)
            print(f"   Batch {batch_num}/{total_batches} done ✅")
        except Exception as e:
            print(f"   ❌ Error embedding batch {batch_num}: {e}")
            raise

    try:
        collection.add(ids=all_ids, embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas)
        print(f"\n💾 Saved {len(all_chunks)} chunks to ChromaDB")
    except Exception as e:
        print(f"\n❌ Failed to store chunks in ChromaDB: {e}")
        print(f"   Check disk space and permissions for: {CHROMA_PATH}")
        raise

    # Print final summary
    print(f"\n{'='*80}")
    print(f"📊 BIOSKETCH EMBEDDING COMPLETE")
    print(f"{'='*80}")
    print(f"   Source: {full_source} ⭐ AUTHORITATIVE")
    print(f"   Total sections: {len(section_stats)}")
    print(f"   Total chunks: {len(all_chunks)}")
    print(f"\n   Section breakdown:")
    for stat in section_stats:
        print(f"   • {stat['section']:<50} {stat['chunks']:>3} chunks")
    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    args = parse_args()

    print("=" * 80)
    print("  embed_biosketch.py — Biosketch Section-Aware Ingestion")
    print("=" * 80)

    # Setup
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise Exception("❌ OPENAI_API_KEY not set — check your environment variables")

    if not args.dry_run:
        client = OpenAI(api_key=OPENAI_API_KEY)
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_or_create_collection(name=COLLECTION)
    else:
        client = None
        collection = None

    # Process biosketch
    process_biosketch(
        filepath=args.biosketch_file,
        collection=collection,
        client=client,
        force_reembed=args.force_reembed,
        dry_run=args.dry_run,
        header_level=args.header_level,
        include_nested=args.include_nested
    )

    print("🎉 Done!\n")


if __name__ == "__main__":
    main()
