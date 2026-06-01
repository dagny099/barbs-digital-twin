---
title: Local Setup
tags:
  - developer
  - setup
---

# Local Setup

Everything you need to run the digital twin locally in about five minutes, plus optional services for the full production stack.

---

## Prerequisites

- Python 3.11+
- An OpenAI API key (`OPENAI_API_KEY`) — this is the only hard requirement
- (Optional) Anthropic, Google, or Ollama API keys for multi-provider LLM support
- (Optional) Neo4j credentials for hybrid retrieval (app falls back to ChromaDB without them)
- (Optional) Pushover API credentials for the notification tool

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/dagny099/barbs-digital-twin.git
cd barbs-digital-twin
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values. At minimum, set `OPENAI_API_KEY`.

See [Environment Variables](../reference/environment-variables.md) for the complete variable reference.

### 5. Run the app

```bash
python app.py
```

Open [http://localhost:7860](http://localhost:7860). The Gradio interface will load.

---

## Optional: Admin Interface

The admin interface provides a side-by-side chat + retrieval inspector, collection browser, and semantic probe. It runs on a separate port:

```bash
python app_admin.py   # http://localhost:7862 (or $ADMIN_PORT if set)
```

!!! note
    `app_admin.py` is intended for local development only. It is not included in the Hugging Face Spaces deployment.

---

## Optional: Neo4j Setup

The app defaults to ChromaDB if Neo4j credentials aren't configured. For full hybrid retrieval:

1. Create a Neo4j AuraDB instance (or run Neo4j locally)
2. Add credentials to `.env`:
   ```
   NEO4J_URI=neo4j+s://your-instance.databases.neo4j.io
   NEO4J_USERNAME=neo4j
   NEO4J_PASSWORD=your-password
   ```
3. Run the population script to build the graph:
   ```bash
   python scripts/populate_neo4j_graph.py
   ```
4. Embed sections into the Neo4j vector index:
   ```bash
   python scripts/embed_sections.py
   ```

---

## Validate Your Setup

Run the healthcheck script to confirm all external services are reachable:

```bash
python scripts/healthcheck.py

# Skip the Pushover notification send (credentials-only validation)
python scripts/healthcheck.py --checks env chroma

# Full end-to-end including a test Pushover notification
python scripts/healthcheck.py --notify
```

Checks covered: environment variables, OpenAI LLM (live completion), OpenAI embeddings, ChromaDB collection count, Pushover credentials. All pass in ~3 seconds.

---

## Running the Test Suite

```bash
.venv/bin/pytest tests/ -v
```

51 pure-logic unit tests, no API keys or network required. Completes in under a second. Run before any push to `main`.

See [Running Tests](running-tests.md) for what's covered and how the test isolation works.

---

## Project Structure

```
barbs-digital-twin/
├── app.py                    # Main Gradio app (public-facing, port 7860)
├── app_admin.py              # Admin/debug interface (local only, port 7862)
├── neo4j_utils.py            # Neo4j driver and query_neo4j_rag()
├── featured_projects.py      # Project walkthrough logic
├── utils.py                  # Shared text processing utilities
├── chunk_inspector.py        # ChromaDB chunk quality auditor
├── replay_retrieval.py       # Neo4j retrieval debugger
├── db_sync.py                # ChromaDB push/pull to HF Hub
├── SYSTEM_PROMPT.md          # LLM system prompt (loaded at runtime)
├── requirements.txt
├── inputs/
│   ├── kb_biosketch.md       # ⭐ Authoritative biographical content
│   ├── kb_*.md               # Other KB documents
│   └── project-summaries/    # One-page PDFs (20 projects)
├── scripts/
│   ├── ingest.py             # Master ingestion manager
│   ├── healthcheck.py        # External service validator
│   ├── analyze_logs.py       # Query log analytics
│   └── ...
├── tests/
│   └── test_pure_logic.py    # 51 unit tests
├── evals/
│   ├── run_evals.py
│   ├── analyze_evals.py
│   └── eval_questions.csv
└── docs/                     # Markdown source docs
```
