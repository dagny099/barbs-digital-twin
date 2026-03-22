# AGENTS.md - Project Context for AI Assistants

This file provides context about the Digital Twin project to help AI coding assistants (like Codex) understand the codebase and assist effectively.

## Project Overview

**Project Name**: Digital Twin - Barbara Hidalgo-Sotelo
**Purpose**: A RAG-powered conversational AI that embodies Barbara's professional knowledge and personality
**Status**: Active development + deployed on Hugging Face Spaces (V2)
**Primary Language**: Python 3.11
**Key Dependencies**: gradio, openai, chromadb, requests

## Architecture Summary

### Core Components

1. **app.py**: Main application
   - Gradio ChatInterface for user interaction
   - RAG pipeline: query → embed → search → context injection → LLM response
   - Tool calling system for extended functionality (notifications, dice roll)
   - System prompt loaded from `SYSTEM_PROMPT.md` at startup

2. **embed_kb_doc.py**: Generic KB document ingestion script
   - Handles all six `inputs/kb_*.md` knowledge-base documents
   - Parses markdown by `##` H2 headers → named sections → chunks
   - Args: `--file PATH`, `--source-type KEY`, `--force-reembed`, `--dry-run`

3. **embed_project_summaries.py**: One-page PDF ingestion
   - Processes `inputs/project-summaries/*.pdf`
   - Template-aware section detection + synthetic overview chunks

4. **embed_jekyll.py**: Live website ingestion
   - Fetches `https://barbhs.com` via sitemap.xml
   - Uses `trafilatura` for clean content extraction

5. **ingest.py**: Master orchestration script
   - Interactive menu with live DB status (chunk counts per source)
   - Non-interactive CLI flags for automation
   - Manages all 8 sources through a single `SOURCES` registry

### Data Flow

```
[inputs/kb_*.md files]   → [embed_kb_doc.py]  ──┐
[inputs/project-summaries/*.pdf] → [embed_project_summaries.py] ──┤
[https://barbhs.com]     → [embed_jekyll.py]  ──┤  OpenAI Embeddings → ChromaDB
                                                  │
[User Query] → [Embed Query] → [Semantic Search] → [Top 3 Chunks]
                                                  │
               [SYSTEM_PROMPT.md + Context + Query]
                                                  │
                           [GPT-4.1-mini w/ Tools]
                                                  │
                           [Tool Execution Loop]
                                                  │
                           [Final Response as Barbara]
```

## Key Files & Directories

| Path | Purpose | Git Tracked? |
|------|---------|--------------|
| `app.py` | Main Gradio app + RAG pipeline | ✅ Yes |
| `ingest.py` | Master ingestion manager (start here) | ✅ Yes |
| `embed_kb_doc.py` | Generic KB document ingestion (all `kb_*.md` files) | ✅ Yes |
| `embed_project_summaries.py` | One-page PDF ingestion | ✅ Yes |
| `embed_jekyll.py` | Jekyll website ingestion | ✅ Yes |
| `utils.py` | Shared text processing utilities | ✅ Yes |
| `clear_collection.py` | Helper to clear ChromaDB collection | ✅ Yes |
| `verify_collection.py` | Helper to verify collection stats | ✅ Yes |
| `SYSTEM_PROMPT.md` | LLM system prompt (loaded by app.py at startup) | ✅ Yes |
| `requirements.txt` | Python dependencies | ✅ Yes |
| `inputs/kb_biosketch.md` | Biographical sketch — authoritative ⭐ | ✅ Yes |
| `inputs/kb_philosophy-and-approach.md` | Working philosophy and meaning-making | ✅ Yes |
| `inputs/kb_professional_positioning.md` | Positioning, differentiators, value prop | ✅ Yes |
| `inputs/kb_projects.md` | Project portfolio registry | ✅ Yes |
| `inputs/kb_career_narrative.md` | Career story and trajectory | ✅ Yes |
| `inputs/kb_publications.md` | Research papers and academic work | ✅ Yes |
| `inputs/project-summaries/` | One-page PDF summaries (20 projects) | ✅ Yes |
| `archive/` | Retired embed scripts (kept for reference, not run) | ✅ Yes |
| `inputs/OLD/` | Retired source documents (old biosketch, resume, READMEs) | ✅ Yes |
| `.chroma_db_DT/` | ChromaDB vector database | ❌ No (gitignored) |
| `.venv/` | Python virtual environment | ❌ No (gitignored) |
| `.env` | Environment variables (API keys) | ❌ No (gitignored, sensitive) |

## Important Configuration Parameters

### Chunking (consistent across all scripts via utils.py)
- **CHUNK_SIZE**: 500 characters
- **OVERLAP**: 50 characters
- **Atomic unit**: Paragraphs (split on `\n\n`)
- **Section parsing**: `parse_markdown_sections()` for all `kb_*.md` files

### Metadata Schema (standardized)
```python
{
    'source': 'source-type:identifier',  # e.g., 'kb-biosketch:kb_biosketch.md'
    'section': 'Section Name' or None,   # e.g., 'Professional Identity'
    'chunk_index': 0                     # resets per section
}
```

### Embeddings
- **Model**: `text-embedding-3-small`
- **Dimensions**: 1536
- **Provider**: OpenAI API

### Vector Store
- **Database**: ChromaDB (persistent)
- **Path**: `.chroma_db_DT/`
- **Collection**: `barb-twin`
- **Retrieval**: Top 3 chunks per query

### LLM
- **Model**: `gpt-4.1-mini`
- **Provider**: OpenAI API
- **Features**: Chat completion + tool calling

## Environment Variables

Required:
- `OPENAI_API_KEY`: OpenAI API key for embeddings + completions

Optional:
- `PUSHOVER_USER`: Pushover user key for notifications
- `PUSHOVER_TOKEN`: Pushover app token for notifications

## Data Sources & Priority

The system follows a **source priority hierarchy** (also encoded in `SYSTEM_PROMPT.md`):

1. **KB Biosketch (AUTHORITATIVE)** — `inputs/kb_biosketch.md` / key: `kb-biosketch`
   - Identity, background, education, values, personality
   - Wins in any conflict with other sources

2. **KB Philosophy & Approach** — `inputs/kb_philosophy-and-approach.md` / key: `kb-philosophy`

3. **KB Professional Positioning** — `inputs/kb_professional_positioning.md` / key: `kb-positioning`

4. **KB Project Portfolio** — `inputs/kb_projects.md` / key: `kb-projects`

5. **KB Career Narrative** — `inputs/kb_career_narrative.md` / key: `kb-career`

6. **KB Publications** — `inputs/kb_publications.md` / key: `kb-publications`

7. **Project Summaries (PDFs)** — `inputs/project-summaries/` / key: `project-summaries`

8. **Jekyll Website** — `https://barbhs.com` / key: `jekyll`

**Retired sources** (moved to `inputs/OLD/`, no longer ingested):
- Old biosketch, resume, GitHub READMEs

## System Prompt Strategy

The system prompt is stored in `SYSTEM_PROMPT.md` and loaded by `app.py` at startup. It defines:
- **Identity**: "You are a digital twin of Barbara..."
- **Personality traits**: Warm, direct, draws on cognitive science + engineering analogies
- **Narrative priorities**: Problems before skills, stories before specs
- **Source priority rules**: Biosketch > philosophy > positioning for identity conflicts
- **Tool usage hints**: Notifications for knowledge gaps and visitor contact

**Critical context injection**: Retrieved KB chunks are injected into the system message per query.

## Tools / Function Calling

Two tools currently implemented:

### `send_notification`
- **Purpose**: Send push notification via Pushover when a visitor wants contact or a question is out of scope
- **Parameters**: `message` (string)
- **Usage**: Automatic — no need to ask the user first

### `dice_roll`
- **Purpose**: Simulate rolling a six-sided die
- **Returns**: Random integer 1-6

### Tool Handler
- **Flow**: LLM requests tool → `handle_tool_call()` executes → result appended to messages → LLM continues

## Shared Utilities Module

All text processing functions are centralized in `utils.py`:
- `parse_paragraphs()` — Split text on blank lines
- `chunk_prose()` — Paragraph-aware chunking with overlap
- `parse_markdown_sections()` — Parse markdown by `##` headers (used by all KB docs)
- `parse_sections_by_delimiter()` — Parse TXT files by delimiter (historical use)
- `build_metadata()` — Construct standardized metadata dicts
- `delete_chunks_by_source()` — Wipe chunks for a source prefix (`--force-reembed`)
- `section_already_embedded()` — Per-section idempotency check

All ingestion scripts import from `utils.py` to ensure consistency.

## Common Development Tasks

### Ingesting or re-ingesting the knowledge base

**Interactive (recommended):**
```bash
python ingest.py
```

**Non-interactive:**
```bash
python ingest.py --all                           # Embed all sources
python ingest.py --all --force                   # Force re-embed everything
python ingest.py --source kb-biosketch           # Embed one source
python ingest.py --source kb-biosketch --force   # Force re-embed one source
python ingest.py --source kb-projects --dry-run  # Preview without embedding
python ingest.py --status                        # Show DB status and exit
```

**Source keys**: `kb-biosketch`, `kb-philosophy`, `kb-positioning`, `kb-projects`, `kb-career`, `kb-publications`, `project-summaries`, `jekyll`

**Verify after embedding:**
```bash
python verify_collection.py --show-sources
```

### Adding a New Data Source

1. Create a markdown file in `inputs/` following the `kb_*.md` naming convention, using `##` headers for sections
2. Add a new entry to the `SOURCES` list in `ingest.py` — follow the existing `kb-*` pattern
3. Update source priority rules in `SYSTEM_PROMPT.md` if needed
4. Run: `python ingest.py --source kb-mynewdoc`
5. Update `CLAUDE.md`, `README.md`, and this file

### Adding a New Tool

1. Define the Python function in `app.py` before the `tools` list
2. Add function descriptor to the `tools` list
3. Add handler case in `handle_tool_call()`
4. Update `SYSTEM_PROMPT.md` with behavioral guidance

### Modifying Chunking Strategy

1. Update `chunk_prose()` in `utils.py` (one place — all scripts inherit it)
2. Delete `.chroma_db_DT/` directory
3. Re-run all sources: `python ingest.py --all`

### Debugging RAG Retrieval

- Terminal output when running `app.py` prints each retrieved chunk with source + section
- Run `python ingest.py --source kb-biosketch --dry-run` to inspect section parsing

### Changing LLM Model

- Update model name in `app.py` (both main completion and tool loop calls)
- Ensure tool calling is supported by the new model

## Known Issues & TODOs

### Gradio Constraints (DO NOT VIOLATE)

- **`gr.Chatbot` must NOT include `type="messages"` as a kwarg** — causes runtime error
- **`gr.Chatbot` must NOT include `show_copy_button=True`** — also causes runtime error
- **History format**: Always use `[{"role": ..., "content": ...}]` dicts, never tuples

### Deployment Considerations

- **ChromaDB on HF Spaces**: Ephemeral on container restart — include pre-built `.chroma_db_DT/` or run `ingest.py --all` in startup
- **API costs**: Monitor OpenAI usage for the expanded V2 KB
- **Environment variables**: Set secrets in HF Spaces settings, not in code

## Testing Checklist

Before committing changes:

- [ ] Run `app.py` locally and test 5-10 queries across different KB areas
- [ ] Verify retrieved context is relevant (check terminal output)
- [ ] Test tool calling (ask for notification or dice roll)
- [ ] Check that personality/voice is maintained
- [ ] Ensure no API keys in code or committed files
- [ ] Run `python ingest.py --status` to confirm all 8 sources have chunks

## Code Style & Patterns

- **Imports**: Standard library, then third-party, then local
- **Function docstrings**: Present for all public functions
- **Comments**: Section headers with `# ── SECTION ──` pattern
- **Variable naming**: Snake_case throughout

## References for Development

- **Gradio ChatInterface docs**: https://www.gradio.app/docs/chatinterface
- **ChromaDB docs**: https://docs.trychroma.com/
- **OpenAI tool calling guide**: https://platform.openai.com/docs/guides/function-calling
- **Pushover API**: https://pushover.net/api

## Contact for Questions

If you're an AI assistant and encounter ambiguity:
1. Check `SYSTEM_PROMPT.md` for behavioral guidance and source priority rules
2. Check the KB biosketch (`inputs/kb_biosketch.md`) for authoritative personal info
3. Ask the user for clarification on implementation choices
4. Prioritize maintaining the existing architecture unless explicitly asked to refactor

---

**Last Updated**: 2026-03-21
**Maintained By**: Barbara Hidalgo-Sotelo
**For**: Codex and other AI coding assistants
