# CLAUDE.md - Project Context for AI Assistants

This file provides context about the Digital Twin project to help AI coding assistants (like Claude Code) understand the codebase and assist effectively.

## Project Overview

**Project Name**: Digital Twin - Barbara Hidalgo-Sotelo
**Purpose**: A RAG-powered conversational AI that embodies Barbara's professional knowledge and personality
**Status**: Active development + deployed on Hugging Face Spaces
**Primary Language**: Python 3.11
**Key Dependencies**: gradio, openai, chromadb, requests

## Architecture Summary

### Core Components

1. **app.py**: Main application
   - Gradio ChatInterface for user interaction
   - RAG pipeline: query → embed → search → context injection → LLM response
   - Tool calling system for extended functionality (notifications, dice roll)
   - System prompt defines Barbara's personality and response guidelines

2. **embed_readmes.py**: Data ingestion script
   - Loads all markdown files from `READMEs/` folder (GitHub project READMEs)
   - Chunks text → embeds → stores in ChromaDB
   - Idempotent: skips already-embedded sources
   - Can be re-run to add new READMEs

3. **embed_mkdocs.py**: Documentation ingestion script
   - Fetches MkDocs sites via their `search_index.json` endpoints
   - Processes clean text from MkDocs search index (no HTML parsing needed)
   - Supports batch embedding (500 chunks at a time)
   - Configured for 8 docs.barbhs.com sites

### Data Flow

```
[Data Sources] → [Chunking] → [OpenAI Embeddings] → [ChromaDB]
                                                           ↓
[User Query] → [Embed Query] → [Semantic Search] → [Top 3 Chunks]
                                                           ↓
                            [System Prompt + Context + Query]
                                                           ↓
                                    [GPT-4.1-mini w/ Tools]
                                                           ↓
                                    [Tool Execution Loop]
                                                           ↓
                                    [Final Response]
```

## Key Files & Directories

| Path | Purpose | Git Tracked? |
|------|---------|--------------|
| `utils.py` | **NEW** Shared text processing utilities | ✅ Yes |
| `app.py` | Main Gradio app + RAG pipeline (no longer embeds data) | ✅ Yes |
| `embed_biosketch.py` | **NEW** Biosketch ingestion with markdown parsing | ✅ Yes |
| `embed_resume.py` | **NEW** Resume ingestion with delimiter parsing | ✅ Yes |
| `embed_readmes.py` | README ingestion script (updated) | ✅ Yes |
| `embed_mkdocs.py` | MkDocs ingestion script (updated) | ✅ Yes |
| `clear_collection.py` | **NEW** Helper to clear ChromaDB collection | ✅ Yes |
| `verify_collection.py` | **NEW** Helper to verify collection stats | ✅ Yes |
| `requirements.txt` | Python dependencies | ✅ Yes |
| `barbara-hidalgo-sotelo-biosketch.md` | Authoritative biographical source | ✅ Yes |
| `Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt` | Resume source | ✅ Yes |
| `READMEs/` | GitHub project README files | ✅ Yes |
| `RESUME-EXPLORER/` | Additional project docs | ✅ Yes |
| `.chroma_db_DT/` | ChromaDB vector database | ❌ No (gitignored) |
| `.chroma_db_DT.backup_2026-03-02/` | Database backup | ❌ No (gitignored) |
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
    'source': 'source-type:identifier',  # e.g., 'resume:2026.txt'
    'section': 'Section Name' or None,   # e.g., 'Education'
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

The system follows a **source priority hierarchy**:

1. **Biosketch (AUTHORITATIVE)**: `barbara-hidalgo-sotelo-biosketch.md`
   - Identity, background, education, values, personality, career
   - Wins in any conflict with other sources

2. **Project READMEs**: `READMEs/*.md` (39 files)
   - Technical project descriptions, implementations, usage
   - Tagged as `github-readme:{repo-name}` in metadata

3. **MkDocs Sites**: Fetched from docs.barbhs.com (8 sites)
   - Detailed documentation, user guides, technical deep-dives
   - Tagged as `mkdocs:{site-name}:{location}` in metadata

## System Prompt Strategy

The system prompt in `app.py` (lines 245-262) defines:
- **Identity**: "You are a digital twin of Barbara..."
- **Personality traits**: Practical, collaborative, loves explaining concepts
- **Current status**: Looking for employment
- **Drives**: Learning, health, helping others
- **Mantra**: "I can, I will, and I shall!"
- **Source priority rules**: Biosketch > READMEs for identity conflicts
- **Tool usage hints**: Notification with mantra for encouragement

**Critical context injection**: System message is enhanced per query with retrieved chunks (line 284).

## Tools / Function Calling

Two tools currently implemented:

### `send_notification`
- **Purpose**: Send push notification via Pushover
- **Parameters**: `message` (string)
- **Usage hint**: When user wants encouragement, send mantra + message
- **Implementation**: Lines 173-176

### `dice_roll`
- **Purpose**: Simulate rolling a six-sided die
- **Parameters**: None
- **Returns**: Random integer 1-6
- **Implementation**: Lines 179-180

### Tool Handler
- **Function**: `handle_tool_call()` (lines 220-241)
- **Flow**: LLM requests tool → handler executes → result appended to messages → LLM continues
- **Loop**: Lines 295-305 (continues until no more tool calls)

## Shared Utilities Module

✅ **Code duplication eliminated!** All text processing functions are now centralized in `utils.py`:
- `parse_paragraphs()` - Split text on blank lines
- `chunk_prose()` - Paragraph-aware chunking with overlap
- `parse_sections_by_delimiter()` - Parse TXT files by delimiter (e.g., resume)
- `parse_markdown_sections()` - Parse markdown by headers (e.g., biosketch)
- `build_metadata()` - Construct standardized metadata dicts

All ingestion scripts import from `utils.py` to ensure consistency.

## Common Development Tasks

### Adding a New Data Source

**For biosketch updates:**
```bash
python embed_biosketch.py --force-reembed
```

**For resume updates:**
```bash
python embed_resume.py --force-reembed
```

**For new README files:**
1. Place file in `READMEs/` folder
2. Run: `python embed_readmes.py` (skips already-embedded files)

**For MkDocs site updates:**
1. Edit `MKDOCS_SITES` list in `embed_mkdocs.py` if adding new site
2. Run: `python embed_mkdocs.py` (skips already-embedded pages)

**Verify after embedding:**
```bash
python verify_collection.py --show-sources
```

Note: ChromaDB is persistent. No need to restart `app.py` - changes are immediately available.

### Adding a New Tool

1. Define the Python function (e.g., in app.py before the tools list)
2. Add function descriptor to `tools` list (lines 212-215 pattern)
3. Add handler case in `handle_tool_call()` (lines 227-232 pattern)
4. Update system prompt if tool needs behavioral guidance

### Modifying Chunking Strategy

1. Update `chunk_prose()` in **all three files**
2. Delete `.chroma_db_DT/` directory
3. Re-run all embedding scripts:
   ```bash
   python app.py  # Creates DB + embeds biosketch
   python embed_readmes.py
   python embed_mkdocs.py
   ```

### Debugging RAG Retrieval

- **See retrieved chunks**: Check terminal output when running `app.py`
- Lines 279-281 print each retrieved chunk with source + chunk_index
- **Test retrieval directly**: Use ChromaDB `.query()` method with test embeddings

### Changing LLM Model

- Update model name on lines 290 and 302 in `app.py`
- Ensure tool calling is supported by the new model
- Test that personality/voice is maintained

## Known Issues & TODOs

### Gradio Constraints (DO NOT VIOLATE)

- **`gr.Chatbot` must NOT include `type="messages"` as a kwarg** — causes a runtime error. Omit the parameter entirely.
- **`gr.Chatbot` must NOT include `show_copy_button=True`** — also causes a runtime error. Omit entirely.
- **History format is messages-style dicts despite omitting `type="messages"`**: This Gradio version uses `{"role": ..., "content": ...}` format internally regardless. History must always be stored and returned as `[{"role": "user", "content": ...}, {"role": "assistant", "content": ...}, ...]`. Do NOT use tuple format `[[user, bot], ...]`.
- **`respond_ai` already expects this dict format**, so no conversion is needed between `chat_fn` and `respond_ai`.

### From Code Comments

1. **Line 310 (app.py)**: Add print statements to see what tools are being called (debugging)
2. **Line 209 (embed_mkdocs.py)**: Fix embed_readmes.py with batching logic (currently can fail on large batches)

### Deployment Considerations

- **ChromaDB on HF Spaces**: Database is ephemeral on container restart; consider:
  - Including pre-built `.chroma_db_DT/` in deployment
  - Running embedding scripts in startup script
- **API costs**: Monitor OpenAI usage; consider caching or rate limiting for public deployment
- **Environment variables**: Set secrets in HF Spaces settings, not in code

## Testing Checklist

Before committing changes:

- [ ] Run `app.py` locally and test 3-5 queries
- [ ] Verify retrieved context is relevant (check terminal output)
- [ ] Test tool calling (ask for notification or dice roll)
- [ ] Check that personality/voice is maintained
- [ ] Ensure no API keys in code or committed files
- [ ] Verify chunking parameters are consistent across all files
- [ ] Test with queries about biosketch, projects, and technical topics

## Code Style & Patterns

- **Imports**: Standard library, then third-party, then local
- **Function docstrings**: Present for complex functions (e.g., `chunk_prose()`)
- **Comments**: Section headers with `#------ SECTION ------` pattern
- **Variable naming**: Snake_case for Python convention
- **Print statements**: Used for debugging/progress tracking (lines 135, 140, 279-281)

## References for Development

- **Gradio ChatInterface docs**: https://www.gradio.app/docs/chatinterface
- **ChromaDB docs**: https://docs.trychroma.com/
- **OpenAI tool calling guide**: https://platform.openai.com/docs/guides/function-calling
- **Pushover API**: https://pushover.net/api

## Contact for Questions

If you're an AI assistant and encounter ambiguity:
1. Check the system prompt in `app.py` for behavioral guidance
2. Refer to the biosketch (`barbara-hidalgo-sotelo-biosketch.md`) for authoritative personal info
3. Ask the user for clarification on implementation choices
4. Prioritize maintaining the existing architecture unless explicitly asked to refactor

---

**Last Updated**: 2026-03-02
**Maintained By**: Barbara Hidalgo-Sotelo
**For**: Claude Code and other AI coding assistants
