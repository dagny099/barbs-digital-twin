# Digital Twin: Barbara Hidalgo-Sotelo

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Demo](https://img.shields.io/badge/demo-live-brightgreen.svg)
![RAG](https://img.shields.io/badge/architecture-RAG-orange.svg)
![LLM](https://img.shields.io/badge/LLM-multi--provider-purple.svg)

A conversational AI digital twin powered by RAG (Retrieval-Augmented Generation) that embodies Barbara Hidalgo-Sotelo's professional knowledge, project portfolio, and personal expertise. Built with Python, Gradio, ChromaDB, and multi-provider LLM support via LiteLLM.

## Overview

This digital twin serves as an intelligent interface to explore Barbara's professional background, technical projects, and expertise. It uses vector embeddings and semantic search to retrieve relevant context from multiple knowledge sources, then generates responses in Barbara's voice and personality.

**For Visitors**: Chat with the twin at [twin.barbhs.com](https://twin.barbhs.com)     
**For Developers**: Clone this repo to explore the RAG architecture, evaluation suite, and admin debugging tools

## Quick Start

Want to run it locally in 5 minutes?

1. Clone the repo: `git clone https://github.com/dagny099/digital-twin.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set `OPENAI_API_KEY` in `.env` (copy from `.env.example`)
4. Run: `python app.py`
5. Open http://localhost:7860

Full setup details below.

## Features

- **Multi-Source Knowledge Base**: Six structured KB documents (biosketch, philosophy, positioning, projects, career narrative, publications) plus one-page project PDFs and the live website
- **Semantic Search & RAG**: ChromaDB vector store with OpenAI embeddings for intelligent context retrieval
- **Section-Aware Ingestion**: Each data source is parsed into named sections, giving the LLM precise provenance for every retrieved chunk
- **Conversational Interface**: Gradio ChatInterface for natural conversations
- **Multi-Provider LLM Support**: Production app (app.py) supports OpenAI, Anthropic, Google, and Ollama models via LiteLLM with optional Settings panel (SHOW_SETTINGS_PANEL env toggle)
- **Tool Integration**: Function calling capabilities (notifications via Pushover, interactive features)
- **First-Person Perspective**: Responds as Barbara, maintaining her voice and personality
- **Production-Grade Logging**: Lightweight query logging (~16μs overhead) tracks model, latency, similarity scores, cost, and tokens for continuous improvement
- **Persistent Memory**: ChromaDB enables incremental knowledge base updates without reprocessing
- **Ingestion Manager**: Single `ingest.py` script orchestrates all data sources with an interactive status-first menu

## Tech Stack

| Component | Technology |
|-----------|------------|
| **LLM** | Multi-provider support via LiteLLM (OpenAI, Anthropic, Google, Ollama)<br>Production default: OpenAI GPT-4.1-mini |
| **Embeddings** | OpenAI text-embedding-3-small (1536 dimensions) |
| **Vector Database** | ChromaDB (persistent local storage) |
| **UI Framework** | Gradio |
| **Language** | Python 3.11 |
| **Deployment** | AWS EC2 (primary), Hugging Face Spaces (secondary) |

## Architecture

```
User Query
    ↓
Gradio Interface
    ↓
Query Embedding (OpenAI)
    ↓
Semantic Search (ChromaDB) → Retrieve top 10 chunks
    ↓
Context + System Prompt + Query → LLM
    ↓
[Optional] Tool Calls (notifications, dice roll)
    ↓
Final Response (as Barbara)
```

### Data Processing Pipeline

1. **Chunking**: Text split into ~500-character chunks with 50-character overlap
2. **Embedding**: Each chunk embedded via OpenAI API
3. **Storage**: Chunks + embeddings + metadata stored in ChromaDB
4. **Retrieval**: Query embedded → top-k semantic search → context injection

## Prompt Engineering

The system prompt is a core architectural component, not an afterthought. `SYSTEM_PROMPT.md` is organized into 13 sections covering persona, voice consistency, narrative priorities, factual accuracy guardrails, and tool integration.

**Key Design Decisions**:
- **Structured sections**: Numbered sections make debugging and iteration easier
- **Explicit failure modes** (Section 13): Table of wrong vs. right responses prevents common errors
- **Source priority ordering** (Section 5): Knowledge base conflicts resolved deterministically
- **"I don't know" protocols** (Sections 8, 9): Uncertainty is acceptable; fabrication is not
- **Featured projects** (Section 4): Proactive surfacing without being spammy

**Design Philosophy**: The prompt balances authenticity (Barbara's actual voice), accuracy (source-based only), and utility (helpful without overpromising). Each section addresses a specific failure mode observed during development and eval testing.

**Validation**: The 92-question evaluation suite (see `evals/`) tests adherence to these guidelines across 8 categories.

[View the full system prompt →](SYSTEM_PROMPT.md) | [Read the design rationale →](PROMPT_DESIGN.md)

## Installation & Setup

### Prerequisites

- Python 3.11+
- OpenAI API key
- (Optional) Pushover API credentials for notifications

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/dagny099/barbs-digital-twin.git my-digital-twin
cd my-digital-twin
```

2. **Create and activate virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set environment variables**

Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

At minimum, `OPENAI_API_KEY` is required. All other variables have working defaults or are optional. See `.env.example` for the full list with descriptions.

5. **Run the application**
```bash
python app.py
```

The Gradio interface will launch at `http://localhost:7860`


## Project Structure

```
digital-twin/
├── app.py                              # Main Gradio application (public-facing)
├── app_admin.py                        # Admin/debug interface (local only, port 7861)
├── featured_projects.py                # Project walkthrough logic and diagram serving
├── ingest.py                           # Master ingestion manager (start here)
├── embed_kb_doc.py                     # Generic: embed any inputs/kb_*.md document
├── embed_project_summaries.py          # Embed one-page project summary PDFs
├── embed_jekyll.py                     # Embed Jekyll website via sitemap
├── db_sync.py                          # Push/pull ChromaDB to/from HF Hub
├── utils.py                            # Shared text processing utilities
├── chunk_inspector.py                  # Audit chunk quality and simulate retrieval
├── verify_collection.py                # Inspect ChromaDB contents
├── clear_collection.py                 # Wipe ChromaDB collection
├── requirements.txt                    # Python dependencies
├── SYSTEM_PROMPT.md                    # LLM system prompt (loaded by app.py)
├── inputs/
│   ├── kb_biosketch.md                 # Biographical sketch  ⭐ authoritative
│   ├── kb_philosophy-and-approach.md   # Working philosophy and meaning-making
│   ├── kb_professional_positioning.md  # Positioning, differentiators, value prop
│   ├── kb_projects.md                  # Project portfolio registry
│   ├── kb_career_narrative.md          # Career story and trajectory
│   ├── kb_publications.md             # Research papers and academic work
│   └── project-summaries/             # One-page PDF summaries (20 projects)
├── archive/                            # Retired embed scripts (kept for reference)
│   ├── embed_biosketch.py             # Replaced by embed_kb_doc.py
│   ├── embed_resume.py                # Resume retired from KB (V2)
│   └── embed_publications.py          # Replaced by embed_kb_doc.py
├── inputs/OLD/                         # Retired source documents
│   ├── Hidalgo-Sotelo_Barbara_RESUME_AI-Engineering_2026.txt
│   ├── barbara-hidalgo-sotelo-biosketch.md
│   └── (GitHub READMEs and other retired sources)
├── .chroma_db_DT/                      # ChromaDB vector store (gitignored)
├── .venv/                              # Virtual environment (gitignored)
└── README.md                           # This file
```

## Knowledge Base Management

### Ingestion Manager (`ingest.py`)

The recommended way to manage all data sources. Run it with no arguments for an interactive menu that shows current DB status before asking you to do anything:

```bash
python ingest.py
```

The menu displays a live status table — chunk counts per source, so you can see at a glance what's embedded and what isn't:

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

Select a source by number → choose "Embed", "Force re-embed", or "Dry run".

**Non-interactive flags** (for scripting or CI/CD):
```bash
python ingest.py --status                              # Show DB status and exit
python ingest.py --all                                 # Embed all sources
python ingest.py --all --force                         # Force re-embed everything
python ingest.py --source kb-biosketch                 # Embed one source
python ingest.py --source kb-biosketch --force         # Force re-embed one source
python ingest.py --source project-summaries --dry-run  # Preview without embedding
```

**Source keys**: `kb-biosketch`, `kb-philosophy`, `kb-positioning`, `kb-projects`, `kb-career`, `kb-publications`, `project-summaries`, `jekyll`

### Checking DB Contents

```bash
python ingest.py --status                          # Quick chunk counts per source
python verify_collection.py                        # Detailed stats + sample chunks
python verify_collection.py --show-sources         # Per-source breakdown
python verify_collection.py --show-sections        # All unique section names
```

### Wiping the DB

```bash
python clear_collection.py                         # Interactive confirmation required
```

---

## Data Sources

The knowledge base uses **section-aware metadata** so the LLM knows exactly where each retrieved chunk came from within a document.

### Metadata Schema
```python
{
    'source': 'source-type:identifier',  # e.g., 'kb-biosketch:kb_biosketch.md'
    'section': 'Section Name' or None,   # e.g., 'Professional Experience', 'Published Papers'
    'chunk_index': 0                     # position within section (resets per section)
}
```

### 1. KB: Biosketch (Authoritative) ⭐
- **File**: `inputs/kb_biosketch.md`
- **Source key**: `kb-biosketch`
- **Priority**: Highest — source of truth for identity, background, values, personality
- **Parsing**: Markdown `##` headers → named sections (all handled by `embed_kb_doc.py`)
- **Wins over**: all other sources in any conflict

### 2. KB: Philosophy & Approach
- **File**: `inputs/kb_philosophy-and-approach.md`
- **Source key**: `kb-philosophy`
- **Content**: How Barbara thinks about data, meaning-making, her father's influence, and what good work looks like

### 3. KB: Professional Positioning
- **File**: `inputs/kb_professional_positioning.md`
- **Source key**: `kb-positioning`
- **Content**: What sets Barbara apart, the cognitive science angle, the knowledge engineering angle, the four problems she solves

### 4. KB: Project Portfolio
- **File**: `inputs/kb_projects.md`
- **Source key**: `kb-projects`
- **Content**: Registry of all major projects with tech stack, deployment status, and cross-project connections

### 5. KB: Career Narrative
- **File**: `inputs/kb_career_narrative.md`
- **Source key**: `kb-career`
- **Content**: Career arc told as a story — five chapters from MIT through independent GenAI work

### 6. KB: Publications & Research
- **File**: `inputs/kb_publications.md`
- **Source key**: `kb-publications`
- **Content**: Academic papers, conference posters, and dissertation with PDF links

> All six KB documents above use `embed_kb_doc.py` — the same parsing logic (`##` headers → sections → `chunk_prose`).

### 7. Project Summaries
- **Folder**: `inputs/project-summaries/` (one-page PDFs)
- **Source key**: `project-summaries`
- **Content**: Curated one-pagers following a consistent template: What it is / Who it's for / What it does / How it works
- **Parsing**: Template-aware section detection (fuzzy prefix matching on known section labels)
- **Special**: Each document also gets a synthetic "overview" chunk combining the title + What it is + Who it's for, optimized for portfolio-style queries
- **Metadata extras**: `project_name`, `tech_stack` (comma-joined list of detected technologies)

### 8. Jekyll Website
- **URL**: `https://barbhs.com` (fetched live via sitemap.xml)
- **Source key**: `jekyll`
- **Tool**: `trafilatura` for main-content extraction (strips nav/footer automatically)
- **Parsing**: Page title used as section name; each page is one document

### 9. Project Walkthroughs
- **Source**: `featured_projects.py` (the `walkthrough_context` field of each featured project)
- **Source key**: `project-walkthroughs`
- **Script**: `embed_walkthroughs.py`
- **Content**: One chunk per featured project — title + summary + walkthrough notes + tags — enabling normal RAG to surface this content without triggering walkthrough mode
- **Metadata**: `project_name`, `section="walkthrough"`, `char_count`

## Shared Utilities (utils.py)

The project uses a centralized `utils.py` module to eliminate code duplication:

### Core Functions
- **`chunk_prose()`**: Paragraph-aware text chunking with overlap
- **`parse_paragraphs()`**: Split text on blank lines
- **`parse_sections_by_delimiter()`**: Parse TXT files by delimiter (e.g., `======`)
- **`parse_markdown_sections()`**: Parse markdown files by headers (e.g., `##`)
- **`build_metadata()`**: Construct standardized metadata dicts
- **`delete_chunks_by_source()`**: Wipe all chunks for a given source prefix (used by `--force-reembed`)
- **`section_already_embedded()`**: Per-section idempotency check (skip if already stored)

All ingestion scripts import from `utils.py` to ensure consistent chunking behavior across all sources.

## Chunking Strategy

- **Chunk Size**: ~500 characters (configurable)
- **Overlap**: 50 characters (configurable)
- **Atomic Unit**: Paragraphs (double-newline delimited)
- **Principle**: Never split mid-sentence; overlap re-includes trailing paragraphs
- **chunk_index semantics**: Resets to 0 for each section (not global)

This approach balances:
- Semantic coherence (paragraphs as natural units)
- Retrieval granularity (500 chars ≈ 1-2 paragraphs)
- Context continuity (overlap prevents boundary issues)
- Section awareness (chunks know their parent section)

## Deployment

Both deployments are automated via GitHub Actions and trigger on every push to `main`.

### EC2 (primary)

The app runs as a `systemd` service on an AWS EC2 instance (Amazon Linux 2). On push to `main`, GitHub Actions SSHes in, pulls the latest code, installs dependencies, restarts the service, and smoke-tests the endpoint.

**Required GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|--------|-------|
| `EC2_HOST` | Public IP or hostname |
| `EC2_USER` | `ec2-user` |
| `EC2_SSH_KEY` | Private key of the dedicated deploy keypair |
| `EC2_APP_DIR` | Path to app on instance (e.g. `/home/ec2-user/barbs-digital-twin`) |
| `EC2_SERVICE_NAME` | systemd service name (e.g. `digital-twin`) |

See `.github/workflows/deploy-ec2.yml` for the full setup guide including keypair generation, sudoers configuration, and the systemd unit file template.

### Hugging Face Spaces (secondary)

Still active. On push to `main`, GitHub Actions syncs app code and input data to the HF Space repo. ChromaDB is ephemeral on HF Spaces — the app rebuilds it from scratch on container restart.

**Required GitHub Secret**: `HF_TOKEN`

See `.github/workflows/deploy-hf.yml` for details.

## Admin Interface

A developer-focused debug interface that runs alongside the main app:

```bash
python app_admin.py   # http://localhost:7862
```

**Shared features** (also in `app.py` when `SHOW_SETTINGS_PANEL=true`):
- **Multi-provider model switching** — compare OpenAI, Anthropic, Google, and Ollama models via LiteLLM
- **Adjustable top-k and temperature** — experiment without code changes
- **Session cost tracking** — running token count and USD cost across the session

**Admin-only features**:
- **Side-by-side chat + retrieval inspector** — see every retrieved chunk with cosine similarity scores
- **Collection browser** — browse, filter, and text-search all ~500 chunks in the knowledge base
- **Semantic probe** — embed any query and rank the entire collection to check KB coverage
- **Separate logging** — `query_log_admin.jsonl` for experimentation without corrupting production analytics

Set your provider API keys in `.env` (`ANTHROPIC_API_KEY`, `GEMINI_API_KEY`) to unlock non-OpenAI models. Ollama requires a local server at the default port. Note that LiteLLM model names require a provider prefix (e.g. `openai/gpt-4.1`, `anthropic/claude-sonnet-4-5`).

**Production tip:** Keep `SHOW_SETTINGS_PANEL=false` in production for a clean UI. Enable it locally for development and testing.

`app_admin.py` is not included in the HF Spaces deployment and is intended for local development only.

## Evaluation

The project includes an offline evaluation harness for systematically testing response quality. See `EVAL_QUICKSTART.md` for the 5-minute getting started guide and `EVAL_WORKFLOW.md` for full documentation.

### Two-axis question design

**92 seed questions** in `eval_questions.csv` organized around two perspectives:

| Type | Categories | Purpose |
|------|------------|---------|
| **Coverage** | `bio`, `projects`, `technical`, `personality`, `tool`, `publication` | Does the system retrieve and answer correctly? Run after knowledge base changes. |
| **Visitor** | `recruiter`, `friendly` | Does the system satisfy real visitors? Simulates recruiter and casual visitor perspectives. |

### Quick commands

```bash
# Full evaluation (~$0.21, ~5 min)
python run_evals.py

# Coverage check after re-embedding (run each separately)
python run_evals.py --category bio
python run_evals.py --category publication

# Visitor experience check after prompt changes
python run_evals.py --category recruiter
python run_evals.py --category friendly

# Analyze and export for manual grading
python analyze_evals.py --export
```

## Roadmap

- [ ] **Multi-modal support**: Integrate image understanding for project screenshots
- [ ] **Citation tracking**: Return source documents with responses
- [ ] **Conversation memory**: Implement session-based memory across conversations
- [ ] **Voice interface**: Add speech-to-text/text-to-speech capabilities
- [ ] **Fine-tuning**: Train a custom model on Barbara's writing style
- [ ] **Knowledge graph integration**: Neo4j backend for relationship-rich queries
- [ ] **Automated updates**: GitHub Actions to re-embed on repo changes
- [x] **Evaluation suite**: 91-question offline eval harness across 8 categories (see `EVAL_QUICKSTART.md`)
- [x] **Multi-provider LLM support**: OpenAI, Anthropic, Google, Ollama via LiteLLM with cost tracking
- [x] **Production-grade logging**: Query analytics with <16μs overhead for continuous improvement (see `LOGGING_GUIDE.md`, `ADMIN_LOGGING_GUIDE.md`)

## Key Design Decisions

### Why ChromaDB?
- **Persistent storage**: No re-embedding on restart
- **Lightweight**: Runs locally without external dependencies
- **Python-native**: Seamless integration with OpenAI SDK
- **Metadata filtering**: Supports source-based filtering and priority rules

### Why multi-provider support (with GPT-4.1-mini as default)?
- **Flexibility**: Test OpenAI, Anthropic, Google, and Ollama models without code changes
- **Cost optimization**: Admin interface enables data-driven model selection via ROI analysis
- **Provider resilience**: Swap providers if one experiences downtime or pricing changes
- **GPT-4.1-mini default**: Cost-effective, fast, tool-calling support, sufficient for RAG + personality
- **Local development**: Settings panel (`SHOW_SETTINGS_PANEL=true`) for experimentation; hidden in production

### Why 500-character chunks?
- **Context window**: Fits 3 chunks comfortably in context with room for conversation
- **Semantic unit**: Aligns with paragraph-level ideas
- **Retrieval quality**: Small enough for precision, large enough for coherence

## Contributing

This is a personal project, but suggestions and ideas are welcome! Feel free to:
- Open issues for bugs or feature requests
- Submit PRs for improvements (especially documentation)
- Fork the repo to create your own digital twin

## License

This project is open-source under the MIT License. See `LICENSE` file for details.

The biographical content and project descriptions are © Barbara Hidalgo-Sotelo. Reuse of the *code/architecture* is encouraged; reuse of the *personal content* should be adapted to your own story.

## Contact & Links

- **LinkedIn**: [barbara-hidalgo-sotelo](https://www.linkedin.com/in/barbara-hidalgo-sotelo)
- **Personal Site**: [barbhs.com](https://www.barbhs.com/)
- **GitHub**: [dagny099](https://github.com/dagny099)
- **Google Scholar**: [Barbara Hidalgo-Sotelo](https://scholar.google.com/citations?hl=en&user=nQG25vkAAAAJ)

---

**Built with curiosity, engineered with precision.**
*"I can, I will, and I shall!"* - Barbara's mantra
