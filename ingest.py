"""
ingest.py
─────────────────────────────────────────────────────────────────────
Master ingestion script for the Digital Twin knowledge base.

Orchestrates all embedding scripts with a status-first interactive menu.
Also supports non-interactive CLI flags for automation (e.g. GitHub Actions).

INTERACTIVE USAGE (default):
    python ingest.py

NON-INTERACTIVE FLAGS:
    python ingest.py --status                    # Show DB status and exit
    python ingest.py --all                       # Embed all sources (skip existing)
    python ingest.py --all --force               # Force re-embed everything
    python ingest.py --source kb-biosketch       # Embed one source (skip existing)
    python ingest.py --source kb-biosketch --force   # Force re-embed one source
    python ingest.py --dry-run                   # Preview without embedding (all sources)
    python ingest.py --source kb-projects --dry-run

SOURCE KEYS:
    kb-biosketch, kb-philosophy, kb-positioning, kb-projects, kb-career,
    kb-publications, project-summaries, jekyll
"""

import os
import sys
import subprocess
import argparse
import chromadb
from collections import Counter

# ── CONFIG ────────────────────────────────────────────────────────────────
CHROMA_PATH = ".chroma_db_DT"
COLLECTION  = "barb-twin"

# ── SOURCE REGISTRY ───────────────────────────────────────────────────────
# Each entry defines one data source and how to invoke its embed script.
#
# Fields:
#   key            Unique identifier used in --source flag and the menu
#   label          Human-readable name shown in the status table
#   description    Short description shown in the status table
#   script         Python script invoked via subprocess
#   base_args      CLI args always passed to the script
#   force_arg      Flag for force re-embed (None = not supported)
#   dry_run_arg    Flag for dry run        (None = not supported)
#   source_prefix  ChromaDB metadata prefix used to count stored chunks
#
# KB documents (kb_*.md in inputs/) all share the same script and format.
# The resume and old biosketch have been retired; their scripts are in archive/.
#
SOURCES = [

    # ── Structured KB documents (all use embed_kb_doc.py) ───────────────────
    # These six markdown files form the core of the knowledge base.
    # Each is parsed by ## H2 headers into named sections before chunking.
    {
        "key":           "kb-biosketch",
        "label":         "KB: Biosketch  ⭐ authoritative",
        "description":   "inputs/kb_biosketch.md",
        "script":        "embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_biosketch.md",
                          "--source-type", "kb-biosketch"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-biosketch:",
    },
    {
        "key":           "kb-philosophy",
        "label":         "KB: Philosophy & Approach",
        "description":   "inputs/kb_philosophy-and-approach.md",
        "script":        "embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_philosophy-and-approach.md",
                          "--source-type", "kb-philosophy"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-philosophy:",
    },
    {
        "key":           "kb-positioning",
        "label":         "KB: Professional Positioning",
        "description":   "inputs/kb_professional_positioning.md",
        "script":        "embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_professional_positioning.md",
                          "--source-type", "kb-positioning"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-positioning:",
    },
    {
        "key":           "kb-projects",
        "label":         "KB: Project Portfolio",
        "description":   "inputs/kb_projects.md",
        "script":        "embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_projects.md",
                          "--source-type", "kb-projects"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-projects:",
    },
    {
        "key":           "kb-career",
        "label":         "KB: Career Narrative",
        "description":   "inputs/kb_career_narrative.md",
        "script":        "embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_career_narrative.md",
                          "--source-type", "kb-career"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-career:",
    },
    {
        "key":           "kb-publications",
        "label":         "KB: Publications & Research",
        "description":   "inputs/kb_publications.md",
        "script":        "embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_publications.md",
                          "--source-type", "kb-publications"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-publications:",
    },


    # ── Other sources ────────────────────────────────────────────────────────
    {
        "key":           "project-summaries",
        "label":         "Project Summaries (PDFs)",
        "description":   "inputs/project-summaries/ (one-page PDFs)",
        "script":        "embed_project_summaries.py",
        "base_args":     [],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "project-summary:",
    },
    {
        "key":           "jekyll",
        "label":         "Jekyll Website",
        "description":   "https://barbhs.com (via sitemap)",
        "script":        "embed_jekyll.py",
        "base_args":     [],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "jekyll:",
    },

    {
        "key":           "project-walkthroughs",
        "label":         "Project Walkthroughs",
        "description":   "Walkthrough contexts from featured_projects.py (1 chunk per project, no splitting)",
        "script":        "embed_walkthroughs.py",
        "base_args":     [],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "project-walkthrough:",
    }
]

SOURCE_BY_KEY = {s["key"]: s for s in SOURCES}

# ── DB STATUS ─────────────────────────────────────────────────────────────

def get_db_status() -> dict:
    """
    Connect to ChromaDB and return chunk counts per source prefix.
    Returns {"_total": N, "biosketch:": N, ...} or {"_error": message}.
    """
    if not os.path.exists(CHROMA_PATH):
        return {"_error": f"DB directory not found: {CHROMA_PATH}/"}

    try:
        client     = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = client.get_or_create_collection(name=COLLECTION)
        all_metas  = collection.get(include=["metadatas"])["metadatas"]

        if not all_metas:
            return {"_total": 0}

        counts = Counter()
        for meta in all_metas:
            src = meta.get("source", "unknown")
            prefix = src.split(":")[0] + ":"
            counts[prefix] += 1

        counts["_total"] = sum(v for k, v in counts.items() if not k.startswith("_"))
        return dict(counts)

    except Exception as e:
        return {"_error": str(e)}


def chunks_for_source(status: dict, source: dict) -> str:
    """Return a formatted status string for one source."""
    if "_error" in status:
        return "⚠️  DB error"
    count = status.get(source["source_prefix"], 0)
    if count == 0:
        return "❌  not embedded"
    return f"✅  {count:,} chunks"


# ── DISPLAY ───────────────────────────────────────────────────────────────

def print_header():
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║         🤖  Digital Twin — Data Ingestion Manager               ║")
    print("╚══════════════════════════════════════════════════════════════════╝")


def print_status_table(status: dict):
    """Print the DB summary line and source table."""
    print()
    if "_error" in status:
        print(f"  ⚠️  Database: {status['_error']}")
        print(f"     Run any embed script to initialize it.\n")
    else:
        total = status.get("_total", 0)
        db_exists = os.path.exists(CHROMA_PATH)
        db_label  = f"{CHROMA_PATH}/"  if db_exists else "(not found)"
        print(f"  Database : {db_label}    Collection : {COLLECTION}    Total : {total:,} chunks")

    print()
    print(f"  {'#':<3} {'Source':<22} {'Description':<42} {'Status'}")
    print(f"  {'─'*3} {'─'*22} {'─'*42} {'─'*22}")

    for i, source in enumerate(SOURCES, start=1):
        status_str = chunks_for_source(status, source)
        desc = source["description"]
        if len(desc) > 41:
            desc = desc[:38] + "..."
        print(f"  {i:<3} {source['label']:<22} {desc:<42} {status_str}")
    print()


def print_menu():
    print("  Commands:")
    print(f"    [1–{len(SOURCES)}]   Select a source to embed")
    print("    a       Embed all sources (skip already-embedded)")
    print("    r       Refresh status")
    print("    q       Quit")
    print()


# ── EXECUTION ─────────────────────────────────────────────────────────────

def run_source(source: dict, force: bool = False, dry_run: bool = False) -> int:
    """
    Invoke an embed script via subprocess.
    Returns the exit code (0 = success).
    """
    cmd = [sys.executable, source["script"]] + source["base_args"]

    if force:
        if source["force_arg"]:
            cmd.append(source["force_arg"])
        else:
            print(f"\n  ⚠️  '{source['key']}' does not support force re-embed.")
            print(f"     To wipe and rebuild this source, run:")
            print(f"       python clear_collection.py   (clears entire DB)")
            print(f"     Then re-run ingest.py and select this source normally.")
            return 1

    if dry_run:
        if source["dry_run_arg"]:
            cmd.append(source["dry_run_arg"])
        else:
            print(f"\n  ⚠️  '{source['key']}' does not support --dry-run.")
            return 1

    print(f"\n  ▶  Running: {' '.join(cmd)}")
    print(f"  {'─' * 60}")
    result = subprocess.run(cmd)
    print(f"  {'─' * 60}")

    if result.returncode == 0:
        print(f"  ✅  {source['label']} — completed successfully")
    else:
        print(f"  ❌  {source['label']} — exited with code {result.returncode}")

    return result.returncode


def prompt_embed_options(source: dict) -> tuple[bool, bool] | None:
    """
    Ask the user how to embed the selected source.
    Returns (force, dry_run) or None if cancelled.
    """
    label = source["label"]
    has_force   = source["force_arg"] is not None
    has_dry_run = source["dry_run_arg"] is not None

    print(f"\n  Selected: {label}")
    print(f"    [1] Embed  (skip already-embedded chunks)")
    if has_force:
        print(f"    [2] Force re-embed  (wipe existing chunks and rebuild)")
    if has_dry_run:
        print(f"    [d] Dry run  (parse and preview without embedding)")
    print(f"    [q] Cancel")
    print()

    while True:
        choice = input("  ❯ ").strip().lower()
        if choice == "1":
            return (False, False)
        if choice == "2" and has_force:
            return (True, False)
        if choice == "d" and has_dry_run:
            return (False, True)
        if choice == "q":
            return None
        print(f"  Invalid choice — try again")


# ── MODES ─────────────────────────────────────────────────────────────────

def interactive_mode():
    """Run the interactive menu loop."""
    print_header()

    while True:
        status = get_db_status()
        print_status_table(status)
        print_menu()

        choice = input("  ❯ ").strip().lower()

        # Quit
        if choice == "q":
            print("\n  Goodbye!\n")
            break

        # Refresh
        elif choice == "r":
            continue

        # Embed all
        elif choice == "a":
            print(f"\n  Embedding all sources (skipping already-embedded)...")
            for source in SOURCES:
                run_source(source, force=False, dry_run=False)
            print(f"\n  ✅  All sources processed.")

        # Select by number
        elif choice.isdigit() and 1 <= int(choice) <= len(SOURCES):
            source = SOURCES[int(choice) - 1]
            result = prompt_embed_options(source)
            if result is None:
                print(f"  Cancelled.")
                continue
            force, dry_run = result
            run_source(source, force=force, dry_run=dry_run)

        else:
            print(f"  Invalid input — enter a number 1–{len(SOURCES)}, 'a' (all), 'r' (refresh), or 'q' (quit)")


def cli_mode(args):
    """Non-interactive execution driven by CLI flags."""
    if args.status:
        print_header()
        status = get_db_status()
        print_status_table(status)
        return

    if args.source:
        key = args.source
        if key not in SOURCE_BY_KEY:
            valid = ", ".join(SOURCE_BY_KEY.keys())
            print(f"❌ Unknown source '{key}'. Valid options: {valid}")
            sys.exit(1)
        sources_to_run = [SOURCE_BY_KEY[key]]
    else:
        sources_to_run = SOURCES  # --all

    errors = 0
    for source in sources_to_run:
        code = run_source(source, force=args.force, dry_run=args.dry_run)
        if code != 0:
            errors += 1

    if errors:
        print(f"\n⚠️  {errors} source(s) had errors.")
        sys.exit(1)

    if not args.dry_run:
        from db_sync import push_db
        push_db()


# ── ARGUMENT PARSING ──────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Digital Twin — Master Ingestion Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest.py                              # Interactive menu
  python ingest.py --status                     # Show DB status and exit
  python ingest.py --all                        # Embed all sources
  python ingest.py --all --force                # Force re-embed everything
  python ingest.py --source kb-biosketch           # Embed one source
  python ingest.py --source kb-publications --force
  python ingest.py --source project-summaries --dry-run

Source keys: kb-biosketch, kb-philosophy, kb-positioning, kb-projects,
             kb-career, kb-publications, project-summaries, jekyll
        """
    )
    parser.add_argument('--status',  action='store_true',
                        help='Show DB status and exit (no embedding)')
    parser.add_argument('--all',     action='store_true',
                        help='Embed all sources non-interactively')
    parser.add_argument('--source',  metavar='KEY',
                        help='Embed a single source by key')
    parser.add_argument('--force',   action='store_true',
                        help='Force re-embed (wipe existing chunks)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without embedding')
    return parser.parse_args()


# ── MAIN ──────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    # If any non-interactive flag is set, go straight to CLI mode
    if args.status or args.all or args.source or args.dry_run:
        cli_mode(args)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
