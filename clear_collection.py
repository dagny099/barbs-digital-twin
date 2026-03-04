"""
clear_collection.py
───────────────────────────────────────────────────────────────
Utility script to clear all chunks from the ChromaDB collection.

Use this before re-embedding all sources with updated metadata schema.

USAGE:
    python clear_collection.py

WARNING:
    This will delete ALL chunks from the collection.
    Make sure you have a backup before running this!

    To backup:
        cp -r .chroma_db_DT .chroma_db_DT.backup_$(date +%Y-%m-%d)

    To restore:
        rm -rf .chroma_db_DT
        mv .chroma_db_DT.backup_YYYY-MM-DD .chroma_db_DT
"""

import chromadb

# ── CONFIG ──────────────────────────────────────────────────────
CHROMA_PATH = ".chroma_db_DT"
COLLECTION  = "barb-twin"
# ────────────────────────────────────────────────────────────────


def main():
    """Clear all chunks from the collection."""
    print("=" * 70)
    print("  clear_collection.py — Clear ChromaDB Collection")
    print("=" * 70)

    # Connect to ChromaDB
    print(f"\n📂 Connecting to ChromaDB at: {CHROMA_PATH}")
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name=COLLECTION)

    # Get current count
    all_data = collection.get()
    current_count = len(all_data["ids"])

    if current_count == 0:
        print(f"\n✨ Collection '{COLLECTION}' is already empty")
        print(f"   No action needed\n")
        return

    # Confirm deletion
    print(f"\n⚠️  WARNING: About to delete {current_count} chunks from '{COLLECTION}'")
    print(f"   This action cannot be undone!")
    print(f"\n   To backup first:")
    print(f"     cp -r {CHROMA_PATH} {CHROMA_PATH}.backup_$(date +%Y-%m-%d)")

    response = input(f"\n   Type 'DELETE' to confirm: ")

    if response != "DELETE":
        print(f"\n❌ Cancelled - no chunks deleted")
        print(f"   Collection remains unchanged\n")
        return

    # Delete all chunks
    print(f"\n🗑️  Deleting {current_count} chunks...")
    collection.delete(ids=all_data["ids"])

    # Verify deletion
    remaining = len(collection.get()["ids"])
    if remaining == 0:
        print(f"   ✅ Successfully deleted all chunks")
        print(f"\n📊 Collection '{COLLECTION}' is now empty")
        print(f"\n   Next steps:")
        print(f"     python embed_biosketch.py      # Embed authoritative source first")
        print(f"     python embed_resume.py         # Embed resume with sections")
        print(f"     python embed_readmes.py        # Embed project READMEs")
        print(f"     python embed_mkdocs.py         # Embed MkDocs sites")
        print(f"     python verify_collection.py    # Verify results\n")
    else:
        print(f"   ⚠️  Warning: {remaining} chunks remain")
        print(f"   Deletion may have been incomplete\n")


if __name__ == "__main__":
    main()
