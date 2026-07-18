"""
retract_sources.py
─────────────────────────────────────────────────────────────────────
Retire superseded chunks from the barb-twin collection by EXACT source match.

Written for the consolidation workflow (see the twin-freshness repo): when a
project graduates to a single authoritative markdown summary, its old
representations — PDF one-pager chunks, the featured_projects walkthrough
chunk, duplicate site-page chunks — are removed so retrieval can't mix stale
and current facts.

Deliberately conservative:
  - DRY-RUN BY DEFAULT: prints exactly what would be deleted and exits.
    Nothing is removed without --apply.
  - EXACT source match (== on the `source` metadata field), never prefix
    match, so `project-summary:chronoscope` cannot swallow a longer name.
  - No push to HF Hub unless --push is given alongside --apply.

USAGE:
    python scripts/retract_sources.py --source "project-summary:chronoscope" \
        --source "project-walkthrough:chronoscope"            # dry-run (default)
    python scripts/retract_sources.py --source "..." --apply         # delete
    python scripts/retract_sources.py --source "..." --apply --push  # + sync HF
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import argparse
from collections import Counter

import chromadb
from dotenv import load_dotenv

load_dotenv(override=True)

CHROMA_PATH = ".chroma_db_DT"
COLLECTION  = "barb-twin"


def main():
    parser = argparse.ArgumentParser(
        description="Retire chunks by exact source metadata value (dry-run by default)")
    parser.add_argument("--source", action="append", required=True, metavar="VALUE",
                        help="exact `source` metadata value to retire (repeatable)")
    parser.add_argument("--apply", action="store_true",
                        help="actually delete (default is dry-run)")
    parser.add_argument("--push", action="store_true",
                        help="after --apply, push the DB to HF Hub (db_sync)")
    args = parser.parse_args()

    col = chromadb.PersistentClient(path=CHROMA_PATH).get_collection(COLLECTION)
    before = col.count()
    data = col.get(include=["metadatas"])

    targets = set(args.source)
    matched_ids: list[str] = []
    per_source: Counter = Counter()
    for id_, meta in zip(data["ids"], data["metadatas"]):
        src = meta.get("source", "")
        if src in targets:
            matched_ids.append(id_)
            per_source[src] += 1

    print(f"Collection {COLLECTION}: {before} chunks total")
    for src in sorted(targets):
        n = per_source.get(src, 0)
        flag = "" if n else "   ⚠️  NO MATCH — check the exact source value"
        print(f"  {n:3d} chunk(s)  {src}{flag}")
    print(f"  → {len(matched_ids)} chunk(s) selected for retirement")

    if not args.apply:
        print("\nDRY RUN — nothing deleted. Re-run with --apply to delete.")
        return

    if matched_ids:
        col.delete(ids=matched_ids)
    after = col.count()
    print(f"✅ Deleted {before - after} chunk(s); collection now {after}")

    if args.push:
        from db_sync import push_db
        push_db()


if __name__ == "__main__":
    main()
