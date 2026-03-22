# CLAUDE.md - Project Context for AI Assistants

This file provides context about the Digital Twin project to help AI coding assistants (like Claude Code) understand the codebase and assist effectively.

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
   - Handles **all six** `inputs/kb_*.md` files with a single parameterised script
   - Parses markdown by `##` H2 headers → named sections → `chunk_prose()`
   - Args: `--file PATH`, `--source-type KEY`, `--force-reembed`, `--dry-run`
   - Replaces the old `embed_biosketch.py` and `embed_publications.py` (now in `archive/`)

3. **embed_project_summaries.py**: PDF ingestion
   - Processes one-page project summary PDFs from `inputs/project-summaries/`
   - Template-aware section detection + synthetic overview chunks

4. **embed_jekyll.py**: Live website ingestion
   - Fetches `https://barbhs.com` via sitemap.xml
   - Uses `trafilatura` for clean main-content extraction

5. **ingest.py**: Master orchestration script
   - Interactive menu with live DB status table (chunk counts per source)
   - Non-interactive CLI flags for scripting/CI
   - Manages all 8 data sources through a single `SOURCES` registry

### Data Flow

```
[inputs/kb_*.md]         → [embed_kb_doc.py]            ──┐
[inputs/project-summaries/*.pdf] → [embed_project_summaries.py] ──┤
[https://barbhs.com]     → [embed_jekyll.py]            ──┤── OpenAI → ChromaDB
                                                            │
[User Query] → [Embed Query] → [Semantic Search (ChromaDB, top 3 chunks)]
                                                            │
                [SYSTEM_PROMPT.md + Retrieved Context + Query]
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
| `embed_jekyll.py` | Jekyll website ingestion via sitemap | ✅ Yes |
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
| `archive/` | Retired embed scripts (embed_biosketch, embed_resume, embed_publications) | ✅ Yes |
| `inputs/OLD/` | Retired source documents (old biosketch, resume, GitHub READMEs) | ✅ Yes |
| `.chroma_db_DT/` | ChromaDB vector database | ❌ No (gitignored) |
| `.venv/` | Python virtual environment | ❌ No (gitignored) |
| `.env` | Environment variables (API keys) | ❌ No (gitignored, sensitive) |

## Important Configuration Parameters

### Chunking (consistent across all scripts via utils.py)
- **CHUNK_SIZE**: 500 characters
- **OVERLAP**: 50 characters
- **Atomic unit**: Paragraphs (split on `\n\n`)
- **Functions**: `chunk_prose()`, `parse_paragraphs()` in `utils.py`
- **Section parsing**: `parse_sections_by_delimiter()`, `parse_markdown_sections()` in `utils.py`

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
   - How Barbara thinks about data, meaning-making, and good work

3. **KB Professional Positioning** — `inputs/kb_professional_positioning.md` / key: `kb-positioning`
   - Differentiators, the cognitive science angle, the four problems she solves

4. **KB Project Portfolio** — `inputs/kb_projects.md` / key: `kb-projects`
   - All major projects with tech stack, deployment status, and cross-project connections

5. **KB Career Narrative** — `inputs/kb_career_narrative.md` / key: `kb-career`
   - Career arc told as a story — five chapters from MIT through independent GenAI work

6. **KB Publications** — `inputs/kb_publications.md` / key: `kb-publications`
   - Academic papers, conference posters, dissertation with PDF links

7. **Project Summaries (PDFs)** — `inputs/project-summaries/` / key: `project-summaries`
   - Curated one-page PDFs for each major project

8. **Jekyll Website** — `https://barbhs.com` / key: `jekyll`
   - Fetched live via sitemap; `trafilatura` extracts clean text

**Retired sources** (no longer ingested — moved to `inputs/OLD/`):
- Old biosketch (`barbara-hidalgo-sotelo-biosketch.md`)
- Resume (`Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt`)
- GitHub READMEs

## System Prompt Strategy

The system prompt is stored in `SYSTEM_PROMPT.md` and loaded by `app.py` at startup. It defines:
- **Identity**: "You are a digital twin of Barbara..."
- **Personality**: Warm, direct, explains things, draws on cognitive science + engineering
- **Narrative priorities**: Problems before skills, stories before specs, philosophy grounded in examples
- **Voice/format rules**: 2-3 paragraph responses, no bullet lists for narrative questions
- **Source priority rules**: Biosketch > philosophy > positioning for identity conflicts
- **Tool usage**: Notifications for knowledge gaps and visitor contact; dice roll for games

**Critical context injection**: Retrieved KB chunks are injected into the system message per query.

## Tools / Function Calling

Two tools currently implemented:

### `send_notification`
- **Purpose**: Send push notification via Pushover when a visitor wants contact or a question is out of scope
- **Parameters**: `message` (string)
- **Usage**: Automatic — no need to ask the user first

### `dice_roll`
- **Purpose**: Simulate rolling a six-sided die
- **Parameters**: None
- **Returns**: Random integer 1-6

### Tool Handler
- **Function**: `handle_tool_call()` in `app.py`
- **Flow**: LLM requests tool → handler executes → result appended to messages → LLM continues

## Shared Utilities Module

All text processing functions are centralized in `utils.py`:
- `parse_paragraphs()` — Split text on blank lines
- `chunk_prose()` — Paragraph-aware chunking with overlap
- `parse_sections_by_delimiter()` — Parse TXT files by delimiter (e.g., resume format — kept for historical reference)
- `parse_markdown_sections()` — Parse markdown by `##` headers (used by all KB docs)
- `build_metadata()` — Construct standardized metadata dicts
- `delete_chunks_by_source()` — Wipe all chunks for a source prefix (used by `--force-reembed`)
- `section_already_embedded()` — Per-section idempotency check (skip if already stored)

All ingestion scripts import from `utils.py` to ensure consistency.

## Common Development Tasks

### Ingesting or re-ingesting the knowledge base

**Interactive (recommended):**
```bash
python ingest.py
```

**Non-interactive:**
```bash
python ingest.py --all                           # Embed all sources (skip existing)
python ingest.py --all --force                   # Force re-embed everything
python ingest.py --source kb-biosketch           # Embed one source
python ingest.py --source kb-biosketch --force   # Force re-embed one source
python ingest.py --source kb-projects --dry-run  # Preview without embedding
```

**Source keys**: `kb-biosketch`, `kb-philosophy`, `kb-positioning`, `kb-projects`, `kb-career`, `kb-publications`, `project-summaries`, `jekyll`

**Verify after embedding:**
```bash
python ingest.py --status
python verify_collection.py --show-sources
```

### Adding a new KB document

1. Create a markdown file in `inputs/` following the `kb_*.md` naming convention
2. Use `##` H2 headers for sections (consistent with all other KB docs)
3. Add a new entry to the `SOURCES` list in `ingest.py` — follow the existing `kb-*` pattern
4. Update source priority rules in `SYSTEM_PROMPT.md` if needed
5. Run: `python ingest.py --source kb-mynewdoc`
6. Update `CLAUDE.md`, `README.md`, and `AGENTS.md`

### Adding a New Tool

1. Define the Python function in `app.py` before the `tools` list
2. Add function descriptor to the `tools` list
3. Add handler case in `handle_tool_call()`
4. Update `SYSTEM_PROMPT.md` with behavioral guidance for the tool

### Modifying Chunking Strategy

1. Update `chunk_prose()` in `utils.py` (one place — all scripts inherit it)
2. Delete `.chroma_db_DT/` to clear the DB
3. Re-run all sources: `python ingest.py --all`

### Debugging RAG Retrieval

- Terminal output when running `app.py` prints each retrieved chunk with source and section
- Run `python ingest.py --source kb-biosketch --dry-run` to inspect section parsing

### Changing the LLM Model

- Update model name in `app.py` (used in both the main completion call and the tool loop)
- Ensure tool calling is supported by the new model
- Test that personality/voice is maintained

## Known Issues & TODOs

### Gradio Constraints (DO NOT VIOLATE)

- **`gr.Chatbot` must NOT include `type="messages"` as a kwarg** — causes a runtime error. Omit entirely.
- **`gr.Chatbot` must NOT include `show_copy_button=True`** — also causes a runtime error. Omit entirely.
- **History format**: Always use messages-style dicts `[{"role": ..., "content": ...}]`, never tuples.

### Deployment Considerations

- **ChromaDB on HF Spaces**: Database is ephemeral on container restart; include pre-built `.chroma_db_DT/` in deployment or run `ingest.py --all` in a startup script
- **API costs**: The V2 KB is larger than V1; monitor OpenAI usage
- **Environment variables**: Set secrets in HF Spaces settings, not in code

## Testing Checklist

Before committing changes:

- [ ] Run `app.py` locally and test 5-10 queries across different KB areas
- [ ] Verify retrieved context is relevant (check terminal output)
- [ ] Test tool calling (ask for notification or dice roll)
- [ ] Check that personality/voice is maintained
- [ ] Ensure no API keys in code or committed files
- [ ] Verify chunking parameters are consistent (`CHUNK_SIZE=500`, `OVERLAP=50`)
- [ ] Test with queries about: identity/biosketch, philosophy/approach, projects, career arc, publications
- [ ] Run `python ingest.py --status` to confirm all 8 sources have chunks

## Code Style & Patterns

- **Imports**: Standard library, then third-party, then local
- **Function docstrings**: Present for all public functions
- **Comments**: Section headers with `# ── SECTION ──` pattern
- **Variable naming**: Snake_case throughout
- **Print statements**: Used for progress tracking in all embed scripts

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
**For**: Claude Code and other AI coding assistants
