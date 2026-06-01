---
title: Environment Variables
tags:
  - reference
  - configuration
---

# Environment Variables

All configuration is done via environment variables. Copy `.env.example` to `.env` and fill in your values. Only `OPENAI_API_KEY` is required to run the app.

---

## Required

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key — used for embeddings (`text-embedding-3-small`) and as the default LLM provider |

---

## LLM Configuration

| Variable | Default | Description |
|---|---|---|
| `LLM_MODEL` | `openai/gpt-4.1` | LiteLLM model string. Format: `provider/model-name`. See examples below. |
| `LLM_TEMPERATURE` | `0.6` | Generation temperature. Lower = more deterministic. Configurable via settings panel in dev mode. |
| `N_CHUNKS_RETRIEVE` | `10` | Number of chunks to retrieve (top-k). `fetch_k = N_CHUNKS_RETRIEVE × 4` for Neo4j pre-filtering. |

### LLM_MODEL examples

```bash
# OpenAI
LLM_MODEL=openai/gpt-4.1
LLM_MODEL=openai/gpt-4o

# Anthropic
LLM_MODEL=anthropic/claude-sonnet-4-5
LLM_MODEL=anthropic/claude-opus-4-5

# Google
LLM_MODEL=gemini/gemini-pro

# Ollama (local)
LLM_MODEL=ollama/llama3
```

---

## Multi-Provider API Keys

| Variable | Provider | Notes |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic (Claude models) | Optional — unlock Claude models in admin interface |
| `GEMINI_API_KEY` | Google (Gemini models) | Optional — unlock Gemini models in admin interface |

Ollama requires a local server running at the default port (`http://localhost:11434`). No API key needed.

---

## Retrieval Backend

| Variable | Default | Description |
|---|---|---|
| `RETRIEVAL_BACKEND` | `neo4j` | Which retrieval backend to use: `"neo4j"` (hybrid graph + vector) or `"chromadb"` (pure vector). Set in each deployment's `.env` — never hardcode. |

Both production deployments use the same codebase; the `.env` file on each server selects the backend:

- `graphy.twin.barbhs.com` → `RETRIEVAL_BACKEND=neo4j`
- `twin.barbhs.com` → `RETRIEVAL_BACKEND=chromadb`

!!! warning "No automatic fallback"
    There is no automatic fallback between backends. If `RETRIEVAL_BACKEND=neo4j` (the default) and Neo4j credentials are missing or the connection fails, the app will error. To use ChromaDB, set `RETRIEVAL_BACKEND=chromadb` explicitly.

---

## Neo4j

| Variable | Description |
|---|---|
| `NEO4J_URI` | Connection URI, e.g. `neo4j+s://your-instance.databases.neo4j.io` |
| `NEO4J_USERNAME` | Neo4j username (typically `neo4j`) |
| `NEO4J_PASSWORD` | Neo4j password |

Required when `RETRIEVAL_BACKEND=neo4j`. Not needed for ChromaDB-only deployments.

---

## UI & Behavior

| Variable | Default | Description |
|---|---|---|
| `SHOW_SETTINGS_PANEL` | `false` | Show model/temperature controls in the Gradio UI. Set to `true` for local dev; keep `false` in production for a clean UI. |
| `ADMIN_PORT` | `7862` | Port for the admin interface (`app_admin.py`) |

---

## Notifications (Pushover)

| Variable | Description |
|---|---|
| `PUSHOVER_TOKEN` | Pushover application token — enables the `send_notification` tool |
| `PUSHOVER_USER` | Pushover user/group key |

Without these, the notification tool is silently disabled. The app runs normally; `send_notification` tool calls will fail gracefully.

---

## Database Sync (Hugging Face Hub)

| Variable | Default | Description |
|---|---|---|
| `HF_TOKEN` | — | Hugging Face token for `db_sync.py` push/pull operations |
| `HF_REPO_ID` | `dagny099/barb-digital-twin-db` | HF Hub repo for ChromaDB backup/sync |

---

## ChromaDB

| Variable | Default | Description |
|---|---|---|
| `CHROMA_DB_PATH` | `.chroma_db_DT/` | Local path to ChromaDB persistent storage |

The collection name (`barb-twin`) is hardcoded in `app.py` and `scripts/healthcheck.py` and is not configurable via environment variable.
