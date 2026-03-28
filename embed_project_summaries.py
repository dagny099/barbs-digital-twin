"""
embed_project_summaries.py
───────────────────────────────────────────────────────────────────────
Script to parse, embed, and persist one-page project summary PDFs into
ChromaDB with section-aware metadata.

STRUCTURE:
    Each PDF follows a consistent 5-section template:
        What it is       → 1-2 sentence elevator pitch
        Who it's for     → target audience
        What it does     → key features (bullet list)
        How it works     → architecture (bullet list)
        How to run       → setup steps (skipped by default — low RAG value)

    Plus a synthetic "overview" chunk combining title + What it is +
    Who it's for for better portfolio-style query retrieval.

    Each section is embedded as an ATOMIC UNIT (no chunking) — sections
    are too short (~150-400 chars) to benefit from chunk_prose().

METADATA per chunk:
    {
        'source':       'project-summary:beehive-tracker',
        'section':      'What it does',       # normalized label
        'project_name': 'Beehive Photo Metadata Tracker',
        'tech_stack':   'Streamlit,OpenAI,Google Cloud Vision',  # comma-joined
        'chunk_index':  0
    }

USAGE:
    python embed_project_summaries.py

    Optional flags:
    --summaries-folder PATH   Path to folder of PDF files (default: inputs/project-summaries)
    --force-reembed           Delete existing chunks and re-embed all
    --dry-run                 Parse and print sections without embedding
    --include-how-to-run      Also embed "How to run" sections (skipped by default)

EXAMPLES:
    # Test parsing without embedding
    python embed_project_summaries.py --dry-run

    # Full embed
    python embed_project_summaries.py

    # Re-embed after PDF updates
    python embed_project_summaries.py --force-reembed
"""

import os
import re
import uuid
import glob
import argparse
import pdfplumber
import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from utils import (
    build_metadata,
    delete_chunks_by_source,
    section_already_embedded,
)

load_dotenv(override=True)

# ── CONFIG ──────────────────────────────────────────────────────────────
SUMMARIES_FOLDER = "inputs/project-summaries"
CHROMA_PATH      = ".chroma_db_DT"
COLLECTION       = "barb-twin"
BATCH_SIZE       = 500
# ────────────────────────────────────────────────────────────────────────

# Section labels: these are startswith() prefixes, not exact matches.
# Handles "What it does (key features)" and "What it does — key features" alike.
SECTION_PREFIXES = [
    "What it is",
    "Who it's for",
    "What it does",
    "How it works",
    "How to run",
]

# Footer line prefixes — strip from text but capture date if present
FOOTER_PREFIXES = ("Sources:", "Evidence:", "Status:", "Source:", "One-page summary")

# Tech keywords for metadata extraction (case-insensitive scan of full text)
TECH_KEYWORDS = [
    "Streamlit", "Gradio", "Neo4j", "ChromaDB", "OpenAI", "SQLite",
    "Ollama", "NetworkX", "Folium", "MySQL", "FastAPI", "Flask",
    "PostgreSQL", "MongoDB", "Pinecone", "LangChain", "DSPy",
    "MLflow", "SpatiaLite", "Plotly", "Matplotlib", "PyTorch",
    "Google Cloud Vision", "Open-Meteo", "KMeans", "BeautifulSoup",
    "Anthropic", "Claude",
]

FEATURED_SLUGS = {
    "digital-twin-one-pager",
    "resume-explorer-one-pager",       
    "concept-cartographer-summary",  # run --dry-run first to confirm slugs are correct,
    "beehive-tracker-one-pager",
    "fitness-dashboard-summary"
}

# ── ARGUMENT PARSING ─────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Embed project summary PDFs with section-aware metadata",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python embed_project_summaries.py --dry-run          # Preview parsing
  python embed_project_summaries.py                    # Full embed
  python embed_project_summaries.py --force-reembed    # Re-embed after updates
        """
    )
    parser.add_argument('--summaries-folder', default=SUMMARIES_FOLDER,
                        help='Path to folder containing PDF files')
    parser.add_argument('--force-reembed', action='store_true',
                        help='Delete existing chunks and re-embed all')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and print sections without embedding')
    parser.add_argument('--include-how-to-run', action='store_true',
                        help='Also embed "How to run" sections (skipped by default)')
    return parser.parse_args()


# ── PDF EXTRACTION ────────────────────────────────────────────────────────

def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract plain text from a PDF using pdfplumber.
    Returns empty string if extraction fails.
    """
    try:
        with pdfplumber.open(filepath) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()
    except Exception as e:
        print(f"   ❌ Failed to extract text from {filepath}: {e}")
        return ""


def slug_from_filename(filepath: str) -> str:
    """
    Derive a clean slug from the PDF filename for use in source metadata.
    e.g. 'beehive-tracker-one-pager.pdf' → 'beehive-tracker'
         'concept-cartographer-summary.pdf' → 'concept-cartographer'
    """
    name = os.path.basename(filepath)
    name = re.sub(r'\.pdf$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_](one-pager|onepager|summary|one_pager)$', '', name, flags=re.IGNORECASE)
    return name.lower()


# ── SECTION PARSING ───────────────────────────────────────────────────────

def is_section_header(line: str) -> str | None:
    """
    Check if a line is a known section header using prefix matching.
    Returns the normalized section name or None.
    Uses startswith() to handle label variations like:
        'What it does (key features)' and 'What it does — key features'
    """
    stripped = line.strip()
    for prefix in SECTION_PREFIXES:
        if stripped.startswith(prefix):
            return prefix  # return normalized prefix, not the exact label
    return None


def is_footer_line(line: str) -> bool:
    """Check if a line is a footer/metadata line to strip from text."""
    stripped = line.strip()
    return any(stripped.startswith(fp) for fp in FOOTER_PREFIXES)


def parse_sections(raw_text: str) -> dict:
    """
    Parse PDF text into a dict of section_name → section_text.

    Template detection:
    - Lines before the first section header = title block
    - Lines are accumulated per section until the next header
    - Footer lines are stripped from text but date string is captured

    Returns:
        {
            'title': 'Beehive Photo Metadata Tracker',
            'What it is': 'Streamlit-based web app that...',
            'Who it\'s for': 'Primary users: ...',
            'What it does': 'Upload hive photos...',
            'How it works': 'Navigation: ...',
            'How to run': 'Clone: git clone...',
            '_footer': 'Sources: README.md, ...',   # raw footer text if present
            '_date': 'March 2026',                  # extracted date if present
        }
    """
    lines = raw_text.split('\n')
    sections = {}
    current_section = None
    current_lines = []
    title_lines = []
    footer_lines = []
    found_first_section = False

    for line in lines:
        # Check for footer lines — capture but don't include in section text
        if is_footer_line(line):
            footer_lines.append(line.strip())
            continue

        section_label = is_section_header(line)

        if section_label:
            # Save previous section
            if current_section and current_lines:
                sections[current_section] = '\n'.join(current_lines).strip()
            elif not found_first_section and title_lines:
                # Everything accumulated before first section = title block
                sections['title'] = ' '.join(
                    l.strip() for l in title_lines if l.strip()
                )

            current_section = section_label
            current_lines = []
            found_first_section = True

        elif not found_first_section:
            # Still in title block
            title_lines.append(line)

        else:
            current_lines.append(line)

    # Save last section
    if current_section and current_lines:
        sections[current_section] = '\n'.join(current_lines).strip()

    # Capture footer
    if footer_lines:
        sections['_footer'] = '\n'.join(footer_lines)

    # Try to extract a date from footer lines
    date_match = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        '\n'.join(footer_lines)
    )
    if date_match:
        sections['_date'] = date_match.group(0)

    return sections


# ── METADATA HELPERS ──────────────────────────────────────────────────────

def extract_tech_stack(full_text: str) -> str:
    """
    Scan full document text for known tech keywords.
    Returns comma-joined string (ChromaDB metadata values must be strings, not lists).
    """
    found = [kw for kw in TECH_KEYWORDS if kw.lower() in full_text.lower()]
    return ','.join(found) if found else ''


def clean_title(raw_title: str) -> str:
    """
    Strip common suffixes from PDF titles to get the project name.
    e.g. 'Beehive Photo Metadata Tracker — One Page' → 'Beehive Photo Metadata Tracker'
         'Concept Cartographer — One-Page Summary' → 'Concept Cartographer'
    """
    # Remove trailing " — One Page", " — One-Page Summary", " - One Page Summary", etc.
    cleaned = re.sub(
        r'\s*[—–-]+\s*One.?Page.*$', '', raw_title, flags=re.IGNORECASE
    ).strip()
    # Also strip trailing "(One-Page Summary)" style
    cleaned = re.sub(r'\s*\(One.?Page.*\)\s*$', '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned or raw_title



# ── CORE PROCESSING ───────────────────────────────────────────────────────

def process_pdf(filepath: str, collection, client: OpenAI,
                force_reembed: bool, dry_run: bool, include_how_to_run: bool):
    """
    Full pipeline for one PDF: extract → parse → build chunks → embed → store.
    Returns number of chunks embedded (0 for dry-run or already-embedded).
    """
    slug = slug_from_filename(filepath)
    source = f"project-summary:{slug}"

    # Extract text
    raw_text = extract_text_from_pdf(filepath)
    if not raw_text:
        print(f"   ⚠️  Skipping {slug} — could not extract text")
        return 0

    # Parse into sections
    sections = parse_sections(raw_text)

    project_name = clean_title(sections.get('title', slug))
    tech_stack   = extract_tech_stack(raw_text)
    date_str     = sections.get('_date', '')

    if dry_run:
        print(f"\n   {'='*60}")
        print(f"   PROJECT: {project_name}")
        print(f"   SLUG:    {slug}")
        print(f"   TECH:    {tech_stack or '(none detected)'}")
        print(f"   DATE:    {date_str or '(none)'}")
        print(f"   SECTIONS FOUND: {[k for k in sections if not k.startswith('_')]}")
        for section_name, text in sections.items():
            if section_name.startswith('_'):
                continue
            print(f"\n   [{section_name}] ({len(text)} chars)")
            preview = text[:200] + '...' if len(text) > 200 else text
            print(f"   {preview}")
        return 0

    # Build list of (section_label, text) to embed
    # Includes synthetic "overview" chunk and optionally "How to run"
    chunks_to_embed = []

    # 1. Synthetic overview chunk: title + What it is + Who it's for
    overview_parts = []
    if project_name:
        overview_parts.append(project_name)
    if sections.get("What it is"):
        overview_parts.append(sections["What it is"])
    if sections.get("Who it's for"):
        overview_parts.append(sections["Who it's for"])
    if overview_parts:
        chunks_to_embed.append(("overview", "\n\n".join(overview_parts)))

    # 2. Individual sections
    for prefix in SECTION_PREFIXES:
        if prefix == "How to run" and not include_how_to_run:
            continue
        text = sections.get(prefix, "").strip()
        if text:
            chunks_to_embed.append((prefix, text))

    if not chunks_to_embed:
        print(f"   ⚠️  {slug}: no sections found after parsing — skipping")
        return 0

    # Check idempotency and filter to only new chunks
    new_chunks = []
    for section_label, text in chunks_to_embed:
        if not force_reembed and section_already_embedded(collection, source, section_label):
            continue
        new_chunks.append((section_label, text))

    if not new_chunks:
        print(f"   ⏭️  {project_name} — already embedded, skipping")
        return 0

    # Build parallel lists for ChromaDB
    all_texts, all_ids, all_metadatas = [], [], []
    for chunk_index, (section_label, text) in enumerate(new_chunks):
        metadata = build_metadata(
            source_type="project-summary",
            identifier=slug,
            section_name=section_label,
            chunk_index=chunk_index,
            project_name=project_name,
            tech_stack=tech_stack,
        )
        metadata["featured"] = slug in FEATURED_SLUGS
        metadata["char_count"] = len(text)

        if date_str:
            metadata['date'] = date_str

        all_texts.append(text)
        all_ids.append(str(uuid.uuid4()))
        all_metadatas.append(metadata)

    section_labels = [s for s, _ in new_chunks]
    print(f"   ✅ {project_name}  →  {len(all_texts)} chunks  {section_labels}")
    return _embed_and_store(all_texts, all_ids, all_metadatas, client, collection)


def _embed_and_store(texts, ids, metadatas, client, collection) -> int:
    """Batch-embed texts and store in ChromaDB. Returns count stored."""
    embeddings = []
    total_batches = -(-len(texts) // BATCH_SIZE)

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        try:
            response = client.embeddings.create(model="text-embedding-3-small", input=batch)
            embeddings.extend([item.embedding for item in response.data])
            if total_batches > 1:
                print(f"      Batch {i // BATCH_SIZE + 1}/{total_batches} done ✅")
        except Exception as e:
            print(f"   ❌ Embedding error: {e}")
            raise

    try:
        collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    except Exception as e:
        print(f"   ❌ Failed to store chunks: {e}")
        raise

    return len(texts)


def print_summary(collection):
    """Show project-summary breakdown in the collection."""
    total = collection.count()
    all_metas = collection.get(include=["metadatas"])["metadatas"]

    project_counts = {}
    section_counts = {}
    for m in all_metas:
        src = m.get("source", "")
        if src.startswith("project-summary:"):
            proj = m.get("project_name", src)
            section = m.get("section", "unknown")
            project_counts[proj] = project_counts.get(proj, 0) + 1
            section_counts[section] = section_counts.get(section, 0) + 1

    print(f"\n{'═'*60}")
    print(f"  📊 COLLECTION SUMMARY  →  '{COLLECTION}'")
    print(f"{'─'*60}")
    print(f"  Total chunks in DB : {total}")
    print(f"{'─'*60}")
    if project_counts:
        print(f"  Project Summaries ({len(project_counts)} projects):")
        for proj, count in sorted(project_counts.items()):
            print(f"    {'↳ ' + proj:<45} {count:>3} chunks")
        print(f"{'─'*60}")
        print(f"  Section breakdown:")
        for section, count in sorted(section_counts.items(), key=lambda x: -x[1]):
            print(f"    {'↳ ' + section:<45} {count:>3} chunks")
    else:
        print(f"  Project Summaries: (none embedded yet)")
    print(f"{'═'*60}\n")


# ── MAIN ──────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    print("=" * 60)
    print("  embed_project_summaries.py — Project Summary Ingestion")
    print("=" * 60)

    # ── Setup ──────────────────────────────────────────────────────
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

    # ── Find PDFs ──────────────────────────────────────────────────
    pattern = os.path.join(args.summaries_folder, "*.pdf")
    pdf_files = sorted(glob.glob(pattern))

    if not pdf_files:
        raise FileNotFoundError(
            f"❌ No PDF files found in '{args.summaries_folder}/' — check your path"
        )

    print(f"\n📁 Found {len(pdf_files)} PDFs in: {args.summaries_folder}/")
    if args.include_how_to_run:
        print(f"   ℹ️  Including 'How to run' sections (--include-how-to-run)")
    else:
        print(f"   ℹ️  Skipping 'How to run' sections (use --include-how-to-run to embed)")

    # ── Handle force re-embed ──────────────────────────────────────
    if args.force_reembed and not args.dry_run:
        print(f"\n🔄 Force re-embed requested...")
        delete_chunks_by_source(collection, "project-summary:")

    # ── Process each PDF ───────────────────────────────────────────
    print(f"\n⚙️  Processing {len(pdf_files)} PDFs...")
    total_embedded = 0

    for filepath in pdf_files:
        n = process_pdf(
            filepath=filepath,
            collection=collection,
            client=client,
            force_reembed=args.force_reembed,
            dry_run=args.dry_run,
            include_how_to_run=args.include_how_to_run,
        )
        total_embedded += n

    # ── Final output ───────────────────────────────────────────────
    if args.dry_run:
        print(f"\n✅ Dry run complete — {len(pdf_files)} PDFs parsed, nothing embedded")
    else:
        if total_embedded > 0:
            print(f"\n💾 Saved {total_embedded} new chunks to ChromaDB at '{CHROMA_PATH}/'")
        print_summary(collection)
        print("🎉 Done! Launch app.py — project summaries are in the knowledge base.\n")


if __name__ == "__main__":
    main()
