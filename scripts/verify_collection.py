"""
verify_collection.py
───────────────────────────────────────────────────────────────
Utility script to verify the ChromaDB collection after embedding.

Displays statistics about:
- Total chunk count
- Chunks by source type
- Chunks with vs without sections
- Sample section names

USAGE:
    python verify_collection.py

    Optional flags:
    --show-sources      Show detailed source breakdown
    --show-sections     Show all unique section names
    --sample N          Show N sample chunks (default: 3)
"""

import chromadb
import argparse
from collections import Counter, defaultdict

# ── CONFIG ──────────────────────────────────────────────────────
CHROMA_PATH = ".chroma_db_DT"
COLLECTION  = "barb-twin"
# ────────────────────────────────────────────────────────────────


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Verify ChromaDB collection")
    parser.add_argument('--show-sources', action='store_true',
                        help='Show detailed source breakdown')
    parser.add_argument('--show-sections', action='store_true',
                        help='Show all unique section names')
    parser.add_argument('--sample', type=int, default=3,
                        help='Number of sample chunks to show (default: 3)')
    return parser.parse_args()


def main():
    """Verify collection statistics."""
    args = parse_args()

    print("=" * 80)
    print("  verify_collection.py — ChromaDB Collection Verification")
    print("=" * 80)

    # Connect to ChromaDB
    print(f"\n📂 Connecting to ChromaDB at: {CHROMA_PATH}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name=COLLECTION)

    # Get all data
    print(f"   Loading collection data...")
    all_data = collection.get(include=["metadatas", "documents"])
    total_chunks = len(all_data["ids"])

    if total_chunks == 0:
        print(f"\n⚠️  Collection '{COLLECTION}' is empty")
        print(f"   Run embedding scripts to populate the collection\n")
        return

    print(f"   ✅ Loaded {total_chunks} chunks\n")

    # ── BASIC STATISTICS ───────────────────────────────────────────
    print("=" * 80)
    print("📊 COLLECTION STATISTICS")
    print("=" * 80)
    print(f"Total chunks: {total_chunks}")

    # Count by source — group by type prefix (derived from "type:identifier" convention)
    sources = [m.get("source", "unknown") for m in all_data["metadatas"]]

    by_type = defaultdict(list)
    for source in sources:
        type_key = source.split(":")[0]
        by_type[type_key].append(source)

    MAX_SUB = 5   # max sub-sources shown per type before truncating

    print("\nChunks by source type:")
    for type_key in sorted(by_type.keys()):
        type_sources   = by_type[type_key]
        type_count     = len(type_sources)
        type_pct       = (type_count / total_chunks) * 100
        sub_counts     = Counter(type_sources)
        unique_sub     = len(sub_counts)

        print(f"  {type_key:<22} {type_count:>5} chunks ({type_pct:>5.1f}%)"
              f"  [{unique_sub} source{'s' if unique_sub != 1 else ''}]")

        # Show sub-source breakdown — truncate long lists
        for src, cnt in sorted(sub_counts.items(), key=lambda x: -x[1])[:MAX_SUB]:
            identifier = src.split(":", 1)[1] if ":" in src else src
            print(f"    ↳ {identifier:<48} {cnt:>3} chunks")
        if unique_sub > MAX_SUB:
            print(f"    ↳ … and {unique_sub - MAX_SUB} more"
                  f"  (use --show-sources for full list)")

    # Section metadata
    sections = [m.get("section") for m in all_data["metadatas"]]
    with_sections = sum(1 for s in sections if s is not None)
    without_sections = sum(1 for s in sections if s is None)

    print(f"\nSection metadata:")
    print(f"  With sections:       {with_sections:>5} chunks ({(with_sections/total_chunks)*100:>5.1f}%)")
    print(f"  Without sections:    {without_sections:>5} chunks ({(without_sections/total_chunks)*100:>5.1f}%)")

    # ── DETAILED SOURCE BREAKDOWN ──────────────────────────────────
    if args.show_sources:
        print("\n" + "=" * 80)
        print("📂 DETAILED SOURCE BREAKDOWN")
        print("=" * 80)
        print(f"{'Source':<60} {'Chunks':>8}")
        print("-" * 80)
        for source, count in sorted(source_counts.items(), key=lambda x: (-x[1], x[0])):
            print(f"{source:<60} {count:>8}")

    # ── SECTION NAMES ──────────────────────────────────────────────
    section_names = [s for s in sections if s is not None]
    unique_sections = set(section_names)

    print(f"\n{'=' * 80}")
    print(f"📑 UNIQUE SECTIONS")
    print("=" * 80)
    print(f"Total unique sections: {len(unique_sections)}")

    if args.show_sections:
        print("\nAll section names:")
        for section in sorted(unique_sections):
            section_count = section_names.count(section)
            print(f"  • {section:<50} ({section_count} chunks)")
    else:
        print("\nSample section names (use --show-sections for full list):")
        for section in sorted(unique_sections)[:10]:
            section_count = section_names.count(section)
            print(f"  • {section:<50} ({section_count} chunks)")
        if len(unique_sections) > 10:
            print(f"  ... and {len(unique_sections) - 10} more")

    # ── SAMPLE CHUNKS ──────────────────────────────────────────────
    if args.sample > 0:
        print(f"\n{'=' * 80}")
        print(f"📄 SAMPLE CHUNKS (showing {args.sample})")
        print("=" * 80)

        for i in range(min(args.sample, total_chunks)):
            meta = all_data["metadatas"][i]
            doc = all_data["documents"][i]

            print(f"\nChunk {i + 1}:")
            print(f"  Source:       {meta.get('source', 'N/A')}")
            print(f"  Section:      {meta.get('section', 'N/A')}")
            print(f"  Chunk Index:  {meta.get('chunk_index', 'N/A')}")
            print(f"  Text Preview: {doc[:150]}...")

    # ── SUMMARY ────────────────────────────────────────────────────
    print(f"\n{'=' * 80}")
    print("✅ VERIFICATION COMPLETE")
    print("=" * 80)
    print(f"Collection '{COLLECTION}' is ready for use")
    print(f"\nTo test RAG retrieval:")
    print(f"  python app.py")
    print(f"  Query: 'What is your educational background?'\n")


if __name__ == "__main__":
    main()
