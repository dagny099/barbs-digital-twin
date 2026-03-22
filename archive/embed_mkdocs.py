"""
embed_mkdocs.py
─────────────────────────────────────────────────────────────────
ONE-TIME script to fetch all MkDocs site content via their
search_index.json files and embed into the existing ChromaDB.

WHY search_index.json?
  MkDocs pre-extracts clean text from every page at build time.
  No HTML parsing, no nav-stripping needed — it's pure signal.

USAGE:
    python embed_mkdocs.py

STRUCTURE EXPECTED:
    your-project/
    ├── app.py
    ├── embed_mkdocs.py       ← this file
    └── .chroma_db_DT/        ← shared ChromaDB
"""

import os
import uuid
import requests
import chromadb
from openai import OpenAI
from bs4 import BeautifulSoup
from utils import chunk_prose, parse_paragraphs

# ── CONFIG ───────────────────────────────────────────────────────
MKDOCS_SITES = [
    {"name": "beehive-tracker",      "base_url": "https://docs.barbhs.com/beehive-tracker/"},
    {"name": "fitness-dashboard",    "base_url": "https://docs.barbhs.com/fitness-dashboard/"},
    {"name": "naruto-network-graph", "base_url": "https://docs.barbhs.com/naruto-network-graph/"},
    {"name": "poolula-platform", "base_url": "https://docs.barbhs.com/poolula-platform"},
    {"name": "chronoscope", "base_url": "https://docs.barbhs.com/chronoscope"},
    {"name": "citation-compass", "base_url": "https://docs.barbhs.com/citation-compass"},
    {"name": "convoscope", "base_url": "https://docs.barbhs.com/convoscope"},
    {"name": "digital-memory-chest", "base_url": "https://docs.barbhs.com/digital-memory-chest"},
    # ── Add your other 5 sites here ──────────────────────────────
    # {"name": "your-project-name",  "base_url": "https://docs.barbhs.com/your-project/"},
]

CHROMA_PATH  = ".chroma_db_DT"   # must match app.py
COLLECTION   = "barb-twin"        # must match app.py
CHUNK_SIZE   = 500                # must match app.py
OVERLAP      = 50                 # must match app.py
MIN_CHARS    = 80                 # skip pages shorter than this (index stubs)
# ─────────────────────────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("❌ OPENAI_API_KEY not set")

client        = OpenAI(api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection    = chroma_client.get_or_create_collection(name=COLLECTION)


# ── CHUNKING ─────────────────────────────────────────────────────
# NOTE: chunk_prose() and parse_paragraphs() are now imported from utils.py
#       to eliminate code duplication across ingestion scripts
# ─────────────────────────────────────────────────────────────────


def strip_html(raw_html: str) -> str:
    """Remove any residual HTML tags from MkDocs text fields."""
    return BeautifulSoup(raw_html, "html.parser").get_text(separator=" ").strip()


def fetch_search_index(base_url: str) -> list[dict] | None:
    """Fetch and parse the MkDocs search_index.json for a site."""
    url = base_url.rstrip("/") + "/search/search_index.json"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get("docs", [])
    except Exception as e:
        print(f"   ❌ Failed to fetch {url}: {e}")
        return None


def parse_docs_to_documents(site_name: str, base_url: str, docs: list[dict]) -> list[dict]:
    """
    Convert MkDocs search index entries into embeddable documents.
    Each page becomes one document; chunking happens downstream.

    The search index 'text' field is clean prose — no HTML nav,
    no sidebar, no footer. Exactly what we want.
    """
    documents = []
    for doc in docs:
        title    = doc.get("title", "").strip()
        raw_text = doc.get("text", "").strip()
        location = doc.get("location", "")

        # Strip any residual HTML tags (some MkDocs themes inject them)
        clean_text = strip_html(raw_text)

        # Build a rich text block: title + body (helps retrieval)
        if title:
            full_text = f"# {title}\n\n{clean_text}"
        else:
            full_text = clean_text

        if len(clean_text) < MIN_CHARS:
            continue  # skip stub/index pages

        page_url = base_url.rstrip("/") + "/" + location.lstrip("/")
        source   = f"mkdocs:{site_name}:{location or 'home'}"

        documents.append({
            "source":   source,
            "text":     full_text,
            "title":    title,
            "page_url": page_url,
            "site":     site_name,
        })

    return documents


def already_embedded(source: str) -> bool:
    """Guard against re-embedding the same source (safe to re-run)."""
    results = collection.get(where={"source": source})
    return len(results["ids"]) > 0


def embed_documents(documents: list[dict]) -> int:
    """Chunk → embed → store. Skips already-embedded sources."""
    all_chunks, all_ids, all_metadatas = [], [], []
    skipped = []

    for doc in documents:
        source = doc["source"]

        if already_embedded(source):
            skipped.append(source)
            continue

        results  = chunk_prose(doc["text"], chunk_size=CHUNK_SIZE, overlap=OVERLAP)
        chunks_  = [r["text"] for r in results]
        ids_     = [str(uuid.uuid4()) for _ in chunks_]
        metas_   = [
            {
                "source":      source,
                "section":     doc["title"],  # Use page title as section
                "chunk_index": i,
                "site":        doc["site"],
                "page_url":    doc["page_url"],
                "title":       doc["title"],
            }
            for i in range(len(chunks_))
        ]

        all_chunks.extend(chunks_)
        all_ids.extend(ids_)
        all_metadatas.extend(metas_)
        print(f"      ✅ [{doc['title'] or 'home'}]  →  {len(chunks_)} chunks")

    if skipped:
        print(f"\n   ⏭️  Skipped {len(skipped)} already-embedded pages")

    if not all_chunks:
        print("   ✨ Nothing new to embed for this site")
        return 0

    print(f"\n   🔢 Embedding {len(all_chunks)} chunks via OpenAI...")

    # This failed when I had 2742 chunks to send, so created a simple batching loop
    # response   = client.embeddings.create(model="text-embedding-3-small", input=all_chunks)
    # embeddings = [item.embedding for item in response.data]
    # collection.add(ids=all_ids, embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas)
    
    BATCH_SIZE = 500  # well under the 2048 limit, safe for large chunks too

    #TODO -- Fix the "embed_readmes.py with this too"

    print(f"\n   🔢 Embedding {len(all_chunks)} chunks in batches of {BATCH_SIZE}...")
    embeddings = []
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        response = client.embeddings.create(model="text-embedding-3-small", input=batch)
        embeddings.extend([item.embedding for item in response.data])
        print(f"      Batch {i//BATCH_SIZE + 1}/{-(-len(all_chunks)//BATCH_SIZE)} done ✅")

    collection.add(ids=all_ids, embeddings=embeddings, documents=all_chunks, metadatas=all_metadatas)
    return len(all_chunks)


def print_summary():
    total     = collection.count()
    all_metas = collection.get(include=["metadatas"])["metadatas"]

    # Group by source category
    categories = {"biosketch": 0, "github-readme": 0, "mkdocs": 0, "other": 0}
    site_counts = {}

    for m in all_metas:
        src = m.get("source", "")
        if src.startswith("mkdocs:"):
            categories["mkdocs"] += 1
            site = m.get("site", "unknown")
            site_counts[site] = site_counts.get(site, 0) + 1
        elif src.startswith("github-readme:"):
            categories["github-readme"] += 1
        elif "biosketch" in src:
            categories["biosketch"] += 1
        else:
            categories["other"] += 1

    print(f"\n{'═'*55}")
    print(f"  📊 COLLECTION SUMMARY  →  '{COLLECTION}'")
    print(f"{'─'*55}")
    print(f"  Total chunks : {total}")
    print(f"{'─'*55}")
    print(f"  {'Biosketch':<30} {categories['biosketch']:>5} chunks  ⭐ authoritative")
    print(f"  {'GitHub READMEs':<30} {categories['github-readme']:>5} chunks")
    print(f"  {'MkDocs Sites':<30} {categories['mkdocs']:>5} chunks")
    if site_counts:
        for site, count in sorted(site_counts.items()):
            print(f"    {'↳ ' + site:<28} {count:>5} chunks")
    print(f"  {'Other':<30} {categories['other']:>5} chunks")
    print(f"{'═'*55}\n")


# ── MAIN ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  embed_mkdocs.py — MkDocs Site Ingestion Pipeline")
    print("=" * 55)

    total_embedded = 0

    for site in MKDOCS_SITES:
        name     = site["name"]
        base_url = site["base_url"]

        print(f"\n🌐 Processing: {name}")
        print(f"   URL: {base_url}")

        docs = fetch_search_index(base_url)
        if docs is None:
            continue

        documents = parse_docs_to_documents(name, base_url, docs)
        print(f"   Found {len(documents)} pages to process")

        n = embed_documents(documents)
        total_embedded += n
        print(f"   💾 Embedded {n} new chunks for {name}")

    print_summary()
    print(f"🎉 Done! {total_embedded} total new chunks added.")
    print(f"   Launch app.py — MkDocs content is now in the knowledge base.\n")
