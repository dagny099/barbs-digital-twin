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
    python ingest.py --check-drift               # Compare source hashes to DB     (NEW)
    python ingest.py --all                       # Embed all sources (skip existing)
    python ingest.py --all --force               # Force re-embed everything
    python ingest.py --source kb-biosketch       # Embed one source (skip existing)
    python ingest.py --source kb-biosketch --force   # Force re-embed one source
    python ingest.py --dry-run                   # Preview without embedding (all sources)
    python ingest.py --source kb-projects --dry-run
    python ingest.py --source kb-answers --dry-run    # verify 13 unique sections parse
    python ingest.py --source kb-origins --dry-run   

SOURCE KEYS:
    kb-biosketch, kb-philosophy, kb-positioning, kb-projects, kb-career,
    kb-publications, kb-answers, kb-origins,
    kb-dissertation-overview, kb-dissertation-relevance,
    kb-dissertation-philosophy, kb-intellectual-foundations,
    kb-easter-eggs,
    project-summaries, jekyll, project-walkthroughs

ENVIRONMENT VARIABLES (read from .env):
    INPUTS_PATH   Absolute path to the canonical inputs directory. Defaults to
                  "inputs" (the legacy in-repo location). When inputs live in
                  a separate private repo, point this at that clone's root —
                  e.g. INPUTS_PATH=/Users/dagny/code/digital-twin-inputs
    HF_TOKEN      HuggingFace Hub token for DB push/pull (see db_sync.py)
    """

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import subprocess
import argparse
import hashlib                              # NEW: drift detection via sha256
import chromadb
import time
import gc
from collections import Counter
from dotenv import load_dotenv              # NEW: read INPUTS_PATH from .env

load_dotenv(override=True)                  # NEW: must run before INPUTS_PATH is read

# ── CONFIG ────────────────────────────────────────────────────────────────
CHROMA_PATH = ".chroma_db_DT"
COLLECTION  = "barb-twin"

# NEW: Root directory for canonical source documents. The SOURCES registry below keeps
# its readable "inputs/..." paths; at invocation time _resolve_args() rewrites them
# under INPUTS_PATH. This decouples "what to ingest" (the registry, in code) from
# "where it lives on this machine" (the env var, in deployment config).
INPUTS_PATH = os.getenv("INPUTS_PATH", "inputs")

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
    # These structured markdown files form the core and extended knowledge base.
    # Each is parsed by ## H2 headers into named sections before chunking.
    {
        "key":           "kb-biosketch",
        "label":         "KB: Biosketch  ⭐ authoritative",
        "description":   "inputs/kb_biosketch.md",
        "script":        "scripts/embed_kb_doc.py",
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
        "script":        "scripts/embed_kb_doc.py",
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
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_professional_positioning.md",
                          "--source-type", "kb-positioning"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-positioning:",
    },
    {
        "key":           "kb-intellectual-foundations",
        "label":         "KB: Intellectual Foundations",
        "description":   "inputs/kb_intellectual_foundations.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_intellectual_foundations.md",
                        "--source-type", "kb-intellectual-foundations"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-intellectual-foundations:",
    },
    {
        "key":           "kb-dissertation-overview",
        "label":         "KB: Dissertation Overview",
        "description":   "inputs/kb_dissertation_overview.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_dissertation_overview.md",
                        "--source-type", "kb-dissertation-overview"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-dissertation-overview:",
    },
    {
        "key":           "kb-dissertation-relevance",
        "label":         "KB: Dissertation Relevance",
        "description":   "inputs/kb_dissertation_modern_relevance.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_dissertation_modern_relevance.md",
                        "--source-type", "kb-dissertation-relevance"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-dissertation-relevance:",
    },
    {
        "key":           "kb-dissertation-philosophy",
        "label":         "KB: Dissertation Philosophy",
        "description":   "inputs/kb_dissertation_philosophy.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_dissertation_philosophy.md",
                        "--source-type", "kb-dissertation-philosophy"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-dissertation-philosophy:",
    },
    {
        "key":           "kb-projects",
        "label":         "KB: Project Portfolio",
        "description":   "inputs/kb_projects.md",
        "script":        "scripts/embed_kb_doc.py",
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
        "script":        "scripts/embed_kb_doc.py",
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
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_publications.md",
                          "--source-type", "kb-publications"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-publications:",
    },
    {
        "key":           "kb-answers",
        "label":         "KB: Answer Bank",
        "description":   "inputs/kb_project_answer_bank.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_project_answer_bank.md",
                          "--source-type", "kb-answers"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-answers:",
    },
    {
        "key":           "kb-origins",
        "label":         "KB: Personal Origin Stories",
        "description":   "inputs/kb_personal_origin_stories.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_personal_origin_stories.md",
                          "--source-type", "kb-origins"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-origins:",
    },
    {
        "key":           "kb-easter-eggs",
        "label":         "KB: Easter Eggs / Recognition",
        "description":   "inputs/kb_easter_eggs.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/kb_easter_eggs.md",
                        "--source-type", "kb-easter-eggs"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "kb-easter-eggs:",
    },

    {
        "key":           "project-walkthroughs",
        "label":         "Project Walkthroughs",
        "description":   "Walkthrough contexts from featured_projects.py (1 chunk per project, no splitting)",
        "script":        "scripts/embed_walkthroughs.py",
        "base_args":     [],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "project-walkthrough:",
    },
    # ── Project summary one-pagers (markdown, chunked by ## headers) ────────
    {
        "key":           "project-digital-twin",
        "label":         "Project: Digital Twin",
        "description":   "inputs/project-summaries/digital-twin.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/project-summaries/digital-twin.md",
                        "--source-type", "project-digital-twin"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "project-digital-twin:",
    },
    {
        "key":           "project-local-rag",
        "label":         "Project: Privacy-first RAG Chatbot",
        "description":   "inputs/project-summaries/local-rag.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/project-summaries/local-rag.md",
                        "--source-type", "project-local-rag"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "project-local-rag:",
    },
    {
        "key":           "project-resume-explorer",
        "label":         "Project: Resume Explorer",
        "description":   "inputs/project-summaries/resume-explorer.md",
        "script":        "scripts/embed_kb_doc.py",
        "base_args":     ["--file", "inputs/project-summaries/resume-explorer.md",
                        "--source-type", "project-resume-explorer"],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "project-resume-explorer:",
    },
    # ... same pattern for concept-cartographer, fitness-dashboard, etc.
    {
        "key":           "project-summaries",
        "label":         "Project Summaries (PDFs)",
        "description":   "inputs/project-summaries/ (one-page PDFs)",
        "script":        "scripts/embed_project_summaries.py",
        "base_args":     [],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "project-summary:",
    },
    {
        "key":           "jekyll",
        "label":         "Jekyll Website",
        "description":   "https://barbhs.com (via sitemap)",
        "script":        "scripts/embed_jekyll.py",
        "base_args":     [],
        "force_arg":     "--force-reembed",
        "dry_run_arg":   "--dry-run",
        "source_prefix": "jekyll:",
    },
]

SOURCE_BY_KEY = {s["key"]: s for s in SOURCES}


# ── PATH RESOLUTION ───────────────────────────────────────────────────────
# NEW: SOURCES entries keep their canonical "inputs/..." paths for readability
# (the registry literal answers "what gets embedded", regardless of host).
# At invocation time we rewrite any --file or --summaries-folder arg to live
# under INPUTS_PATH. Non-destructive — the registry itself isn't mutated.

def _resolve_args(args):
    """Rewrite path-bearing args to live under INPUTS_PATH. Returns a new list."""
    resolved = list(args)
    for i, arg in enumerate(resolved):
        if arg in ("--file", "--summaries-folder") and i + 1 < len(resolved):
            path = resolved[i + 1]
            if path.startswith("inputs/"):
                resolved[i + 1] = os.path.join(INPUTS_PATH, path[len("inputs/"):])
    return resolved


def _source_filepath(source):
    """Resolved --file path for a source, or None if the source doesn't use one."""
    args = source["base_args"]
    if "--file" not in args:
        return None
    idx = args.index("--file")
    path = args[idx + 1]
    if path.startswith("inputs/"):
        return os.path.join(INPUTS_PATH, path[len("inputs/"):])
    return path


def _source_type(source):
    """The --source-type value for a source, or None."""
    args = source["base_args"]
    if "--source-type" not in args:
        return None
    return args[args.index("--source-type") + 1]


# ── DB PULL (idempotent per session) ──────────────────────────────────────
# NEW: Pull-before-embed handshake. Whichever machine you're on, you start
# from canonical state — not your possibly-stale local cache — so two machines
# can no longer silently overwrite each other's pushes.

_db_pulled_this_session = False

def _ensure_db_pulled():
    """Pull current DB from HF Hub before embedding. Runs at most once per session."""
    global _db_pulled_this_session
    if _db_pulled_this_session:
        return
    print(f"\n⬇️  Pulling current DB from HF Hub before embedding...")
    try:
        from db_sync import pull_db
        pull_db()
    except Exception as e:
        print(f"   ⚠️  Pull failed ({e}) — proceeding with local state")
    _db_pulled_this_session = True   # Mark done either way; don't retry on every action.


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


# ── DRIFT DETECTION ───────────────────────────────────────────────────────
# NEW: Compare each source file's current sha256 to the content_hash stored
# in its ChromaDB chunks. Surfaces five states so you can act on each:
#   ✅ in sync       — source hash matches DB hash
#   ⚠️  DRIFTED      — source changed since embed; re-embed with --force-reembed
#   ❓ unhashed     — chunks exist but pre-date content_hash; one-time backfill
#   ❌ missing      — source file expected but not found at the resolved path
#   ⏭️  not embedded — registry knows about it but no chunks in DB yet

def check_drift():
    """Print a drift report comparing source files to ChromaDB content hashes."""
    print_header()
    print(f"\n  Drift check: source files (sha256) vs ChromaDB content_hash")
    print(f"  INPUTS_PATH = {INPUTS_PATH}\n")

    if not os.path.exists(CHROMA_PATH):
        print(f"  ⚠️  DB not found at {CHROMA_PATH}/ — run `python ingest.py --all` first\n")
        return

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name=COLLECTION)
    all_metas = collection.get(include=["metadatas"])["metadatas"] or []

    # Build map: full_source -> content_hash. We take the first occurrence;
    # all chunks for one source share the same hash by construction.
    db_hashes = {}
    for meta in all_metas:
        src = meta.get("source")
        if src and src not in db_hashes:
            db_hashes[src] = meta.get("content_hash")   # may be None for legacy chunks

    print(f"  {'Source':<32} {'Status':<18} {'Notes'}")
    print(f"  {'─'*32} {'─'*18} {'─'*30}")

    for source in SOURCES:
        key = source["key"]
        filepath = _source_filepath(source)
        source_type = _source_type(source)

        # Skip sources that don't have a single --file (jekyll, walkthroughs, summaries dir)
        if filepath is None:
            continue

        if not os.path.exists(filepath):
            print(f"  {key:<32} {'❌ missing':<18} {filepath}")
            continue

        with open(filepath, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        full_source = f"{source_type}:{os.path.basename(filepath)}"

        if full_source not in db_hashes:
            print(f"  {key:<32} {'⏭️  not embedded':<18}")
        elif db_hashes[full_source] is None:
            print(f"  {key:<32} {'❓ unhashed':<18} pre-dates content_hash field")
        elif db_hashes[full_source] == file_hash:
            print(f"  {key:<32} {'✅ in sync':<18}")
        else:
            print(f"  {key:<32} {'⚠️  DRIFTED':<18} re-embed with --force-reembed")

    print()


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
        print(f"  Inputs   : {INPUTS_PATH}/")        # NEW: surface canonical inputs path

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
    print("    c       Check drift (compare source files to DB hashes)")    # NEW
    print("    r       Refresh status")
    print("    q       Quit")
    print()


# ── EXECUTION ─────────────────────────────────────────────────────────────

def run_source(source: dict, force: bool = False, dry_run: bool = False) -> int:
    """
    Invoke an embed script via subprocess.
    Returns the exit code (0 = success).
    """
    # CHANGED: paths in base_args are resolved under INPUTS_PATH at invocation time.
    cmd = [sys.executable, source["script"]] + _resolve_args(source["base_args"])

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
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(cmd, cwd=project_root)
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

        # NEW: Check drift
        elif choice == "c":
            check_drift()

        # Embed all
        elif choice == "a":
            _ensure_db_pulled()                  # NEW: pull-before-embed handshake
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
            if not dry_run:
                _ensure_db_pulled()              # NEW: pull-before-embed handshake
            run_source(source, force=force, dry_run=dry_run)

        else:
            print(f"  Invalid input — enter a number 1–{len(SOURCES)}, 'a' (all), 'c' (drift), 'r' (refresh), or 'q' (quit)")


def cli_mode(args):
    """Non-interactive execution driven by CLI flags."""
    if args.status:
        print_header()
        status = get_db_status()
        print_status_table(status)
        return

    # NEW: drift-check command (read-only, no pull/push needed)
    if args.check_drift:
        check_drift()
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

    # NEW: pull-before-embed handshake (skipped on dry-run since nothing is written)
    if not args.dry_run:
        _ensure_db_pulled()

    errors = 0
    for source in sources_to_run:
        code = run_source(source, force=args.force, dry_run=args.dry_run)
        if code != 0:
            errors += 1

    if errors:
        print(f"\n⚠️  {errors} source(s) had errors.")
        sys.exit(1)

    if not args.dry_run:
        # Wait for all embed subprocesses to fully release ChromaDB file locks
        # before attempting to tar the database for HuggingFace upload.
        # Without this delay, SQLite file handles may still be open, causing
        # database corruption in the uploaded tarball.
        print(f"\n⏳ Waiting for database file locks to release...")
        time.sleep(3)
        gc.collect()

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
  python ingest.py --check-drift                # Compare source hashes to DB
  python ingest.py --all                        # Embed all sources
  python ingest.py --all --force                # Force re-embed everything
  python ingest.py --source kb-biosketch           # Embed one source
  python ingest.py --source kb-publications --force
  python ingest.py --source project-summaries --dry-run

Source keys: kb-biosketch, kb-philosophy, kb-positioning, kb-projects,
             kb-career, kb-publications, kb-answers, kb-origins, project-summaries, jekyll,
             project-walkthroughs
        """
    )
    parser.add_argument('--status',  action='store_true',
                        help='Show DB status and exit (no embedding)')
    parser.add_argument('--check-drift', action='store_true',                # NEW
                        help='Compare source files to stored content hashes and exit')
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
    if args.status or args.check_drift or args.all or args.source or args.dry_run:
        cli_mode(args)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
