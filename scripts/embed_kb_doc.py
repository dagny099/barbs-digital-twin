"""
embed_kb_doc.py
────────────────────────────────────────────────────────────────────────────
Generic script to embed any inputs/kb_*.md knowledge-base document into
ChromaDB with section-aware (## H2 header) metadata.

All six structured KB documents share the same format — markdown with ##
section headers — so a single parameterised script replaces the old
source-specific embed_biosketch.py, embed_publications.py, etc. (those
scripts now live in archive/ for reference).

SUPPORTED DOCUMENTS (all in inputs/):
    kb_biosketch.md                — biographical sketch; authoritative identity source ⭐
    kb_philosophy-and-approach.md  — working philosophy and meaning-making approach
    kb_professional_positioning.md — positioning, differentiators, and value proposition
    kb_projects.md                 — project portfolio registry (all major projects)
    kb_career_narrative.md         — career story, trajectory, and context
    kb_publications.md             — research papers, conference work, dissertation

CALLED BY:
    ingest.py  (preferred — gives you the interactive menu + status table)

DIRECT USAGE:
    python embed_kb_doc.py --file inputs/kb_biosketch.md --source-type kb-biosketch
    python embed_kb_doc.py --file inputs/kb_projects.md  --source-type kb-projects --dry-run
    python embed_kb_doc.py --file inputs/kb_career_narrative.md \\
                           --source-type kb-career --force-reembed

FLAGS:
    --file PATH           Path to the kb_*.md file (required)
    --source-type KEY     ChromaDB source-type key, e.g. kb-biosketch (required)
    --force-reembed       Wipe all existing chunks for this source and re-embed
    --dry-run             Parse and preview sections; do not embed anything

METADATA SCHEMA (per stored chunk):
    {
        "source":      "kb-biosketch:kb_biosketch.md",   # source_type:filename
        "section":     "Professional Identity",           # ## header name
        "chunk_index": 0                                  # resets per section
    }

CHUNKING:
    chunk_size = 500 chars, overlap = 50 chars, atomic unit = paragraph
    All handled by utils.chunk_prose() — consistent with every other source.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import uuid
import argparse
from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from utils import (
    parse_markdown_sections,
    chunk_prose,
    build_metadata,
    get_sensitivity,
    delete_chunks_by_source,
    section_already_embedded,
)

load_dotenv(override=True)

# ── CONFIG ──────────────────────────────────────────────────────────────────
CHROMA_PATH = ".chroma_db_DT"
COLLECTION  = "barb-twin"
CHUNK_SIZE  = 900
OVERLAP     = 100
MIN_CHUNK_CHARS = 150   # added mar-25
BATCH_SIZE  = 500   # max chunks per OpenAI embeddings API call
# ────────────────────────────────────────────────────────────────────────────

# Canonical mapping of source-type keys → expected filenames.
# Used only for documentation/help text; not enforced at runtime.
KB_DOCS = {
    "kb-biosketch":    "inputs/kb_biosketch.md",
    "kb-philosophy":   "inputs/kb_philosophy-and-approach.md",
    "kb-positioning":  "inputs/kb_professional_positioning.md",
    "kb-projects":     "inputs/kb_projects.md",
    "kb-career":       "inputs/kb_career_narrative.md",
    "kb-publications": "inputs/kb_publications.md",
}


def parse_args():
    kb_list = "\n".join(f"  {k:<18} {v}" for k, v in KB_DOCS.items())
    parser = argparse.ArgumentParser(
        description="Embed a kb_*.md knowledge-base document with section-aware metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Known source-type keys and their files:
{kb_list}

Examples:
  python embed_kb_doc.py --file inputs/kb_biosketch.md --source-type kb-biosketch
  python embed_kb_doc.py --file inputs/kb_projects.md  --source-type kb-projects --dry-run
  python embed_kb_doc.py --file inputs/kb_career_narrative.md \\
                         --source-type kb-career --force-reembed
        """,
    )
    parser.add_argument(
        "--file", required=True,
        help="Path to the kb_*.md file to embed",
    )
    parser.add_argument(
        "--source-type", required=True,
        help="Source-type key written into ChromaDB metadata (e.g. kb-biosketch)",
    )
    parser.add_argument(
        "--force-reembed", action="store_true",
        help="Delete all existing chunks for this source-type and re-embed from scratch",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Parse and preview sections without embedding or storing anything",
    )
    return parser.parse_args()


def merge_tiny_chunks(chunks, min_chars=150):
    if not chunks:
        return chunks
    merged = []
    carry  = None
    for chunk in chunks:
        if carry is not None:
            combined = carry["text"] + "\n\n" + chunk["text"]
            chunk = {**chunk, "text": combined, "char_count": len(combined)}
            carry = None
        if len(chunk["text"]) < min_chars:
            carry = chunk
        else:
            merged.append(chunk)
    if carry is not None:
        if merged:
            combined = merged[-1]["text"] + "\n\n" + carry["text"]
            merged[-1] = {**merged[-1], "text": combined, "char_count": len(combined)}
        else:
            merged.append(carry)
    return merged


# ── PROCESSING PIPELINE ─────────────────────────────────────────────────────

def process_kb_doc(
    filepath: str,
    source_type: str,
    collection,
    client: OpenAI,
    force_reembed: bool = False,
    dry_run: bool = False,
):
    """
    Full pipeline: load → parse sections by ## headers → chunk → embed → store.

    Args:
        filepath:      Path to the kb_*.md markdown file.
        source_type:   ChromaDB source-type key (e.g. 'kb-biosketch').
        collection:    ChromaDB collection object. None in dry-run mode.
        client:        OpenAI client. None in dry-run mode.
        force_reembed: If True, wipe existing chunks for this source first.
        dry_run:       If True, print sections and exit without any embedding.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"❌  File not found: {filepath}")

    filename    = os.path.basename(filepath)
    full_source = f"{source_type}:{filename}"   # e.g. "kb-biosketch:kb_biosketch.md"

    # ── Load ────────────────────────────────────────────────────────────────
    print(f"\n📄 Loading: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()
    print(f"   ✅ Loaded {len(raw_text):,} characters")

    # ── Parse sections by ## headers ────────────────────────────────────────
    # include_nested=True merges ### subsections into their parent ## section,
    # keeping each top-level topic as a single retrieval unit.
    print(f"\n🔍 Parsing sections (## H2 headers, subsections merged)...")
    sections = parse_markdown_sections(raw_text, header_level=2, include_nested=True)
    print(f"   ✅ Found {len(sections)} sections")

    # Section summary table
    print(f"\n📋 Section Summary:")
    print(f"   {'Section Name':<50} {'Lines':<15} {'Chars'}")
    # After the section summary table, show the sensitivity tier
    sensitivity = get_sensitivity(source_type)
    print(f"\n   🔒 Sensitivity tier: {sensitivity}")
    print(f"   {'-'*80}")
    for s in sections:
        line_range = f"{s['start_line']}-{s['end_line']}"
        print(f"   {s['section_name']:<50} {line_range:<15} {len(s['text']):>6}")

    # ── Dry run: stop here ───────────────────────────────────────────────────
    if dry_run:
        print(f"\n🔍 DRY RUN — showing first 300 chars of each section:")
        for s in sections:
            print(f"\n{'='*70}")
            print(f"SECTION: {s['section_name']}")
            print(f"{'='*70}")
            preview = s["text"][:300] + "..." if len(s["text"]) > 300 else s["text"]
            print(preview)
        print(f"\n✅ Dry run complete — nothing embedded")
        return

    # ── Force re-embed: wipe existing chunks ────────────────────────────────
    if force_reembed:
        delete_chunks_by_source(collection, full_source)

    # ── Chunk each section ──────────────────────────────────────────────────
    all_chunks, all_ids, all_metadatas = [], [], []
    section_stats = []

    for section in sections:
        section_name = section["section_name"]
        section_text = section["text"]

        # ── Skip sections too small to be useful ──
        if len(section_text.strip()) < 160:
            print(f"   ⏭️   Skipping '{section_name}' (too short: {len(section_text)} chars)")
            continue

        # Per-section idempotency: skip if this (source, section) pair is already stored
        if not force_reembed and section_already_embedded(collection, full_source, section_name):
            print(f"   ⏭️   Skipping '{section_name}' (already embedded)")
            continue

        chunk_results = chunk_prose(section_text, chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        chunk_results = merge_tiny_chunks(chunk_results, min_chars=MIN_CHUNK_CHARS)  # ← add this

        if not chunk_results:
            print(f"   ⚠️   '{section_name}' produced no chunks (empty section?)")
            continue

        for chunk_index, chunk_data in enumerate(chunk_results):
            metadata = build_metadata(
                source_type=source_type,
                identifier=filename,
                section_name=section_name,
                chunk_index=chunk_index,
            )
            all_chunks.append(f"[{section_name}]\n{chunk_data['text']}")
            all_ids.append(str(uuid.uuid4()))
            all_metadatas.append(metadata)

        section_stats.append({"section": section_name, "chunks": len(chunk_results)})
        print(f"   ✅ '{section_name}'  →  {len(chunk_results)} chunk(s)")

    if not all_chunks:
        print(f"\n✨ Nothing new to embed — already up to date")
        return

    # ── Embed via OpenAI (batched) ───────────────────────────────────────────
    print(f"\n🔢 Embedding {len(all_chunks)} chunks via OpenAI (text-embedding-3-small)...")
    embeddings = []
    total_batches = -(-len(all_chunks) // BATCH_SIZE)   # ceiling division
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=batch,
            )
            embeddings.extend([item.embedding for item in response.data])
            print(f"   Batch {i // BATCH_SIZE + 1}/{total_batches} done ✅")
        except Exception as e:
            print(f"   ❌ Embedding error on batch {i // BATCH_SIZE + 1}: {e}")
            raise

    # ── Store in ChromaDB ────────────────────────────────────────────────────
    try:
        collection.add(
            ids=all_ids,
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=all_metadatas,
        )
        print(f"\n💾 Saved {len(all_chunks)} chunks to ChromaDB")
    except Exception as e:
        print(f"\n❌ Failed to store chunks in ChromaDB: {e}")
        raise

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"📊 EMBEDDING COMPLETE — {source_type}")
    print(f"{'='*70}")
    print(f"   Source:   {full_source}")
    print(f"   Sections: {len(section_stats)}")
    print(f"   Chunks:   {len(all_chunks)}")
    print(f"\n   Section breakdown:")
    for stat in section_stats:
        print(f"   • {stat['section']:<50} {stat['chunks']:>3} chunk(s)")
    print(f"{'='*70}\n")


# ── ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    print("=" * 70)
    print("  embed_kb_doc.py — KB Document Ingestion")
    print(f"  File:        {args.file}")
    print(f"  Source type: {args.source_type}")
    print("=" * 70)

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise EnvironmentError(
            "❌  OPENAI_API_KEY not set — check your environment variables"
        )

    chroma_client = None
    if not args.dry_run:
        client        = OpenAI(api_key=OPENAI_API_KEY)
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection    = chroma_client.get_or_create_collection(name=COLLECTION)
    else:
        client     = None
        collection = None

    try:
        process_kb_doc(
            filepath=args.file,
            source_type=args.source_type,
            collection=collection,
            client=client,
            force_reembed=args.force_reembed,
            dry_run=args.dry_run,
        )
    finally:
        # Explicitly close ChromaDB connection to release SQLite file locks
        if chroma_client is not None:
            del collection
            del chroma_client
            import gc
            gc.collect()

    print("🎉 Done!\n")


if __name__ == "__main__":
    main()
