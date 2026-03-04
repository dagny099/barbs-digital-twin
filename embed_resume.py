"""
embed_resume.py
───────────────────────────────────────────────────────────────
ONE-TIME script to parse, chunk, embed, and persist resume with
section-aware metadata into ChromaDB.

STRUCTURE:
    Parses resume by '======' delimiters to extract sections.
    Each section is chunked separately with metadata:
        {'source': 'resume:filename', 'section': 'Section Name', 'chunk_index': i}

USAGE:
    python embed_resume.py

    Optional flags:
    --resume-file PATH    Path to resume TXT file (default: Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt)
    --force-reembed       Delete existing resume chunks and re-embed
    --dry-run             Parse and print sections without embedding

EXAMPLES:
    # Test parsing without embedding
    python embed_resume.py --dry-run

    # Embed with default resume file
    python embed_resume.py

    # Re-embed after updates
    python embed_resume.py --force-reembed

    # Use custom resume file
    python embed_resume.py --resume-file path/to/resume.txt
"""

import os
import uuid
import argparse
from openai import OpenAI
import chromadb
from utils import (
    parse_sections_by_delimiter,
    chunk_prose,
    build_metadata
)

# ── CONFIG ──────────────────────────────────────────────────────
DEFAULT_RESUME = "Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt"
CHROMA_PATH    = ".chroma_db_DT"
COLLECTION     = "barb-twin"
CHUNK_SIZE     = 500
OVERLAP        = 50
BATCH_SIZE     = 500  # for batched embedding API calls
# ────────────────────────────────────────────────────────────────


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Embed resume with section metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python embed_resume.py --dry-run              # Test parsing
  python embed_resume.py                        # Embed resume
  python embed_resume.py --force-reembed        # Re-embed existing
        """
    )
    parser.add_argument('--resume-file', default=DEFAULT_RESUME,
                        help='Path to resume TXT file')
    parser.add_argument('--force-reembed', action='store_true',
                        help='Delete existing resume chunks and re-embed')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and print sections without embedding')
    return parser.parse_args()


def load_resume(filepath: str) -> str:
    """Load resume text from file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"❌ Resume file not found: {filepath}")

    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def section_already_embedded(collection, source: str, section: str) -> bool:
    """Check if a specific section from this source is already embedded."""
    try:
        results = collection.get(where={"$and": [{"source": source}, {"section": section}]})
        return len(results["ids"]) > 0
    except Exception:
        # If query fails (e.g., collection doesn't exist yet), assume not embedded
        return False


def delete_existing_resume(collection, source_pattern: str):
    """Delete all chunks from resume source."""
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


def process_resume(filepath: str, collection, client: OpenAI,
                   force_reembed: bool = False, dry_run: bool = False):
    """Main processing pipeline: parse → section → chunk → embed → store."""

    # Extract filename for metadata
    filename = os.path.basename(filepath)
    source_identifier = filename
    source_type = "resume"
    full_source = f"{source_type}:{source_identifier}"

    # Load resume
    print(f"\n📄 Loading resume: {filepath}")
    raw_text = load_resume(filepath)
    print(f"   ✅ Loaded {len(raw_text)} characters")

    # Parse into sections
    print(f"\n🔍 Parsing sections by '======' delimiter...")
    sections = parse_sections_by_delimiter(raw_text, delimiter="======")
    print(f"   ✅ Found {len(sections)} sections")

    # Print section summary
    print(f"\n📋 Section Summary:")
    print(f"   {'Section Name':<40} {'Lines':<15} {'Chars'}")
    print(f"   {'-'*70}")
    for section in sections:
        line_range = f"{section['start_line']}-{section['end_line']}"
        char_count = len(section['text'])
        print(f"   {section['section_name']:<40} {line_range:<15} {char_count:>6}")

    if dry_run:
        print(f"\n🔍 DRY RUN MODE - Showing first 200 chars of each section:")
        for section in sections:
            print(f"\n{'='*70}")
            print(f"SECTION: {section['section_name']}")
            print(f"{'='*70}")
            preview = section['text'][:200] + "..." if len(section['text']) > 200 else section['text']
            print(preview)
        print(f"\n✅ Dry run complete - no data embedded")
        return

    # Handle force re-embed
    if force_reembed:
        delete_existing_resume(collection, full_source)

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
        print(f"\n✨ Nothing new to embed - resume already processed")
        return

    print(f"\n🔢 Embedding {len(all_chunks)} total chunks via OpenAI (batched)...")
    embeddings = []
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        try:
            response = client.embeddings.create(model="text-embedding-3-small", input=batch)
            embeddings.extend([item.embedding for item in response.data])
            batch_num = i // BATCH_SIZE + 1
            total_batches = -(-len(all_chunks) // BATCH_SIZE)  # ceiling division
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
    print(f"\n{'='*70}")
    print(f"📊 RESUME EMBEDDING COMPLETE")
    print(f"{'='*70}")
    print(f"   Source: {full_source}")
    print(f"   Total sections: {len(section_stats)}")
    print(f"   Total chunks: {len(all_chunks)}")
    print(f"\n   Section breakdown:")
    for stat in section_stats:
        print(f"   • {stat['section']:<40} {stat['chunks']:>3} chunks")
    print(f"{'='*70}\n")


def main():
    """Main entry point."""
    args = parse_args()

    print("=" * 70)
    print("  embed_resume.py — Resume Section-Aware Ingestion")
    print("=" * 70)

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

    # Process resume
    process_resume(
        filepath=args.resume_file,
        collection=collection,
        client=client,
        force_reembed=args.force_reembed,
        dry_run=args.dry_run
    )

    print("🎉 Done!\n")


if __name__ == "__main__":
    main()
