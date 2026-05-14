# Barbara's Digital Twin — Living Architecture Reference

> **Last reviewed:** 2026-05-13
> To refresh: re-run this prompt against the repo, or run `python scripts/generate_onepager.py` (planned).
> Configuration values shown below are the **code-level defaults**; override any via `.env` (see `.env.example`).

---

## What it is

A conversational AI digital twin of Barbara Hidalgo-Sotelo — a cognitive scientist and AI/ML engineer. Visitors ask questions and receive answers in Barbara's first-person voice, grounded in a structured knowledge base using retrieval-augmented generation (RAG). The system is production-deployed on Hugging Face Spaces and live at [barbhs.com](https://barbhs.com).

## Who it's for

- **Recruiters and hiring managers** wanting fast, source-grounded answers about Barbara's background.
- **Collaborators and developers** exploring her technical work.
- **Barbara herself** — the twin surfaces her writing and projects in a format that scales across many conversations.

---

## Architecture

### Data flow (end-to-end)

```
Visitor question
       │
       ▼
  Audience tier detection (public / personal / inner_circle)
       │
       ▼
  OpenAI embedding  →  ChromaDB vector search  →  top-N chunks
  (text-embedding-3-small)    (.chroma_db_DT)     (N_CHUNKS_RETRIEVE=10)
       │
       ▼
  System prompt + retrieved context + conversation history
       │
       ▼
  LiteLLM completion  →  optional tool call  →  streamed reply
  (LLM_MODEL=gpt-4.1)   (Pushover / dice)
       │
       ▼
  JSONL query log  +  thumbs-up/down vote capture
```

### Tech stack

| Layer | Technology | Notes |
|---|---|---|
| UI | Gradio `ChatInterface` | Custom CSS (IBM Plex Sans, warm/teal palette, dark mode) |
| Embeddings | OpenAI `text-embedding-3-small` | Fixed; used at ingest and query time |
| Vector store | ChromaDB (persistent) | Collection `barb-twin`, path `.chroma_db_DT` |
| LLM completions | LiteLLM (multi-provider) | Default `gpt-4.1`; supports OpenAI, Anthropic, Google, Ollama |
| Tool calling | OpenAI function-calling API | Pushover notifications, dice rolls |
| DB sync | HuggingFace Hub dataset | `dagny099/digital-twin-db`; auto-pull on startup if missing |
| Deployment | HuggingFace Spaces | `SPACE_ID` env var; also runs locally on `PORT=7860` |
| Analytics | Google Analytics (GA4) | Injected into Gradio `head` |
| Logging | JSONL (`query_log.jsonl`) | Per-query: model, cost, session, thumbs vote, owner flag |

### Configuration defaults

All values are overridable via `.env` without code changes.

| ENV variable | Default | Effect |
|---|---|---|
| `LLM_MODEL` | `gpt-4.1` | Chat completion model (LiteLLM prefix optional for OpenAI) |
| `LLM_TEMPERATURE` | `0.7` | Completion temperature across app, admin, and evals |
| `N_CHUNKS_RETRIEVE` | `10` | Chunks returned per query; also used by evals and chunk_inspector |
| `MAX_HISTORY_MESSAGES` | `14` | Conversation turns sent to the LLM (7 user + 7 assistant) |
| `SHOW_SETTINGS_PANEL` | `false` | Shows model/temp/top-k sliders in UI (dev only) |
| `PORT` | `7860` | Local server port (ignored on HF Spaces) |
| `PUSHOVER_USER/TOKEN` | _(blank)_ | Enables visitor-to-Barbara push notifications |
| `CHUNK_SIZE` | `900` | Target chunk size in chars at ingest time (paragraph boundaries respected) |
| `CHUNK_OVERLAP` | `100` | Overlap between consecutive chunks in chars at ingest time |

> **Ingest-time only:** `CHUNK_SIZE` and `CHUNK_OVERLAP` only take effect when re-embedding. Changing them requires a force re-ingest (`python scripts/ingest.py --all --force`) to apply to the live knowledge base. Atomic unit is always paragraph (double-newline); chunks never split mid-sentence.

---

## Features in production

### Sensitivity gating
Three-tier content access control based on passphrase detection across the full conversation history:
- **public** — default; filtered to `sensitivity=public` chunks
- **personal** — unlocked by a shared phrase; adds personal content
- **inner_circle** — no filter; full knowledge base access

Implemented as ChromaDB `where` filters, not prompt-level rules. Tiers persist for the session once unlocked.

### Multi-provider LLM support
LiteLLM routes completions to OpenAI, Anthropic, Google, or local Ollama models. The `SHOW_SETTINGS_PANEL` flag exposes a model dropdown in the UI for development; in production the model is fixed via env.

### Tool calling
Two tools are registered when the model supports function calling:
- **`send_notification`** — sends a Pushover push to Barbara's phone when a visitor flags a knowledge gap or requests contact
- **`dice_roll`** — demo tool for testing the tool-calling pipeline

### Project walkthrough mode
When a visitor mentions a known project by name, the system automatically injects a structured walkthrough context block (including diagram path) into the retrieval context. Managed by `featured_projects.py`.

### Knowledge base auto-bootstrap
On startup, if `.chroma_db_DT/` is missing, the app pulls the tarball from HF Hub (`dagny099/digital-twin-db`) and extracts it. If still empty, it triggers a full `ingest.py --all` run and pushes the result back. Ensures zero-config cold starts.

### Observability
Every query is logged to `query_log.jsonl` with: timestamp, session ID, question (redacted if sensitive), model, temperature, token cost (USD), chunks retrieved, tool calls, walkthrough triggered, thumbs vote, and an owner-traffic flag. The `dashboard/app.py` and `analytics/` modules process this log.

### Admin app
`app_admin.py` is a separate Gradio app (port `ADMIN_PORT=7862`, HTTP basic auth) with the settings panel always enabled, giving full multi-provider access for testing.

---

## Knowledge base

Sixteen source types, all embedded into the same ChromaDB collection.

| Source type | Script | Content |
|---|---|---|
| KB documents (13 files) | `embed_kb_doc.py` | Biosketch, philosophy, positioning, career, projects, publications, answer bank, origin stories, easter eggs, dissertation series, intellectual foundations |
| Project summaries | `embed_project_summaries.py` | One-page PDFs in `inputs/project-summaries/` |
| Project walkthroughs | `embed_walkthroughs.py` | Structured walkthrough contexts from `featured_projects.py` |
| Jekyll website | `embed_jekyll.py` | Live content from barbhs.com via sitemap |

KB documents are parsed into named sections (by `## H2` headers) before chunking. Each chunk carries `source`, `chunk_index`, and `sensitivity` metadata for filtering.

---

## On the roadmap

**Neo4j migration** (`docs/NEO4J_MIGRATION_PLAN_2026-05-11.md`): Replace ChromaDB with a graph-backed store to improve granularity, cross-entity connections, and ranking. Currently in planning/prototype phase. When this ships, update the Vector store row above and the chunking section.

---

---

## How to Run

### Prerequisites

- Python 3.11+
- `OPENAI_API_KEY` set in `.env` (required)
- Optional: `PUSHOVER_USER`, `PUSHOVER_TOKEN`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`

```bash
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

### Local

```bash
python app.py
# Opens at http://localhost:7860
```

### Admin app (development)

```bash
python app_admin.py
# Opens at http://localhost:7862 (HTTP basic auth, set ADMIN_USER/ADMIN_PASSWORD)
```

### Analytics dashboard

```bash
bash scripts/run_dashboard.sh
# or: python dashboard/app.py
```

### HuggingFace Spaces

Push to the `main` branch. HF Spaces builds and serves automatically.
The app pulls the ChromaDB tarball from `dagny099/digital-twin-db` on startup (requires `HF_TOKEN`).

---

## How to Ingest

`scripts/ingest.py` is the master orchestrator. It shows a live status table of all sources and their chunk counts before taking any action.

### Interactive (recommended)

```bash
python scripts/ingest.py
```

Presents a numbered menu. Select a source, then choose: embed (skip existing), force re-embed, or dry-run.

### Non-interactive (CI / automation)

```bash
# Show DB status without embedding
python scripts/ingest.py --status

# Embed all sources (skip already-embedded)
python scripts/ingest.py --all

# Force re-embed everything from scratch
python scripts/ingest.py --all --force

# Embed one source
python scripts/ingest.py --source kb-biosketch
python scripts/ingest.py --source kb-biosketch --force

# Preview what would be chunked (no API calls)
python scripts/ingest.py --source kb-projects --dry-run
```

### Source keys

```
kb-biosketch  kb-philosophy  kb-positioning  kb-projects  kb-career
kb-publications  kb-answers  kb-origins  kb-easter-eggs
kb-dissertation-overview  kb-dissertation-relevance  kb-dissertation-philosophy
kb-intellectual-foundations
project-summaries  project-walkthroughs  jekyll
```

After a successful `--all` run, `ingest.py` automatically calls `db_sync.push_db()` to upload the updated tarball to HF Hub.

To wipe and rebuild from scratch:

```bash
python scripts/clear_collection.py
python scripts/ingest.py --all
```

---

## How to Evaluate

The offline eval harness tests single-turn Q&A against the current KB and prompt. Best used for regression checks after KB edits, prompt changes, or model swaps.

### Quick check (10 questions)

```bash
python evals/run_evals.py --limit 10
python evals/analyze_evals.py
```

### Full suite

```bash
python evals/run_evals.py
python evals/analyze_evals.py --export --output evals/eval_results/latest_review.csv
```

### By category

```bash
python evals/run_evals.py --category bio
python evals/run_evals.py --category projects
python evals/run_evals.py --category technical
```

### Key files

| File | Purpose |
|---|---|
| `evals/eval_questions.csv` | Question bank (richer schema: question_id, type, intent, audience_mode, difficulty, must_cover) |
| `evals/run_evals.py` | Runner — respects `LLM_MODEL`, `LLM_TEMPERATURE`, `N_CHUNKS_RETRIEVE` from env |
| `evals/analyze_evals.py` | Analysis and CSV export for human review |
| `evals/eval_results/*.json` | Saved run outputs |

### When to run

- After editing `SYSTEM_PROMPT.md`
- After adding or re-ingesting KB sources
- After changing model, temperature, or `N_CHUNKS_RETRIEVE`
- Before any production deployment

---

## How to Use chunk_inspector

`chunk_inspector.py` audits the ChromaDB collection and simulates retrieval without calling the LLM. Run it after any re-ingest to catch quality problems before the twin ever sees them.

### Full audit

```bash
python chunk_inspector.py
```

Reports: chunk size distribution, per-source breakdown, tiny-chunk flags (< 150 chars), and gap detection.

### Targeted audit

```bash
# One source only
python chunk_inspector.py --source kb-projects

# Show only problematic (tiny) chunks
python chunk_inspector.py --tiny

# Dump every chunk
python chunk_inspector.py --all-chunks
```

### Retrieval simulation

Embeds a query and shows the top-N chunks exactly as the LLM would see them:

```bash
python chunk_inspector.py --query "Resume Explorer architecture"
python chunk_inspector.py --query "beekeeping" --n 12
```

`--n` defaults to the value of `N_CHUNKS_RETRIEVE` in your `.env` (default: 10).

### What to look for

| Flag | Meaning |
|---|---|
| Tiny chunk (< 150 chars) | Orphaned paragraph; likely a header or stub — consider merging |
| Source with 0 chunks | Script may have failed silently — re-run with `--dry-run` to debug |
| Low chunk count for a large doc | Chunking may have split on wrong delimiter |
| Retrieval sim returns off-topic chunks | Embedding quality issue or metadata filter mismatch |
