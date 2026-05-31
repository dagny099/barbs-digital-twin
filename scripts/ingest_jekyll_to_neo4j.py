"""
ingest_jekyll_to_neo4j.py
=========================
Idempotent ingestion of Jekyll site content (_posts, data-stories) into Neo4j.

Analogous to embed_jekyll.py but targets Neo4j instead of ChromaDB.
Uses MERGE throughout — safe to re-run at any time without wiping the graph.
Sections whose content changed get their embedding cleared so embed_sections.py
re-embeds only what changed.

USAGE:
    python scripts/ingest_jekyll_to_neo4j.py               # incremental
    python scripts/ingest_jekyll_to_neo4j.py --dry-run      # preview only
    python scripts/ingest_jekyll_to_neo4j.py --force-reingest
    python scripts/ingest_jekyll_to_neo4j.py --max-files 3 --dry-run
    python scripts/ingest_jekyll_to_neo4j.py --include-dirs _posts
    python scripts/ingest_jekyll_to_neo4j.py --exclude-files 2021-08-11-sensor-fleet-part-1.md

RE-RUN WORKFLOW (after updating your site):
    cd /Users/bhs/PROJECTS/dagny099.github.io && git pull
    python scripts/ingest_jekyll_to_neo4j.py
    python scripts/embed_sections.py
"""

import os
import sys
import re
import hashlib
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from datetime import datetime, timezone

import yaml
from dotenv import load_dotenv

from neo4j_utils import get_driver, close_driver
from utils import parse_markdown_sections, get_sensitivity

load_dotenv(override=True)

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Default: sibling directory ../dagny099.github.io relative to this project.
# Override with JEKYLL_REPO_PATH in .env if your repo lives elsewhere.
JEKYLL_REPO = Path(
    os.getenv("JEKYLL_REPO_PATH",
              Path(__file__).resolve().parent.parent.parent / "dagny099.github.io")
)

SOURCE_DIRS = [
#    {"dir": "_posts",       "source_type": "jekyll-post"},
    {"dir": "data-stories", "source_type": "jekyll-story"},
]

# Filenames (no path) to skip at ingestion time.
# Useful for deactivating posts without removing them from the Jekyll repo.
EXCLUDE_FILES = [
    "index.md",
    # Sensor-fleet detail posts — uncomment whichever you want to skip:
    "2021-08-11-sensor-fleet-part-1.md",
    "2021-08-14-sensor-fleet-part-2.md",
    "2021-08-17-sensor-fleet-part-3.md",
    "2021-08-22-sensor-fleet-part-4.md",
    "2021-08-27-sensor-fleet-part-5.md",
    "2021-09-05-sensor-fleet-part-6.md",
]

AUTO_EXCLUDE  = {"index.md"}  # always skipped regardless of directory
MIN_BODY_CHARS = 200          # skip files with too little prose after cleaning

# ─────────────────────────────────────────────────────────────────────────────


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def extract_front_matter(raw: str) -> tuple[dict, str]:
    """Split YAML front matter from body. Returns (meta_dict, body_text)."""
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
                return meta, parts[2].strip()
            except yaml.YAMLError:
                pass
    return {}, raw


def clean_body(text: str) -> str:
    """Strip Liquid tags and inline HTML; collapse excess blank lines."""
    text = re.sub(r"\{%[^%]*%\}", "", text)   # {% block tags %}
    text = re.sub(r"\{\{[^}]*\}\}", "", text)  # {{ output tags }}
    text = re.sub(r"<[^>]+>", "", text)        # <html tags>
    text = re.sub(r"\n{3,}", "\n\n", text)     # collapse blank lines
    return text.strip()


def extract_date_from_filename(filename: str) -> str:
    """Extract YYYY-MM-DD from Jekyll post filename, or empty string."""
    m = re.match(r"(\d{4}-\d{2}-\d{2})-", filename)
    return m.group(1) if m else ""


def doc_id_for(source_type: str, meta: dict, stem: str) -> str:
    """Stable document ID: source_type + permalink (or filename stem)."""
    permalink = str(meta.get("permalink", "")).strip("/")
    key = permalink if permalink else stem
    return f"{source_type}:{key}"


def process_file(
    session,
    filepath: Path,
    source_type: str,
    force_reingest: bool,
    dry_run: bool,
    stats: dict,
) -> str | None:
    """
    Parse and MERGE one Jekyll file. Returns the doc_id if the file was
    accepted (even skipped-unchanged), or None if rejected (draft/too short).
    """
    raw  = filepath.read_text(encoding="utf-8")
    meta, body = extract_front_matter(raw)

    # Skip unpublished content (published: false in front matter)
    if meta.get("published") is False:
        print(f"  ⏭  {filepath.name}  (published: false)")
        stats["skipped_draft"] += 1
        return None

    body = clean_body(body)
    if len(body) < MIN_BODY_CHARS:
        print(f"  ⏭  {filepath.name}  (too short after cleaning — {len(body)} chars)")
        stats["skipped_short"] += 1
        return None

    stem        = filepath.stem
    doc_id      = doc_id_for(source_type, meta, stem)
    title       = str(meta.get("title", stem))
    excerpt     = str(meta.get("excerpt", ""))
    permalink   = str(meta.get("permalink", ""))
    tags        = meta.get("tags", []) or []
    if isinstance(tags, str):
        tags = [tags]
    pub_date    = str(meta.get("date", extract_date_from_filename(filepath.name) or ""))
    sensitivity = get_sensitivity(source_type)
    body_hash   = _sha256(body)
    now         = datetime.now(timezone.utc).isoformat()

    sections = parse_markdown_sections(body, header_level=2, include_nested=True)
    if not sections:
        print(f"  ⏭  {filepath.name}  (no sections parsed)")
        stats["skipped_short"] += 1
        return None

    if dry_run:
        print(f"\n  {'='*58}")
        print(f"  FILE     : {filepath.name}")
        print(f"  doc_id   : {doc_id}")
        print(f"  title    : {title}")
        print(f"  date     : {pub_date}   tags: {tags}")
        print(f"  sections : {len(sections)}")
        for s in sections:
            print(f"    [{s['section_name'][:50]}]  {len(s['text'])} chars")
        stats["files_dry_run"] += 1
        return doc_id

    # ── MERGE Document node ───────────────────────────────────────────────
    session.run(
        """
        MERGE (d:Document {id: $id})
        SET d.source_type    = $source_type,
            d.file_path      = $file_path,
            d.title          = $title,
            d.sensitivity    = $sensitivity,
            d.content_hash   = $content_hash,
            d.last_updated   = $last_updated,
            d.published_date = $published_date,
            d.permalink      = $permalink,
            d.excerpt        = $excerpt,
            d.tags           = $tags
        """,
        {
            "id":             doc_id,
            "source_type":    source_type,
            "file_path":      str(filepath),
            "title":          title,
            "sensitivity":    sensitivity,
            "content_hash":   body_hash,
            "last_updated":   now,
            "published_date": pub_date,
            "permalink":      permalink,
            "excerpt":        excerpt,
            "tags":           tags,
        },
    )

    # ── MERGE Section nodes ───────────────────────────────────────────────
    section_ids   = []
    n_written     = 0

    for order, sec in enumerate(sections):
        text = sec["text"].strip()
        if len(text) < 50:
            continue

        sec_id   = f"{doc_id}:{sec['section_name']}"
        sec_hash = _sha256(text)

        existing = session.run(
            "MATCH (s:Section {id: $id}) RETURN s.content_hash AS hash",
            {"id": sec_id},
        ).single()

        if existing and existing["hash"] == sec_hash and not force_reingest:
            section_ids.append(sec_id)
            stats["sections_unchanged"] += 1
            continue

        session.run(
            """
            MERGE (s:Section {id: $id})
            SET s.name         = $name,
                s.full_text    = $full_text,
                s.sensitivity  = $sensitivity,
                s.order        = $order,
                s.char_count   = $char_count,
                s.content_hash = $content_hash,
                s.embedding    = null
            WITH s
            MATCH (d:Document {id: $doc_id})
            MERGE (d)-[:HAS_SECTION]->(s)
            """,
            {
                "id":           sec_id,
                "name":         sec["section_name"],
                "full_text":    text,
                "sensitivity":  sensitivity,
                "order":        order,
                "char_count":   len(text),
                "content_hash": sec_hash,
                "doc_id":       doc_id,
            },
        )
        section_ids.append(sec_id)
        n_written += 1
        stats["sections_written"] += 1

    # ── NEXT_SECTION chain ────────────────────────────────────────────────
    for i in range(len(section_ids) - 1):
        session.run(
            "MATCH (a:Section {id: $a}), (b:Section {id: $b}) MERGE (a)-[:NEXT_SECTION]->(b)",
            {"a": section_ids[i], "b": section_ids[i + 1]},
        )

    tag_str    = f"  [{', '.join(str(t) for t in tags[:3])}]" if tags else ""
    change_str = f"  ✏ {n_written} updated" if n_written else "  (unchanged)"
    print(f"  ✅ {filepath.name}  →  {len(section_ids)} sections{change_str}{tag_str}")
    stats["files_processed"] += 1
    return doc_id


def delete_orphan_nodes(session, current_doc_ids: set, source_types: list[str]) -> int:
    """Delete Document + Section nodes for files no longer present on disk."""
    records = session.run(
        "MATCH (d:Document) WHERE d.source_type IN $types RETURN d.id AS id",
        {"types": source_types},
    ).data()

    orphan_ids = [r["id"] for r in records if r["id"] not in current_doc_ids]
    for doc_id in orphan_ids:
        session.run(
            """
            MATCH (d:Document {id: $id})
            OPTIONAL MATCH (d)-[:HAS_SECTION]->(s:Section)
            DETACH DELETE s, d
            """,
            {"id": doc_id},
        )
    return len(orphan_ids)


def print_summary(session, source_types: list[str]) -> None:
    total_docs = session.run(
        "MATCH (d:Document) WHERE d.source_type IN $types RETURN count(d) AS cnt",
        {"types": source_types},
    ).single()["cnt"]
    total_secs = session.run(
        "MATCH (d:Document)-[:HAS_SECTION]->(s:Section) WHERE d.source_type IN $types RETURN count(s) AS cnt",
        {"types": source_types},
    ).single()["cnt"]
    unembedded = session.run(
        "MATCH (d:Document)-[:HAS_SECTION]->(s:Section) WHERE d.source_type IN $types AND s.embedding IS NULL RETURN count(s) AS cnt",
        {"types": source_types},
    ).single()["cnt"]

    print(f"\n{'═'*55}")
    print(f"  Jekyll content in Neo4j")
    print(f"{'─'*55}")
    print(f"  Documents : {total_docs}")
    print(f"  Sections  : {total_secs}")
    if unembedded:
        print(f"  ⚠  {unembedded} section(s) need embedding")
        print(f"     → run: python scripts/embed_sections.py")
    else:
        print(f"  ✓ All sections embedded")
    print(f"{'═'*55}\n")


def parse_args():
    p = argparse.ArgumentParser(
        description="Idempotent Jekyll → Neo4j ingestion (posts + data-stories)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/ingest_jekyll_to_neo4j.py --dry-run
  python scripts/ingest_jekyll_to_neo4j.py
  python scripts/ingest_jekyll_to_neo4j.py --force-reingest
  python scripts/ingest_jekyll_to_neo4j.py --include-dirs _posts
  python scripts/ingest_jekyll_to_neo4j.py --max-files 3 --dry-run
        """,
    )
    p.add_argument("--dry-run",        action="store_true",
                   help="Preview what would be processed without writing to Neo4j")
    p.add_argument("--force-reingest", action="store_true",
                   help="Re-process all files even if content hash is unchanged")
    p.add_argument("--max-files",      type=int, default=None,
                   help="Limit files per directory (for testing)")
    p.add_argument("--include-dirs",   nargs="+", metavar="DIR",
                   help="Only process these directories (overrides SOURCE_DIRS config)")
    p.add_argument("--exclude-files",  nargs="+", metavar="FILE",
                   help="Additional filenames to skip (augments EXCLUDE_FILES config)")
    return p.parse_args()


def main():
    args = parse_args()

    print("=" * 55)
    print("  ingest_jekyll_to_neo4j.py")
    print("=" * 55)

    if not JEKYLL_REPO.exists():
        print(f"❌ JEKYLL_REPO not found: {JEKYLL_REPO}")
        print("   Set JEKYLL_REPO_PATH in your .env or check the default path")
        sys.exit(1)

    print(f"  Jekyll repo : {JEKYLL_REPO}")
    if args.dry_run:
        print("  Mode        : DRY RUN (no Neo4j writes)")
    elif args.force_reingest:
        print("  Mode        : FORCE REINGEST (all sections re-processed)")
    else:
        print("  Mode        : INCREMENTAL (unchanged sections skipped)")

    # Build effective exclude set (config + auto + CLI)
    exclude_set = AUTO_EXCLUDE | set(EXCLUDE_FILES)
    if args.exclude_files:
        exclude_set |= set(args.exclude_files)

    # Build effective source dirs (CLI override or full config)
    if args.include_dirs:
        source_dirs = [s for s in SOURCE_DIRS if s["dir"] in args.include_dirs]
        if not source_dirs:
            print(f"❌ No matching SOURCE_DIRS for: {args.include_dirs}")
            sys.exit(1)
    else:
        source_dirs = SOURCE_DIRS

    source_types = [s["source_type"] for s in source_dirs]
    driver = None if args.dry_run else get_driver()

    stats = {
        "files_processed":  0,
        "files_dry_run":    0,
        "skipped_draft":    0,
        "skipped_excluded": 0,
        "skipped_short":    0,
        "sections_written": 0,
        "sections_unchanged": 0,
    }
    all_doc_ids = set()

    try:
        for source_cfg in source_dirs:
            dir_path    = JEKYLL_REPO / source_cfg["dir"]
            source_type = source_cfg["source_type"]

            if not dir_path.exists():
                print(f"\n⚠  Directory not found: {dir_path} — skipping")
                continue

            files = sorted(dir_path.glob("*.md"))
            if args.max_files:
                files = files[:args.max_files]

            print(f"\n📂 {source_cfg['dir']}  ({source_type})  —  {len(files)} .md files")

            session = None if args.dry_run else driver.session()
            try:
                for filepath in files:
                    if filepath.name in exclude_set:
                        print(f"  ⏭  {filepath.name}  (excluded)")
                        stats["skipped_excluded"] += 1
                        continue

                    doc_id = process_file(
                        session, filepath, source_type,
                        args.force_reingest, args.dry_run, stats,
                    )
                    if doc_id:
                        all_doc_ids.add(doc_id)
            finally:
                if session:
                    session.close()

        # ── Deletion pass: remove nodes for files no longer on disk ───────
        if not args.dry_run:
            with driver.session() as session:
                n_deleted = delete_orphan_nodes(session, all_doc_ids, source_types)
            if n_deleted:
                print(f"\n🗑  Removed {n_deleted} orphaned document(s) (files deleted from repo)")

        # ── Run summary ───────────────────────────────────────────────────
        print(f"\n{'─'*55}")
        if args.dry_run:
            print(f"  DRY RUN — {stats['files_dry_run']} files would be processed")
        else:
            print(f"  Files processed    : {stats['files_processed']}")
            print(f"  Sections written   : {stats['sections_written']}")
            print(f"  Sections unchanged : {stats['sections_unchanged']}")
        print(f"  Skipped (draft)    : {stats['skipped_draft']}")
        print(f"  Skipped (excluded) : {stats['skipped_excluded']}")
        print(f"  Skipped (short)    : {stats['skipped_short']}")

        if not args.dry_run:
            with driver.session() as session:
                print_summary(session, source_types)

    finally:
        if driver:
            close_driver()


if __name__ == "__main__":
    main()
