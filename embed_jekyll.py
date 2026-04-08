"""
embed_jekyll.py
─────────────────────────────────────────────────────────────────
Script to fetch all pages from a Jekyll/GitHub Pages site via its
sitemap.xml and embed into the existing ChromaDB collection.

WHY trafilatura?
  Trafilatura uses heuristic + ML-based main content detection to
  strip nav, footers, sidebars, and ads automatically — no custom
  HTML parsing needed. Cleaner output than BeautifulSoup for this use case.

USAGE:
    python embed_jekyll.py

    Optional flags:
    --site-url URL          Base URL of Jekyll site (default: see JEKYLL_SITES)
    --site-name NAME        Short name for metadata (default: derived from URL)
    --force-reembed         Delete existing chunks for this site and re-embed
    --dry-run               Fetch + parse pages without embedding
    --max-pages N           Limit to first N pages (useful for testing)

EXAMPLES:
    # Dry run to preview what would be embedded
    python embed_jekyll.py --dry-run

    # Embed with default site list
    python embed_jekyll.py

    # Re-embed after site content changes
    python embed_jekyll.py --force-reembed

    # Test with first 5 pages only
    python embed_jekyll.py --max-pages 5 --dry-run

    # Embed a specific site
    python embed_jekyll.py --site-url https://dagny099.github.io --site-name dagny099-site

STRUCTURE EXPECTED:
    your-project/
    ├── app.py
    ├── embed_jekyll.py       ← this file
    └── .chroma_db_DT/        ← shared ChromaDB
"""

import os
import uuid
import argparse
import trafilatura
from trafilatura.sitemaps import sitemap_search
import chromadb
from openai import OpenAI
from utils import chunk_prose, build_metadata

# ── CONFIG ───────────────────────────────────────────────────────
JEKYLL_SITES = [
    {"name": "dagny099-site", "base_url": "https://barbhs.com"},
    # Add more sites here if needed:
    # {"name": "other-site", "base_url": "https://example.github.io"},
]

CHROMA_PATH  = ".chroma_db_DT"   # must match app.py
COLLECTION   = "barb-twin"        # must match app.py
CHUNK_SIZE   = 900                # must match app.py
OVERLAP      = 120                 # must match app.py
MIN_CHARS    = 80                 # skip pages shorter than this (stub/redirect pages)
WHOLE_DOC_THRESHOLD = 1200
BATCH_SIZE   = 500                # OpenAI embedding batch size
# ─────────────────────────────────────────────────────────────────


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Embed Jekyll/GitHub Pages site content via sitemap",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python embed_jekyll.py --dry-run                      # Preview pages
  python embed_jekyll.py                                 # Embed all sites
  python embed_jekyll.py --force-reembed                 # Re-embed after updates
  python embed_jekyll.py --max-pages 5 --dry-run         # Test with 5 pages
  python embed_jekyll.py --site-url https://dagny099.github.io --site-name my-site
        """
    )
    parser.add_argument('--site-url', default=None,
                        help='Override: embed a single site by URL')
    parser.add_argument('--site-name', default=None,
                        help='Short name for metadata (used with --site-url)')
    parser.add_argument('--force-reembed', action='store_true',
                        help='Delete existing chunks for this site and re-embed')
    parser.add_argument('--dry-run', action='store_true',
                        help='Fetch and parse pages without embedding')
    parser.add_argument('--max-pages', type=int, default=None,
                        help='Limit to first N pages (for testing)')
    return parser.parse_args()


# ── FETCHING ──────────────────────────────────────────────────────

def get_urls_from_sitemap(base_url: str) -> list[str]:
    """
    Fetch all page URLs from the site's sitemap.xml.
    Tries /sitemap.xml and /sitemap_index.xml automatically.
    Returns empty list if no sitemap found.
    """
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    print(f"   🗺️  Fetching sitemap: {sitemap_url}")

    try:
        urls = sitemap_search(sitemap_url)
        if not urls:
            # Some Jekyll setups use sitemap_index.xml
            alt_url = base_url.rstrip("/") + "/sitemap_index.xml"
            urls = sitemap_search(alt_url)
        return list(urls) if urls else []
    except Exception as e:
        print(f"   ❌ Failed to fetch sitemap: {e}")
        return []


def fetch_and_extract(url: str) -> dict | None:
    """
    Fetch a page and extract main content using trafilatura.
    Returns dict with {text, title, url} or None if extraction fails.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None

        # Extract main content — trafilatura strips nav/footer/sidebar automatically
        text = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            no_fallback=False,        # Fall back to raw text if heuristics fail
            favor_precision=False,    # Favor recall for personal/portfolio sites
        )

        # Extract metadata separately for title
        meta = trafilatura.extract_metadata(downloaded)
        title = meta.title if meta and meta.title else url.split("/")[-1] or "home"

        if not text or len(text.strip()) < MIN_CHARS:
            return None

        return {
            "text": text.strip(),
            "title": title,
            "url": url,
        }

    except Exception as e:
        print(f"   ⚠️  Failed to extract {url}: {e}")
        return None


# ── INGESTION ─────────────────────────────────────────────────────

def already_embedded(collection, source: str) -> bool:
    """Guard against re-embedding the same page (safe to re-run)."""
    results = collection.get(where={"source": source})
    return len(results["ids"]) > 0


def delete_existing_site(collection, site_name: str):
    """Delete all chunks from a given site."""
    try:
        all_data = collection.get(include=["metadatas"])
        source_prefix = f"jekyll:{site_name}:"
        matching_ids = [
            id_ for id_, meta in zip(all_data["ids"], all_data["metadatas"])
            if meta.get("source", "").startswith(source_prefix)
        ]
        if matching_ids:
            print(f"   🗑️  Deleting {len(matching_ids)} existing chunks for {site_name}...")
            collection.delete(ids=matching_ids)
            print(f"   ✅ Deleted successfully")
        else:
            print(f"   ℹ️  No existing chunks found for {site_name}")
    except Exception as e:
        print(f"   ⚠️  Warning: Could not delete existing chunks: {e}")


def url_to_path(url: str, base_url: str) -> str:
    """Derive a clean path string from a URL for use in source metadata."""
    path = url.replace(base_url.rstrip("/"), "").strip("/")
    return path or "home"


def process_site(site_name: str, base_url: str, collection, client: OpenAI,
                 force_reembed: bool = False, dry_run: bool = False,
                 max_pages: int = None):
    """Main pipeline for one site: discover → fetch → chunk → embed → store."""

    print(f"\n🌐 Processing site: {site_name}")
    print(f"   URL: {base_url}")

    # ── Discover pages via sitemap ────────────────────────────────
    urls = get_urls_from_sitemap(base_url)
    if not urls:
        print(f"   ❌ No URLs found. Check that {base_url}/sitemap.xml exists.")
        print(f"      (Tip: add 'jekyll-sitemap' to your Gemfile plugins)")
        return 0

    if max_pages:
        urls = urls[:max_pages]
        print(f"   ⚠️  Limiting to first {max_pages} pages (--max-pages flag)")

    print(f"   Found {len(urls)} URLs in sitemap")

    # ── Handle force re-embed ─────────────────────────────────────
    if force_reembed and not dry_run:
        delete_existing_site(collection, site_name)

    # ── Fetch + extract each page ─────────────────────────────────
    print(f"\n   📥 Fetching and extracting page content...")
    all_chunks, all_ids, all_metadatas = [], [], []
    skipped_existing, skipped_empty, pages_processed = 0, 0, 0

    for url in urls:
        path = url_to_path(url, base_url)
        source = f"jekyll:{site_name}:{path}"

        # Skip if already embedded (and not force re-embedding)
        if not force_reembed and not dry_run and already_embedded(collection, source):
            skipped_existing += 1
            continue

        page = fetch_and_extract(url)
        if not page:
            skipped_empty += 1
            continue

        pages_processed += 1

        if dry_run:
            preview = page["text"][:200] + "..." if len(page["text"]) > 200 else page["text"]
            print(f"\n   {'='*60}")
            print(f"   PAGE: {page['title']}")
            print(f"   URL:  {url}")
            print(f"   CHARS: {len(page['text'])}")
            print(f"   PREVIEW: {preview}")
            continue

        # Chunk the page content
        if len(page["text"]) <= WHOLE_DOC_THRESHOLD:
            chunk_results = [{"text": page["text"], "para_start": 0,
                            "para_end": -1, "char_count": len(page["text"])}]
        else:
            chunk_results = chunk_prose(page["text"], chunk_size=CHUNK_SIZE, overlap=OVERLAP)
            
        if not chunk_results:
            skipped_empty += 1
            continue

        for chunk_index, chunk_data in enumerate(chunk_results):
            chunk_id = str(uuid.uuid4())
            metadata = build_metadata(
                source_type="jekyll",
                identifier=f"{site_name}:{path}",
                section_name=page["title"],
                chunk_index=chunk_index,
                site=site_name,
                page_url=url,
                title=page["title"],
            )
            all_chunks.append(chunk_data["text"])
            all_ids.append(chunk_id)
            all_metadatas.append(metadata)

        print(f"   ✅ [{page['title']}]  →  {len(chunk_results)} chunks")

    # ── Summary for dry run ───────────────────────────────────────
    if dry_run:
        print(f"\n   ✅ Dry run complete — {pages_processed} pages found, no data embedded")
        print(f"      Skipped (too short/empty): {skipped_empty}")
        return 0

    if skipped_existing > 0:
        print(f"\n   ⏭️  Skipped {skipped_existing} already-embedded pages")

    if not all_chunks:
        print(f"   ✨ Nothing new to embed for {site_name}")
        return 0

    # ── Embed + store ─────────────────────────────────────────────
    print(f"\n   🔢 Embedding {len(all_chunks)} chunks in batches of {BATCH_SIZE}...")
    embeddings = []
    total_batches = -(-len(all_chunks) // BATCH_SIZE)  # ceiling division

    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        try:
            response = client.embeddings.create(model="text-embedding-3-small", input=batch)
            embeddings.extend([item.embedding for item in response.data])
            print(f"      Batch {i // BATCH_SIZE + 1}/{total_batches} done ✅")
        except Exception as e:
            print(f"   ❌ Error embedding batch: {e}")
            raise

    try:
        collection.add(
            ids=all_ids,
            embeddings=embeddings,
            documents=all_chunks,
            metadatas=all_metadatas
        )
        print(f"   💾 Saved {len(all_chunks)} chunks to ChromaDB")
    except Exception as e:
        print(f"   ❌ Failed to store chunks: {e}")
        raise

    return len(all_chunks)


def print_summary(collection):
    """Show Jekyll-specific breakdown in the collection."""
    total = collection.count()
    all_metas = collection.get(include=["metadatas"])["metadatas"]

    jekyll_counts = {}
    for m in all_metas:
        src = m.get("source", "")
        if src.startswith("jekyll:"):
            site = m.get("site", "unknown")
            jekyll_counts[site] = jekyll_counts.get(site, 0) + 1

    print(f"\n{'═'*55}")
    print(f"  📊 COLLECTION SUMMARY  →  '{COLLECTION}'")
    print(f"{'─'*55}")
    print(f"  Total chunks : {total}")
    print(f"{'─'*55}")
    if jekyll_counts:
        print(f"  Jekyll Sites:")
        for site, count in sorted(jekyll_counts.items()):
            print(f"    {'↳ ' + site:<28} {count:>5} chunks")
    else:
        print(f"  Jekyll Sites: (none embedded yet)")
    print(f"{'═'*55}\n")


# ── MAIN ─────────────────────────────────────────────────────────
def main():
    args = parse_args()

    print("=" * 55)
    print("  embed_jekyll.py — Jekyll Site Ingestion Pipeline")
    print("=" * 55)

    # ── Setup ─────────────────────────────────────────────────────
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise Exception("❌ OPENAI_API_KEY not set — check your environment variables")

    chroma_client = None
    if not args.dry_run:
        client = OpenAI(api_key=OPENAI_API_KEY)
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_or_create_collection(name=COLLECTION)
    else:
        client = None
        collection = None

    try:
        # ── Determine sites to process ────────────────────────────────
        if args.site_url:
            # Single site override from CLI
            site_name = args.site_name or args.site_url.split("//")[-1].split(".")[0]
            sites = [{"name": site_name, "base_url": args.site_url}]
        else:
            sites = JEKYLL_SITES

        # ── Process each site ─────────────────────────────────────────
        total_embedded = 0
        for site in sites:
            n = process_site(
                site_name=site["name"],
                base_url=site["base_url"],
                collection=collection,
                client=client,
                force_reembed=args.force_reembed,
                dry_run=args.dry_run,
                max_pages=args.max_pages,
            )
            total_embedded += n

        if not args.dry_run:
            print_summary(collection)
            print(f"🎉 Done! {total_embedded} total new chunks added.")
            print(f"   Launch app.py — Jekyll content is now in the knowledge base.\n")
        else:
            print(f"\n🎉 Dry run complete.\n")
    finally:
        # Explicitly close ChromaDB connection to release SQLite file locks
        if chroma_client is not None:
            del collection
            del chroma_client
            import gc
            gc.collect()


if __name__ == "__main__":
    main()
