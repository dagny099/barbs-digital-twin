---
title: KB Ingestion
tags:
  - developer
  - ingestion
  - knowledge-base
---

# KB Ingestion

The ingestion pipeline transforms source documents into embedded chunks stored in both Neo4j and ChromaDB. Start here when you're adding or updating knowledge base content.

---

## The Ingestion Manager

`scripts/ingest.py` is the recommended entry point for all ingestion operations. Run it with no arguments for an interactive menu that shows current database status before asking you to do anything:

```bash
python scripts/ingest.py
```

The menu displays a live status table — chunk counts per source:

```
  #   Source                     Description                            Status
  1   KB: Biosketch ⭐            inputs/kb_biosketch.md               ✅  42 chunks
  2   KB: Philosophy & Approach  inputs/kb_philosophy-and-appro...     ✅  31 chunks
  3   KB: Professional Pos...    inputs/kb_professional_positio...      ✅  28 chunks
  4   KB: Project Portfolio      inputs/kb_projects.md                 ✅  65 chunks
  5   KB: Career Narrative       inputs/kb_career_narrative.md         ✅  44 chunks
  6   KB: Publications & Res...  inputs/kb_publications.md             ✅  18 chunks
  7   Project Summaries (PDFs)   inputs/project-summaries/ (one...     ✅  98 chunks
  8   Jekyll Website             https://barbhs.com (via sitemap)      ✅  210 chunks
```

Select a source by number, then choose **Embed**, **Force re-embed**, or **Dry run**.

---

## Non-Interactive Flags

For scripting or CI/CD use:

```bash
python scripts/ingest.py --status                              # Show DB status and exit
python scripts/ingest.py --all                                 # Embed all sources
python scripts/ingest.py --all --force                         # Force re-embed everything
python scripts/ingest.py --source kb-biosketch                 # Embed one source
python scripts/ingest.py --source kb-biosketch --force         # Force re-embed one source
python scripts/ingest.py --source project-summaries --dry-run  # Preview without embedding
```

### Available Source Keys

| Key | File/Location |
|---|---|
| `kb-biosketch` | `inputs/kb_biosketch.md` |
| `kb-philosophy` | `inputs/kb_philosophy-and-approach.md` |
| `kb-positioning` | `inputs/kb_professional_positioning.md` |
| `kb-projects` | `inputs/kb_projects.md` |
| `kb-career` | `inputs/kb_career_narrative.md` |
| `kb-publications` | `inputs/kb_publications.md` |
| `project-summaries` | `inputs/project-summaries/` (PDFs) |
| `jekyll` | `https://barbhs.com` (via sitemap) |
| `project-walkthroughs` | `featured_projects.py` |

---

## Checking Database Contents

```bash
# Quick chunk counts per source
python scripts/ingest.py --status

# Detailed stats and sample chunks
python scripts/verify_collection.py

# Per-source breakdown
python scripts/verify_collection.py --show-sources

# All unique section names
python scripts/verify_collection.py --show-sections
```

---

## Auditing Chunk Quality

`chunk_inspector.py` audits ChromaDB chunk quality and simulates retrieval before the LLM ever sees it:

```bash
python chunk_inspector.py                        # Full audit report
python chunk_inspector.py --source kb-projects   # One source only
python chunk_inspector.py --query "Resume Explorer architecture"
python chunk_inspector.py --tiny                 # Show only bad chunks (<150 chars)
python chunk_inspector.py --all-chunks           # Dump every chunk
python chunk_inspector.py --query "..." --n 12   # Retrieve N chunks
```

**What it checks:**
1. Chunk size distribution — find orphaned tiny chunks
2. Per-source breakdown — chunk count and average size per source
3. Retrieval simulation — embed a query, show retrieved chunks as the LLM would see them
4. Gap detection — sections with suspiciously few chunks

---

## Wiping the Database

!!! warning "Destructive operation"
    This deletes all embeddings. You'll need to re-run `python scripts/ingest.py --all` to rebuild.

```bash
python scripts/clear_collection.py   # Interactive confirmation required
```

---

## Adding New Content

To add a new KB document:

1. Create `inputs/kb_your-topic.md` using `##` headers for section boundaries
2. Add a new entry to the ingestion manager in `scripts/ingest.py`
3. Run `python scripts/ingest.py --source your-key` to embed it
4. Verify with `python chunk_inspector.py --source your-key`
5. Test retrieval with `python chunk_inspector.py --query "something in your new doc"`

!!! tip "Write for retrieval, not for reading"
    Curated content with question-shaped vocabulary ("projects I'm proud of," "applied ML") consistently outperforms narrative content with chronological vocabulary — even when the narrative is more topically specific. See [Entry 002](../lessons-learned/entry-002.md) for a concrete example.

---

## Shared Utilities (`utils.py`)

All ingestion scripts use `utils.py` to ensure consistent chunking behavior:

- `chunk_prose()` — paragraph-aware chunking with overlap
- `parse_markdown_sections()` — parse markdown files by `##` headers
- `build_metadata()` — construct standardized metadata dicts
- `delete_chunks_by_source()` — wipe all chunks for a source prefix (used by `--force`)
- `section_already_embedded()` — per-section idempotency check
