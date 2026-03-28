"""
chunk_inspector.py
──────────────────────────────────────────────────────────────────────────
Audit your ChromaDB knowledge base and simulate retrieval — without
calling the LLM. Run this after any re-ingest to catch chunk quality
problems before the twin ever sees them.

USAGE:
    python chunk_inspector.py                        # Full audit report
    python chunk_inspector.py --source kb-projects   # One source only
    python chunk_inspector.py --query "Resume Explorer architecture"
    python chunk_inspector.py --tiny                 # Show only bad chunks
    python chunk_inspector.py --all-chunks           # Dump every chunk
    python chunk_inspector.py --query "..." --n 12   # Retrieve N chunks

WHAT IT DOES:
    1. Chunk size distribution — find orphaned tiny chunks (<150 chars)
    2. Per-source breakdown — chunk count and avg size per source
    3. Retrieval simulation — embed a query, show the 8 chunks retrieved,
       formatted exactly as the LLM would see them
    4. Gap detection — sections with suspiciously few chunks
"""

import os
import sys
import argparse
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from collections import defaultdict

load_dotenv(override=True)

# ── CONFIG — must match app.py ──────────────────────────────────────────────
CHROMA_PATH      = ".chroma_db_DT"
COLLECTION       = "barb-twin"
MIN_CHUNK_CHARS  = 150    # chunks below this are flagged as problematic
N_RETRIEVE       = int(os.getenv("N_CHUNKS_RETRIEVE", 10))  # matches app.py default
# ────────────────────────────────────────────────────────────────────────────


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(name=COLLECTION)


# ── AUDIT ────────────────────────────────────────────────────────────────────

def audit_chunks(collection, source_filter: str = None, show_tiny: bool = False,
                 show_all: bool = False):
    """
    Print a full audit report of chunk quality in the collection.
    """
    all_data = collection.get(include=["documents", "metadatas"])
    docs      = all_data["documents"]
    metas     = all_data["metadatas"]

    if not docs:
        print("❌  Collection is empty.")
        return

    # Apply source filter if given
    if source_filter:
        pairs = [(d, m) for d, m in zip(docs, metas)
                 if m.get("source", "").startswith(source_filter)]
        if not pairs:
            print(f"❌  No chunks found with source prefix: {source_filter}")
            return
        docs, metas = zip(*pairs)

    total = len(docs)
    sizes = [len(d) for d in docs]

    # ── Overall stats ────────────────────────────────────────────────────────
    print(f"\n{'═'*65}")
    print(f"  CHUNK AUDIT  —  collection: {COLLECTION}")
    if source_filter:
        print(f"  Source filter: {source_filter}")
    print(f"{'─'*65}")
    print(f"  Total chunks : {total:,}")
    print(f"  Min size     : {min(sizes):,} chars")
    print(f"  Max size     : {max(sizes):,} chars")
    print(f"  Avg size     : {sum(sizes)//len(sizes):,} chars")
    tiny_chunks = [(d, m) for d, m in zip(docs, metas) if len(d) < MIN_CHUNK_CHARS]
    print(f"  Tiny (<{MIN_CHUNK_CHARS}ch) : {len(tiny_chunks):,}  {'⚠️  FIX THESE' if tiny_chunks else '✅'}")

    # ── Per-source breakdown ─────────────────────────────────────────────────
    source_data = defaultdict(list)
    for d, m in zip(docs, metas):
        src_key = m.get("source", "unknown").split(":")[0] + ":"
        source_data[src_key].append(len(d))

    print(f"\n{'─'*65}")
    print(f"  {'Source prefix':<35} {'Chunks':>7} {'Avg size':>10} {'Tiny':>6}")
    print(f"  {'─'*35} {'─'*7} {'─'*10} {'─'*6}")
    for src, chunk_sizes in sorted(source_data.items()):
        n_tiny = sum(1 for s in chunk_sizes if s < MIN_CHUNK_CHARS)
        tiny_flag = f"⚠️  {n_tiny}" if n_tiny else "✅"
        avg = sum(chunk_sizes) // len(chunk_sizes)
        print(f"  {src:<35} {len(chunk_sizes):>7,} {avg:>10,} {tiny_flag:>6}")

    # ── Size distribution buckets ────────────────────────────────────────────
    buckets = {"<150": 0, "150–300": 0, "300–600": 0, "600–900": 0, ">900": 0}
    for s in sizes:
        if   s <  150: buckets["<150"]     += 1
        elif s <  300: buckets["150–300"]  += 1
        elif s <  600: buckets["300–600"]  += 1
        elif s <  900: buckets["600–900"]  += 1
        else:          buckets[">900"]     += 1

    print(f"\n{'─'*65}")
    print(f"  Size distribution:")
    bar_total = max(buckets.values()) or 1
    for label, count in buckets.items():
        bar = "█" * int(count / bar_total * 30)
        pct = count / total * 100
        flag = "  ← 🔴 too small" if label == "<150" and count > 0 else ""
        print(f"  {label:>8}  {bar:<30}  {count:>4} ({pct:.0f}%){flag}")

    # ── Show tiny chunks ─────────────────────────────────────────────────────
    if show_tiny and tiny_chunks:
        print(f"\n{'─'*65}")
        print(f"  TINY CHUNKS ({len(tiny_chunks)} total):")
        for d, m in tiny_chunks[:20]:
            src = m.get("source", "?")
            sec = m.get("section", "?")
            print(f"\n  [{src} — {sec}]  ({len(d)} chars)")
            print(f"  {repr(d[:120])}")
        if len(tiny_chunks) > 20:
            print(f"\n  ... and {len(tiny_chunks) - 20} more. Run --tiny to see all.")

    # ── Show all chunks ──────────────────────────────────────────────────────
    if show_all:
        print(f"\n{'─'*65}")
        print(f"  ALL CHUNKS:")
        for i, (d, m) in enumerate(zip(docs, metas)):
            src = m.get("source", "?")
            sec = m.get("section", "?")
            idx = m.get("chunk_index", "?")
            print(f"\n  [{i+1}] {src} — {sec} (chunk {idx}, {len(d)} chars)")
            print(f"  {d[:200]}{'...' if len(d) > 200 else ''}")

    print(f"\n{'═'*65}\n")


# ── RETRIEVAL SIMULATION ──────────────────────────────────────────────────────

def simulate_retrieval(collection, query: str, n_results: int = N_RETRIEVE,
                       source_filter: str = None):
    """
    Embed a query and retrieve top N chunks — exactly as app.py does it.
    Prints what the LLM context window would actually contain.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌  OPENAI_API_KEY not set — needed for embedding the query.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    print(f"\n{'═'*65}")
    print(f"  RETRIEVAL SIMULATION")
    print(f"  Query: \"{query}\"")
    print(f"  N results: {n_results}")
    if source_filter:
        print(f"  Source filter: {source_filter}")
    print(f"{'─'*65}")

    # Embed the query
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=[query]
    )
    query_embedding = response.data[0].embedding

    # Retrieve
    kwargs = dict(query_embeddings=[query_embedding], n_results=n_results,
                  include=["documents", "metadatas", "distances"])
    if source_filter:
        kwargs["where"] = {"source": {"$eq": source_filter}}

    results = collection.query(**kwargs)

    retrieved_docs   = results["documents"][0]
    retrieved_metas  = results["metadatas"][0]
    retrieved_dists  = results["distances"][0]

    # ── Show what the LLM sees (with metadata prefix — the fix from app.py) ──
    print(f"\n  ── CONTEXT AS LLM SEES IT (with metadata prefix) ──\n")
    total_chars = 0
    for i, (doc, meta, dist) in enumerate(
        zip(retrieved_docs, retrieved_metas, retrieved_dists)
    ):
        src     = meta.get("source", "?")
        section = meta.get("section", "")
        prefix  = f"[{src} — {section}]" if section else f"[{src}]"
        flagged = "  ← ⚠️  TINY" if len(doc) < MIN_CHUNK_CHARS else ""
        print(f"  {'─'*60}")
        print(f"  #{i+1}  dist={dist:.4f}  {len(doc)} chars{flagged}")
        print(f"  {prefix}")
        print(f"  {doc[:300]}{'...' if len(doc) > 300 else ''}")
        total_chars += len(doc) + len(prefix)

    print(f"\n{'─'*65}")
    print(f"  Total context: ~{total_chars:,} chars injected into system prompt")
    print(f"  Tiny chunks retrieved: "
          f"{sum(1 for d in retrieved_docs if len(d) < MIN_CHUNK_CHARS)}/{n_results}")
    print(f"{'═'*65}\n")


# ── QUICK QUERIES — canonical test set for your twin ─────────────────────────

CANONICAL_QUERIES = [
    "What projects has Barbara built?",
    "Tell me about Resume Explorer",
    "How does the digital twin work?",
    "What is Barbara's background?",
    "What problems does Barbara solve?",
    "How does she approach RAG systems?",
    "What tech stack does she use?",
    "Tell me about the beehive project",
]

def run_canonical_queries(collection, n_results: int = N_RETRIEVE):
    """
    Run the standard test queries and show retrieval stats for each.
    Use this to compare before/after a re-ingest.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌  OPENAI_API_KEY not set")
        return

    client = OpenAI(api_key=api_key)

    print(f"\n{'═'*65}")
    print(f"  CANONICAL QUERY EVAL  ({len(CANONICAL_QUERIES)} queries × {n_results} chunks)")
    print(f"{'─'*65}")
    print(f"  {'Query':<45} {'Tiny':>5} {'Avg dist':>9} {'Sources'}")
    print(f"  {'─'*45} {'─'*5} {'─'*9} {'─'*30}")

    for query in CANONICAL_QUERIES:
        response = client.embeddings.create(
            model="text-embedding-3-small", input=[query]
        )
        embedding = response.data[0].embedding

        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

        docs  = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        n_tiny   = sum(1 for d in docs if len(d) < MIN_CHUNK_CHARS)
        avg_dist = sum(dists) / len(dists)
        sources  = list(dict.fromkeys(
            m.get("source", "?").split(":")[0] for m in metas
        ))

        tiny_flag = f"⚠️  {n_tiny}" if n_tiny else "  0"
        q_short   = query[:44] + "…" if len(query) > 44 else query
        print(f"  {q_short:<45} {tiny_flag:>5} {avg_dist:>9.4f}  {', '.join(sources[:3])}")

    print(f"{'═'*65}\n")


# ── ARGUMENT PARSING ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Audit ChromaDB chunk quality and simulate retrieval.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python chunk_inspector.py                         # Full audit
  python chunk_inspector.py --tiny                  # Show tiny chunks only
  python chunk_inspector.py --source kb-projects    # One source
  python chunk_inspector.py --query "Resume Explorer architecture"
  python chunk_inspector.py --canonical             # Run standard test queries
  python chunk_inspector.py --all-chunks --source kb-biosketch
        """
    )
    parser.add_argument("--source",      metavar="PREFIX",
                        help="Filter to chunks whose source starts with PREFIX")
    parser.add_argument("--query",       metavar="TEXT",
                        help="Simulate retrieval for this query (requires OPENAI_API_KEY)")
    parser.add_argument("--n",           type=int, default=N_RETRIEVE,
                        help=f"Number of chunks to retrieve (default: {N_RETRIEVE})")
    parser.add_argument("--tiny",        action="store_true",
                        help="Print the full text of every tiny chunk")
    parser.add_argument("--all-chunks",  action="store_true",
                        help="Print every chunk (use with --source to limit output)")
    parser.add_argument("--canonical",   action="store_true",
                        help="Run standard test query set and show stats")
    return parser.parse_args()


# ── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    if not os.path.exists(CHROMA_PATH):
        print(f"❌  ChromaDB not found at {CHROMA_PATH}/")
        print(f"    Run: python ingest.py --all")
        sys.exit(1)

    collection = get_collection()

    if collection.count() == 0:
        print("❌  Collection is empty — run ingest.py first.")
        sys.exit(1)

    if args.query:
        simulate_retrieval(collection, args.query, n_results=args.n,
                           source_filter=args.source)
    elif args.canonical:
        run_canonical_queries(collection, n_results=args.n)
    else:
        audit_chunks(collection, source_filter=args.source,
                     show_tiny=args.tiny, show_all=args.all_chunks)


if __name__ == "__main__":
    main()
