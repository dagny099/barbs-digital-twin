# Usage Guide

Developer reference for running, customizing, and maintaining the Digital Twin.

---

## Running the App

### Public app (user-facing)

```bash
python app.py        # http://localhost:7860
```

### Admin/debug interface (developer-only)

```bash
python app_admin.py  # http://localhost:7861
```

The admin app requires `litellm` (`pip install litellm`) and provides a chunk inspector,
multi-provider model switching, semantic probe, and session cost tracking. See
`docs/CLAUDE.md` for a full feature list. It is **not** deployed to Hugging Face Spaces.

---

## Environment Variables

Copy `.env.example` to `.env` and set values before running either app.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | Used for embeddings and OpenAI completions |
| `LLM_MODEL` | No | `gpt-4.1` | Model for completions (use LiteLLM prefix in admin app: `openai/gpt-4.1`) |
| `LLM_TEMPERATURE` | No | `0.7` | Temperature for all LLM calls; applies to app, admin app, and eval runner |
| `N_CHUNKS_RETRIEVE` | No | `10` | Number of chunks retrieved per query |
| `PUSHOVER_USER` | No | — | Enables visitor notifications to Barbara's phone |
| `PUSHOVER_TOKEN` | No | — | Required if `PUSHOVER_USER` is set |
| `PORT` | No | `7860` | Server port for `app.py` |
| `ADMIN_PORT` | No | `7861` | Server port for `app_admin.py` |
| `ANTHROPIC_API_KEY` | No | — | Unlocks Anthropic models in admin app |
| `GEMINI_API_KEY` | No | — | Unlocks Google models in admin app |

---

## Managing the Knowledge Base

The `ingest.py` script orchestrates all data sources. Always start here:

```bash
python ingest.py              # Interactive menu with live DB status
python ingest.py --status     # Show chunk counts per source and exit
```

### Non-interactive commands

```bash
python ingest.py --all                            # Embed all sources (skip existing)
python ingest.py --all --force                    # Force re-embed everything
python ingest.py --source kb-biosketch            # Embed one source
python ingest.py --source kb-biosketch --force    # Force re-embed one source
python ingest.py --source kb-projects --dry-run   # Preview without embedding
```

**Source keys**: `kb-biosketch`, `kb-philosophy`, `kb-positioning`, `kb-projects`,
`kb-career`, `kb-publications`, `project-summaries`, `jekyll`, `project-walkthroughs`

### Verifying the DB

```bash
python ingest.py --status
python verify_collection.py --show-sources
python verify_collection.py --show-sections
```

---

## Customizing the Interface

### Suggested questions (Explore Topics accordion)

Edit `CURATED_EXAMPLES` near the top of `app.py`:

```python
CURATED_EXAMPLES = {
    "Professional": [
        "What led you from cognitive science to AI engineering?",
        ...
    ],
    "Bridge": [...],
    "Personal": [...],
}
```

Three categories, three questions each. The accordion groups them with color-coded buttons
(`btn-professional`, `btn-bridge`, `btn-personal` in `custom_css`).

### Pinned example questions (below the chat input)

Edit the `examples` list in the `gr.ChatInterface` call in `app.py`. These always show
and are not part of the accordion:

```python
examples=["What problems does Barbara solve?", "Walk me through a project", ...]
```

### System prompt

Edit `SYSTEM_PROMPT.md` directly. It is loaded at startup by `app.py`. Changes take
effect on next app restart (or on next message in the admin app's ephemeral edit mode).

After significant prompt edits, run the eval harness to check for regressions:
```bash
cd evals && python run_evals.py --category recruiter --category friendly
```

---

## Adding a New Knowledge Base Document

1. Create a markdown file in `inputs/` using `##` H2 headers for sections (e.g. `inputs/kb_mynewtopic.md`)
2. Add an entry to the `SOURCES` list in `ingest.py` following the existing `kb-*` pattern
3. Update source priority rules in `SYSTEM_PROMPT.md` if needed
4. Embed it: `python ingest.py --source kb-mynewtopic`
5. Update `docs/CLAUDE.md` and this file

---

## Adding a New Tool

Tools extend the LLM's capabilities via function calling (e.g. Pushover notifications, dice roll).

1. Define the Python function in `app.py`
2. Add a function descriptor to the `tools` list
3. Add a handler case in `handle_tool_call()`
4. Update `SYSTEM_PROMPT.md` with behavioral guidance for when to use the tool
5. Mirror the definition in `app_admin.py` (both files maintain their own tool lists)

---

## Deployment (Hugging Face Spaces)

1. Create a Space and set Secrets for `OPENAI_API_KEY` and any optional vars
2. Deploy `app.py`, `requirements.txt`, `inputs/`, `assets/`, and the pre-built `.chroma_db_DT/`
3. On cold start, if `.chroma_db_DT/` is missing, the app pulls from HF Hub; if that fails,
   it runs `ingest.py --all` from scratch (requires input files to be present)

Use `db_sync.py` to push a fresh local DB to HF Hub after a full re-ingest:

```bash
python db_sync.py push
```

---

## Evaluation

See `evals/EVAL_QUICKSTART.md` for the full guide. Quick reference:

```bash
cd evals
python run_evals.py              # Full run — ~$0.21, ~5 min
python run_evals.py --limit 10   # Smoke test
python run_evals.py --category recruiter
python analyze_evals.py          # Summarize latest results
python analyze_evals.py --export # Export CSV for manual grading
```

Run evals before every deployment and after any edit to `SYSTEM_PROMPT.md` or KB sources.

---

## Debugging Retrieval

**In the terminal**: `app.py` prints each retrieved chunk (source, section, text preview) on
every query when running locally.

**In the admin app**: the Chunks and Raw metadata inspector tabs show cosine similarity scores
and full chunk text for every query.

**Standalone tools**:

```bash
python ingest.py --source kb-biosketch --dry-run   # Preview section parsing
python verify_collection.py --show-sources          # Per-source chunk counts
python app_admin.py                                 # Semantic probe: "does the KB cover X?"
```

`chunk_inspector.py` is the most thorough local debugging tool. Run it after any re-ingest to
catch chunk quality problems before they affect production:

```bash
python chunk_inspector.py                              # Full audit: size distribution, tiny chunk detection, per-source breakdown
python chunk_inspector.py --tiny                       # Print full text of every chunk under 150 chars
python chunk_inspector.py --source kb-projects         # Audit one source only
python chunk_inspector.py --query "Resume Explorer architecture"  # Simulate retrieval for a query
python chunk_inspector.py --canonical                  # Run 8 standard test queries and show retrieval stats
python chunk_inspector.py --all-chunks --source kb-biosketch     # Dump every chunk in a source
```
